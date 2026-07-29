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



## HM Staff, Attendance, Leave and Payroll Update

### Staff login

Staff can log in using either their normal username or their generated Staff ID, for example:

```text
Username / Staff ID: STF000017
Password: password
```

The login form accepts both values and maps Staff ID to the correct staff account.

### Staff dashboard/profile

Each staff user can access their own staff dashboard/profile at:

```text
/accounts/staff/profile/
```

Staff can see:

- Personal profile and staff barcode.
- Staff ID.
- Department and designation.
- Employment type.
- Attendance history and attendance calendar.
- Leave history.
- Paid leave limit, used leave, and remaining leave balance.
- Personal notifications.

Normal staff can view only their own attendance and cannot edit attendance records.

### Biometric attendance workflow

Attendance salary calculation is based on biometric/fingerprint attendance records only.

Supported biometric inputs:

```text
/accounts/staff/attendance/device-punch/
python manage.py sync_fingerprint_attendance attendance.csv
```

Rules:

- First fingerprint scan starts attendance.
- Next fingerprint scan ends attendance.
- Working hours are calculated automatically.
- Full day requires 9 hours by default.
- Full day is marked Present.
- Less than required working hours is marked Partial / Half Day.
- Approved leave is shown as leave.
- Rejected leave appears red on the attendance calendar.

Calendar colors:

- Green = Present / Full Attendance.
- Yellow = Half Day / Partial Attendance.
- Red = Absent.
- Green = Approved Leave.
- Red = Rejected Leave.

Manual attendance correction/punch page is restricted to Main Super Admin only. Departments and staff cannot edit biometric attendance records.

### Leave workflow

Default paid leave limit is 5 paid days per year and is configurable by Main Super Admin in hospital settings.

Workflow:

1. Staff submits leave request.
2. Department Head receives notification and approves/rejects for own department.
3. Staff receives notification when leave is approved or rejected.
4. If leave exceeds paid yearly limit, Main Super Admin override is required.

Leave URLs:

```text
/accounts/staff/leave/
/accounts/staff/leave/request/
/accounts/staff/leave/<leave_id>/review/
```

### Payroll and salary rules

Only Finance and Main Super Admin can view salary amounts, salary profiles, payroll reports, and payment records.

Departments and Department Heads cannot view salary amounts and cannot process payroll.

Payroll is generated from biometric/fingerprint attendance records only:

- Full day = configured per-day salary.
- Half day = 50% of configured per-day salary.
- Approved leave = paid day, within leave policy.
- Absent day = unpaid when using per-day salary; deducted when using monthly salary.
- Overtime can be calculated if overtime rate is configured.

Payroll URLs for Finance/Super Admin:

```text
/accounts/staff/salary/profiles/
/accounts/staff/salary/generate/
/accounts/staff/salary/payments/
/accounts/staff/salary/export/
```

Finance payroll page includes search and filters for all staff, department, employment type, and individual staff.

### Notifications added

Notifications are sent for:

- Leave approved.
- Leave rejected.
- Salary processed.
- Existing leave request and system announcement workflows.

### Permission matrix summary

| Role | Attendance | Leave | Salary/Payroll |
|---|---|---|---|
| Super Admin | View and correct | Full approve/override | Full access |
| Finance | View attendance summaries | View/report as needed | Full payroll/payment access |
| Department Head | View own department only | Approve/reject own department | No access |
| Staff | View own only | Request/view own | No access to salary records |

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


## Part 1 Improvements Added

- Manage Doctor page now includes a doctor/name search box and department filter.
- Finance dashboard defaults detailed records to the last 24 hours; older records are preserved and appear when date filters are applied.
- Demo data creation now adds 10 realistic staff users across multiple hospital departments.
- Demo data creation now generates biometric attendance records for those staff.
- Staff card has been aligned with the patient-card print style and includes a Back button.
- Staff profile includes a Back button.
- Attendance calendar is interactive for Main Super Admin: choose a staff member, select Present / Approved Leave / Half Day / Absent, then click a date and the color updates immediately.
- Attendance colors: Green Present, Light Green Approved Leave, Yellow Half Day, Red Absent or Rejected Leave.
- Saturdays/configured weekly holidays are highlighted as holidays.
- Patient Medical Reports now show real document PDF records with View and Download actions.
- Demo data creation now adds 10 sample patient medical report PDFs that open in browser preview and download correctly.
- Patient registration includes the existing Choose Photo / Upload Photo field.
- Registration dashboard now has a Recent Patients section showing only patients registered in the last 24 hours; older patients are not deleted and remain searchable by filters.

