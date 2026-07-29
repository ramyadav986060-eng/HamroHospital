from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class OperationType(models.Model):
    """
    Master catalogue of operations/surgical procedures (spec section 5):
    Heart Surgery, Brain Surgery, ENT Surgery, etc. Each has a fixed price
    and a home department, and a suggested default operating team, so Cash
    Counter never has to type a price manually and a new Surgery record can
    be pre-filled from here. Mirrored into website.HospitalService so it is
    immediately searchable/billable from the Cash Counter, same as any other
    billing item.
    """
    name = models.CharField(max_length=150, unique=True)
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='operation_types',
    )
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2)
    default_operating_team = models.CharField(
        max_length=255, blank=True, help_text='e.g. Surgeon + 2 Assistant Surgeons + Anesthetist + 2 OT Nurses',
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ot_operation_type'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (NPR {self.fixed_price})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_hospital_service()

    def _sync_hospital_service(self):
        from website.models import HospitalService
        HospitalService.objects.update_or_create(
            service_code=f"OP-{self.pk:05d}",
            defaults={
                'name': self.name, 'department': self.department,
                'price': self.fixed_price, 'is_active': self.is_active,
            },
        )


class OTRoom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ot_room'
        ordering = ['name']

    def __str__(self):
        return self.name


def _generate_surgery_number():
    year = timezone.now().year
    prefix = f"SURG-{year}-"
    with transaction.atomic():
        last = (
            Surgery.objects.select_for_update()
            .filter(surgery_number__startswith=prefix)
            .order_by('-surgery_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.surgery_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = Surgery.objects.filter(surgery_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class Surgery(models.Model):
    """
    One operation/surgery record - feeds the "operation records" section of
    the patient's digital file (spec section 2) and is the source used by
    Billing for surgery charges (spec section 6).
    """
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class AnesthesiaType(models.TextChoices):
        GENERAL = 'general', 'General'
        REGIONAL = 'regional', 'Regional'
        LOCAL = 'local', 'Local'
        SEDATION = 'sedation', 'Sedation'

    surgery_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='surgeries')
    admission = models.ForeignKey(
        'admissions.Admission', on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries',
    )
    surgery_name = models.CharField(max_length=200)
    operation_type = models.ForeignKey(
        OperationType, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries',
        help_text='Optional link to the priced catalogue entry this surgery is based on.',
    )
    surgeon = models.ForeignKey(
        'doctors.Doctor', on_delete=models.PROTECT, related_name='surgeries_performed',
    )
    assistant_surgeons = models.CharField(max_length=255, blank=True)
    ot_room = models.ForeignKey(OTRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries')
    anesthesia_type = models.CharField(max_length=15, choices=AnesthesiaType.choices, blank=True)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    scheduled_datetime = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    pre_op_notes = models.TextField(blank=True)
    operative_notes = models.TextField(blank=True)
    post_op_notes = models.TextField(blank=True)
    complications = models.TextField(blank=True)

    charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries_scheduled',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    barcode = models.ImageField(upload_to='operation_theatre/barcodes/', blank=True, null=True)

    class Meta:
        db_table = 'ot_surgery'
        ordering = ['-scheduled_datetime']

    def __str__(self):
        return f"{self.surgery_number} - {self.surgery_name} ({self.patient.full_name})"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.surgery_number:
            self.surgery_number = _generate_surgery_number()
        super().save(*args, **kwargs)
        if is_new or not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique Operation Theatre module barcode, same pattern as Admission."""
        from accounts.qr_utils import generate_barcode_file
        self.barcode.save(f"{self.surgery_number}.png", generate_barcode_file(self.surgery_number), save=False)
        Surgery.objects.filter(pk=self.pk).update(barcode=self.barcode.name)
