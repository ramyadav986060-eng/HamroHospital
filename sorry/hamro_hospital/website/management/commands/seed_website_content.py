import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from departments.models import Department, DepartmentUnit
from doctors.models import Doctor, DoctorSchedule, Weekday
from website.models import MedicalService, Announcement

# (service name, description, matching Department name or None)
MEDICAL_SERVICES = [
    ('Emergency', 'Round-the-clock emergency care for accidents, trauma, and critical conditions.', 'Emergency'),
    ('General Medicine', 'Diagnosis and treatment of common adult illnesses and chronic conditions.', 'General OPD'),
    ('Orthopedics', 'Care for bones, joints, ligaments, and the musculoskeletal system.', 'Orthopedics'),
    ('ENT', 'Diagnosis and treatment of ear, nose, and throat conditions.', 'ENT'),
    ('Neurology', 'Diagnosis and management of brain, spine, and nervous system disorders.', 'Neurology'),
    ('Neurosurgery', 'Surgical treatment of brain, spine, and nervous system conditions.', 'Neurology'),
    ('Cardiology', 'Heart health checkups, diagnostics, and cardiovascular treatment.', 'Cardiology'),
    ('Pediatrics', 'Healthcare for infants, children, and adolescents.', 'Pediatrics'),
    ('Gynecology', "Comprehensive care for women's reproductive health.", 'Gynecology'),
    ('Dermatology', 'Treatment for skin, hair, and nail conditions.', 'Dermatology'),
    ('Urology', 'Care for the urinary tract and male reproductive system.', 'Urology'),
    ('Ophthalmology', 'Complete eye care, from checkups to surgery.', 'Ophthalmology'),
    ('Psychiatry', 'Mental health assessment, counselling, and treatment.', 'Psychiatry'),
    ('Dental', 'General and cosmetic dental care.', 'Dental'),
    ('ICU', 'Critical care and continuous monitoring for seriously ill patients.', 'ICU'),
    ('Laboratory', 'Blood tests and other diagnostic lab investigations.', 'Laboratory'),
    ('Pharmacy', 'In-house dispensing of prescribed medicines.', 'Pharmacy'),
    ('Radiology', 'X-ray, ultrasound, CT, and other diagnostic imaging.', 'Radiology'),
    ('General & Laparoscopic Surgery', 'Elective and emergency surgical procedures, including minimally invasive laparoscopic surgery.', 'Surgery'),
    ('Obstetrics & Maternity Care', 'Antenatal checkups, delivery care, and postnatal support.', 'Obstetrics'),
    ('Physiotherapy & Rehabilitation', 'Physical therapy for injury recovery, mobility, and post-surgical rehabilitation.', 'Physiotherapy'),
    ('Oncology (Cancer Care)', 'Cancer screening, diagnosis, and treatment planning.', 'Oncology'),
    ('Pathology', 'Tissue and specimen analysis to diagnose disease.', 'Pathology'),
    ('Gastroenterology', 'Diagnosis and treatment of digestive system disorders.', 'Gastroenterology'),
]

ANNOUNCEMENTS = [
    ('Online Appointments Now Available', 'Book your Hospital Extension appointment online, anytime.', Announcement.Category.APPOINTMENT),
    ('Pay Online with eSewa', 'You can now pay hospital bills and appointment fees through eSewa.', Announcement.Category.PAYMENT),
    ('Extended OPD Hours', 'OPD registration counters are now open until 2:00 PM, Sunday to Thursday.', Announcement.Category.NOTICE),
    ('Public Holiday Notice', 'OPD services will run on a limited schedule during upcoming public holidays. Emergency is open 24/7.', Announcement.Category.HOLIDAY),
    ('New Service: Radiology Home Reports', 'Radiology reports are now available for download from the Patient Portal.', Announcement.Category.SERVICE),
]

# Departments that get an explicit Unit 1 / Unit 2 split for schedule demo purposes
DEPARTMENTS_WITH_UNITS = ['General OPD', 'Orthopedics', 'Cardiology', 'Pediatrics', 'Gynecology', 'Dermatology']

WEEKDAY_CODES = [code for code, _ in Weekday.choices]  # sun..sat, matches Nepal week


class Command(BaseCommand):
    help = (
        "Seed demo Medical Services, public Announcements, Department Units, and "
        "structured Doctor Schedules on top of the existing departments/doctors. "
        "Idempotent — safe to run multiple times."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_medical_services()
        self._seed_announcements()
        self._seed_department_units()
        self._seed_doctor_schedules()

    def _seed_medical_services(self):
        created = 0
        for order, (name, description, dept_name) in enumerate(MEDICAL_SERVICES):
            department = Department.objects.filter(name=dept_name).first() if dept_name else None
            _, was_created = MedicalService.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'department': department,
                    'icon_class': (department.icon_class if department else 'bi bi-heart-pulse'),
                    'display_order': order,
                },
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f'Medical Services: {created} created ({MedicalService.objects.count()} total).'
        ))

    def _seed_announcements(self):
        created = 0
        now = timezone.now()
        for title, message, category in ANNOUNCEMENTS:
            _, was_created = Announcement.objects.get_or_create(
                title=title,
                defaults={'message': message, 'category': category, 'is_active': True, 'publish_at': now},
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f'Announcements: {created} created ({Announcement.objects.count()} total).'
        ))

    def _seed_department_units(self):
        created = 0
        for dept_name in DEPARTMENTS_WITH_UNITS:
            department = Department.objects.filter(name=dept_name).first()
            if not department:
                continue
            for unit_name in ['Unit 1', 'Unit 2']:
                _, was_created = DepartmentUnit.objects.get_or_create(
                    department=department, name=unit_name,
                )
                created += was_created
        self.stdout.write(self.style.SUCCESS(
            f'Department Units: {created} created ({DepartmentUnit.objects.count()} total).'
        ))

        # Assign existing doctors in those departments to a unit round-robin, if unset.
        assigned = 0
        for dept_name in DEPARTMENTS_WITH_UNITS:
            department = Department.objects.filter(name=dept_name).first()
            if not department:
                continue
            units = list(department.units.all())
            if not units:
                continue
            for i, doctor in enumerate(department.doctors.filter(unit__isnull=True)):
                doctor.unit = units[i % len(units)]
                doctor.save(update_fields=['unit'])
                assigned += 1
        self.stdout.write(self.style.SUCCESS(f'Doctors assigned to a unit: {assigned}.'))

    def _seed_doctor_schedules(self):
        """
        Convert each doctor's existing free-text available_days / time-range
        into structured per-weekday DoctorSchedule rows, so the new
        department/doctor pages have real schedule data to show. Leaves the
        original available_days/available_time_start/end fields untouched.
        """
        created = 0
        default_start = datetime.time(9, 0)
        default_end = datetime.time(15, 0)
        for doctor in Doctor.objects.filter(is_active=True):
            if doctor.schedules.exists():
                continue
            codes = [c.strip() for c in doctor.available_days.split(',') if c.strip()] or ['sun', 'mon', 'tue', 'wed', 'thu']
            start = doctor.available_time_start or default_start
            end = doctor.available_time_end or default_end
            for code in codes:
                if code not in WEEKDAY_CODES:
                    continue
                _, was_created = DoctorSchedule.objects.get_or_create(
                    doctor=doctor, weekday=code,
                    defaults={'start_time': start, 'end_time': end},
                )
                created += was_created
        self.stdout.write(self.style.SUCCESS(f'Doctor Schedule rows: {created} created.'))
