from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Consultation(models.Model):
    """One consultation per OPD Visit (1:1), created/edited by the attending doctor."""
    visit = models.OneToOneField('patients.Visit', on_delete=models.CASCADE, related_name='consultation')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.PROTECT, related_name='consultations')

    diagnosis = models.CharField(max_length=255, blank=True)
    clinical_notes = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    # Recommendations (spec section 12)
    recommend_admission = models.BooleanField(default=False)
    recommend_surgery = models.BooleanField(default=False)
    recommended_surgery_name = models.CharField(max_length=150, blank=True)

    prescription_file = models.FileField(upload_to='consultations/prescriptions/', blank=True, null=True, help_text='Upload PDF or Image scan of the handwritten prescription.')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'consultations_consultation'
        ordering = ['-created_at']

    def __str__(self):
        return f"Consultation for {self.visit.patient.full_name} ({self.visit.receipt_number})"

    @property
    def patient(self):
        return self.visit.patient


class PrescriptionItem(models.Model):
    """One medicine line within a consultation's prescription. Free-text medicine name."""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='prescription_items')
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text='e.g. 500mg')
    frequency = models.CharField(max_length=100, help_text='e.g. Twice daily (BID)')
    duration = models.CharField(max_length=100, help_text='e.g. 5 days')
    instructions = models.CharField(max_length=255, blank=True, help_text='e.g. After meals')

    class Meta:
        db_table = 'consultations_prescription_item'
        ordering = ['id']

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage} {self.frequency}"


