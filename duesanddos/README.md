For Next.js: Make sure you open a terminal, cd frontend, and then run npm run dev
For Django / Python: Open a terminal, cd backend, then run source .venv/bin/activate, and then run your python server
--> python manage.py runserver or script commands.



# Dues & Do's — Developer Guide

Roommate expense splitting + chore management. This document covers the full backend + frontend setup.

---

## Project Structure

```
dues-and-dos/
├── backend/
│   ├── apps/
│   │   ├── authentication/       # JWT auth, password reset
│   │   │   ├── authentication.py # Cookie-based JWT authenticator
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── tests.py
│   │   └── users/               # Custom User model + /api/me/
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       └── urls.py
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx             # Landing page
    │   │   ├── layout.tsx           # Root layout
    │   │   ├── globals.css
    │   │   ├── login/page.tsx
    │   │   ├── register/page.tsx
    │   │   ├── forgot-password/page.tsx
    │   │   ├── reset-password/page.tsx
    │   │   ├── dashboard/page.tsx   # Protected
    │   │   ├── terms/page.tsx
    │   │   └── privacy/page.tsx
    │   ├── components/
    │   │   ├── layout/AuthLayout.tsx
    │   │   └── ui/FormField.tsx
    │   ├── hooks/
    │   │   └── useAuth.tsx          # AuthContext + useAuth hook
    │   ├── lib/
    │   │   ├── api.ts               # Axios client + auth API
    │   │   └── errors.ts            # API error parser
    │   └── types/index.ts
    ├── next.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    └── .env.example
```

---

## API Endpoints

### POST `/api/auth/register/`

**Request:**
```json
{
  "email": "alex@example.com",
  "password": "SecurePass1",
  "full_name": "Alex Johnson"
}
```

**Response 201:**
```json
{
  "user": {
    "id": 1,
    "email": "alex@example.com",
    "full_name": "Alex Johnson",
    "display_name": "Alex Johnson",
    "avatar_url": null,
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "message": "Account created successfully."
}
```
Sets `access_token` and `refresh_token` as httpOnly cookies.

---

### POST `/api/auth/login/`

**Request:**
```json
{ "email": "alex@example.com", "password": "SecurePass1" }
```

**Response 200:**
```json
{ "user": { ... }, "message": "Login successful." }
```
Sets auth cookies.

---

### POST `/api/auth/logout/`

Requires auth cookie. Blacklists refresh token, clears cookies.

**Response 200:**
```json
{ "message": "Logged out successfully." }
```

---

### POST `/api/auth/forgot-password/`

**Request:**
```json
{ "email": "alex@example.com" }
```

**Response 200 (always):**
```json
{ "message": "If an account with that email exists, you'll receive a reset link shortly." }
```
Sends email with link: `https://<FRONTEND_DOMAIN>/reset-password?uid=<uid>&token=<token>`

---

### POST `/api/auth/reset-password/`

**Request:**
```json
{
  "uid": "MQ",
  "token": "abc-xyz...",
  "new_password": "NewSecure1"
}
```

**Response 200:**
```json
{ "message": "Password reset successfully. Please log in." }
```

---

### POST `/api/auth/token/refresh/`

Reads refresh cookie, issues new access + refresh cookies.

---

### GET `/api/me/`

Requires auth. Returns current user profile.

---

### PATCH `/api/me/`

Requires auth. Update `full_name` and/or `avatar` (multipart).

**Request (multipart/form-data):**
```
full_name: "New Name"
avatar: <file>
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+

---

### Backend

```bash
cd backend

# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your local DB credentials

# 4. Create database
createdb dues_and_dos  # or via psql

# 5. Run migrations
python manage.py migrate

# 6. Create superuser (optional)
python manage.py createsuperuser

# 7. Start dev server
python manage.py runserver
```

Backend runs at: http://localhost:8000

---

### Frontend

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000 (default)

# 3. Start dev server
npm run dev
```

Frontend runs at: http://localhost:3000

---

## Running Tests

```bash
cd backend
python manage.py test apps.authentication
```

Run with verbosity:
```bash
python manage.py test apps.authentication --verbosity=2
```

Run with pytest (install pytest-django):
```bash
pip install pytest pytest-django
pytest apps/authentication/tests.py -v
```

---

## Database Migrations

After making model changes:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Environment Variables

### Backend `.env`

| Variable | Description | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | — |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DB_NAME` | PostgreSQL database name | `dues_and_dos` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `FRONTEND_DOMAIN` | For password reset links | `http://localhost:3000` |
| `EMAIL_BACKEND` | Django email backend | console (local) |
| `EMAIL_HOST_PASSWORD` | SendGrid / SMTP password | — |
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@duesanddos.com` |
| `USE_S3` | Enable S3 media storage | `False` |
| `AWS_ACCESS_KEY_ID` | AWS key | — |
| `AWS_SECRET_ACCESS_KEY` | AWS secret | — |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | — |

### Frontend `.env.local`

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL | `http://localhost:8000` |

---

## Auth Flow Summary

1. **Register/Login** → Backend sets `access_token` (15min) + `refresh_token` (7d) as httpOnly cookies
2. **Every request** → Axios sends cookies automatically (`withCredentials: true`)
3. **401 response** → Axios interceptor calls `/api/auth/token/refresh/` silently
4. **Refresh fails** → Dispatches `auth:logout` event → AuthContext clears user, redirects to `/login`
5. **Dashboard** → `useAuth` fetches `/api/me/` on mount; redirects to `/login` if unauthenticated
6. **Logout** → Backend blacklists refresh token, clears cookies

---

## AWS Production Deployment

### Elastic Beanstalk (Backend)

1. Set `DEBUG=False`, `USE_S3=True`
2. Set all env vars in EB environment configuration
3. Add `gunicorn` as the WSGI server (already in requirements.txt)
4. `Procfile`: `web: gunicorn config.wsgi:application --bind 0.0.0.0:8000`
5. Configure RDS PostgreSQL and update `DB_*` vars
6. Run migrations via EB SSH or a deploy hook

### Vercel / Amplify (Frontend)

1. Set `NEXT_PUBLIC_API_URL` to your EB backend URL
2. Deploy with `npm run build`

### S3 Media

Set `USE_S3=True` and configure `AWS_*` env vars. Avatar uploads will automatically go to S3.

---

## Security Checklist (Production)

- [ ] `DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` is random and secret (50+ chars)
- [ ] `ALLOWED_HOSTS` is exact (no wildcards)
- [ ] `SIMPLE_JWT.AUTH_COOKIE_SECURE = True` (HTTPS only)
- [ ] `CORS_ALLOWED_ORIGINS` is exact frontend domain
- [ ] Database is not publicly accessible (use VPC)
- [ ] S3 bucket is private (no public ACL)
- [ ] Email SMTP credentials are from a dedicated sender service (SendGrid/SES)
