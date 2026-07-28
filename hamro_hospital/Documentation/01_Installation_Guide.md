# Installation Guide

## 1. Prerequisites
- Python 3.11 or 3.12 installed and on PATH
- pip (comes with Python)
- (Optional) Git, if you're cloning rather than unzipping

## 2. Unzip / clone the project
Extract the ZIP so that `manage.py` sits at the project root, e.g.:

```
tu_hospital_management_system/
    manage.py
    config/
    patients/
    ...
    Documentation/
```

## 3. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Install dependencies
```powershell
pip install -r requirements.txt
```

## 5. Configure environment variables (optional)
The system runs out of the box with SQLite and sensible defaults. If you
want to override anything (hospital name, eSewa keys, email, etc.), copy
`.env.example` to `.env` and edit it — see `03_Database_Setup.md` for the
database-related variables.

## 6. Run migrations
```powershell
python manage.py migrate
```

## 7. Seed the demo database
```powershell
python manage.py seed_all
```
This is the ONE command that builds the entire interconnected demo hospital
(500 patients, 150 doctors, thousands of visits/bills/prescriptions/etc.).
It takes several minutes — see `05_Seeding_Commands.md` for details and options.

## 8. Create your own superuser (optional)
```powershell
python manage.py createsuperuser
```
Or just use the built-in demo accounts — see `07_Admin_Login_And_Demo_Accounts.md`.

## 9. Collect static files (only needed for production-style deployment)
```powershell
python manage.py collectstatic --noinput
```

## 10. Run the development server
```powershell
python manage.py runserver
```
Visit **http://127.0.0.1:8000/**.

## 11. Log in
Go to `/accounts/login/` and use any demo account from
`07_Admin_Login_And_Demo_Accounts.md`, or the superuser you created.
