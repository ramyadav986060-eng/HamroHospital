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
