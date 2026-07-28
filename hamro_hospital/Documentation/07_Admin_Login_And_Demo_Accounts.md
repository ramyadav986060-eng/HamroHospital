# Admin Login & Demo Accounts

Running `python manage.py seed_all` (or directly `python manage.py
create_demo_accounts`) creates one login per staff role. **All demo
accounts share the same password: `sashi`**

Log in at: `/accounts/login/`

| Username | Role | Typical use |
|---|---|---|
| `admin` | Super Admin | Full system access, Django admin, all dashboards |
| `registration` | Registration Counter | Patient registration, OPD visit creation |
| `cashier` | Cash Counter | Billing, receipts, invoices |
| `doctor` | Doctor | Consultations, diagnoses, prescriptions |
| `pharmacy` | Pharmacy | Medicine dispensing, pharmacy sales |
| `laboratory` | Laboratory | Lab test requests and reports |
| `radiology` | Radiology | Radiology requests and reports |
| `insurance` | Insurance | Insurance claims review |
| `admission` | Ward/Admission | Admissions, ward & bed allocation |
| `nursing` | Nursing | Nursing dashboard |
| `operationtheatre` | Operation Theatre | Surgery scheduling |
| `bloodbank` | Blood Bank | Blood unit inventory and issues |
| `accounts` | Accounts Department | Financial reports |
| `medicalrecords` | Medical Records | Patient documents |

## Creating your own superuser instead
```powershell
python manage.py createsuperuser
```
Follow the prompts for username/email/password.

## Changing the shared demo password
Demo account passwords are set in
`accounts/management/commands/create_demo_accounts.py` (the
`DEMO_PASSWORD` constant). Change it there and re-run:
```powershell
python manage.py create_demo_accounts
```

## Patient-side login (Patient Portal)
Patients can also log in to their own portal using their **Patient ID**
(e.g. `HT-2026-000123`) and phone number, or the credentials created for
them at registration — see the Patient Portal module for details.
