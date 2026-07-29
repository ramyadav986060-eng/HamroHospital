"""
seed_all - the ONE master command for the complete Hamro Hospital demo database.

    python manage.py seed_all

What it does, in order:
  1. Runs every existing prerequisite seeder if its data isn't present yet
     (seed_nepal_address, seed_demo_data, create_demo_accounts,
     seed_checkpoint3_data, seed_final_requirements). Safe / idempotent -
     each of those already uses get_or_create internally.
  2. Tops up Doctors to --doctors (default 150), spread realistically across
     every department.
  3. Tops up Patients to --patients (default 500), each with a full Nepal
     address, and ~35% carrying insurance.
  4. Generates OPD Visits + Consultations + Prescriptions (+ Lab/Radiology
     requests, many completed with reports) up to --visits (default 5000),
     spread across the last 3 years so the hospital "feels" established.
  5. Generates online Appointment bookings (paid via eSewa, with QR) up to
     --appointments (default 5000), about half later linked to a real
     Patient (i.e. they showed up and were registered).
  6. Generates Bills (OPD/Pharmacy/Lab/Radiology/IPD, each with its own
     barcode) up to --bills (default 4000).
  7. Generates Pharmacy dispensing sales up to --pharmacy-sales (4000),
     linked to real prescriptions where possible.
  8. Generates Admissions (with ward/bed allocation, ~55% already
     discharged) up to --admissions (500), plus a Surgery record for ~30%
     of them, plus a matching IPD Bill.
  9. Generates Insurance Claims up to --insurance-claims (300), only for
     patients who actually carry insurance.
 10. Generates a follow-up Visit for ~15% of completed visits, and a
     PatientDocument for every Lab/Radiology report and every Admission
     discharge summary, so nothing on a patient's profile is ever empty.

Every number is a *target*, not an increment - re-running the command tops
up whatever is missing rather than duplicating data, so it is always safe
to run again (e.g. after a fresh `migrate`).
"""
import datetime
import random

from django.core import management
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from django.core.management.base import BaseCommand

