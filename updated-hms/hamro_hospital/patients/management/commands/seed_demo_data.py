from django.core.management.base import BaseCommand
from django.db import transaction

from departments.models import Department
from doctors.models import Doctor
from website.models import Testimonial, DiseaseInfo
from patients.models import InsuranceCompany

DEPARTMENTS = [
    ('General OPD', 'General outpatient consultation for all common illnesses.', 300, 'bi bi-hospital'),
    ('Orthopedics', 'Bone, joint, and musculoskeletal care.', 600, 'bi bi-bandaid'),
    ('ENT', 'Ear, Nose and Throat treatment.', 500, 'bi bi-ear'),
    ('Gynecology', "Women's reproductive health.", 600, 'bi bi-gender-female'),
    ('Obstetrics', 'Pregnancy and childbirth care.', 600, 'bi bi-heart'),
    ('Pediatrics', 'Healthcare for infants, children and adolescents.', 500, 'bi bi-emoji-smile'),
    ('Psychiatry', 'Mental health diagnosis and treatment.', 700, 'bi bi-brain'),
    ('Dermatology', 'Skin, hair and nail care.', 600, 'bi bi-droplet'),
    ('Cardiology', 'Heart and cardiovascular care.', 800, 'bi bi-heart-pulse'),
    ('Neurology', 'Brain, spine and nervous system care.', 800, 'bi bi-lightning'),
    ('Gastroenterology', 'Digestive system care.', 700, 'bi bi-capsule'),
    ('Pulmonology', 'Lung and respiratory care.', 700, 'bi bi-lungs'),
    ('Urology', 'Urinary tract and male reproductive care.', 700, 'bi bi-droplet-half'),
    ('Nephrology', 'Kidney care.', 750, 'bi bi-droplet-fill'),
    ('Ophthalmology', 'Eye care.', 500, 'bi bi-eye'),
    ('Dental', 'Dental and oral care.', 400, 'bi bi-emoji-laughing'),
    ('Surgery', 'General and specialized surgery.', 1000, 'bi bi-scissors'),
    ('Emergency', '24/7 emergency care.', 500, 'bi bi-exclamation-triangle'),
    ('ICU', 'Intensive care unit.', 0, 'bi bi-activity'),
    ('Oncology', 'Cancer diagnosis and treatment.', 900, 'bi bi-radioactive'),
    ('Physiotherapy', 'Physical rehabilitation.', 400, 'bi bi-person-arms-up'),
    ('Radiology', 'Diagnostic imaging.', 0, 'bi bi-camera'),
    ('Pathology', 'Disease diagnosis via lab analysis.', 0, 'bi bi-clipboard-pulse'),
    ('Laboratory', 'Blood and diagnostic testing.', 0, 'bi bi-flask'),
    ('Pharmacy', 'Medicine dispensing.', 0, 'bi bi-capsule-pill'),
]

DOCTORS = [
    ('General OPD', 'Ramesh Sharma', 'MBBS', 'General Physician', 8),
    ('Cardiology', 'Sunita Koirala', 'MBBS, MD (Cardiology)', 'Cardiologist', 12),
    ('Pediatrics', 'Anup Thapa', 'MBBS, MD (Pediatrics)', 'Pediatrician', 6),
    ('Orthopedics', 'Bikash Gurung', 'MBBS, MS (Ortho)', 'Orthopedic Surgeon', 10),
    ('Gynecology', 'Sarita Basnet', 'MBBS, MD (Gynae)', 'Gynecologist', 9),
    ('Dermatology', 'Prakash Rai', 'MBBS, MD (Derma)', 'Dermatologist', 5),
]

DISEASES = [
    ('Type 2 Diabetes', 'General OPD', 'A chronic condition affecting blood sugar regulation.',
     'Managed through diet, medication, and regular monitoring of blood glucose levels.',
     'Increased thirst\nFrequent urination\nFatigue\nBlurred vision'),
    ('Hypertension', 'Cardiology', 'Persistently elevated blood pressure.',
     'Controlled through lifestyle changes and antihypertensive medication.',
     'Headaches\nShortness of breath\nNosebleeds\nOften asymptomatic'),
    ('Asthma', 'Pulmonology', 'A chronic respiratory condition causing airway inflammation.',
     'Managed with inhalers and avoidance of triggers.',
     'Wheezing\nShortness of breath\nChest tightness\nCoughing'),
]


class Command(BaseCommand):
    help = 'Seed demo departments, doctors, diseases, testimonials, and an insurance company for local testing.'

    @transaction.atomic
    def handle(self, *args, **options):
        dept_map = {}
        for name, desc, fee, icon in DEPARTMENTS:
            dept, _ = Department.objects.get_or_create(
                name=name, defaults={'description': desc, 'consultation_fee': fee, 'icon_class': icon},
            )
            dept_map[name] = dept
        self.stdout.write(self.style.SUCCESS(f'{len(DEPARTMENTS)} departments ensured.'))

        for dept_name, full_name, qualification, specialization, exp in DOCTORS:
            Doctor.objects.get_or_create(
                full_name=full_name,
                defaults={
                    'department': dept_map[dept_name], 'qualification': qualification,
                    'specialization': specialization, 'experience_years': exp,
                    'consultation_fee': dept_map[dept_name].consultation_fee or 500,
                    'available_days': 'sun,mon,tue,wed,thu', 'is_featured': True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'{len(DOCTORS)} doctors ensured.'))

        for name, dept_name, summary, description, symptoms in DISEASES:
            from django.utils.text import slugify
            DiseaseInfo.objects.get_or_create(
                name=name,
                defaults={
                    'slug': slugify(name), 'department': dept_map.get(dept_name),
                    'summary': summary, 'description': description, 'symptoms': symptoms,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'{len(DISEASES)} disease articles ensured.'))

        Testimonial.objects.get_or_create(
            patient_name='Hari Prasad Adhikari',
            defaults={'message': 'The staff were caring and the doctors explained everything clearly.', 'rating': 5},
        )

        InsuranceCompany.objects.get_or_create(
            name='Nepal Life Insurance', defaults={'contact_person': 'Claims Desk', 'phone_number': '01-4000000'},
        )

        self.stdout.write(self.style.SUCCESS('Demo data seeding complete.'))
