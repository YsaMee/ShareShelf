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

- A Python version supported by Django 6.1.
- SWI-Prolog, required for matching and request/lending rules. See [docs/prolog.md](docs/prolog.md).
- A database configured with `DATABASE_URL` (the project uses `dj-database-url` and includes PostgreSQL support).
- SMTP credentials for password-reset email.

## Setup

From the project root, create and activate a virtual environment, then install the Python packages:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root. Set values for your own environment; do not commit credentials:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
EMAIL_HOST_USER=your-smtp-account@example.com
EMAIL_HOST_PASSWORD=your-smtp-password
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