FIRST_NAMES_M = [
    'Ram', 'Shyam', 'Hari', 'Gopal', 'Krishna', 'Bishnu', 'Ganesh', 'Mahesh',
    'Suresh', 'Ramesh', 'Dinesh', 'Mahendra', 'Narendra', 'Surendra', 'Rajendra',
    'Bikash', 'Anup', 'Prakash', 'Dipesh', 'Sandip', 'Nabin', 'Kiran', 'Rajesh',
    'Bishal', 'Sujan', 'Milan', 'Rohit', 'Ashok', 'Deepak', 'Narayan', 'Bimal',
    'Buddha', 'Santosh', 'Sanjay', 'Sunil', 'Manoj', 'Binod', 'Bharat',
    'Yagya', 'Keshav', 'Madhav', 'Basudev', 'Damodar', 'Umesh', 'Yubraj', 'Padam',
    'Tek', 'Man', 'Him', 'Jit',
]
FIRST_NAMES_F = [
    'Sita', 'Gita', 'Radha', 'Laxmi', 'Kamala', 'Bimala', 'Nirmala', 'Sarada',
    'Sunita', 'Sarita', 'Anita', 'Rita', 'Puja', 'Manisha', 'Sabina', 'Kabita',
    'Sushila', 'Sabitri', 'Rekha', 'Pratima', 'Sangita', 'Anjali', 'Devi',
    'Parbati', 'Durga', 'Saraswati', 'Ganga', 'Kalpana', 'Sarala', 'Renuka', 'Meera',
    'Indira', 'Shova', 'Shanti', 'Kamana', 'Bina', 'Bandana', 'Roshani',
    'Sarmila', 'Goma', 'Bishnu Maya', 'Him Kumari', 'Man Kumari', 'Til Kumari',
]
LAST_NAMES = [
    'Sharma', 'Koirala', 'Thapa', 'Gurung', 'Basnet', 'Rai', 'Shrestha', 'Adhikari',
    'Poudel', 'Khadka', 'Magar', 'Tamang', 'Bhattarai', 'Karki', 'Bista', 'Lama',
    'Chhetri', 'Subedi', 'Neupane', 'Regmi', 'Acharya', 'Dahal', 'Bhandari',
    'Pandey', 'Joshi', 'Baral', 'Ojha', 'Devkota', 'Khatri', 'Rana', 'Malla',
    'Yadav', 'Mahato', 'Sah', 'Limbu', 'Rijal', 'Paudel', 'Ghimire', 'Bogati',
]
QUALIFICATIONS = [
    'MBBS', 'MBBS, MD', 'MBBS, MS', 'MBBS, MD (Internal Medicine)',
    'MBBS, MS (Surgery)', 'MBBS, DM (Cardiology)', 'MBBS, MCh',
    'MBBS, MD (Pediatrics)', 'MBBS, MD (Gynecology & Obstetrics)',
    'MBBS, DNB', 'MBBS, MD (Radiology)', 'MBBS, MD (Anesthesiology)',
]
DIAGNOSES = [
    'Common Cold', 'Viral Fever', 'Hypertension', 'Type 2 Diabetes Mellitus',
    'Gastritis', 'Acute Bronchitis', 'Migraine', 'Urinary Tract Infection',
    'Lower Back Pain', 'Allergic Rhinitis', 'Osteoarthritis', 'Anemia',
    'Bronchial Asthma', 'Peptic Ulcer Disease', 'Dyslipidemia', 'Hypothyroidism',
    'Acute Gastroenteritis', 'Chronic Kidney Disease (Stage 2)', 'Pneumonia',
    'Dengue Fever (Suspected)', 'Typhoid Fever', 'Conjunctivitis', 'Dermatitis',
    'Anxiety Disorder', 'Iron Deficiency Anemia', 'Sinusitis', 'Tonsillitis',
]
CHIEF_COMPLAINTS = [
    'Fever for 3 days', 'Cough and cold', 'Abdominal pain', 'Headache',
    'Body ache and weakness', 'Chest discomfort', 'Difficulty breathing',
    'Joint pain', 'Burning micturition', 'Vomiting and loose motion',
    'Skin rash', 'Routine health checkup', 'Follow-up visit', 'Dizziness',
    'Loss of appetite', 'Back pain', 'Blurred vision', 'Sore throat',
]
DOSAGES = ['1 tablet', '2 tablets', '1 capsule', '5ml', '10ml', '1 sachet']
FREQUENCIES = ['Once daily (OD)', 'Twice daily (BID)', 'Thrice daily (TID)', 'Every 8 hours', 'At bedtime (HS)']
DURATIONS = ['3 days', '5 days', '7 days', '10 days', '14 days', '1 month']
INSTRUCTIONS = ['After meals', 'Before meals', 'With plenty of water', 'Empty stomach', '']

DEMO_PDF_BYTES = b'%PDF-1.4\n%Demo placeholder file generated by seed_all.\n'


def rand_past_date(days_back_max=3 * 365):
    return timezone.now().date() - datetime.timedelta(days=random.randint(0, days_back_max))


def rand_past_datetime(days_back_max=3 * 365):
    d = rand_past_date(days_back_max)
    return timezone.make_aware(datetime.datetime.combine(
        d, datetime.time(hour=random.randint(8, 18), minute=random.randint(0, 59)),
    ))


