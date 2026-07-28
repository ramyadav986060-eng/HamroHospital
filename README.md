# Hamro Hospital Management System

A Django-based Hospital Management System with integrated patient registration, OPD, doctor consultation, referrals, billing, cashier workflow, laboratory, radiology, pharmacy, admission, nursing, operation theatre, blood bank, insurance, finance reports, staff attendance and payroll foundations.

## Repository contents

- `hamro_hospital/` - main Django project source code.
- `hamro_hospital.zip` - backup/archive copy of the project source.
- `HIS_Workflow_Integration_Report.pdf` - workflow integration report.
- `HIS_Professional_Improvement_Roadmap.pdf` - professional HIS improvement roadmap.
- `FINAL_IMPLEMENTATION_REPORT.md` - final completion report.

## Quick setup

```bash
cd hamro_hospital
python -m venv venv
venv\Scripts\activate   # Windows
# or: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py create_demo_accounts
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Staff login:

```text
/accounts/login/
```

Demo accounts are created by:

```bash
python manage.py create_demo_accounts
```

Default demo password:

```text
sashi
```

## Important production configuration

Before going live, configure environment variables.

```env
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=replace-with-strong-secret
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
ESEWA_SANDBOX=False
ESEWA_MERCHANT_CODE=your_live_merchant_code
ESEWA_SECRET_KEY=your_live_secret_key
```

See:

```text
hamro_hospital/PRODUCTION_DEPLOYMENT.md
```

## Production readiness check

```bash
python manage.py verify_production_config
python manage.py check
python manage.py migrate
python manage.py test workflow
```

## Background workers

For production WebSockets and background jobs:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

Use ASGI server for WebSockets:

```bash
daphne config.asgi:application
```

## Fingerprint attendance integration

Manual/local punch page:

```text
/accounts/staff/attendance/punch/
```

Device/API endpoint:

```text
/accounts/staff/attendance/device-punch/?staff_id=STF000001&direction=in
```

CSV import:

```bash
python manage.py sync_fingerprint_attendance attendance.csv
```

CSV format:

```csv
staff_id,timestamp,direction,device_log_id
STF000001,2026-07-28T09:00:00,in,DEV001
STF000001,2026-07-28T18:05:00,out,DEV002
```

## Final status

The system is ready for acceptance testing and staged production configuration. External services such as Redis, Celery workers, eSewa live credentials and fingerprint device SDK/API must be configured on the deployment server.
