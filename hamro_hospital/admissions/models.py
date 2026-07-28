from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Ward(models.Model):
    class WardType(models.TextChoices):
        GENERAL = 'general', 'General'
        ICU = 'icu', 'ICU'
        PRIVATE = 'private', 'Private'
        EMERGENCY = 'emergency', 'Emergency'
        MATERNITY = 'maternity', 'Maternity'
        PEDIATRIC = 'pediatric', 'Pediatric'

    name = models.CharField(max_length=100, unique=True)
    ward_type = models.CharField(max_length=15, choices=WardType.choices)
    floor = models.CharField(max_length=50, blank=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Default daily admission charge for this ward/bed type.')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'admissions_ward'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_ward_type_display()})"

    @property
    def total_beds(self):
        return self.beds.count()

    @property
    def available_beds(self):
        return self.beds.filter(is_occupied=False).count()


class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=20)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        db_table = 'admissions_bed'
        ordering = ['ward', 'bed_number']
        unique_together = [('ward', 'bed_number')]

    def __str__(self):
        return f"{self.ward.name} - Bed {self.bed_number}"


def _generate_admission_number():
    year = timezone.now().year
    prefix = f"ADM-{year}-"
    with transaction.atomic():
        last = (
            Admission.objects.select_for_update()
            .filter(admission_number__startswith=prefix)
            .order_by('-admission_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.admission_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = Admission.objects.filter(admission_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class Admission(models.Model):
    class Status(models.TextChoices):
        ADMITTED = 'admitted', 'Currently Admitted'
        DISCHARGED = 'discharged', 'Discharged'
        TRANSFERRED = 'transferred', 'Transferred'

    class DischargeCondition(models.TextChoices):
        RECOVERED = 'recovered', 'Recovered'
        IMPROVED = 'improved', 'Improved'
        REFERRED = 'referred', 'Referred'
        DAMA = 'dama', 'DAMA (Discharge Against Medical Advice)'
        EXPIRED = 'expired', 'Expired'

    admission_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='admissions')
    department = models.ForeignKey('departments.Department', on_delete=models.PROTECT, related_name='admissions')
    admitting_doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions',
    )
    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions')

    reason_for_admission = models.CharField(max_length=255)
    diagnosis = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ADMITTED)

    admission_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_condition = models.CharField(max_length=15, choices=DischargeCondition.choices, blank=True)
    discharge_summary = models.TextField(blank=True)
    follow_up_instructions = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions_created',
    )
    barcode = models.ImageField(upload_to='admissions/barcodes/', blank=True, null=True)

    class Meta:
        db_table = 'admissions_admission'
        ordering = ['-admission_date']

    def __str__(self):
        return f"{self.admission_number} - {self.patient.full_name}"

    @property
    def length_of_stay_days(self):
        end = self.discharge_date or timezone.now()
        delta = end.date() - self.admission_date.date()
        return max(1, delta.days + 1)

    @property
    def admission_charge_estimate(self):
        return self.length_of_stay_days * self.ward.daily_rate

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.admission_number:
            self.admission_number = _generate_admission_number()
        super().save(*args, **kwargs)
        if is_new and self.bed:
            Bed.objects.filter(pk=self.bed_id).update(is_occupied=True)
        if is_new or not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique Admission module barcode."""
        from accounts.qr_utils import generate_barcode_file
        self.barcode.save(f"{self.admission_number}.png", generate_barcode_file(self.admission_number), save=False)
        Admission.objects.filter(pk=self.pk).update(barcode=self.barcode.name)

    def discharge(self, condition, summary='', follow_up_instructions=''):
        """Discharges the patient and frees the bed automatically."""
        self.status = self.Status.DISCHARGED
        self.discharge_date = timezone.now()
        self.discharge_condition = condition
        self.discharge_summary = summary
        self.follow_up_instructions = follow_up_instructions
        self.save()
        if self.bed_id:
            Bed.objects.filter(pk=self.bed_id).update(is_occupied=False)

    @property
    def length_of_stay_days(self):
        end = self.discharge_date or timezone.now()
        return max((end - self.admission_date).days, 0)

class DischargeChecklist(models.Model):
    """Operational discharge clearance checklist for an admission."""
    admission = models.OneToOneField(Admission, on_delete=models.CASCADE, related_name='discharge_checklist')
    all_bills_paid = models.BooleanField(default=False)
    lab_reports_complete = models.BooleanField(default=False)
    radiology_reports_complete = models.BooleanField(default=False)
    medicine_charges_complete = models.BooleanField(default=False)
    discharge_summary_prepared = models.BooleanField(default=False)
    nursing_clearance = models.BooleanField(default=False)
    insurance_clearance = models.BooleanField(default=False)
    bed_release_ready = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='discharge_checklists_updated')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admissions_discharge_checklist'

    def __str__(self):
        return f'Discharge checklist for {self.admission.admission_number}'

    @property
    def is_complete(self):
        return all([
            self.all_bills_paid,
            self.lab_reports_complete,
            self.radiology_reports_complete,
            self.medicine_charges_complete,
            self.discharge_summary_prepared,
            self.nursing_clearance,
            self.insurance_clearance,
            self.bed_release_ready,
        ])

class AdmissionDeposit(models.Model):
    class DepositType(models.TextChoices):
        DEPOSIT = 'deposit', 'Deposit'
        USED = 'used', 'Used Against Bill'
        REFUND = 'refund', 'Refund'

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='deposits')
    deposit_type = models.CharField(max_length=10, choices=DepositType.choices, default=DepositType.DEPOSIT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, default='cash')
    receipt_number = models.CharField(max_length=50, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admission_deposits_received')
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admissions_deposit'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.admission.admission_number} - {self.get_deposit_type_display()} NPR {self.amount}'


class BedTransfer(models.Model):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='bed_transfers')
    from_ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_from')
    from_bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_from')
    to_ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name='transfers_to')
    to_bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_to')
    reason = models.CharField(max_length=255, blank=True)
    transferred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bed_transfers_done')
    transferred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admissions_bed_transfer'
        ordering = ['-transferred_at']

    def __str__(self):
        return f'{self.admission.admission_number}: {self.from_ward} -> {self.to_ward}'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new:
            self.from_ward = self.admission.ward
            self.from_bed = self.admission.bed
        super().save(*args, **kwargs)
        if is_new:
            if self.from_bed_id:
                Bed.objects.filter(pk=self.from_bed_id).update(is_occupied=False)
            if self.to_bed_id:
                Bed.objects.filter(pk=self.to_bed_id).update(is_occupied=True)
            Admission.objects.filter(pk=self.admission_id).update(ward=self.to_ward, bed=self.to_bed)