Run the following to create/update demo users, dummy staff, attendance and sample reports:

```bash
python manage.py create_demo_accounts
```

## Part 2 Cash Counter Improvements Added

- Cash Counter dashboard cards are now clickable and open detailed billing drill-down pages.
- Drill-down pages include search, date filter, payment method filter, patient filter, department filter, and Close button.
- Cash Counter dashboard and Today's Collections default to latest 24 hours; older records are hidden from dashboard only and remain retrievable through filters.
- Large amounts use compact display through the shared short amount formatter, with full details available in drill-down pages.
- Added a dedicated Payment Section on Cash Counter dashboard with patient search and department payment category buttons.
- Payment categories include Laboratory, Radiology, Blood Bank, ECG/Ultrasound, CT/MRI, Operation Theater, Pharmacy, and Other Services.
- Laboratory and Radiology billing screens now show category-specific guidance, service search, checkbox selection, and selected-row highlighting.
- Operation Theater payment screen includes review notes, referring department/doctor fields, operation category, staff discount, insurance fields, and supporting document upload.
- Staff discount remains configurable by Super Admin and is applied by scanning/entering Staff ID.
- Invoice/receipt page now includes a direct PDF download button.
- Demo setup now creates sample billable hospital services for lab, radiology, blood bank, OT, pharmacy, and other services.

## Part 3 Registration, EHS Service and Patient Portal Improvements Added

- Patient registration includes optional patient photo upload; registration works without a photo and stores photo on the patient profile when uploaded.
- Public/portal wording has been standardized to **EHS Service** to avoid duplicate Extension/EHS module confusion. Existing URLs remain compatible, but labels now show EHS Service.
- EHS Service ticket pricing is configurable by Main Super Admin in Hospital Settings:
  - EHS New Ticket Fee
  - EHS Follow-up Ticket Fee
  - EHS Additional Charges Note
- EHS Service registration uses its own pricing and remains separated from General OPD queues.
- Patient Portal now has an **Online Registration** page with two choices:
  - General OPD → General Registration Counter
  - EHS Service → EHS Service Counter
- Patient Portal login now accepts Hospital ID + password, with phone/email optional for additional verification, fixing login problems after generated registration credentials.
- Patient Portal dashboard includes Online Registration and keeps medical/billing access. Patient card print/generate actions remain restricted by staff-side permissions.
- Patient attendance is not present in the portal; attendance remains exclusively inside the Staff Module.

## Part 4 Doctor Dashboard and Referral Improvements Added

- Doctors are treated as hospital staff and can open their Hospital Staff ID Card from the Doctor Dashboard.
- Staff ID Card includes hospital branding, staff/doctor role, department, contact, staff QR code and staff barcode.
- Staff QR code field added for every staff user; existing staff receive QR when saved/updated.
- Doctor OPD Visits card is clickable and opens a date/search drill-down page showing today's OPD visits by default, with historical retrieval by selected date.
- Referral creation now uses fast patient lookup by barcode/QR value, Patient ID, phone number or patient name.
- Patient details auto-fill on referral form: Patient ID, full name, age/gender, blood group, address, phone, registration number and medical record hint.
- Referral destination department has a search field for fast lookup.
- Referral form now includes diagnosis, working clinical impression, referral reason, requested services, optional fee, clinical notes, supporting attachment and send action.
- Pharmacy referral supports prescribed medicines, dosage, frequency, duration and notes.
- Admission referral stores admission reason/clinical details/ward notes and notifies the Admission role immediately.
- Department referrals continue to notify Laboratory, Radiology, Pharmacy, Nursing, Admission, Operation Theatre and Blood Bank according to type.

## Part 5 Pharmacy Improvements Added

