# ShareShelf rules in Prolog

ShareShelf's matching and request rules are written in Prolog
(`shareshelf_app/logic/rules.pl`) and run with SWI-Prolog. Django never decides
these things itself: it sends Prolog the facts and asks.

| Rule in `rules.pl` | What it decides | Used by |
| --- | --- | --- |
| `matches(Request, Item)` | Which give-away items match an open request (same category, someone else's, available, and the condition the seeker wants) | "Possible matches" on the dashboard, "Ask for this" |
| `allowed(Kind, Role, From, To, Qty, Paused, NewQty)` | Who may move a request to which status, and what happens to the item's stock | Accept, decline, hand over, confirm, mark returned, cancel |
| `loan_problem(LimitDays, From, ReturnBy, Today, Problem)` | What's wrong with a borrower's dates: start in the past, return not after start, longer than the lending limit | The borrow form on lent items |
| `overdue(Request, Today)` | Which loans are past their return date | The "overdue" warnings on the dashboard |

`shareshelf_app/logic/__init__.py` is the bridge. It turns Django objects into
Prolog facts, runs one query with SWI-Prolog, and reads the answer back.

## Install SWI-Prolog (everyone who runs the app)

The app won't start without it: `runserver` stops with `shareshelf_app.E001`.

**Windows**
1. Download the 64-bit installer from https://www.swi-prolog.org/download/stable
2. Run it with the default options. ShareShelf looks in
   `C:\Program Files\swipl\bin\` automatically, so you don't need to add it to PATH.

**Mac:** `brew install swi-prolog`

**Linux:** `sudo apt install swi-prolog-nox`

If you installed it somewhere else, set `SWIPL_PATH` to the full path of
`swipl` (or `swipl.exe`), for example in your `.env`.

## Run the tests

```
python manage.py test
```

The tests in `shareshelf_app/tests.py` run the real rules through SWI-Prolog.
They don't use the database, so they work without `DATABASE_URL`.

## Changing a rule

Edit `rules.pl`, then run the tests. For example, to let a seeker who asked for
"Gently Used" also accept "New" items, add one `meets/2` clause:

```prolog
meets('Gently Used', 'New').
```
