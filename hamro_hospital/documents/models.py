from django.conf import settings
from django.db import models


def patient_document_upload_path(instance, filename):
    code = instance.patient.patient_code if instance.patient_id else 'unfiled'
    return f"patient_documents/{code}/{filename}"


class DocumentCategory(models.TextChoices):
    LAB_REPORT = 'lab_report', 'Laboratory Report'
    RADIOLOGY_REPORT = 'radiology_report', 'Radiology Report (X-Ray/CT/MRI/USG)'
    PRESCRIPTION = 'prescription', 'Prescription'
    DOCTOR_NOTE = 'doctor_note', "Doctor's Note"
    NURSING_NOTE = 'nursing_note', 'Nursing Note / Document'
    BLOOD_ISSUE_REPORT = 'blood_issue_report', 'Blood Issue Report'
    DISCHARGE_SUMMARY = 'discharge_summary', 'Discharge Summary'
    OPERATION_RECORD = 'operation_record', 'Operation / Surgery Record'
    REFERRAL_LETTER = 'referral_letter', 'Referral Letter'
    INSURANCE_DOCUMENT = 'insurance_document', 'Insurance Document'
    CONSENT_FORM = 'consent_form', 'Consent Form'
    INVOICE = 'invoice', 'Invoice / Billing Document'
    OTHER = 'other', 'Other'


class PatientDocument(models.Model):
    """
    One uploaded PDF/file attached to a patient's digital file.

    Every department uploads through this single model (see spec section 3),
    so a patient's profile can show one merged, chronological document list
    regardless of which counter/department produced the file.

    Replacing a document does not delete history: the old row is kept with
    is_active=False and a pointer forward to its replacement, so Medical
    Records can always see what a document used to say.
    """
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='documents',
    )
    category = models.CharField(max_length=30, choices=DocumentCategory.choices)
    title = models.CharField(max_length=200, help_text='e.g. "CBC Report - 2026-07-20"')
    file = models.FileField(upload_to=patient_document_upload_path)

    department_note = models.CharField(
        max_length=100, blank=True,
        help_text='Which department/module this came from, e.g. "Laboratory", "Radiology"',
    )
    remarks = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documents_uploaded',
    )
    uploaded_by_role = models.CharField(max_length=30, blank=True)

    version = models.PositiveIntegerField(default=1)
    replaces = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replaced_by_set',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='False once a newer version has replaced this file, or it was deleted; kept for audit history.',
    )
    is_deleted = models.BooleanField(default=False, help_text='Deleted by Super Admin (spec 8: only Super Admin can delete).')
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents_deleted',
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents_patient_document'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['patient', 'category']),
            models.Index(fields=['patient', 'is_active']),
        ]

    def __str__(self):
        return f"{self.title} ({self.patient.patient_code})"

    def replace_with(self, new_file, uploaded_by, title=None, remarks=''):
        """Creates the new version, points it back at this row, retires this row."""
        new_doc = PatientDocument.objects.create(
            patient=self.patient,
            category=self.category,
            title=title or self.title,
            file=new_file,
            department_note=self.department_note,
            remarks=remarks,
            uploaded_by=uploaded_by,
            uploaded_by_role=getattr(uploaded_by, 'role', ''),
            version=self.version + 1,
            replaces=self,
        )
        PatientDocument.objects.filter(pk=self.pk).update(is_active=False)
        return new_doc

    def soft_delete(self, deleted_by):
        from django.utils import timezone
        self.is_active = False
        self.is_deleted = True
        self.deleted_by = deleted_by
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'is_deleted', 'deleted_by', 'deleted_at'])
