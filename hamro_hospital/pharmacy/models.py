import datetime

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Medicine(models.Model):
    """Master medicine catalogue - only Super Admin can add/edit/adjust prices."""
    medicine_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    generic_name = models.CharField(max_length=150, blank=True)
    brand_name = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=100, blank=True)
    strength = models.CharField(max_length=50, blank=True, help_text='e.g. 500mg')
    unit = models.CharField(max_length=30, default='Tablet', help_text='Tablet, Syrup, Injection, etc.')

    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=10)

    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    manufacturer = models.CharField(max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pharmacy_medicine'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.medicine_code})"

    @property
    def is_out_of_stock(self):
        return self.current_stock <= 0

    @property
    def is_low_stock(self):
        return 0 < self.current_stock <= self.minimum_stock

    @property
    def is_near_expiry(self):
        if not self.expiry_date:
            return False
        return 0 <= (self.expiry_date - datetime.date.today()).days <= 90

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < datetime.date.today())


class StockAdjustment(models.Model):
    """
    Every purchase, correction, write-off, or patient return against a
    medicine's stock. Never edits history - always appends a new row and
    stores the resulting stock level for a clean audit trail.
    """
    class Reason(models.TextChoices):
        PURCHASE = 'purchase', 'Purchase'
        CORRECTION = 'correction', 'Correction'
        EXPIRED_WRITE_OFF = 'expired_write_off', 'Expired Write-off'
        PATIENT_RETURN = 'patient_return', 'Patient Return'

    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='stock_adjustments')
    quantity_change = models.IntegerField(help_text='Positive to add stock, negative to remove.')
    reason = models.CharField(max_length=20, choices=Reason.choices)
    resulting_stock = models.PositiveIntegerField(editable=False)
    notes = models.CharField(max_length=255, blank=True)
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pharmacy_stock_adjustment'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medicine.name}: {self.quantity_change:+d} ({self.get_reason_display()})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            medicine = Medicine.objects.select_for_update().get(pk=self.medicine_id)
            new_stock = medicine.current_stock + self.quantity_change
            if new_stock < 0:
                raise ValueError('Stock adjustment would result in negative stock.')
            medicine.current_stock = new_stock
            medicine.save(update_fields=['current_stock'])
            self.resulting_stock = new_stock
            super().save(*args, **kwargs)


def _generate_sale_number():
    """PH-YYYYMMDD-00001, atomic per-day counter."""
    today_str = timezone.now().strftime('%Y%m%d')
    prefix = f"PH-{today_str}-"
    with transaction.atomic():
        last = (
            PharmacySale.objects.select_for_update()
            .filter(sale_number__startswith=prefix)
            .order_by('-sale_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.sale_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = PharmacySale.objects.filter(sale_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:05d}"


class PharmacySale(models.Model):
    class PrescriptionSource(models.TextChoices):
        DIGITAL = 'digital', 'Digital Prescription'
        MANUAL = 'manual', 'Manual / Paper Prescription'
        WALKIN = 'walkin', 'Walk-in Sale (No Prescription)'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        ESEWA = 'esewa', 'eSewa'
        KHALTI = 'khalti', 'Khalti'
        PHONEPE = 'phonepe', 'PhonePe'
        MOBILE_BANKING = 'mobile_banking', 'Mobile Banking'
        FONEPAY = 'fonepay', 'FonePay'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CARD = 'card', 'Card Payment'
        INSURANCE = 'insurance', 'Insurance'
        CREDIT = 'credit', 'Credit'

    sale_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_sales',
    )
    consultation = models.ForeignKey(
        'consultations.Consultation', on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_sales',
    )
    prescription_source = models.CharField(max_length=10, choices=PrescriptionSource.choices)
    manual_prescription_copy = models.FileField(upload_to='manual_prescriptions/', blank=True, null=True)

    payment_method = models.CharField(max_length=15, choices=PaymentMethod.choices)
    insurance_company = models.ForeignKey(
        'patients.InsuranceCompany', on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_sales',
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pharmacy_sales_made')
    barcode = models.ImageField(upload_to='pharmacy/barcodes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pharmacy_sale'
        ordering = ['-created_at']

    def __str__(self):
        return self.sale_number

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.sale_number:
            self.sale_number = _generate_sale_number()
        super().save(*args, **kwargs)
        if is_new or not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique Pharmacy barcode for this sale."""
        from accounts.qr_utils import generate_barcode_file
        self.barcode.save(f"{self.sale_number}.png", generate_barcode_file(self.sale_number), save=False)
        PharmacySale.objects.filter(pk=self.pk).update(barcode=self.barcode.name)

    def recalculate_total(self):
        total = sum((item.line_total for item in self.items.all()), start=0)
        self.total_amount = total
        PharmacySale.objects.filter(pk=self.pk).update(total_amount=total)


class PharmacySaleItem(models.Model):
    sale = models.ForeignKey(PharmacySale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='sale_items')
    medicine_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    prescription_item = models.ForeignKey(
        'consultations.PrescriptionItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='sale_items',
    )

    class Meta:
        db_table = 'pharmacy_sale_item'

    def __str__(self):
        return f"{self.medicine_name} x{self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