class Command(BaseCommand):
    help = 'Master command: seeds the ENTIRE interconnected Hamro Hospital demo database in one shot.'

    def add_arguments(self, parser):
        parser.add_argument('--patients', type=int, default=50, help='Target total (small complete demo dataset).')
        parser.add_argument('--doctors', type=int, default=15)
        parser.add_argument('--appointments', type=int, default=50)
        parser.add_argument('--visits', type=int, default=50)
        parser.add_argument('--bills', type=int, default=50)
        parser.add_argument('--pharmacy-sales', type=int, default=50)
        parser.add_argument('--admissions', type=int, default=50)
        parser.add_argument('--insurance-claims', type=int, default=50)
        parser.add_argument(
            '--skip-prereqs', action='store_true',
            help='Skip running the prerequisite seed commands (assume already seeded).',
        )

    def handle(self, *args, **options):
        t0 = timezone.now()
        if not options['skip_prereqs']:
            self._run_prereqs()

        from patients.models import Patient, District, InsuranceCompany, InsuranceCategory, Visit
        from departments.models import Department
        from doctors.models import Doctor
        from accounts.models import User

        districts = list(District.objects.all())
        departments = list(Department.objects.filter(is_active=True))
        ins_categories = list(InsuranceCategory.objects.all())
        if not districts or not departments:
            self.stderr.write(self.style.ERROR('Prerequisites missing districts/departments even after seeding.'))
            return

        doctors = self._seed_doctors(options['doctors'], departments)
        try:
            management.call_command('seed_website_content')
        except Exception as exc:  # pragma: no cover - keep seed_all resilient if run standalone
            self.stdout.write(self.style.WARNING(f'   seed_website_content: {exc}'))
        patients = self._seed_patients(options['patients'], districts, ins_categories)
        self._seed_appointments(options['appointments'], patients, departments, doctors)
        visits = self._seed_visits_and_clinical(options['visits'], patients, departments, doctors)
        self._seed_bills(options['bills'], patients, visits)
        self._seed_pharmacy_sales(options['pharmacy_sales'], patients, visits)
        admissions = self._seed_admissions(options['admissions'], patients, departments, doctors)
        # Five insured demo patients make the insurance workflow visible without
        # inflating the dataset.
        for patient in patients[:5]:
            if not patient.has_insurance:
                patient.insurance_company = random.choice(list(InsuranceCompany.objects.all()))
                patient.insurance_category = random.choice(list(InsuranceCategory.objects.all()))
                patient.has_insurance = True
                patient.insurance_policy_number = f'DEMO-{patient.patient_code}'
                patient.save(update_fields=['insurance_company', 'insurance_category', 'has_insurance', 'insurance_policy_number'])
        self._seed_insurance_claims(options['insurance_claims'], patients)
        self._create_portal_accounts_and_documents(patients)

        elapsed = (timezone.now() - t0).total_seconds()
        self.stdout.write(self.style.SUCCESS(
            f"\nseed_all complete in {elapsed:.1f}s. "
            f"Patients={Patient.objects.count()} Doctors={Doctor.objects.count()} "
            f"Visits={Visit.objects.count()} Admissions={admissions and Patient.objects.count()}"
        ))

    # ------------------------------------------------------------------
    def _create_portal_accounts_and_documents(self, patients):
        """Give every demo patient a portal login and one medical document."""
        from patient_portal.models import PatientAccount
        from documents.models import PatientDocument, DocumentCategory
        from accounts.models import User

        staff_user = User.objects.filter(is_active_staff=True).first()
        for patient in patients:
            account, created = PatientAccount.objects.get_or_create(patient=patient)
            if created:
                # Documented demo credential; users can change it by creating a new account.
                account.set_password('sashi')
                account.save(update_fields=['password_hash'])
            if not patient.documents.exists():
                PatientDocument.objects.create(
                    patient=patient, category=DocumentCategory.DOCTOR_NOTE,
                    title='Demo Medical Record', department_note='Medical Records',
                    remarks='Compact demo record generated for the patient portal.',
                    uploaded_by=staff_user,
                    uploaded_by_role=getattr(staff_user, 'role', ''),
                    file=ContentFile(DEMO_PDF_BYTES, name=f'{patient.patient_code}-medical-record.pdf'),
                )
        self.stdout.write(self.style.SUCCESS('Patient Portal accounts/documents ensured (password: sashi).'))

    # ------------------------------------------------------------------
    def _run_prereqs(self):
        from patients.models import District, Patient
        from departments.models import Department
        from accounts.models import User

        if not District.objects.exists():
            self.stdout.write('-> seed_nepal_address')
            management.call_command('seed_nepal_address')
        if not Department.objects.exists():
            self.stdout.write('-> seed_demo_data')
            management.call_command('seed_demo_data')
        if User.objects.filter(role='nursing').count() == 0:
            self.stdout.write('-> create_demo_accounts')
            try:
                management.call_command('create_demo_accounts')
            except Exception as exc:  # pragma: no cover - already-seeded races
                self.stdout.write(self.style.WARNING(f'   create_demo_accounts: {exc}'))
        # Compact catalog + core data only; legacy checkpoint seeders create 25+ patients.
        self.stdout.write('-> seed_final_requirements (compact catalog)')
        management.call_command('seed_final_requirements', patients=10)

    # ------------------------------------------------------------------
    def _seed_doctors(self, target, departments):
        from doctors.models import Doctor

        existing = Doctor.objects.count()
        to_create = max(0, target - existing)
        specializations_by_dept = {d.name: d.name for d in departments}
        created = 0
        used_names = set(Doctor.objects.values_list('full_name', flat=True))
        for _ in range(to_create):
            is_male = random.random() < 0.6
            first = random.choice(FIRST_NAMES_M if is_male else FIRST_NAMES_F)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"
            attempt = 0
            while name in used_names and attempt < 5:
                name = f"{first} {last} {random.randint(2, 99)}"
                attempt += 1
            used_names.add(name)
            dept = random.choice(departments)
            Doctor.objects.create(
                department=dept,
                full_name=name,
                qualification=random.choice(QUALIFICATIONS),
                specialization=specializations_by_dept[dept.name],
                experience_years=random.randint(1, 30),
                consultation_fee=dept.consultation_fee or random.choice([300, 500, 700, 1000]),
                biography=f"Dr. {name} is a dedicated {dept.name} specialist at Hamro Hospital "
                          f"with {random.randint(1, 30)} years of clinical experience.",
                available_days=','.join(random.sample(
                    ['sun', 'mon', 'tue', 'wed', 'thu', 'fri'], k=random.randint(4, 6),
                )),
                available_time_start=datetime.time(random.choice([8, 9, 10]), 0),
                available_time_end=datetime.time(random.choice([15, 16, 17]), 0),
                is_active=True,
                is_featured=random.random() < 0.15,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Doctors: {created} created ({Doctor.objects.count()} total).'))
        return list(Doctor.objects.filter(is_active=True))

    # ------------------------------------------------------------------
    def _seed_patients(self, target, districts, ins_categories):
        from patients.models import Patient

        existing = Patient.objects.count()
        to_create = max(0, target - existing)
        blood_groups = [c for c, _ in Patient.BloodGroup.choices if c]
        created = 0
        for i in range(to_create):
            is_male = random.random() < 0.5
            first = random.choice(FIRST_NAMES_M if is_male else FIRST_NAMES_F)
            last = random.choice(LAST_NAMES)
            dob = timezone.now().date() - datetime.timedelta(days=random.randint(365 // 2, 365 * 85))
            district = random.choice(districts)
            has_insurance = random.random() < 0.35 and ins_categories
            category = random.choice(ins_categories) if has_insurance else None
            patient = Patient.objects.create(
                first_name=first, last_name=last,
                gender=Patient.Gender.MALE if is_male else Patient.Gender.FEMALE,
                date_of_birth=dob,
                age_at_registration=f"{timezone.now().date().year - dob.year} Years",
                phone_number=f"98{random.randint(10000000, 49999999)}",
                district=district,
                municipality=f"{district.name} Municipality",
                ward_number=random.randint(1, 32),
                local_address=f"Ward {random.randint(1, 32)}, {district.name}",
                blood_group=random.choice(blood_groups),
                occupation=random.choice(['Farmer', 'Business', 'Student', 'Housewife', 'Service', 'Driver', 'Teacher', 'Laborer']),
                guardian_name=f"{random.choice(FIRST_NAMES_M)} {last}",
                emergency_contact_name=f"{random.choice(FIRST_NAMES_M if not is_male else FIRST_NAMES_F)} {last}",
                emergency_contact_phone=f"98{random.randint(10000000, 49999999)}",
                known_allergies=random.choice(['', '', '', 'Penicillin', 'Sulfa drugs', 'Dust', 'Aspirin']),
                has_insurance=bool(has_insurance),
                insurance_company=category.company if category else None,
                insurance_category=category,
                insurance_policy_number=f"POL-{random.randint(100000, 999999)}" if has_insurance else '',
                insurance_membership_number=f"MEM-{random.randint(100000, 999999)}" if has_insurance else '',
                insurance_card_number=f"CARD-{random.randint(100000, 999999)}" if has_insurance else '',
                insurance_expiry_date=timezone.now().date() + datetime.timedelta(days=random.randint(30, 700)) if has_insurance else None,
            )
            created += 1
            if created % 100 == 0:
                self.stdout.write(f'   ...{created} patients so far')
        self.stdout.write(self.style.SUCCESS(f'Patients: {created} created ({Patient.objects.count()} total).'))
        return list(Patient.objects.all())

    # ------------------------------------------------------------------
    def _seed_appointments(self, target, patients, departments, doctors):
        from appointments.models import Appointment
        from patients.models import District

        districts = list(District.objects.all())
        existing = Appointment.objects.count()
        to_create = max(0, target - existing)
        created = 0
        for i in range(to_create):
            is_male = random.random() < 0.5
            first = random.choice(FIRST_NAMES_M if is_male else FIRST_NAMES_F)
            last = random.choice(LAST_NAMES)
            dob = timezone.now().date() - datetime.timedelta(days=random.randint(365, 365 * 80))
            district = random.choice(districts)
            dept = random.choice(departments)
            dept_doctors = [d for d in doctors if d.department_id == dept.id] or doctors
            doctor = random.choice(dept_doctors) if dept_doctors else None
            patient_type = random.choice(['new', 'old'])
            appt = Appointment.objects.create(
                first_name=first, last_name=last,
                gender=('M' if is_male else 'F'),
                date_of_birth=dob,
                phone_number=f"97{random.randint(10000000, 49999999)}",
                email='',
                district=district,
                municipality='', ward_number=random.randint(1, 32), local_address='',
                department=dept, doctor=doctor,
                preferred_date=timezone.now().date() + datetime.timedelta(days=random.randint(-30, 30)),
                preferred_time=datetime.time(random.choice([9, 10, 11, 14, 15, 16]), random.choice([0, 15, 30, 45])),
                chief_complaint=random.choice(CHIEF_COMPLAINTS),
                patient_type=patient_type,
                registration_fee=dept.consultation_fee or 300,
                # Each compact demo appointment belongs to a portal patient.
                linked_patient=patients[i % len(patients)] if patients else None,
            )
            # 90% of bookings succeed in payment, like a real system
            if random.random() < 0.9:
                appt.mark_paid(esewa_ref_id=f"ESW{random.randint(10**9, 10**10 - 1)}")
            else:
                appt.mark_failed()
            created += 1
            if created % 500 == 0:
                self.stdout.write(f'   ...{created} appointments so far')
        self.stdout.write(self.style.SUCCESS(f'Appointments: {created} created ({Appointment.objects.count()} total).'))

    # ------------------------------------------------------------------
    def _seed_visits_and_clinical(self, target, patients, departments, doctors):
        from patients.models import Visit
        from consultations.models import Consultation, PrescriptionItem, LabTestRequest, RadiologyRequest, RequestStatus, Urgency
        from laboratory.models import LabTest
        from radiology.models import RadiologyTest

        existing = Visit.objects.count()
        to_create = max(0, target - existing)
        lab_tests = list(LabTest.objects.all())
        rad_tests = list(RadiologyTest.objects.all())
        radiology_service_types = [c for c, _ in RadiologyRequest.ServiceType.choices]

        created_visits = []
        created = 0
        for i in range(to_create):
            patient = patients[i % len(patients)]
            dept = random.choice(departments)
            dept_doctors = [d for d in doctors if d.department_id == dept.id]
            doctor = random.choice(dept_doctors) if dept_doctors else random.choice(doctors)
            visit_date = rand_past_date()
            visit = Visit.objects.create(
                patient=patient, department=dept, doctor=doctor,
                patient_type=random.choice(['new', 'old']),
                registration_fee=dept.consultation_fee or 300,
                chief_complaint=random.choice(CHIEF_COMPLAINTS),
                visit_date=visit_date,
                created_by=None,
            )
            consultation = Consultation.objects.create(
                visit=visit, doctor=doctor,
                diagnosis=random.choice(DIAGNOSES),
                clinical_notes='Patient examined. Vitals stable. Advised medication, rest, and follow-up as needed.',
                follow_up_date=visit_date + datetime.timedelta(days=random.choice([7, 14, 30])) if random.random() < 0.4 else None,
            )
            for _ in range(random.randint(1, 3)):
                PrescriptionItem.objects.create(
                    consultation=consultation,
                    medicine_name=random.choice(['Paracetamol 500mg', 'Amoxicillin 500mg', 'Omeprazole 20mg',
                                                  'Cetirizine 10mg', 'Metformin 500mg', 'Ibuprofen 400mg',
                                                  'Azithromycin 500mg', 'Vitamin C 500mg', 'ORS Powder']),
                    dosage=random.choice(DOSAGES), frequency=random.choice(FREQUENCIES),
                    duration=random.choice(DURATIONS), instructions=random.choice(INSTRUCTIONS),
                )
            if lab_tests:
                is_completed = True
                lab_req = LabTestRequest.objects.create(
                    consultation=consultation, test_name=random.choice(lab_tests).name,
                    urgency=random.choice(list(Urgency.values)),
                    status=RequestStatus.COMPLETED if is_completed else random.choice([RequestStatus.REQUESTED, RequestStatus.IN_PROGRESS]),
                    result_notes='All parameters within normal limits.' if is_completed else '',
                )
                if is_completed:
                    LabTestRequest.objects.filter(pk=lab_req.pk).update(
                        completed_at=timezone.now(),
                    )
            if rad_tests:
                is_completed = True
                rad_req = RadiologyRequest.objects.create(
                    consultation=consultation, service_type=random.choice(radiology_service_types),
                    urgency=random.choice(list(Urgency.values)),
                    status=RequestStatus.COMPLETED if is_completed else random.choice([RequestStatus.REQUESTED, RequestStatus.IN_PROGRESS]),
                    findings='No significant abnormality detected.' if is_completed else '',
                    impression='Normal study.' if is_completed else '',
                )
                if is_completed:
                    RadiologyRequest.objects.filter(pk=rad_req.pk).update(completed_at=timezone.now())
            created_visits.append(visit)
            created += 1
            if created % 500 == 0:
                self.stdout.write(f'   ...{created} visits so far')
        self.stdout.write(self.style.SUCCESS(
            f'Visits/Consultations/Prescriptions: {created} created ({Visit.objects.count()} visits total).'
        ))
        return created_visits or list(Visit.objects.all())

    # ------------------------------------------------------------------
    def _seed_bills(self, target, patients, visits):
        from billing.models import Bill, BillItem, PaymentMethod, BillType
        from website.models import HospitalService
        from accounts.models import User

        existing = Bill.objects.count()
        to_create = max(0, target - existing)
        services_by_dept = {}
        for svc in HospitalService.objects.filter(is_active=True):
            services_by_dept.setdefault(svc.department_id, []).append(svc)
        all_services = list(HospitalService.objects.filter(is_active=True))
        cashier = User.objects.filter(role='cash_counter').first() or User.objects.filter(is_superuser=True).first()

        created = 0
        for i in range(to_create):
            # One bill per demo patient before any extras: complete portal data.
            visit = visits[i % len(visits)] if visits else None
            patient = visit.patient if visit else patients[i % len(patients)]
            bill_type = random.choice([BillType.OPD, BillType.OPD, BillType.LAB, BillType.PHARMACY, BillType.OTHER])
            candidates = services_by_dept.get(visit.department_id) if visit else None
            svc_pool = candidates or all_services
            payment_method = random.choice([PaymentMethod.CASH, PaymentMethod.CASH, PaymentMethod.ESEWA,
                                             PaymentMethod.INSURANCE if patient.has_insurance else PaymentMethod.CASH])
            bill = Bill.objects.create(
                patient=patient, bill_type=bill_type, cashier=cashier,
                payment_method=payment_method,
                insurance_company=patient.insurance_company if payment_method == PaymentMethod.INSURANCE else None,
            )
            for _ in range(random.randint(1, 3)):
                svc = random.choice(svc_pool)
                BillItem.objects.create(bill=bill, service=svc, service_name=svc.name, unit_price=svc.price,
                                         quantity=random.randint(1, 2))
            bill.recalculate_total()
            created += 1
            if created % 500 == 0:
                self.stdout.write(f'   ...{created} bills so far')
        self.stdout.write(self.style.SUCCESS(f'Bills: {created} created ({Bill.objects.count()} total).'))

    # ------------------------------------------------------------------
    def _seed_pharmacy_sales(self, target, patients, visits):
        from pharmacy.models import Medicine, PharmacySale, PharmacySaleItem
        from consultations.models import PrescriptionItem
        from accounts.models import User

        existing = PharmacySale.objects.count()
        to_create = max(0, target - existing)
        medicines = list(Medicine.objects.filter(is_active=True, current_stock__gt=0))
        if not medicines:
            medicines = list(Medicine.objects.filter(is_active=True))
        cashier = User.objects.filter(role='pharmacy').first() or User.objects.filter(is_superuser=True).first()

        created = 0
        for i in range(to_create):
            # One pharmacy sale per demo patient before any extras: complete portal data.
            visit = visits[i % len(visits)] if visits else None
            patient = visit.patient if visit else patients[i % len(patients)]
            consultation = getattr(visit, 'consultation', None) if visit else None
            source = 'digital' if consultation else random.choice(['manual', 'walkin'])
            sale = PharmacySale.objects.create(
                patient=patient, consultation=consultation if source == 'digital' else None,
                prescription_source=source,
                payment_method=random.choice(['cash', 'cash', 'esewa', 'insurance' if patient.has_insurance else 'cash']),
                sold_by=cashier,
            )
            for _ in range(random.randint(1, 4)):
                med = random.choice(medicines)
                PharmacySaleItem.objects.create(
                    sale=sale, medicine=med, medicine_name=med.name, unit_price=med.selling_price,
                    quantity=random.randint(1, 3),
                )
            sale.recalculate_total()
            created += 1
            if created % 500 == 0:
                self.stdout.write(f'   ...{created} pharmacy sales so far')
        self.stdout.write(self.style.SUCCESS(f'Pharmacy sales: {created} created ({PharmacySale.objects.count()} total).'))

    # ------------------------------------------------------------------
    def _seed_admissions(self, target, patients, departments, doctors):
        from admissions.models import Ward, Bed, Admission
        from operation_theatre.models import Surgery, OTRoom, OperationType
        from billing.models import Bill, BillItem, PaymentMethod, BillType
        from website.models import HospitalService
        from accounts.models import User

        existing = Admission.objects.count()
        to_create = max(0, target - existing)
        ot_rooms = list(OTRoom.objects.all()) or [OTRoom.objects.create(name='OT-1')]
        op_types = list(OperationType.objects.all())
        cashier = User.objects.filter(role='cash_counter').first() or User.objects.filter(is_superuser=True).first()
        room_charge_svc = HospitalService.objects.filter(name__icontains='Bed Charge').first()

        created = 0
        for i in range(to_create):
            ward = Ward.objects.order_by('?').first()
            if not ward:
                break
            bed = Bed.objects.filter(ward=ward, is_occupied=False).order_by('?').first()
            if not bed:
                # every ward full - free a random bed for demo purposes rather than stalling
                bed = Bed.objects.filter(ward=ward).order_by('?').first()
                if bed:
                    Bed.objects.filter(pk=bed.pk).update(is_occupied=False)
                else:
                    continue
            patient = patients[i % len(patients)]
            dept = random.choice(departments)
            dept_doctors = [d for d in doctors if d.department_id == dept.id]
            doctor = random.choice(dept_doctors) if dept_doctors else random.choice(doctors)
            admission = Admission.objects.create(
                patient=patient, department=dept, admitting_doctor=doctor, ward=ward, bed=bed,
                reason_for_admission=random.choice(['Fever for observation', 'Post-surgical recovery',
                                                      'Delivery', 'Injury management', 'Acute abdominal pain',
                                                      'Cardiac monitoring', 'Respiratory distress']),
                diagnosis=random.choice(DIAGNOSES),
            )
            is_discharged = random.random() < 0.55
            if is_discharged:
                admission.discharge(
                    condition=random.choice(['recovered', 'improved', 'referred', 'dama']),
                    summary='Patient responded well to treatment and is stable for discharge.',
                    follow_up_instructions='Continue prescribed medication; follow up after 1 week.',
                )
            if op_types and random.random() < 0.3:
                op = random.choice(op_types)
                Surgery.objects.create(
                    patient=patient, admission=admission, surgery_name=op.name, operation_type=op,
                    surgeon=doctor, ot_room=random.choice(ot_rooms),
                    anesthesia_type=random.choice(['general', 'regional', 'local']),
                    status=Surgery.Status.COMPLETED if is_discharged else Surgery.Status.SCHEDULED,
                    scheduled_datetime=timezone.now() - datetime.timedelta(days=random.randint(1, 60)),
                    charge_amount=op.fixed_price,
                )
            # matching IPD bill
            bill = Bill.objects.create(
                patient=patient, bill_type=BillType.IPD, admission=admission, cashier=cashier,
                payment_method=random.choice([PaymentMethod.CASH, PaymentMethod.INSURANCE if patient.has_insurance else PaymentMethod.CASH]),
                insurance_company=patient.insurance_company if patient.has_insurance else None,
            )
            if room_charge_svc:
                BillItem.objects.create(bill=bill, service=room_charge_svc, service_name=room_charge_svc.name,
                                         unit_price=room_charge_svc.price, quantity=random.randint(1, 7))
            bill.recalculate_total()
            created += 1
            if created % 100 == 0:
                self.stdout.write(f'   ...{created} admissions so far')
        self.stdout.write(self.style.SUCCESS(f'Admissions: {created} created ({Admission.objects.count()} total).'))
        return created

    # ------------------------------------------------------------------
    def _seed_insurance_claims(self, target, patients):
        from insurance.models import InsuranceClaim
        from billing.models import Bill

        existing = InsuranceClaim.objects.count()
        to_create = max(0, target - existing)
        insured_patients = [p for p in patients if p.has_insurance and p.insurance_company_id]
        if not insured_patients:
            self.stdout.write(self.style.WARNING('No insured patients available - skipping insurance claims.'))
            return
        created = 0
        for i in range(to_create):
            patient = random.choice(insured_patients)
            related_bill = Bill.objects.filter(patient=patient).order_by('?').first()
            amount = related_bill.total_amount if related_bill else random.choice([1000, 2500, 5000, 10000])
            claim = InsuranceClaim.objects.create(
                patient=patient, insurance_company=patient.insurance_company,
                related_bill=related_bill, amount_claimed=amount,
                remarks='Auto-generated demo claim.',
            )
            status = random.choice(['pending', 'approved', 'approved', 'settled', 'rejected'])
            if status in ('approved', 'settled') and patient.insurance_category:
                approved, payable = patient.insurance_category.split_amount(amount)
                InsuranceClaim.objects.filter(pk=claim.pk).update(
                    status=status, approved_amount=approved, co_payment_amount=payable,
                    reviewed_at=timezone.now(),
                )
            elif status == 'rejected':
                InsuranceClaim.objects.filter(pk=claim.pk).update(
                    status=status, rejected_amount=amount, review_notes='Policy exclusion applies.',
                    reviewed_at=timezone.now(),
                )
            created += 1
            if created % 100 == 0:
                self.stdout.write(f'   ...{created} insurance claims so far')
        self.stdout.write(self.style.SUCCESS(f'Insurance claims: {created} created ({InsuranceClaim.objects.count()} total).'))
