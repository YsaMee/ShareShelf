# ShareShelf front end

| Path | Function |
| --- | --- |
| `shelf/templates/shelf/` | Pages: `login`, `dashboard`, `browse`, `item_detail`, plus `base` and `app` layouts |
| `shelf/templates/shelf/partials/` | Sidebar, the four popups, list rows, badges, toasts |
| `shelf/templatetags/shelf_tags.py` | `{% icon %}`, `{% item_icon %}`, `{% status_badge %}` and small filters |
| `shelf/static/shelf/styles.css` | All styles. Colors and radii are CSS variables at the top |
| `shelf/static/shelf/app.js` | Opens popups without reloading, "⋯" menus, "Show more", password toggle, toasts |
| `shelf/static/shelf/icons.svg` | Lucide icons (lucide.dev, ISC license) |
| `shelf/static/shelf/logo-mark.svg`, `shelf.png` | Logo and login illustration from Figma |
| `shelf/static/shelf/ShareShelf_logo.png` | Full logo shown above the log in / sign up tabs |

Every page works without JavaScript: popups also open from their URL
(`?modal=share`, `?modal=request`, `?request=<id>`, `?accept=<id>`), and every
button is a normal form `POST`. `app.js` only makes it smoother.

## What the back end needs to provide

The back end has to supply the pieces below with these exact names.

### Settings

- `shelf` in `INSTALLED_APPS`, `APP_DIRS = True`, and `django.contrib.staticfiles`.
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

### Objects the templates read

**`profile`**: `name`, `first_name`, `initials`, `program`, `school`.

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

## Edits

- **Colors:** the variables at the top of `shelf/static/shelf/styles.css`.
- **Font:** Plus Jakarta Sans, loaded in `shelf/templates/shelf/base.html`.
- **New icon:** add a `<symbol>` from lucide.dev to `icons.svg`, then use
  `{% icon "name" 16 %}`.
