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
| `browse` | GET | `?q=`, `?category=` | Items classmates are sharing |
| `item_detail` | GET | item id | One item |
| `request_item` | POST | item id | "Request this item" |
| `post_item` | POST | | "Post an item" popup |
| `change_qty` | POST | item id; `step=up|down` | Quantity buttons |
| `toggle_pause` | POST | item id | "Pause / Resume sharing" |
| `remove_item` | POST | item id | "Remove from shelf" |
| `accept_incoming` | POST | request id | Accept popup |
| `decline_incoming` | POST | request id | "Decline" |
| `complete_incoming` | POST | request id | "Handed it to …" |
| `post_request` | POST | | "Request an item" popup |
| `cancel_request` | POST | request id | "Cancel request" |
| `confirm_handoff` | POST | request id | "I got it" |
| `ask_for_match` | POST | request id, item id | "Ask for this" on a suggested match |

### Objects the templates read

**`profile`**: `name`, `first_name`, `initials`, `program`, `school`.

**Item**: `id`, `name`, `category`, `condition`, `qty`, `paused`,
`description`, `location`, `icon`, `tone`, `owner.profile`.

**Request**: `id`, `name`, `category`, `note`, `needed_by` (date), `location`,
`status` (one of `open`, `requested`, `matched`, `fulfilled`, `cancelled`,
`declined`), plus:

- `status_label`: what to call the status. The seeker and the sharer see
  different words (e.g. `requested` is "Requested" to the seeker and
  "Pending" to the sharer).
- `condition_label`: "Any condition" or the preference.
- `is_closed`: true for fulfilled, cancelled and declined.
- `other_party`: the other student's `profile`.
- `meetup`: `None`, or an object with `location` and `label` (e.g. "Nov 3, 1:00 PM").

### Context for each page

**`login.html`**: `form` (fields `name`, `program`, `email`, `password`; shows
`non_field_errors`), `mode` (`"login"` or `"signup"`).

**`dashboard.html`**:

| Variable | Contents |
| --- | --- |
| `greeting` | "Good morning" / "Good afternoon" / "Good evening" |
| `stats` | `items_shared`, `shared_today`, `available`, `open_requests`, `matched`, `students_helped`, `helped_today`, `waiting_on_you` |
| `incoming` | list of `{request, item, can_accept, posted}` for requests on your items |
| `new_incoming` | how many of those are waiting for an answer |
| `shelf` | list of rows: `{item, status, can_decrease, can_increase}`, where `status` is "Available", "Reserved", "None left" or "Paused" |
| `shelf_limit`, `shelf_hidden` | rows shown before "Show more", and how many are hidden |
| `requests` | list of `{request, posted, matches}` for your own requests; `matches` is a list of items |
| `request_limit`, `requests_hidden` | same as the shelf |
| `share_form`, `request_form` | the two popup forms (prefixes `share` and `request`) |
| `accept`, `accept_form` | the request being accepted and its form (prefix `accept`: `location`, `date`, `time`), or `None` |
| `handoff`, `handoff_matches` | the request whose details are open, and its suggested items, or `None` |
| `condition_prefs` | list of `(value, hint)` for the condition preference picker |
| `max_note` | note length limit (200) |
| `open_modal` | `"share"` or `"request"` to reopen a popup with form errors |
| `dashboard_url` | `reverse("dashboard")` |

**`browse.html`**: `items`, `query`, `category`, `categories` (starting with
"All"), `posted` (dict of item id → "Posted today" etc.), `request_form`,
`condition_prefs`, `max_note`, `open_modal`.

**`item_detail.html`**: `item`, `requested` (true if you already asked for
it), `posted`.

## Easy edits

- **Colors:** the variables at the top of `shelf/static/shelf/styles.css`.
- **Font:** Plus Jakarta Sans, loaded in `shelf/templates/shelf/base.html`.
- **New icon:** add a `<symbol>` from lucide.dev to `icons.svg`, then use
  `{% icon "name" 16 %}`.
