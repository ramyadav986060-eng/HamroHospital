# Hamro Hospital Management System (Nepal) - Checkpoint 2 (Full System)

A Django 5 Hospital Management System built for hospitals in Nepal - now with
**all 14 modules integrated into one project**.

## What's included

Fully working (models, forms, views, URLs, templates, admin - no placeholders):

- **Public website** - Home, About, Departments, Doctors, Diseases, Gallery, Contact
- **Accounts & Roles** - custom User model with 8 roles, role-based access decorators,
  append-only system-wide Audit Trail, staff login/logout, Super Admin staff management
- **Departments** - full CRUD (Super Admin)
- **Doctors** - full CRUD, schedule, photo, consultation fee (Super Admin)
- **Patients** - Nepal address system (all 7 provinces / 77 districts, seeded and
  searchable), auto-generated Patient ID (`HT-2026-000001`), QR code generation,
  OPD Visit with auto token numbers and auto registration fee, printable OPD Ticket
  and Patient Card, 24-hour free-edit window with audit logging
- **Appointments** - public online booking with a complete eSewa ePay v2 integration
  (HMAC-SHA256 signed requests, callback verification), printable receipt with QR
- **Consultations** - Doctor's queue, diagnosis, dynamic prescription builder,
  lab/radiology test requests, full patient consultation history
- **Laboratory** - request queue, result upload, printable lab report
- **Radiology** - request queue (X-Ray/CT/MRI/ECG/Echo/Ultrasound/Custom), findings
  & impression, printable report, its own `RAD-2026-000001` numbering
- **Admissions** - Ward & Bed management, admit/discharge workflow with automatic
  bed-freeing on discharge, length-of-stay tracking
- **Billing (Cash Counter)** - patient lookup, multi-service billing with automatic
  totals, Cash/eSewa/Insurance payment, audit-safe price snapshotting, printable
  receipt, separately-audited reprint, today's collections
- **Pharmacy + Inventory** - medicine catalogue with low-stock/out-of-stock/near-expiry/
  expired flags, atomic stock adjustments, dispensing against digital/manual/walk-in
  prescriptions with live stock validation, printable pharmacy bill
- **Insurance** - insurer directory (Super Admin), claim submission and
  approve/reject/settle review workflow, claims report
- **Reports** - Revenue Dashboard (daily/monthly/yearly), Registration, Department,
  Doctor, Cash Counter, Pharmacy, and Laboratory reports
- **Patient Portal** - self-service signup/login on the main public website using
  Hospital ID + phone number + password; logged-in patients can view all their
  visits, prescriptions, lab reports, radiology reports, admissions, bills,
  pharmacy purchases, and insurance claims, and can **book a new visit or
  follow-up themselves** - this creates the same Visit/receipt/token/OPD ticket
  a Registration Counter staff member would create, reusing the identical
  ticket template and QR code

## Requirements

- Python 3.12+ (developed against 3.12; should also work on 3.10/3.11)
- pip

## Setup (Windows / Linux / macOS)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate

# ONE command builds the entire interconnected demo hospital:
# 500 patients, 150 doctors, 5000 appointments, 5000 visits/consultations/
# prescriptions, ~4000 bills, 4000 pharmacy sales, 500 admissions,
# 300 insurance claims, medicines, lab/radiology catalogues, demo staff
# accounts for every role, etc. Takes 5-10 minutes; safe to re-run.
python manage.py seed_all

