# ShareShelf front end

| Path | Function |
| --- | --- |
| `shareshelf_app/templates/shelf/` | Pages: `login`, `dashboard`, `browse`, `item_detail`, `settings`, `terms`, `privacy`, the four `password_reset_*` steps, plus the `base`, `app`, `auth`, `legal` and `error` layouts |
| `shareshelf_app/templates/` | `403.html`, `404.html`, `500.html` (Django looks for these at the top level) |
| `shareshelf_app/templates/shelf/partials/` | Sidebar (with the profile menu), the five popups (including Edit profile), list rows, badges, toasts, the login hero and password rule chips |
| `shareshelf_app/templatetags/shelf_tags.py` | `{% icon %}`, `{% item_icon %}`, `{% status_badge %}` and small filters |
| `shareshelf_app/static/shelf/styles.css` | All styles. Colors and radii are CSS variables at the top |
| `shareshelf_app/static/shelf/app.js` | Opens popups without reloading, "⋯" menus, "Show more", password toggle, toasts |
| `shareshelf_app/static/shelf/icons.svg` | Lucide icons (lucide.dev, ISC license) |
| `shareshelf_app/static/shelf/logo-mark.svg`, `shelf.png` | Logo and login illustration from Figma |
| `shareshelf_app/static/shelf/ShareShelf_logo.png` | Full logo shown above the log in / sign up tabs |

Every page works without JavaScript: popups also open from their URL
(`?modal=share`, `?modal=request`, `?request=<id>`, `?accept=<id>`), and every
button is a normal form `POST`. `app.js` only makes it smoother.

## What the back end needs to provide

The back end has to supply the pieces below with these exact names.

### Settings

- `shareshelf_app` in `INSTALLED_APPS`, `APP_DIRS = True`, and `django.contrib.staticfiles`.
- Context processors: `request`, `auth`, `messages`, plus one that puts the
  logged-in student's profile in every template as **`profile`**.
- Success and error messages go through `django.contrib.messages`
  (`messages.success` / `messages.error`); they show as toasts.

### URL names

| Name | Method | Arguments | Function |
| --- | --- | --- | --- |
| `login`, `signup` | GET/POST | | Log in / create account |
| `logout` | POST | | Log out |
| `dashboard` | GET | | Overview |
| `browse` | GET | `?q=`, `?category=`, `?mode=give|lend` | Items classmates are sharing |
| `item_detail` | GET | item id | One item |
| `request_item` | POST | item id | "Request this item", or the borrower's form on lent items (prefix `borrow`: `borrow_from`, `return_by`, `note`; optional `open_request`) |
| `post_item` | POST | | Share side of the "New post" popup |
| `change_qty` | POST | item id; `step=up|down` | Quantity buttons |
| `toggle_pause` | POST | item id | "Pause / Resume sharing" |
| `remove_item` | POST | item id | "Remove from shelf" |
| `accept_incoming` | POST | request id | Accept popup |
| `decline_incoming` | POST | request id | "Decline" |
| `complete_incoming` | POST | request id | "Handed it to …" / "Lent it to …" |
| `mark_returned` | POST | request id | "Mark as returned" on a lent item |
| `post_request` | POST | | Request side of the "New post" popup |
| `cancel_request` | POST | request id | "Cancel request" |
| `confirm_handoff` | POST | request id | "I got it" |
| `ask_for_match` | POST | request id, item id | "Ask for this" on a suggested match |
| `settings` | GET/POST | | Settings page; POST saves the Edit profile popup (with `next` = the page it was opened from) |
| `password_change` | POST | | Password form on the Settings page |
| `password_reset` | GET/POST | | "Forgot password?": asks for the email |
| `password_reset_done` | GET | | "Check your email" |
| `password_reset_confirm` | GET/POST | `uidb64`, `token` | Link from the email: set a new password |
| `password_reset_complete` | GET | | "Your password is updated" |
| `terms`, `privacy` | GET | | Terms of Service and Privacy Policy (open without logging in) |

### Objects the templates read

**`profile`**: `name`, `first_name`, `initials`, `program` (with choices, so
`get_program_display` gives the full name shown to classmates), `school`, plus for Edit profile:
`full_name`, `display_name`,
`year_level` and `get_year_level_display`, `bio`, `pickup_spot`. Templates show `name`
everywhere, so make `name` return the display name when it's set and the full name otherwise.

**Item**: `id`, `name`, `category`, `condition` (New / Gently Used /
Functional), `qty`, `paused`, `description`, `location`, `icon`, `tone`,
`owner.profile`, `listing` (`give` or `lend`), `is_lend`, `lend_limit` and
`get_lend_limit_display` (e.g. "Up to 2 weeks"), and `listing_label`
("Give away" or "Lend · Up to 2 weeks").

**Request**: `id`, `name`, `category`, `note`, `needed_by` (date), `location`,
`status` (one of `open`, `requested`, `matched`, `lent`, `returned`,
`fulfilled`, `cancelled`, `declined`), `is_lend`, `borrow_from` and
`return_by` (dates, for lent items), plus:

- `status_label`: what to call the status. The seeker and the sharer see
  different words (e.g. `requested` is "Requested" to the seeker and
  "Pending" to the sharer).
- `condition_label`: "Any condition" or the preference.
- `is_closed`: true for fulfilled, returned, cancelled and declined.
- `other_party`: the other student's `profile`.
- `meetup`: `None`, or an object with `location` and `label` (e.g. "Nov 3, 1:00 PM").

### Context for each page

