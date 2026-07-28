# Hamro Hospital Management System — Documentation

This folder contains everything needed to install, seed, and run the
hospital management system on a fresh machine.

| File | Purpose |
|---|---|
| `01_Installation_Guide.md` | Step-by-step setup from a clean checkout to a running server |
| `02_Requirements.md` | Software/hardware requirements and Python package list |
| `03_Database_Setup.md` | Database engine notes and configuration |
| `04_Migration_Commands.md` | How to create/apply Django migrations |
| `05_Seeding_Commands.md` | How to generate the full demo dataset (`seed_all`) |
| `06_Common_Error_Fixes.md` | Fixes for the errors people hit most often |
| `07_Admin_Login_And_Demo_Accounts.md` | Every login the system ships with |
| `PowerShell Commands.txt` | Every command above, ready to copy-paste on Windows |

## Quick start (Windows PowerShell)

```powershell
cd tu_hospital_management_system
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_all
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

The `admin` demo account (see `07_Admin_Login_And_Demo_Accounts.md`) already
has Super Admin access if you don't want to create your own superuser.
