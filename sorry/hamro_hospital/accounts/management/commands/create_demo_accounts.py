import datetime
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Role, User, StaffAttendance, StaffSalaryProfile

DEMO_PASSWORD = 'password'

DEMO_USERS = {
    'admin': Role.SUPER_ADMIN,
    'registration': Role.REGISTRATION_COUNTER,
    'extension': Role.EXTENSION_COUNTER,
    'ehs': Role.EXTENSION_COUNTER,
    'cashier': Role.CASH_COUNTER,
    'doctor': Role.DOCTOR,
    'pharmacy': Role.PHARMACY,
    'laboratory': Role.LABORATORY,
    'radiology': Role.RADIOLOGY,
    'insurance': Role.INSURANCE,
    'admission': Role.WARD_ADMISSION,
    'nursing': Role.NURSING,
    'operationtheatre': Role.OPERATION_THEATRE,
    'bloodbank': Role.BLOOD_BANK,
    'accounts': Role.ACCOUNTS_DEPT,
    'medicalrecords': Role.MEDICAL_RECORDS,
    'staff': Role.HOSPITAL_STAFF,
    'departmenthead': Role.DEPARTMENT_HEAD,
}

DEMO_STAFF = [
    ('staff.ram', 'Ram', 'Shrestha', 'Front Desk Assistant', 'General Medicine', 'full_time'),
    ('staff.sita', 'Sita', 'Tamang', 'Lab Assistant', 'Laboratory', 'full_time'),
    ('staff.bikash', 'Bikash', 'Rai', 'Radiology Assistant', 'Radiology', 'full_time'),
    ('staff.mina', 'Mina', 'Gurung', 'Pharmacy Assistant', 'Pharmacy', 'full_time'),
    ('staff.arjun', 'Arjun', 'KC', 'Ward Helper', 'Admission', 'contract'),
    ('staff.nirmala', 'Nirmala', 'Thapa', 'Nursing Assistant', 'Nursing', 'full_time'),
    ('staff.prakash', 'Prakash', 'Adhikari', 'OT Technician', 'Operation Theatre', 'full_time'),
    ('staff.laxmi', 'Laxmi', 'Maharjan', 'Blood Bank Assistant', 'Blood Bank', 'part_time'),
    ('staff.suman', 'Suman', 'Bista', 'Insurance Desk Assistant', 'Insurance', 'full_time'),
    ('staff.kabita', 'Kabita', 'Khadka', 'Accounts Assistant', 'Finance', 'full_time'),
]


