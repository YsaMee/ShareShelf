# ShareShelf backend

ShareShelf is a campus item-sharing app built with Django and SWI-Prolog. Students can list items to give away or lend, browse and request items, arrange handoffs, and track lending returns.

## Features

- Create an account with a `.edu.ph` email and manage a student profile.
- Post items to give away or lend, with category, condition, quantity, location, and (for lending) a maximum lending period.
- Search and filter classmates' active listings.
- Post item requests and see suggested matches.
- Accept or decline requests, arrange meetups, confirm handoffs, and mark lent items returned.
- Track listings, requests, incoming activity, and overdue lent items on the dashboard.
- Reset a forgotten password by email.

## Requirements

- Python 3.12 or newer (required by Django 6.1).
- SWI-Prolog, required for matching and request/lending rules. See [docs/prolog.md](docs/prolog.md).
- A PostgreSQL database configured with `DATABASE_URL`. Ask a teammate for the team's shared database URL.
- SMTP credentials for password-reset email.

## Setup

Open PowerShell normally (not as administrator), go to the project folder, then create and activate a virtual environment and install the Python packages:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If activation fails with "running scripts is disabled on this system", allow scripts for your account once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Create a `.env` file in the project root (for example with `notepad .env`). Set values for your own environment; do not commit credentials:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
EMAIL_HOST_USER=your-smtp-account@example.com
EMAIL_HOST_PASSWORD=your-smtp-password
```

The database connection requires SSL by default. To use a local PostgreSQL without SSL, add:

```dotenv
DATABASE_SSL=False
```

To try the app offline without PostgreSQL, use a local SQLite file instead (it starts empty, not with the team's data):

```dotenv
DATABASE_URL=sqlite:///db.sqlite3
DATABASE_SSL=False
```

For a local SWI-Prolog install outside the usual locations or system `PATH`, add its full executable path:

```dotenv
SWIPL_PATH=C:\Program Files\swipl\bin\swipl.exe
```

Apply database migrations and start Django:

```powershell
python manage.py migrate
python manage.py runserver
```

Open the local address printed by `runserver` in a browser. Django checks for SWI-Prolog at startup; if it cannot find it, install it or configure `SWIPL_PATH`.

Each time you work on the project, open a new PowerShell window in the project folder and run `.venv\Scripts\Activate.ps1` before any `python manage.py` command. After `git pull`, run `python manage.py migrate` in case a teammate changed the database.

### Common problems

| Error | Fix |
| --- | --- |
| `fatal: could not create work tree dir ...: Permission denied` | PowerShell is in a protected folder such as `C:\Windows\System32`. Run `cd "$HOME\Documents"` first. |
| `running scripts is disabled on this system` | Run the `Set-ExecutionPolicy` command above. |
| `ModuleNotFoundError` | The virtual environment isn't active (no `(.venv)` in the prompt). Run `.venv\Scripts\Activate.ps1`. |
| `settings.DATABASES is improperly configured` | Django can't read `DATABASE_URL`. Check that the file is named `.env`, not `.env.txt` (`Get-ChildItem -Force -Filter ".env*"`), then restart `runserver`: `.env` is only read at startup. |
| `shareshelf_app.E001` | SWI-Prolog isn't installed or can't be found. See [docs/prolog.md](docs/prolog.md). |

Never paste a full Django error page into chat or an issue: it shows your `.env` values and anything typed into forms.

## Project structure

| Path | Purpose |
| --- | --- |
| `config/` | Django project settings and URL configuration |
| `shareshelf_app/` | Django models, forms, views, templates, and static assets |
| `shareshelf_app/logic/rules.pl` | Prolog rules for matches, request transitions, lending dates, and overdue items |
| `shareshelf_app/logic/__init__.py` | Python interface between Django and SWI-Prolog |
| `docs/frontend.md` | Front-end pages, interactions, and template requirements |
| `docs/backend.md` | Back-end architecture, routes, models, and request handling |
| `docs/prolog.md` | Prolog rule reference and SWI-Prolog installation instructions |

## Documentation

- [Front end](docs/frontend.md)
- [Back end](docs/backend.md)
- [SWI-Prolog rules](docs/prolog.md)

## Security note

The checked-in settings are intended for development. Before deployment, configure a unique secret key, set `DEBUG=False`, restrict `ALLOWED_HOSTS`, and use production database and email credentials.
