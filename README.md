# Classroom Ledger — LMS

A self-contained Flask learning management system for a single course, covering attendance, class links, assignments, group/individual projects, and certificate approval.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

The app runs at `http://localhost:5000`. A SQLite database (`lms.db`) is created automatically on first run, along with a default admin account:

- **Username:** `admin`
- **Password:** `admin123`

Change this password after logging in (or set a new one by editing `app.py`'s `seed_admin()` before first run).

## Roles

**Admin / instructor** — manages the class from `/admin`: register and edit students, take attendance, share class links, post assignments and projects, grade submissions, and approve or reject certificate requests.

**Student** — uses `/student`: views their attendance record, class links, assignments and projects (submitting work and tracking deadlines), and requests/views their certificate once approved. Students can either be registered by the admin (Students → Register a student) or self-register from the login page's "Register" link; either way a default password of `student123` is set unless the admin specifies one.

## Notable behavior

- Assignment and project deadlines are enforced both in the UI (live countdown, disabled forms once closed) and on the server (submissions rejected after the deadline).
- Projects can allow group submissions, individual submissions, or both — configurable per project. Group submissions record a group name and a free-text list of teammates; the submitting student's account is the one on record.
- Certificates move through `not_requested → pending → approved/rejected`. Approved certificates get a unique code and a printable certificate page.

## Project structure

```
app.py              application factory, blueprint registration, admin seeding
config.py           Flask config (SQLite path, secret key)
models.py           SQLAlchemy models
auth.py             login / logout / self-registration
admin_routes.py      admin-facing routes
student_routes.py    student-facing routes
utils.py             auth decorators
templates/           Jinja templates ("Classroom Ledger" design system)
static/css/style.css  design tokens and component styles
static/js/main.js     deadline countdowns, submission-type toggle, confirms, attendance quick-fill
```

## Resetting data

Delete `lms.db` and restart the app to start over with a fresh database and a freshly seeded admin account.