class Command(BaseCommand):
    help = f'Creates demo staff logins, realistic dummy staff, attendance and reports. Password: {DEMO_PASSWORD}'

    def handle(self, *args, **options):
        departments = self.ensure_departments()
        self.ensure_billable_services(departments)
        for username, role in DEMO_USERS.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': username.capitalize(), 'last_name': 'Demo', 'role': role, 'is_staff': True, 'is_superuser': (role == Role.SUPER_ADMIN)},
            )
            user.set_password(DEMO_PASSWORD)
            user.role = role
            user.is_staff = True
            if role == Role.SUPER_ADMIN:
                user.is_superuser = True
            if role == Role.DEPARTMENT_HEAD:
                user.department = departments.get('General Medicine')
                user.is_department_head = True
                user.designation = 'Department In-charge'
            elif role == Role.HOSPITAL_STAFF:
                user.department = departments.get('General Medicine')
                user.designation = 'Hospital Staff'
            user.save()
            self.stdout.write(self.style.SUCCESS(f"{'created' if created else 'updated'}: {username} ({role})"))
        self.create_realistic_staff(departments)
        self.create_sample_patients_and_reports()
        self.stdout.write(self.style.SUCCESS(f'\nDone. Password for all demo accounts: {DEMO_PASSWORD}'))

    def ensure_departments(self):
        from departments.models import Department
        names = ['General Medicine', 'Laboratory', 'Radiology', 'Pharmacy', 'Admission', 'Nursing', 'Operation Theatre', 'Blood Bank', 'Insurance', 'Finance']
        result = {}
        for name in names:
            dept, _ = Department.objects.get_or_create(name=name, defaults={'description': f'{name} Department', 'is_active': True})
            result[name] = dept
        return result


    def ensure_billable_services(self, departments):
        from website.models import HospitalService
        services = [
            ('LAB-BLOOD', 'Blood Test / CBC', 'Laboratory', 500), ('LAB-STOOL', 'Stool Test', 'Laboratory', 300),
            ('LAB-URINE', 'Urine Test', 'Laboratory', 250), ('LAB-CULTURE', 'Culture Test', 'Laboratory', 800),
            ('RAD-XRAY', 'X-Ray', 'Radiology', 700), ('RAD-ECG', 'ECG', 'Radiology', 500),
            ('RAD-ECHO', 'Echo', 'Radiology', 1500), ('RAD-USG', 'Ultrasound', 'Radiology', 1200),
            ('RAD-CT', 'CT Scan', 'Radiology', 6000), ('RAD-MRI', 'MRI', 'Radiology', 9000),
            ('RAD-DOP', 'Doppler', 'Radiology', 2000), ('RAD-MAM', 'Mammography', 'Radiology', 2500),
            ('BB-BLOOD', 'Blood Bank Service Charge', 'Blood Bank', 1000),
            ('OT-MINOR', 'Minor Operation Package', 'Operation Theatre', 5000),
            ('OT-MAJOR', 'Major Operation Package', 'Operation Theatre', 25000),
            ('PH-MED', 'Pharmacy Medicine Sale', 'Pharmacy', 100),
            ('GEN-OTHER', 'Other Hospital Service', 'General Medicine', 500),
        ]
        for code, name, dept_name, price in services:
            HospitalService.objects.update_or_create(
                service_code=code,
                defaults={'name': name, 'department': departments.get(dept_name), 'price': price, 'is_active': True},
            )

    def create_realistic_staff(self, departments):
        for username, first, last, designation, dept_name, employment_type in DEMO_STAFF:
            user, _ = User.objects.get_or_create(username=username, defaults={'first_name': first, 'last_name': last, 'role': Role.HOSPITAL_STAFF, 'is_staff': True})
            user.set_password(DEMO_PASSWORD)
            user.first_name = first
            user.last_name = last
            user.role = Role.HOSPITAL_STAFF
            user.department = departments.get(dept_name)
            user.designation = designation
            user.employment_type = employment_type
            user.is_staff = True
            user.is_active_staff = True
            user.save()
            profile, _ = StaffSalaryProfile.objects.get_or_create(staff=user)
            profile.per_day_salary = 1000
            profile.base_monthly_salary = 30000
            profile.save()
            self.create_attendance_for_staff(user)

    def create_attendance_for_staff(self, user):
        today = timezone.localdate()
        for offset in range(1, 21):
            day = today - datetime.timedelta(days=offset)
            if day.weekday() == 5:
                StaffAttendance.objects.update_or_create(staff=user, date=day, defaults={'status': StaffAttendance.Status.HOLIDAY, 'source': 'fingerprint', 'remarks': 'Saturday holiday'})
            elif offset % 7 == 0:
                StaffAttendance.objects.update_or_create(staff=user, date=day, defaults={'check_in': timezone.make_aware(datetime.datetime.combine(day, datetime.time(9, 0))), 'check_out': timezone.make_aware(datetime.datetime.combine(day, datetime.time(13, 30))), 'source': 'fingerprint'})
            elif offset % 11 == 0:
                StaffAttendance.objects.update_or_create(staff=user, date=day, defaults={'status': StaffAttendance.Status.ABSENT, 'source': 'fingerprint', 'remarks': 'No biometric punch'})
            else:
                StaffAttendance.objects.update_or_create(staff=user, date=day, defaults={'check_in': timezone.make_aware(datetime.datetime.combine(day, datetime.time(8, 45))), 'check_out': timezone.make_aware(datetime.datetime.combine(day, datetime.time(18, 0))), 'source': 'fingerprint'})

    def create_sample_patients_and_reports(self):
        from patients.models import Province, District, Patient
        from documents.models import PatientDocument, DocumentCategory
        province, _ = Province.objects.get_or_create(number=3, defaults={'name': 'Bagmati Province'})
        district, _ = District.objects.get_or_create(province=province, name='Kathmandu')
        uploader = User.objects.filter(role=Role.MEDICAL_RECORDS).first() or User.objects.filter(is_superuser=True).first()
        names = [('Aarav','Sharma'),('Anita','Rai'),('Bimala','Tamang'),('Dipak','Shrestha'),('Elina','Gurung'),('Kiran','KC'),('Maya','Thapa'),('Nabin','Maharjan'),('Puja','Bista'),('Ramesh','Khadka')]
        for i, (first, last) in enumerate(names, start=1):
            patient, _ = Patient.objects.get_or_create(
                phone_number=f'98000010{i:02d}',
                defaults={'first_name': first, 'last_name': last, 'gender': Patient.Gender.FEMALE if i % 2 else Patient.Gender.MALE, 'date_of_birth': datetime.date(1990+i, 1, min(i, 28)), 'age_at_registration': f'{34-i%10} Years', 'district': district, 'created_by': uploader},
            )
            if not patient.documents.filter(title__startswith='Sample Medical Report').exists():
                pdf = self.make_report_pdf(patient, i)
                doc = PatientDocument(patient=patient, category=DocumentCategory.OTHER, title=f'Sample Medical Report {i}', uploaded_by=uploader, uploaded_by_role=getattr(uploader, 'role', ''), department_note='Medical Records', remarks='Demo report opens in PDF preview.')
                doc.file.save(f'sample_medical_report_{i}.pdf', ContentFile(pdf), save=True)

    def make_report_pdf(self, patient, index):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.setFont('Helvetica-Bold', 16)
        p.drawString(72, 780, 'Hamro Hospital - Sample Medical Report')
        p.setFont('Helvetica', 11)
        rows = [f'Report No: DEMO-MR-{index:03d}', f'Patient: {patient.full_name}', f'Patient ID: {patient.patient_code}', f'Phone: {patient.phone_number}', 'Findings: Demo clinical summary for preview and download testing.', 'Impression: Stable. Follow up as advised.']
        y = 740
        for row in rows:
            p.drawString(72, y, row)
            y -= 24
        p.showPage(); p.save(); buffer.seek(0)
        return buffer.getvalue()
