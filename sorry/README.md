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
password
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

## Completed production-ready modules

- Patient registration, OPD visit/token workflow, patient barcode/QR lookup, and patient portal.
- EHS / Extension Service registration using the same patient database with separated visit/revenue marking.
- Doctor consultation, prescriptions, referrals, department service orders, and patient timeline.
- Laboratory, Radiology, Pharmacy, Admissions/Ward, Nursing, Operation Theatre, Blood Bank, Insurance, Medical Records, Billing/Cash Counter, Finance, Attendance, Leave, and Payroll modules.
- Comprehensive reports with date filters, search, sorting, print, PDF export, and Excel export.
- Staff identity with Staff ID/barcode, staff profile, attendance history, leave history, payroll and salary slips.
- Notifications and audit trail foundations for sensitive workflows.

## User roles and permission summary

- **Main Super Admin**: full access to all modules, settings, staff, finance, reports, dashboards, and administration.
- **Finance / Accounts**: revenue, billing summaries, extension fees, attendance reports, payroll, salary history/payment records, and financial exports. Clinical records remain outside normal finance workflow.
- **Department Head / Sub-Admin**: own-department staff list/edit, own-department attendance review, own-department leave review, own-department referrals/notifications, and department-scoped reports only. No finance, payroll, global settings, registration, or other-department confidential data.
- **Registration / EHS Counter**: patient lookup, patient registration, OPD/EHS visit creation, tokens, and registration receipts.
- **Cashier**: billing, payment collection, pending bills, receipts, refunds, and bill lookup.
- **Doctor**: consultation queue, patient search, clinical notes, prescriptions, referrals, lab/radiology/admission/nursing/OT/blood-bank requests.
- **Laboratory / Radiology / Pharmacy / Nursing / Admission / Blood Bank / Operation Theatre / Insurance / Medical Records**: module-specific operational dashboards and workflows.
- **Hospital Staff**: own profile, staff card/barcode, attendance, leave requests/history, notifications, and password change.
- **Patient**: portal dashboard, profile, patient card, visit booking, timeline, visits, bills, lab/radiology report viewing where available.

## Important workflows

- Registration -> OPD token -> Doctor consultation -> Department referrals/service orders -> Cash Counter payment -> Department completion -> Reports.
- Doctor -> Laboratory/Radiology/Pharmacy/Admission/Nursing/Blood Bank/Operation Theatre referrals with department notification and patient timeline updates.
- Attendance -> Leave request -> Department Head review -> Super Admin override for leave-limit exceptions.
- Finance -> Payroll generation -> Salary payment -> Salary slip/report export.
- Billing -> Receipts -> Reports and revenue dashboards.

## PostgreSQL deployment

SQLite is the default local development database. PostgreSQL is enabled entirely by environment variables, without changing code:

```env
DJANGO_DB_ENGINE=postgres
POSTGRES_DB=hamro_hospital
POSTGRES_USER=hamro_hospital
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=60
```

Then run:

```bash
python manage.py migrate
python manage.py create_demo_accounts
python manage.py collectstatic
```

Use the included `POSTGRESQL_MIGRATION_GUIDE.pdf` for data migration from SQLite to PostgreSQL.

## Final status

The system has passed final code checks, clean migration verification, workflow/report tests, report export checks, role dashboard smoke tests, and PostgreSQL settings validation. It is ready for acceptance testing and staged production configuration. External services such as Redis, Celery workers, eSewa/Khalti/FonePay live credentials and fingerprint device SDK/API must be configured on the deployment server.

## Easiest local start

For Windows, double-click or run:

```bat
run.bat
```

For Linux/macOS:

```bash
chmod +x run.sh
./run.sh
```

These scripts will:

1. Create `.venv` if missing.
2. Install requirements.
3. Copy `.env.example` to `.env` if needed.
4. Run migrations.
5. Ensure demo accounts exist.
6. Start the Django development server.

After the first run, daily development is normally just:

```bash
python manage.py runserver
```

or run the script again.



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

## Environment template

The project includes:

```text
hamro_hospital/.env.example
```

Copy it to:

```text
hamro_hospital/.env
```

and update values for PostgreSQL, Redis, Celery, eSewa, email, SMS, and fingerprint device integration when deploying live.

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

## Part 9 Department Head and Leave Management Improvements Added

- Department Head is now treated as a Hospital Staff member with `is_department_head=True`, not a separate demo user type.
- Department Head uses the same staff profile, staff dashboard, staff card, barcode, QR code, attendance, leave, medical portal and staff actions as normal staff.
- Role display shows Department Head when a staff member is designated as department head.
- Only Main Super Admin can assign/remove Department Head status through staff role management.
- Department Heads can view/manage staff in their own department but cannot change role/department-head privileges through the limited edit form.
- A Leave link is available in the main sidebar directly below Main Dashboard for staff and department heads.
- Leave request form now shows auto-filled Staff ID, Staff Name and Department, calculates number of leave days and supports optional document upload.
- Leave workflow routing:
  - Regular Staff → Department Head + Super Admin
  - Department Head → Super Admin only
- Department Heads cannot review their own leave requests.
- Leave notifications are sent for leave request submission, approval and rejection.
- Leave status remains Pending, Approved, Rejected or Cancelled and staff can track status from the Leave module.
- Department Heads receive no extra salary/payroll/billing permissions.

## Part 10 Final System-Wide Medical History and Portal Improvements Added

- Patient Portal login supports Patient ID + registered phone/email + password, and phone/email remains optional after account creation when Patient ID + password are valid.
- Patient Portal dashboard provides access to profile, online registration, OPD/EHS booking, visits, billing, insurance, admissions, lab/radiology, pharmacy, referrals/prescriptions and Medical History documents.
- Patient Portal profile editing is restricted to permitted fields only: email, address/local details, district, photo and approved remarks. Patient ID, registered name and registered phone are not editable from portal.
- Standalone Medical Records user/module remains removed; Medical History is now a feature inside patient, doctor and clinical workflows.
- Automatic Medical History document creation added through system signals for registrations, EHS/OPD visits, invoices, doctor notes, lab reports, radiology reports, pharmacy receipts, admissions, discharge summaries, nursing notes, surgery records, insurance claims and referrals.
- Patient Medical History documents can be viewed/downloaded by the patient portal but not modified/deleted by patients.
- Doctors and authorized clinical roles access Medical History through patient profile/document sections.
- Staff financial access remains restricted: staff cannot see hospital-wide revenue/cash collection/financial reports; salary/payment access is limited to own staff context or Finance/Super Admin workflows.
- Django Admin navigation was synchronized by removing active Medical Records app/role references.
- Universal patient search and staff lookup continue to support ID/barcode/QR/phone/name patterns where applicable.