python manage.py runserver
```

Then open **http://127.0.0.1:8000/** for the public site, and
**http://127.0.0.1:8000/accounts/login/** to sign in as staff using any of
the demo accounts below (all created automatically by `seed_all`) - no
`createsuperuser` step needed, though you're welcome to run
`python manage.py createsuperuser` too if you'd rather use your own login.

## Creating other staff roles

Log in as Super Admin -> **Staff Accounts** -> **Add Staff Member**, and pick a
role. All 8 roles now have a working dashboard: Registration Counter, Cash
Counter, Doctor, Pharmacy, Laboratory, Radiology Counter, Insurance Counter,
and Super Admin.

## Setting up billable services & medicines

**Hospital Services** (used by Billing) now have a full Super Admin screen at
**Dashboard -> Hospital Services** (add/edit code, name, department, price).
**Medicines** (used by Pharmacy) have their own screen at **Dashboard ->
Medicines**. Both are also visible in Django Admin at **/admin/** if you
prefer bulk editing there.

## Patient Portal signup

Patients can create their own portal login at **/portal/signup/** (also
linked from the "Patient Login" navbar item on the public site). Signup
requires the patient's Hospital ID (e.g. `HT-2026-000001`) and the phone
number already on their patient record - so a patient must already be
registered by the Registration Counter at least once before they can sign up.
This is a separate login system from staff accounts; it does not use Django's
built-in auth system.

## Project layout

```
hamro_hospital/
├── manage.py
├── requirements.txt
├── README.md
├── .env.example
├── config/              settings, urls, ASGI/WSGI, Celery, Channels
├── accounts/            staff users, roles, notifications, audit, backups, attendance, leave, payroll
├── website/             public homepage, departments, doctors, services, EHS/Extension pages
├── departments/         departments and units
├── doctors/             doctors, profiles, schedules, extension fees, quota/leave
├── patients/            patient registration, Hospital ID, barcode/QR, OPD visits, tokens
├── patient_portal/      patient login, profile, booking, timeline, bills, reports
├── appointments/        online booking and Extension Service booking bridge
├── consultations/       doctor consultation, prescriptions, lab/radiology requests
├── referrals/           referral workflow, department queues, pending bill generation
├── workflow/            service orders, payment events, patient timeline
├── billing/             cash counter, bills, receipts, refunds, staff discounts
├── finance/             accounts dashboard, extension fees, financial workflow
├── reports/             revenue, department, staff, payroll, PDF/Excel exports
├── laboratory/          lab queue, manual tests, panels, results, verification
├── radiology/           imaging queue, templates, reports, verification
├── pharmacy/            medicines, batches, suppliers, stock ledger, dispensing
├── admissions/          wards, beds, admission, deposits, transfers, discharge
├── nursing/             vitals, notes, medication, inpatient nursing workflow
├── operation_theatre/   OT rooms, operation types, surgeries, charges
├── blood_bank/          blood units, requests, compatibility, issue records
├── insurance/           insurance companies and claims
├── documents/           patient documents and medical file uploads
├── medical_records/     medical-records dashboard and patient record access
├── templates/           shared and module templates
├── static/              CSS, JS, logo, favicon assets
└── media/               runtime uploads/barcodes/QR files (not committed)
```

## Demo Accounts

Created automatically by `python manage.py create_demo_accounts`.

Same password for **every** demo account: **`password`**

| Username | Role |
|---|---|
| admin | Main Super Admin |
| registration | Registration Counter |
| extension | EHS / Extension Registration Counter |
| ehs | EHS / Extension Registration Counter |
| cashier | Cash Counter |
| doctor | Doctor |
| pharmacy | Pharmacy |
| laboratory | Laboratory |
| radiology | Radiology Counter |
| insurance | Insurance Counter |
| admission | Ward / Admission |
| nursing | Nursing |
| operationtheatre | Operation Theatre |
| bloodbank | Blood Bank |
| accounts | Finance / Accounts |
| medicalrecords | Medical Records |
| staff | Hospital Staff |
| departmenthead | Department Head / Sub-Admin |

Total demo staff users: **18**.

Safe to re-run — updates password/role instead of duplicating if accounts already exist.

## Implemented module summary

This codebase contains the integrated Hospital Management System modules requested for production readiness:

- Registration and EHS/Extension registration with shared patient identity.
- Patient barcode/QR lookup and Hospital ID based search.
- Patient portal, OPD visit/token workflow, and appointment/booking bridge.
- Doctor consultation, prescription, referral, lab/radiology/admission/nursing/OT/blood-bank workflows.
- Cash counter billing, receipts, pending payments, refunds, staff discount and admission deposit credit.
- Laboratory, Radiology, Pharmacy, Admissions/Ward, Nursing, Operation Theatre, Blood Bank, Insurance and Medical Records modules.
- Staff profile, staff barcode, attendance, Nepali-calendar-style attendance view, leave requests/review and payroll/salary records.
- Finance/Accounts reporting, extension fee management, department revenue and payroll reports.
- Comprehensive reports with date filters, search, print, PDF export and Excel export.
- Super Admin backup center with database, media, full backup, restore guidance/history and cloud-ready deployment notes.

## Notes

- Each module (Billing, Pharmacy, Laboratory, Admission, Insurance) now generates
  its own unique rectangular barcode on its own records, separate from the
  Patient's square QR code. Run `pip install -r requirements.txt` (adds
  `python-barcode`) then `python manage.py migrate` to pick this up.

- Uses SQLite by default - zero extra database setup needed.
- `DEBUG=True` by default for local development; set `DJANGO_DEBUG=False` and a
  real `DJANGO_SECRET_KEY` before any real deployment.
- All sequential IDs (Patient, Visit receipt, Appointment, Bill, Pharmacy sale,
  Insurance claim, Admission, Radiology request) are generated inside atomic,
  row-locked transactions so concurrent activity across counters can never collide.
- eSewa credentials in `.env.example` are the public eSewa **test/sandbox**
  merchant code and secret - replace with your live merchant credentials before
  going live, and double-check eSewa's current merchant documentation, since
  payment gateway APIs can change.

