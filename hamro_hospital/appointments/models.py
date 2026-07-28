import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


def _generate_appointment_number():
    """
    Generate the next sequential Hospital Extension Service number as
    HES000001, HES000002, ... inside an atomic, row-locked transaction so
    concurrent bookings can never collide or duplicate a number.
    """
    prefix = "HES"
    with transaction.atomic():
        last = (
            Appointment.objects.select_for_update()
            .filter(appointment_number__startswith=prefix)
            .exclude(appointment_number='')
            .order_by('-appointment_number')
            .first()
        )
        next_seq = 1
        if last and last.appointment_number:
            try:
                next_seq = int(last.appointment_number[len(prefix):]) + 1
            except ValueError:
                next_seq = Appointment.objects.filter(appointment_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class Appointment(models.Model):
    """
    Public online appointment booking, paid via eSewa.

    Lifecycle:
      1. Visitor submits the booking form -> row created with a unique
         transaction_uuid and payment_status=PENDING. appointment_number is
         still blank at this point.
      2. Visitor is redirected to eSewa (sandbox or live) to pay the
         registration fee (same New/Old fee logic as walk-in registration).
      3. eSewa redirects back to our success/failure URL. On success we
         verify the transaction and call mark_paid(), which stamps the
         permanent appointment_number, sets status to PAID, stores the
         eSewa reference ID, and generates a QR code.
      4. A failed/cancelled payment leaves payment_status=FAILED and the
         visitor sees a "Payment Failed" page with an option to retry.
    """

    class PatientType(models.TextChoices):
        NEW = 'new', 'New Patient'
        OLD = 'old', 'Old Patient'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash on Arrival'
        ESEWA = 'esewa', 'eSewa'
        KHALTI = 'khalti', 'Khalti'
        PHONEPE = 'phonepe', 'PhonePe'
        MOBILE_BANKING = 'mobile_banking', 'Mobile Banking'
        FONEPAY = 'fonepay', 'FonePay'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CARD = 'card', 'Card Payment'

    appointment_number = models.CharField(max_length=30, unique=True, blank=True, null=True, db_index=True)
    transaction_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Patient details captured directly on the public form (not yet a
    # registered Patient record - Registration Counter formally registers
    # them, using this appointment as reference, when they arrive).
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    age = models.PositiveIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    district = models.ForeignKey('patients.District', on_delete=models.PROTECT, related_name='appointments')
    municipality = models.CharField(max_length=150, blank=True)
    ward_number = models.PositiveSmallIntegerField(null=True, blank=True)
    local_address = models.CharField(max_length=200, blank=True)

    department = models.ForeignKey('departments.Department', on_delete=models.PROTECT, related_name='appointments')
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments',
    )
    preferred_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    chief_complaint = models.CharField(max_length=255, blank=True)

    patient_type = models.CharField(max_length=10, choices=PatientType.choices, default=PatientType.NEW)
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2)

    payment_method = models.CharField(
        max_length=15, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    esewa_ref_id = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    qr_code = models.ImageField(upload_to='appointments/qrcodes/', blank=True, null=True)
    barcode = models.ImageField(upload_to='appointments/barcodes/', blank=True, null=True)

    linked_patient = models.ForeignKey(
        'patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='online_appointments',
        help_text='Set by Registration Counter once the patient physically checks in.',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'appointments_appointment'
        ordering = ['-created_at']

    def __str__(self):
        return self.appointment_number or f"Pending ({self.transaction_uuid})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def mark_paid(self, esewa_ref_id):
        """Called by the eSewa success callback view after signature verification."""
        if self.payment_status == self.PaymentStatus.PAID:
            return  # idempotent - eSewa may redirect/callback more than once
        self.payment_status = self.PaymentStatus.PAID
        self.esewa_ref_id = esewa_ref_id
        self.paid_at = timezone.now()
        if not self.appointment_number:
            self.appointment_number = _generate_appointment_number()
        self.save()
        self._generate_qr_code()
        self._generate_barcode()

    def mark_failed(self):
        self.payment_status = self.PaymentStatus.FAILED
        self.save(update_fields=['payment_status'])

    def _generate_qr_code(self):
        import io
        import qrcode
        from django.core.files.base import ContentFile

        qr_img = qrcode.make(self.appointment_number)
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        self.qr_code.save(f"{self.appointment_number}.png", ContentFile(buffer.getvalue()), save=False)
        Appointment.objects.filter(pk=self.pk).update(qr_code=self.qr_code.name)

    def _generate_barcode(self):
        import io
        import barcode as barcode_lib
        from barcode.writer import ImageWriter
        from django.core.files.base import ContentFile

        rv = io.BytesIO()
        Code128 = barcode_lib.get_barcode_class('code128')
        Code128(self.appointment_number, writer=ImageWriter()).write(rv, options={'write_text': False, 'module_height': 10})
        self.barcode.save(f"{self.appointment_number}_barcode.png", ContentFile(rv.getvalue()), save=False)
        Appointment.objects.filter(pk=self.pk).update(barcode=self.barcode.name)
