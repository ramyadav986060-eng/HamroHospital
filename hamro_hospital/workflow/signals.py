from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from workflow.models import PatientTimeline
from workflow.utils import add_timeline


@receiver(post_save, sender='patients.Patient')
def patient_registered_timeline(sender, instance, created, **kwargs):
    if created:
        add_timeline(
            instance,
            PatientTimeline.EventType.REGISTRATION,
            'Patient registered',
            f'Patient ID {instance.patient_code} created.',
            actor=instance.created_by,
            related_url=reverse('patients:patient_detail', args=[instance.pk]),
            source=instance,
        )


@receiver(post_save, sender='patients.Visit')
def visit_timeline(sender, instance, created, **kwargs):
    if created:
        add_timeline(
            instance.patient,
            PatientTimeline.EventType.VISIT,
            f'OPD visit {instance.receipt_number}',
            f'{instance.department.name} - Token {instance.token_number}',
            actor=instance.created_by,
            related_url=reverse('patients:opd_ticket', args=[instance.pk]),
            source=instance,
        )


@receiver(post_save, sender='billing.Bill')
def bill_timeline(sender, instance, created, **kwargs):
    if created:
        add_timeline(
            instance.patient,
            PatientTimeline.EventType.BILL,
            f'Bill generated {instance.bill_number}',
            f'NPR {instance.total_amount} - {instance.get_status_display()}',
            actor=instance.cashier,
            related_url=reverse('billing:receipt', args=[instance.pk]),
            source=instance,
        )


@receiver(post_save, sender='admissions.Admission')
def admission_timeline(sender, instance, created, **kwargs):
    if created:
        add_timeline(
            instance.patient,
            PatientTimeline.EventType.ADMISSION,
            f'Admission {instance.admission_number}',
            f'{instance.ward.name} / Bed {instance.bed.bed_number if instance.bed else "-"}',
            actor=instance.created_by,
            related_url=reverse('admissions:admission_detail', args=[instance.pk]),
            source=instance,
        )
    elif instance.status == instance.Status.DISCHARGED:
        # Avoid duplicate discharge spam by using source fields as a natural key.
        PatientTimeline.objects.get_or_create(
            patient=instance.patient,
            event_type=PatientTimeline.EventType.DISCHARGE,
            source_app=instance._meta.app_label,
            source_model=instance._meta.model_name,
            source_object_id=instance.pk,
            title=f'Discharged {instance.admission_number}',
            defaults={
                'description': instance.discharge_summary,
                'related_url': reverse('admissions:admission_detail', args=[instance.pk]),
            },
        )

@receiver(post_save, sender='pharmacy.PharmacySale')
def pharmacy_sale_timeline(sender, instance, created, **kwargs):
    if created and instance.patient_id:
        add_timeline(instance.patient, PatientTimeline.EventType.PHARMACY, f'Pharmacy sale {instance.sale_number}', f'NPR {instance.total_amount}', actor=instance.sold_by, related_url=reverse('pharmacy:receipt', args=[instance.pk]), source=instance)


@receiver(post_save, sender='documents.PatientDocument')
def document_timeline(sender, instance, created, **kwargs):
    if created and instance.patient_id:
        add_timeline(instance.patient, PatientTimeline.EventType.DOCUMENT, f'Document uploaded: {instance.title}', instance.get_category_display(), actor=instance.uploaded_by, related_url=reverse('documents:document_view', args=[instance.pk]), source=instance)


@receiver(post_save, sender='insurance.InsuranceClaim')
def insurance_claim_timeline(sender, instance, created, **kwargs):
    if created:
        add_timeline(instance.patient, PatientTimeline.EventType.OTHER, f'Insurance claim {instance.claim_number}', f'NPR {instance.amount_claimed} - {instance.get_status_display()}', actor=instance.submitted_by, related_url=reverse('insurance:claim_slip', args=[instance.pk]), source=instance)


@receiver(post_save, sender='blood_bank.BloodIssue')
def blood_issue_timeline(sender, instance, created, **kwargs):
    if created:
        add_timeline(instance.patient, PatientTimeline.EventType.BLOOD_BANK, f'Blood issued: {instance.blood_unit.bag_number}', instance.purpose, actor=instance.issued_by, source=instance)


@receiver(post_save, sender='consultations.LabTestRequest')
def lab_request_created_timeline(sender, instance, created, **kwargs):
    if created and instance.patient_obj:
        add_timeline(instance.patient_obj, PatientTimeline.EventType.LAB, f'Lab requested: {instance.test_name}', instance.clinical_note, related_url=reverse('laboratory:update_result', args=[instance.pk]), source=instance)


@receiver(post_save, sender='consultations.RadiologyRequest')
def radiology_request_created_timeline(sender, instance, created, **kwargs):
    if created and instance.patient_obj:
        add_timeline(instance.patient_obj, PatientTimeline.EventType.RADIOLOGY, f'Radiology requested: {instance.display_service_name}', instance.clinical_note, related_url=reverse('radiology:update_report', args=[instance.pk]), source=instance)
