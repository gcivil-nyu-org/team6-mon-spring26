# Local Development Guide

Follow these steps to get **Dues & Do's** running on your local machine for development.

## 📋 Prerequisites

-   **Python 3.10+**
-   **Pip** (Python Package Installer)
-   **Virtualenv** (Recommended)
-   **S3 Bucket** (Optional, for avatar uploads)
-   **Google OAuth Credentials** (Optional, for social login)

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

### 4. Configuration
Create a `.env` file in the `duesanddos/` directory using the `.env.example` as a template.

**Mac/Linux:**
```bash
cp duesanddos/.env.example duesanddos/.env
```

**Windows:**
```cmd
copy duesanddos\.env.example duesanddos\.env
```

*Edit the `.env` file with your local database credentials and API keys.*

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Start the Server
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
