# ShareShelf back end

| Path | Function |
| --- | --- |
| `config/settings.py` | Django configuration: installed apps, middleware, templates, database, Manila time zone, static/media files, and email settings |
| `config/urls.py` | Named page and action routes; Django's built-in password-reset views and public legal pages |
| `shareshelf_app/models.py` | Database models for student profiles, item listings, and requests, including request status and meetup details |
| `shareshelf_app/forms.py` | Server-side validation for sign-in, sign-up, listings, requests, borrowing dates, meetups, profiles, and password changes |
| `shareshelf_app/views.py` | Page rendering and POST actions; checks access, updates records, and returns redirects or form errors |
| `shareshelf_app/logic/__init__.py` | Python bridge that passes facts to SWI-Prolog and turns its answers into matches, allowed status changes, date errors, or overdue IDs |
| `shareshelf_app/logic/rules.pl` | Prolog rules for matching, request transitions and stock changes, loan date limits, and overdue loans |
| `shareshelf_app/checks.py` | Django startup check that reports when SWI-Prolog is unavailable |
| `shareshelf_app/admin.py` | Registers profiles, items, and requests in Django admin |

## Data models

- **`UserProfile`** belongs one-to-one with Django's user account. It stores the student's full and display names, program, school, year level, bio, and pickup spot. Its `name`, `first_name`, and `initials` properties provide display-friendly values.
- **`Item`** belongs to an owner and stores the item name, give-away or lending type, quantity, category, condition, lending limit, pickup location, description, and paused state. Quantity is limited to 1–20.
- **`Request`** belongs to a requester and can be linked to an item. It stores the request details, condition preference, status, meetup information, and borrowing dates when applicable. Helper properties provide display labels, the other student's profile, and meetup text.

## Request flow

1. A view receives a page request or form submission. Login-protected views require an authenticated user; state-changing actions use POST.
2. Django forms validate submitted fields. Views also check ownership and current status before changing an item or request.
3. For matching, request transitions, stock changes, lending-date rules, and overdue checks, `views.py` calls `shareshelf_app.logic`.
4. The bridge sends the relevant facts to SWI-Prolog, runs the corresponding rule, and returns the result to Django. Django saves permitted changes and renders a page or redirects with a success or error message.

SWI-Prolog must be installed for the app's rules to run. The bridge checks `SWIPL_PATH`, then the system `PATH`, then common install locations. See [prolog.md](prolog.md) for installation and rule details.

## Main routes

| Name | Method | Function |
| --- | --- | --- |
| `login`, `signup` | GET/POST | Sign in or create a student account. Sign-up requires a `.edu.ph` email and a password with at least 8 characters, letters, and digits. |
| `logout` | POST | End the current session. |
| `dashboard` | GET | Show the student's listings, requests, incoming requests, matches, and overdue lending reminders. |
| `browse` | GET | Show other students' active items; accepts `q`, `category`, and `mode=give|lend` filters. |
| `item_detail` | GET | Show an item's details and request or borrow options. |
| `post_item`, `post_request` | POST | Create an item listing or an open request. |
| `request_item` | POST | Request a give-away item or submit borrowing dates for a lent item; can attach an existing open request. |
| `change_qty`, `toggle_pause`, `remove_item` | POST | Update the owner's listing quantity, availability, or remove it when no active exchange is attached. |
| `accept_incoming`, `decline_incoming` | POST | Let an item owner respond to a pending request. Accepting records meetup details and reserves one unit. |
| `complete_incoming`, `mark_returned` | POST | Record a completed give-away handoff, start a lending period, or record a return. |
| `cancel_request`, `confirm_handoff`, `ask_for_match` | POST | Cancel a request, confirm receipt, or ask for a suggested matching item. |
| `settings`, `password_change` | GET/POST | Edit the student's profile or change their password. A successful password change keeps the session active. |
| `password_reset`, `password_reset_done`, `password_reset_confirm`, `password_reset_complete` | GET/POST | Django's password-reset email flow. Email delivery uses the configured Django mailer. |
| `terms`, `privacy` | GET | Public legal pages. |

## Validation and safeguards

- Forms validate required fields, choices, lengths, and dates on the server; browser-side checks are only a convenience.
- Borrowing dates cannot start in the past, must end after the start date, and cannot exceed the item's lending limit. Meetup dates and times cannot be in the past.
- Listing actions verify that the signed-in user owns the item. Request actions verify the relevant requester, owner, and request status.
- Accepting a request and marking a lent item returned use database transactions and row locks so stock changes stay consistent when simultaneous submissions occur.
- Profile updates accept a `next` redirect only when Django confirms it is a safe same-host URL.
- Success and error feedback uses Django's messages framework; the front end displays these messages as toasts.

## Settings and running

- `shareshelf_app` is in `INSTALLED_APPS`; templates use `APP_DIRS` and the request, auth, messages, and `profile_context` context processors.
- Database and email connection values are configured in `config/settings.py` and can be supplied through the project `.env` file. Keep secrets out of source control.
- `STATICFILES_DIRS` points to the app's static assets.
- Run database migrations with `python manage.py migrate`, then start the development server with `python manage.py runserver`.
- Django runs the SWI-Prolog availability check at startup. Install SWI-Prolog or set `SWIPL_PATH` if it cannot be found.

## Extending the back end

- Add or change database fields in `models.py`, update the corresponding form and view behavior, then create and apply a Django migration.
- Add or change matching, request-transition, lending-date, or overdue rules in `logic/rules.pl`; update the bridge only when the facts or query interface changes.
- Keep URL names and template context keys in sync with the front end. See [frontend.md](frontend.md) for the pages and data the templates expect.
