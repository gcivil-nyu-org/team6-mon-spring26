# Local Development Guide

Follow these steps to get **Dues & Do's** running on your local machine for development.

## 📋 Prerequisites

- **Python 3.10+**
- **Pip** (Python Package Installer)
- **Virtualenv** (Recommended)
- **PostgreSQL 16+** (required for local development)
- **S3 Bucket** (Optional, for avatar uploads)
- **Google OAuth Credentials** (Optional, for social login)

## 🛠️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/noobacker/team6-mon-spring26.git
cd team6-mon-spring26
```

### 2. Set Up Virtual Environment

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install and Start PostgreSQL

**On macOS with Homebrew**

Install PostgreSQL:
```
brew install postgresql@16
```
Initialize the local PostgreSQL data directory the first time only:
```
mkdir -p /usr/local/var/postgresql@16
/usr/local/opt/postgresql@16/bin/initdb -D /usr/local/var/postgresql@16
```
Start PostgreSQL:
```
brew services start postgresql@16
```
Verify that PostgreSQL is running:
```
/usr/local/opt/postgresql@16/bin/pg_isready -h 127.0.0.1 -p 5432
```
Create the local development database:
```
/usr/local/opt/postgresql@16/bin/createdb duesanddos
```
**Notes**

- PostgreSQL must be running locally on `127.0.0.1:5432` before running migrations or starting the Django server.

- On some Homebrew setups, PostgreSQL is installed but not linked into your shell path. If commands like `psql` or `createdb` are not found, use the full path shown above.

- The default local PostgreSQL role may be your macOS username rather than `postgres`.

### 5. Configuration
Create a `.env` file in the `duesanddos/` directory using the `.env.example` as a template.

**Mac/Linux:**
```bash
cp duesanddos/.env.example duesanddos/.env
```

**Windows:**
```cmd
copy duesanddos\.env.example duesanddos\.env
```

Edit the `.env` file with your local database credentials and API keys.

For a standard local macOS/Homebrew PostgreSQL setup, use:
```
DB_NAME=duesanddos
DB_USER=your_macos_username
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
```
For example:
```
DB_NAME=duesanddos
DB_USER=forzanarime
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
```

### 6. Run Migrations
```bash
python manage.py migrate
```

### 7. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 8. Start the Server
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`.

---

## 🏗️ Project Structure

-   `duesanddos/`: Main Django project directory.
    -   `accounts/`: Core app handling users, profiles, and households.
    -   `static/`: Global CSS, JS, and image assets.
    -   `templates/`: Site-wide HTML templates.
-   `media/`: Local storage for uploaded files (if S3 is disabled).

## 🧪 Running Tests
```bash
python manage.py test
```

## Troubleshooting
`connection refused` **on** `127.0.0.1:5432`

PostgreSQL is not running locally. Start it with:

```
brew services start postgresql@16
```

`role "postgres" does not exist`

Your local PostgreSQL instance may use your macOS username as the default database role. Set `DB_USER` in `.env` to your macOS username instead of `postgres`.

`database "duesanddos" does not exist`

Create it with:
```
/usr/local/opt/postgresql@16/bin/createdb duesanddos
```