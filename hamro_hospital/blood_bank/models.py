from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class BloodGroup(models.TextChoices):
    A_POS = 'A+', 'A+'
    A_NEG = 'A-', 'A-'
    B_POS = 'B+', 'B+'
    B_NEG = 'B-', 'B-'
    AB_POS = 'AB+', 'AB+'
    AB_NEG = 'AB-', 'AB-'
    O_POS = 'O+', 'O+'
    O_NEG = 'O-', 'O-'


def _generate_bag_number():
    year = timezone.now().year
    prefix = f"BLD-{year}-"
    with transaction.atomic():
        last = (
            BloodUnit.objects.select_for_update()
            .filter(bag_number__startswith=prefix)
            .order_by('-bag_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.bag_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = BloodUnit.objects.filter(bag_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class BloodUnit(models.Model):
    class Component(models.TextChoices):
        WHOLE_BLOOD = 'whole_blood', 'Whole Blood'
        PACKED_CELLS = 'packed_cells', 'Packed Red Cells'
        PLASMA = 'plasma', 'Fresh Frozen Plasma'
        PLATELETS = 'platelets', 'Platelets'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESERVED = 'reserved', 'Reserved'
        ISSUED = 'issued', 'Issued'
        EXPIRED = 'expired', 'Expired'
        DISCARDED = 'discarded', 'Discarded'

    bag_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices)
    component = models.CharField(max_length=20, choices=Component.choices, default=Component.WHOLE_BLOOD)
    quantity_ml = models.PositiveIntegerField(default=450)

    donor_name = models.CharField(max_length=150, blank=True)
    donor_phone = models.CharField(max_length=20, blank=True)

    collection_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='blood_units_added',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blood_bank_unit'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['blood_group', 'status'])]

    def __str__(self):
        return f"{self.bag_number} - {self.blood_group} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.bag_number:
            self.bag_number = _generate_bag_number()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()


class RequestUrgency(models.TextChoices):
    ROUTINE = 'routine', 'Routine'
    URGENT = 'urgent', 'Urgent'
    EMERGENCY = 'emergency', 'Emergency'


class BloodRequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ISSUED = 'issued', 'Issued'
    CANCELLED = 'cancelled', 'Cancelled'


class BloodRequest(models.Model):
    """Doctor requests blood for a patient (spec 12: 'Doctor requests
    blood -> Blood Bank receives request -> Blood Bank issues blood'). One
    request can be fulfilled by one BloodIssue."""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='blood_requests')
    consultation = models.ForeignKey(
        'consultations.Consultation', on_delete=models.SET_NULL, null=True, blank=True, related_name='blood_requests',
    )
    blood_group_needed = models.CharField(max_length=3, choices=BloodGroup.choices)
    component = models.CharField(max_length=20, choices=BloodUnit.Component.choices, default=BloodUnit.Component.WHOLE_BLOOD)
    units_needed = models.PositiveIntegerField(default=1)
    urgency = models.CharField(max_length=10, choices=RequestUrgency.choices, default=RequestUrgency.ROUTINE)
    clinical_note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=BloodRequestStatus.choices, default=BloodRequestStatus.PENDING)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='blood_requests_made',
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blood_bank_request'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.blood_group_needed} x{self.units_needed} for {self.patient.full_name} ({self.get_status_display()})"

    @property
    def doctor_display(self):
        if self.requested_by_id:
            return self.requested_by.get_full_name() or self.requested_by.username
        return '—'


class BloodIssue(models.Model):
    """One unit issued to a patient. Frees the unit into ISSUED status permanently."""
    blood_unit = models.OneToOneField(BloodUnit, on_delete=models.PROTECT, related_name='issue')
    blood_request = models.OneToOneField(
        BloodRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='issue',
    )
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='blood_issues')
    admission = models.ForeignKey(
        'admissions.Admission', on_delete=models.SET_NULL, null=True, blank=True, related_name='blood_issues',
    )
    purpose = models.CharField(max_length=200, blank=True)
    cross_match_notes = models.TextField(blank=True)
    issue_report = models.FileField(upload_to='blood_bank/issue_reports/', blank=True, null=True)

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='blood_issued',
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blood_bank_issue'
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.blood_unit.bag_number} -> {self.patient.full_name}"
