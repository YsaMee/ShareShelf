"""Bridge between Django and the Prolog rules in rules.pl.

Each call starts SWI-Prolog, sends the facts it needs on standard input, runs
one query and reads the answer back. Python never decides what matches, which
status change is allowed or whether borrowing dates are valid: it asks Prolog.
"""

import os
import shutil
import subprocess
from pathlib import Path

RULES = Path(__file__).with_name("rules.pl")
TIMEOUT_SECONDS = 10

# Where SWI-Prolog usually lives when it isn't on PATH (the Windows installer
# doesn't add it by default).
_FALLBACK_PATHS = (
    r"C:\Program Files\swipl\bin\swipl.exe",
    r"C:\Program Files (x86)\swipl\bin\swipl.exe",
    "/Applications/SWI-Prolog.app/Contents/MacOS/swipl",
    "/opt/homebrew/bin/swipl",
    "/usr/local/bin/swipl",
    "/usr/bin/swipl",
)


class PrologUnavailable(RuntimeError):
    """SWI-Prolog isn't installed, couldn't be run, or the query failed."""


def swipl_path():
    """The SWI-Prolog program to run: $SWIPL_PATH, then PATH, then the usual install folders."""
    configured = os.environ.get("SWIPL_PATH")
    if configured:
        return configured
    return shutil.which("swipl") or next((p for p in _FALLBACK_PATHS if Path(p).exists()), None)


# ---------- Turning Python values into Prolog terms ----------


def atom(text):
    """A quoted Prolog atom that is safe for any text: Gently Used -> 'Gently Used'."""
    return "'" + str(text).replace("\\", "\\\\").replace("'", "\\'") + "'"


def boolean(value):
    return "true" if value else "false"


def day(value):
    """Dates become day numbers so Prolog can compare them as integers."""
    return str(value.toordinal())


def item_fact(item):
    return (
        f"item({item.pk}, {item.owner_id}, {item.listing}, {atom(item.category)}, "
        f"{atom(item.condition)}, {item.qty}, {boolean(item.paused)})."
    )


def wanted_fact(shelf_request):
    return (
        f"wanted({shelf_request.pk}, {shelf_request.requester_id}, "
        f"{atom(shelf_request.category)}, {atom(shelf_request.preference)})."
    )


def lent_fact(shelf_request):
    return f"lent({shelf_request.pk}, {day(shelf_request.return_by)})."


# ---------- Running a query ----------


def _query(goal, facts=()):
    exe = swipl_path()
    if not exe:
        raise PrologUnavailable(
            "SWI-Prolog not found. Install it from https://www.swi-prolog.org/download/stable "
            "or set SWIPL_PATH to the full path of swipl."
        )
    program = "\n".join(facts) + "\n"
    try:
        result = subprocess.run(
            [
                exe, "-q",
                "-g", "set_stream(user_input, encoding(utf8))",
                "-g", "consult(user)",
                "-g", goal,
                "-t", "halt",
                str(RULES),
            ],
            input=program,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrologUnavailable(f"Couldn't run SWI-Prolog: {exc}") from exc
    if result.returncode != 0:
        raise PrologUnavailable(f"Prolog query failed: {result.stderr.strip()}")
    return result.stdout.split()


# ---------- The questions Django asks ----------


def find_matches(items, open_requests):
    """Every (request id, item id) pair that the matches/2 rule proves."""
    facts = [item_fact(item) for item in items] + [wanted_fact(r) for r in open_requests]
    if not facts:
        return []
    words = _query("print_matches", facts)
    return [(int(r), int(i)) for r, i in zip(words[::2], words[1::2])]


def is_match(item, shelf_request):
    return (shelf_request.pk, item.pk) in find_matches([item], [shelf_request])


def allowed_qty(shelf_request, role, target, item=None):
    """The item's stock after the step, or None if the step isn't allowed.

    role is "seeker" or "sharer". Requests without an item (open requests)
    are checked with a stock of 0.
    """
    kind = "lend" if shelf_request.is_lend else "give"
    qty = item.qty if item else 0
    paused = item.paused if item else False
    goal = f"print_allowed({kind}, {role}, {shelf_request.status}, {target}, {qty}, {boolean(paused)})"
    answer = _query(goal)
    return None if answer == ["no"] else int(answer[0])


def loan_problems(limit_days, start, return_by, today):
    """Why the proposed borrowing dates don't work (e.g. ["too_long"]); empty if they're fine."""
    goal = f"print_loan_problems({int(limit_days or 0)}, {day(start)}, {day(return_by)}, {day(today)})"
    return _query(goal)


def find_overdue(lent_requests, today):
    """Ids of lent requests whose return date has passed."""
    facts = [lent_fact(r) for r in lent_requests if r.return_by]
    if not facts:
        return set()
    return {int(word) for word in _query(f"print_overdue({day(today)})", facts)}