def _generate_radiology_number():
    year = timezone.now().year
    prefix = f"RAD-{year}-"
    with transaction.atomic():
        last = (
            RadiologyRequest.objects.select_for_update()
            .filter(radiology_number__startswith=prefix)
            .order_by('-radiology_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.radiology_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = RadiologyRequest.objects.filter(radiology_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class RequestStatus(models.TextChoices):
    REQUESTED = 'requested', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    SAMPLE_COLLECTED = 'sample_collected', 'Sample Collected'
    IN_PROGRESS = 'in_progress', 'Testing In Progress'
    COMPLETED = 'completed', 'Completed'


class Urgency(models.TextChoices):
    ROUTINE = 'routine', 'Routine'
    URGENT = 'urgent', 'Urgent'
    STAT = 'stat', 'STAT (Immediate)'


class LabTestRequest(models.Model):
    """A laboratory test requested by the doctor during a consultation, OR
    a walk-in record created directly by Laboratory staff when a patient
    arrives with a physical referral letter (spec section 5: both
    workflows must be supported)."""
    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name='lab_requests', null=True, blank=True,
    )
    # Set directly for walk-in/manual records; for doctor-raised requests this
    # is left blank and patient_obj falls back to consultation.visit.patient.
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='manual_lab_requests', null=True, blank=True,
    )
    is_manual = models.BooleanField(
        default=False, help_text='True when Laboratory staff created this record directly for a walk-in patient.',
    )
    test_name = models.CharField(max_length=200)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.ROUTINE)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.REQUESTED)

    # Manual-entry / referral context (spec: doctor name, department, clinical
    # note, uploaded referral letter must be reviewable before accepting).
    referred_by = models.CharField(max_length=150, blank=True, help_text='Referring doctor name (walk-in entries)')
    department_name = models.CharField(max_length=100, blank=True)
    clinical_note = models.TextField(blank=True)
    referral_letter = models.FileField(upload_to='laboratory/referral_letters/', blank=True, null=True)

    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_requests_accepted',
    )

    result_notes = models.TextField(blank=True)
    result_file = models.FileField(upload_to='lab_results/', blank=True, null=True)

    lab_code = models.CharField(max_length=30, unique=True, editable=False, db_index=True, blank=True, null=True)
    barcode = models.ImageField(upload_to='laboratory/barcodes/', blank=True, null=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_requests_processed',
    )

    class Meta:
        db_table = 'consultations_lab_test_request'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.test_name} for {self.patient_obj.full_name} ({self.get_status_display()})"

    @property
    def patient_obj(self):
        """Works for both a doctor-raised request and a walk-in record."""
        if self.patient_id:
            return self.patient
        return self.consultation.patient

    @property
    def doctor_display(self):
        if self.consultation_id:
            return self.consultation.doctor.full_name if self.consultation.doctor else '—'
        return self.referred_by or 'Walk-in (no referring doctor recorded)'

    @property
    def department_display(self):
        if self.consultation_id and self.consultation.visit.department:
            return self.consultation.visit.department.name
        return self.department_name or '—'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.lab_code:
            self.lab_code = f"LAB-{self.pk:06d}"
            LabTestRequest.objects.filter(pk=self.pk).update(lab_code=self.lab_code)
        if not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique Laboratory barcode for this test request."""
        from accounts.qr_utils import generate_barcode_file
        self.barcode.save(f"{self.lab_code}.png", generate_barcode_file(self.lab_code), save=False)
        LabTestRequest.objects.filter(pk=self.pk).update(barcode=self.barcode.name)


class RadiologyRequest(models.Model):
    """Imaging requested by the doctor during a consultation, OR a walk-in
    record created directly by Radiology staff (spec section 6 mirrors
    Laboratory section 5: both workflows must be supported)."""

    class ServiceType(models.TextChoices):
        XRAY = 'xray', 'X-Ray'
        CT = 'ct', 'CT Scan'
        MRI = 'mri', 'MRI'
        ECG = 'ecg', 'ECG'
        ECHO = 'echo', 'Echo'
        ULTRASOUND = 'ultrasound', 'Ultrasound'
        CUSTOM = 'custom', 'Other / Custom'

    radiology_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    barcode = models.ImageField(upload_to='radiology/barcodes/', blank=True, null=True)
    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name='radiology_requests', null=True, blank=True,
    )
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='manual_radiology_requests', null=True, blank=True,
    )
    is_manual = models.BooleanField(
        default=False, help_text='True when Radiology staff created this record directly for a walk-in patient.',
    )
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    custom_service_name = models.CharField(max_length=150, blank=True, help_text='Used when Service Type = Other')
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.ROUTINE)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.REQUESTED)

    referred_by = models.CharField(max_length=150, blank=True, help_text='Referring doctor name (walk-in entries)')
    department_name = models.CharField(max_length=100, blank=True)
    clinical_note = models.TextField(blank=True)
    referral_letter = models.FileField(upload_to='radiology/referral_letters/', blank=True, null=True)

    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_requests_accepted',
    )

    report_notes = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    report_file = models.FileField(upload_to='radiology_reports/', blank=True, null=True)
    image_file = models.ImageField(upload_to='radiology_images/', blank=True, null=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_requests_processed',
    )

    class Meta:
        db_table = 'consultations_radiology_request'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.radiology_number} - {self.get_service_type_display()}"

    def save(self, *args, **kwargs):
        if not self.radiology_number:
            self.radiology_number = _generate_radiology_number()
        super().save(*args, **kwargs)
        if not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique Radiology barcode for this request."""
        from accounts.qr_utils import generate_barcode_file
        barcode_file = generate_barcode_file(self.radiology_number)
        if barcode_file:
            self.barcode.save(f"{self.radiology_number}_barcode.png", barcode_file, save=True)

    @property
    def display_service_name(self):
        return self.custom_service_name if self.service_type == self.ServiceType.CUSTOM else self.get_service_type_display()

    @property
    def patient_obj(self):
        """Works for both a doctor-raised request and a walk-in record."""
        if self.patient_id:
            return self.patient
        return self.consultation.patient

    @property
    def doctor_display(self):
        if self.consultation_id:
            return self.consultation.doctor.full_name if self.consultation.doctor else '—'
        return self.referred_by or 'Walk-in (no referring doctor recorded)'

    @property
    def department_display(self):
        if self.consultation_id and self.consultation.visit.department:
            return self.consultation.visit.department.name
        return self.department_name or '—'