**`login.html`**: `mode` (`"login"` or `"signup"`) and `form`. Log in uses
`email` and `password`. Sign up uses `name`, `email` (must end in `.edu.ph`),
`program` (a choice field; the dropdown lists its choices), `password`,
`confirm_password` and `agree` (the terms checkbox). Errors show under each
field, and `non_field_errors` at the top. The password chips update in the
browser, but the back end must check the same rules: 8+ characters, letters
and digits, and matching passwords.

**`dashboard.html`**:

| Variable | Contents |
| --- | --- |
| `greeting` | "Good morning" / "Good afternoon" / "Good evening" |
| `stats` | `items_shared`, `shared_today`, `available`, `open_requests`, `matched`, `students_helped`, `helped_today`, `waiting_on_you` |
| `incoming` | list of `{request, item, can_accept, posted, overdue}` for requests on your items, including items you've lent out |
| `new_incoming` | how many of those are waiting for an answer |
| `shelf` | list of rows: `{item, status, can_decrease, can_increase}`, where `status` is "Available", "Reserved", "Lent out", "None left" or "Paused" |
| `shelf_limit`, `shelf_hidden` | rows shown before "Show more", and how many are hidden |
| `requests` | list of `{request, posted, matches, overdue}` for your own requests; `matches` is a list of items |
| `request_limit`, `requests_hidden` | same as the shelf |
| `share_form`, `request_form` | the two sides of the "New post" popup (prefixes `share` and `request`). `share_form` fields: `listing`, `name`, `qty`, `category`, `condition`, `lend_limit` (required when lending), `location`, `description` |
| `listing_choices`, `listing_hints` | Give away / Lend temporarily options and their one-line hints |
| `accept`, `accept_form` | the request being accepted and its form (prefix `accept`: `location`, `date`, `time`), or `None` |
| `handoff`, `handoff_matches`, `handoff_overdue` | the request whose details are open, its suggested items, and whether its loan is overdue |
| `condition_prefs` | list of `(value, hint)` for the condition preference picker |
| `max_note` | note length limit (200) |
| `open_modal` | `"share"` or `"request"` to reopen a popup with form errors |
| `dashboard_url` | `reverse("dashboard")` |

**`browse.html`**: `items`, `query`, `category`, `categories` (starting with
"All"), `mode` (`""`, `give` or `lend`), `posted` (dict of item id → "Posted
today" etc.), `share_form`, `request_form`, `listing_choices`, `listing_hints`,
`condition_prefs`, `max_note`, `open_modal`.

**`item_detail.html`**: `item`, `requested` (true if you already asked for
it), `posted`, `today`, `borrow_form` (for lent items), and `open_request`
(an open request this borrow will fill, when coming from "possible matches").
The back end must check borrow dates: not in the past, return after borrow,
within the lending limit, and not past the end of term.

**`settings.html`**: `password_form` (Django's `PasswordChangeForm`: `old_password`,
`new_password1`, `new_password2`). The read-only email comes from `user.email`. After a
password change, call `update_session_auth_hash` so the student stays logged in (the page
says so). When the password form has errors, render `settings.html` again with it.

**Edit profile popup**: it's in `app.html`, so every logged-in page has it, and it opens
from the profile menu, the Settings page, or `?modal=profile`. It needs **`profile_form`** on
every logged-in page, so supply it from a context processor (an unbound form built from the
student's profile). Fields:

| Field | Notes |
| --- | --- |
| `full_name`, `display_name` | both required |
| `school`, `program`, `pickup_spot` | choice fields; the dropdowns list their choices. Add a blank choice to `pickup_spot` if it's optional. Give `pickup_spot` the same choices as `Item.location`: the "New post" forms start on the student's saved spot, which only works if it's one of their options |
| `year_level` | choice field, one button per choice (BS Architecture runs five years, so include a 5th Year). Put the choices on the model field so `get_year_level_display` exists: classmates see "BS Architecture · 3rd Year" |
| `bio` | shown under the student's name on their items, and in the accept and handoff popups |
| `bio` | 300 characters max |

On success, redirect to the posted `next` (check it with `url_has_allowed_host_and_scheme`).
On errors, render `settings.html` with the bound form as `profile_form` and
`open_modal = "profile"` so the popup reopens showing the errors.

**Password reset**: use Django's built-in views from `django.contrib.auth.views`
and point them at these templates:

| View | Settings |
| --- | --- |
| `PasswordResetView` | `template_name="shelf/password_reset_form.html"`, `email_template_name="shelf/password_reset_email.txt"`, `subject_template_name="shelf/password_reset_subject.txt"` |
| `PasswordResetDoneView` | `template_name="shelf/password_reset_done.html"` |
| `PasswordResetConfirmView` | `template_name="shelf/password_reset_confirm.html"` |
| `PasswordResetCompleteView` | `template_name="shelf/password_reset_complete.html"` |

Keep the URL names above: Django's views redirect to `password_reset_done` and
`password_reset_complete` by default. Sending the email needs `EMAIL_BACKEND` set
(the console backend is fine while developing).

**`terms.html`, `privacy.html`**: no context; a `TemplateView` is enough. The text is a
first draft for the group to review.

**`403.html`, `404.html`, `500.html`**: no context. Django uses them automatically when
`DEBUG = False`.

## Edits

- **Colors:** the variables at the top of `shareshelf_app/static/shelf/styles.css`.
- **Font:** Plus Jakarta Sans, loaded in `shareshelf_app/templates/shelf/base.html`.
- **New icon:** add a `<symbol>` from lucide.dev to `icons.svg`, then use
  `{% icon "name" 16 %}`.