- Pharmacy dashboard duplicate Incoming Doctor Referral panels were removed.
- Only one Incoming Doctor Referrals section remains, positioned below Find Patient to Dispense.
- Pharmacy dashboard layout is now organized as: Dashboard Summary, Find Patient to Dispense, Incoming Doctor Referrals, Dispensing Area, Dispensing History.
- Medicine dispensing page now has real-time medicine search.
- Medicine search supports medicine name, generic name, brand name, medicine code/barcode, batch number and strength.
- Medicine list filters instantly while typing to avoid scrolling through large inventories.
- Selected medicine rows highlight immediately.
- Added Scroll to Top and Scroll to Bottom controls for long medicine lists.
- Existing dispensing workflow is preserved.

## Part 6 Admission Improvements Added

- Admission dashboard summary cards are clickable and open detailed views with search, date filters, and Close button.
- Admission dashboard defaults to latest 24-hour admission activity; records are never deleted and can be retrieved by date/range.
- Admission charge references are configurable by Main Super Admin through Hospital Settings: admission base fee, ICU daily charge, cabin/private daily charge, and ward daily rates.
- Ward/bed pricing remains controlled through Super Admin-managed Ward daily rates; no admission pricing is hardcoded in admission workflow.
- Admit Patient form now includes patient search/information, department, referring/admitting doctor, ward, available bed, diagnosis, admission reason, admission date/time and notes.
- Bed selection only lists unoccupied beds and updates when admissions/transfers/discharges change occupancy.
- Discharge form now includes professional follow-up fields: follow-up date, department, doctor, instructions, investigations and notes.
- Discharge summary/package PDF redesigned with hospital header, patient details, admission details, treatment summary, medicines, diet/activity/emergency advice, follow-up section, financial summary, barcode and signature/stamp areas.
- Discharge checklist workflow remains mandatory before discharge completion.

## Part 7 Operation Theater Improvements Added

- Operation Theater patient information cards were redesigned to prevent long SURG/OP/EN numbers from overlapping or wrapping badly.
- OT dashboard summary cards are clickable and open detailed pages with search, date filter and Close button.
- OT dashboard defaults to latest 24-hour records; old records are not deleted and can be retrieved by filters.
- Patient lookup in OT supports patient ID/barcode/QR value, phone and name through the existing search and scanner pattern.
- OT slip was redesigned with hospital logo, patient details, patient barcode, patient QR, doctor, department, OT room, scheduled procedure, date/time, ward/bed and signature areas.
- Operation charges are based on Super Admin-managed Operation Types and synced billable hospital services; no cashier-entered fixed pricing is required.
- "ServiceOrder Queue" wording in Operation Theater dashboard was replaced with Operation Theater Payment / Active payment records.
- Operation Theater Payment redirects to the standard surgery billing workflow with staff discount and insurance support.
- OT revenue detail page follows the same search/date/close behavior as other finance modules.

## Part 8 Staff Module and Salary Management Improvements Added

- Standalone Medical Records role/module was removed from active routing and demo users. Medical information remains available through patient profile sections, documents, doctors, admission, laboratory, radiology and patient portal.
- Hospital staff profile now includes staff photo, Staff ID, unique barcode, unique QR code, department, designation, contact, address, emergency contact, blood group and employment status.
- Staff ID Card redesigned as a professional Hospital Staff ID Card with front/back information, hospital branding, staff photo, barcode and QR code.
- Staff dashboard/profile now uses staff-specific actions: View Staff Card, Attendance, Leave Record, Change Password, Book OPD/EHS as Patient and Staff Medical Portal.
- Staff can access medical care through the Patient Portal/Online Registration flow while attendance remains exclusive to the Staff Module.
- Staff attendance retains monthly records, date range filters, department filter, search, All Time-style retrieval via reports, PDF/Excel export and history.
- Dedicated Salary Management section is available in Accounts via Staff Salary Profiles and Salary Payments.
- Salary configuration now includes salary type, effective date, bank account number, bank name, daily salary or monthly salary and future bank-transfer status fields.
- Salary payments record bank transfer readiness/status and transaction reference for future banking integration.
- Salary filters support staff search, department, employment type and individual staff.
- Long staff lists include Scroll to Top and Scroll to Bottom controls.
- Departments and Department Heads remain blocked from salary/payroll access.
