from django.db.models.signals import post_save
from django.dispatch import receiver

from documents.models import DocumentCategory
from documents.utils import add_medical_history_document


def _actor(obj):
    return getattr(obj, 'created_by', None) or getattr(obj, 'cashier', None) or getattr(obj, 'sold_by', None) or getattr(obj, 'processed_by', None) or getattr(obj, 'recorded_by', None) or getattr(obj, 'submitted_by', None)


@receiver(post_save, sender='patients.Visit')
def visit_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.patient, category=DocumentCategory.OTHER, title=f'OPD/EHS Registration {instance.receipt_number}', department_note='Registration' if not instance.is_extension_service else 'EHS Service', uploaded_by=instance.created_by, source_key=f'visit-{instance.pk}', rows=[('Receipt', instance.receipt_number), ('Department', instance.department.name), ('Type', instance.get_patient_type_display()), ('Fee', instance.registration_fee), ('Payment', instance.get_payment_status_display())])


@receiver(post_save, sender='billing.Bill')
def bill_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.patient, category=DocumentCategory.INVOICE, title=f'Invoice {instance.bill_number}', department_note='Billing / Cash Counter', uploaded_by=instance.cashier, source_key=f'bill-{instance.pk}', rows=[('Bill Number', instance.bill_number), ('Type', instance.get_bill_type_display()), ('Payment Method', instance.get_payment_method_display()), ('Total', instance.total_amount), ('Status', instance.get_status_display())])


@receiver(post_save, sender='consultations.Consultation')
def consultation_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.patient, category=DocumentCategory.DOCTOR_NOTE, title=f'Clinical Note {instance.created_at:%Y-%m-%d}', department_note='Doctor', uploaded_by=getattr(instance.doctor, 'user_account', None), source_key=f'consultation-{instance.pk}', rows=[('Doctor', instance.doctor.full_name if instance.doctor else '-'), ('Diagnosis', instance.diagnosis), ('Follow-up', instance.follow_up_date or '-')], body=instance.clinical_notes)


@receiver(post_save, sender='consultations.LabTestRequest')
def lab_history(sender, instance, created, **kwargs):
    if getattr(instance, 'status', '') == 'completed':
        patient = instance.patient_obj
        add_medical_history_document(patient, category=DocumentCategory.LAB_REPORT, title=f'Lab Report {instance.lab_code or instance.pk}', department_note='Laboratory', uploaded_by=instance.processed_by, source_key=f'lab-{instance.pk}-{instance.status}', rows=[('Test', instance.test_name), ('Status', instance.get_status_display()), ('Verified', instance.verified_at or '-')], body=instance.result_notes)


@receiver(post_save, sender='consultations.RadiologyRequest')
def radiology_history(sender, instance, created, **kwargs):
    if getattr(instance, 'status', '') == 'completed':
        patient = instance.patient_obj
        add_medical_history_document(patient, category=DocumentCategory.RADIOLOGY_REPORT, title=f'Radiology Report {instance.radiology_number}', department_note='Radiology', uploaded_by=instance.processed_by, source_key=f'rad-{instance.pk}-{instance.status}', rows=[('Service', instance.display_service_name), ('Status', instance.get_status_display()), ('Verified', instance.verified_at or '-')], body=(instance.findings or '') + '\n' + (instance.impression or ''))


@receiver(post_save, sender='pharmacy.PharmacySale')
def pharmacy_history(sender, instance, created, **kwargs):
    if created and instance.patient:
        add_medical_history_document(instance.patient, category=DocumentCategory.PRESCRIPTION, title=f'Pharmacy Receipt {instance.sale_number}', department_note='Pharmacy', uploaded_by=instance.sold_by, source_key=f'pharmacy-{instance.pk}', rows=[('Sale Number', instance.sale_number), ('Payment', instance.get_payment_method_display()), ('Total', instance.total_amount), ('Source', instance.get_prescription_source_display())])


@receiver(post_save, sender='admissions.Admission')
def admission_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.patient, category=DocumentCategory.OTHER, title=f'Admission Summary {instance.admission_number}', department_note='Admission', uploaded_by=instance.created_by, source_key=f'admission-{instance.pk}', rows=[('Admission No', instance.admission_number), ('Department', instance.department.name), ('Ward/Bed', f'{instance.ward.name} / {instance.bed.bed_number if instance.bed else "-"}'), ('Diagnosis', instance.diagnosis), ('Reason', instance.reason_for_admission)])
    elif instance.status == instance.Status.DISCHARGED:
        add_medical_history_document(instance.patient, category=DocumentCategory.DISCHARGE_SUMMARY, title=f'Discharge Summary {instance.admission_number}', department_note='Admission', uploaded_by=instance.created_by, source_key=f'discharge-{instance.pk}', rows=[('Admission No', instance.admission_number), ('Discharged', instance.discharge_date), ('Final Diagnosis', instance.diagnosis), ('Follow-up Date', instance.follow_up_date or '-')], body=instance.discharge_summary)


@receiver(post_save, sender='nursing.NursingNote')
def nursing_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.admission.patient, category=DocumentCategory.NURSING_NOTE, title=f'Nursing Note {instance.recorded_at:%Y-%m-%d %H:%M}', department_note='Nursing', uploaded_by=instance.recorded_by, source_key=f'nursing-{instance.pk}', rows=[('Admission', instance.admission.admission_number), ('Type', instance.get_note_type_display())], body=instance.content)


@receiver(post_save, sender='operation_theatre.Surgery')
def surgery_history(sender, instance, created, **kwargs):
    if created or instance.status == instance.Status.COMPLETED:
        add_medical_history_document(instance.patient, category=DocumentCategory.OPERATION_RECORD, title=f'Operation Record {instance.surgery_number}', department_note='Operation Theater', uploaded_by=instance.created_by, source_key=f'surgery-{instance.pk}-{instance.status}', rows=[('Surgery No', instance.surgery_number), ('Procedure', instance.surgery_name), ('Surgeon', instance.surgeon.full_name), ('Status', instance.get_status_display())], body='\n'.join([instance.pre_op_notes, instance.operative_notes, instance.post_op_notes, instance.complications]))


@receiver(post_save, sender='insurance.InsuranceClaim')
def insurance_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.patient, category=DocumentCategory.INSURANCE_DOCUMENT, title=f'Insurance Claim {instance.claim_number}', department_note='Insurance', uploaded_by=instance.submitted_by, source_key=f'insurance-{instance.pk}', rows=[('Claim No', instance.claim_number), ('Company', instance.insurance_company.name), ('Claimed', instance.amount_claimed), ('Status', instance.get_status_display())])


@receiver(post_save, sender='referrals.Referral')
def referral_history(sender, instance, created, **kwargs):
    if created:
        add_medical_history_document(instance.patient, category=DocumentCategory.REFERRAL_LETTER, title=f'Referral {instance.get_referral_type_display()} {instance.created_at:%Y-%m-%d}', department_note='Referral', uploaded_by=instance.created_by, source_key=f'referral-{instance.pk}', rows=[('Destination', instance.get_referral_type_display()), ('Department', instance.to_department.name if instance.to_department else '-'), ('Diagnosis', instance.diagnosis), ('Status', instance.get_status_display())], body='\n'.join([instance.reason, instance.clinical_notes, instance.requested_items]))
