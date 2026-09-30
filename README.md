# ACC Consultation System

A complete academic Flask web application for managing student consultations with authorized medical experts. It uses Flask, Jinja2, SQLite, SQLAlchemy, Flask-Login, Flask-WTF CSRF protection, and Werkzeug password hashing.

> **Academic/demo system:** This project manages consultation records. It does not diagnose medical conditions or make automated treatment decisions. Do not use the seeded credentials in production.

## 1. Features

- Exactly three roles: **SUPER ADMIN**, **MEDICAL EXPERT**, **STUDENT**
- Backend-enforced RBAC
- Student self-registration
- Secure password hashing
- Flask-Login session authentication with a registered `user_loader`
- CSRF protection for POST forms
- Consultation request → accept/reject → in progress → notes/recommendations → completed workflow
- Student-only access to their own consultations
- Expert-only access to assigned consultations
- Super Admin user management, role assignment, activation/deactivation, consultations, activity logs, and settings
- Search and filtering
- Friendly responsive healthcare/student UI
- Custom 403/404/500 pages
- SQLite + SQLAlchemy relationships and indexes
- Development seed data
- Automated tests

## 2. Project structure

```text
acc-consultation-system/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── auth/routes.py
│   ├── admin/routes.py
│   ├── medical/routes.py
│   ├── student/routes.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── medical/
│   │   ├── student/
│   │   └── errors/
│   └── static/
│       ├── css/style.css
│       ├── js/app.js
│       └── images/
├── instance/
├── tests/
├── config.py
├── seed.py
├── run.py
├── requirements.txt
├── .env.example
└── README.md
```

## 3. Requirements

- Python 3.11+ recommended
- pip
- A terminal / PowerShell

## 4. Installation on Windows

Open PowerShell in the project folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, use:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 5. Initialize and seed the database

```powershell
.venv\Scripts\python.exe seed.py
```

The database is created at `instance/acc_consultation.db`. Running `seed.py` resets the development database.

## 6. Run

```powershell
.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:5000`.

## 7. Development credentials

These are fictional and intended only for local development:

| Role | Email | Password |
|---|---|---|
| Super Admin | `admin@acc.local` | `Admin123!` |
| Medical Expert | `alex@acc.local` | `Expert123!` |
| Medical Expert | `jamie@acc.local` | `Expert123!` |
| Students | `student1@acc.local` through `student5@acc.local` | `Student123!` |

**Change or remove these credentials before any real deployment.**

## 8. Security notes

1. Set a long random `SECRET_KEY` in `.env`.
2. Use HTTPS in production and set `SESSION_COOKIE_SECURE=true`.
3. Use a production database if deploying beyond a classroom demo.
4. Do not place `.env` under source control.
5. Back up the database according to your institution's requirements.
6. Review access permissions before storing any real health-related information.
7. The application deliberately does not implement automated diagnosis or treatment decisions.

## 9. Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The tests cover authentication, the Flask-Login user loader path, invalid login handling, and backend RBAC.

## 10. Important architecture detail

`app/auth/routes.py` registers:

```python
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
```

This is required by Flask-Login and prevents the common **"Missing user_loader or request_loader"** configuration error.
