from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


def _generate_bill_number():
    """BILL-YYYYMMDD-00001, atomic per-day counter."""
    today_str = timezone.now().strftime('%Y%m%d')
    prefix = f"BILL-{today_str}-"
    with transaction.atomic():
        last = (
            Bill.objects.select_for_update()
            .filter(bill_number__startswith=prefix)
            .order_by('-bill_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.bill_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = Bill.objects.filter(bill_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:05d}"


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
    OTHER = 'other', 'Other'


class BillType(models.TextChoices):
    OPD = 'opd', 'OPD Billing'
    IPD = 'ipd', 'IPD Billing'
    LAB = 'lab', 'Lab Billing'
    RADIOLOGY = 'radiology', 'Radiology Billing'
    BLOOD_BANK = 'blood_bank', 'Blood Bank Billing'
    PHARMACY = 'pharmacy', 'Pharmacy Billing'
    SURGERY = 'surgery', 'Surgery Billing'
    OTHER = 'other', 'Other'


class Bill(models.Model):
    class Status(models.TextChoices):
        PAID = 'paid', 'Paid'
        REFUNDED = 'refunded', 'Refunded'

    bill_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='bills')
    bill_type = models.CharField(max_length=10, choices=BillType.choices, default=BillType.OPD)
    admission = models.ForeignKey(
        'admissions.Admission', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills',
    )
    surgery = models.ForeignKey(
        'operation_theatre.Surgery', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills',
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills_created',
    )
    counter_name = models.CharField(
        max_length=100, default='Main Cash Counter',
        help_text='e.g. "Main Cash Counter", "Laboratory Counter", "Radiology Counter"',
    )
    payment_method = models.CharField(max_length=15, choices=PaymentMethod.choices)
    insurance_company = models.ForeignKey(
        'patients.InsuranceCompany', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills',
    )
    insurance_coverage_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PAID)
    barcode = models.ImageField(upload_to='billing/barcodes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_bill'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.bill_number} - {self.patient.full_name}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.bill_number:
            self.bill_number = _generate_bill_number()
        super().save(*args, **kwargs)
        if is_new or not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique rectangular barcode for this bill/invoice (separate from Patient QR)."""
        from accounts.qr_utils import generate_barcode_file
        self.barcode.save(f"{self.bill_number}.png", generate_barcode_file(self.bill_number), save=False)
        Bill.objects.filter(pk=self.pk).update(barcode=self.barcode.name)

    def recalculate_total(self):
        total = sum((item.line_total for item in self.items.all()), start=0)
        self.total_amount = total
        Bill.objects.filter(pk=self.pk).update(total_amount=total)

    @property
    def discount_total(self):
        return sum(
            (d.discount_amount for d in self.discount_requests.filter(status=DiscountRequest.Status.APPROVED)),
            start=0,
        )

    @property
    def final_amount_paid(self):
        return self.total_amount - self.discount_total - self.insurance_coverage_amount


class BillItem(models.Model):
    """
    One billed service line. service_name/unit_price are snapshotted at
    billing time so a later Super Admin price change never rewrites a
    historical receipt (audit-safe).
    """
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(
        'website.HospitalService', on_delete=models.SET_NULL, null=True, blank=True, related_name='bill_items',
    )
    service_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'billing_bill_item'

    def __str__(self):
        return f"{self.service_name} x{self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class ReprintLog(models.Model):
    """
    A separately audited reprint action that never touches the original
    Bill record - matches the spec's "reprint never modifies the original".
    """
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='reprints')
    reprinted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reprinted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_reprint_log'


class RefundRequest(models.Model):
    """
    Cash Counter requests a refund against a paid bill; the Accounts
    department (or Super Admin) reviews and approves/rejects it. Approving
    marks the underlying Bill as REFUNDED - the bill itself is never edited
    or deleted, matching the audit-safe pattern used across the system.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='refund_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds_requested',
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'billing_refund_request'
        ordering = ['-requested_at']

    def __str__(self):
        return f"Refund for {self.bill.bill_number} ({self.get_status_display()})"

    def approve(self, reviewed_by, notes=''):
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
        Bill.objects.filter(pk=self.bill_id).update(status=Bill.Status.REFUNDED)

    def reject(self, reviewed_by, notes=''):
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class DiscountRequest(models.Model):
    """
    Cash Counter's "Poor Patient" discount workflow (spec section 7).

    A discount is requested against an already-created Bill (e.g. after a
    surgery bill of Rs. 50,000 is raised, Cash Counter requests it be
    reduced to Rs. 10,000 for a financially weak patient). Accounts / Super
    Admin approves or rejects; approving records the discount but - like
    RefundRequest - never edits the original bill amount, keeping the full
    audit trail intact. The receipt/report layer subtracts approved
    discounts from what the patient still owes.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='discount_requests')
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(
        max_length=150,
        help_text="e.g. 'Financially weak patient', 'Staff family', 'Charity case'",
    )
    remarks = models.TextField(
        blank=True,
        help_text="e.g. 'Patient is financially weak. Operation completed for Rs. 10,000 instead of Rs. 50,000.'",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='discounts_requested',
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='discounts_approved',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'billing_discount_request'
        ordering = ['-requested_at']

    def __str__(self):
        return f"Discount for {self.bill.bill_number} ({self.get_status_display()})"

    @property
    def payable_amount(self):
        return self.original_amount - self.discount_amount

    def approve(self, approved_by, notes=''):
        self.status = self.Status.APPROVED
        self.approved_by = approved_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

    def reject(self, approved_by, notes=''):
        self.status = self.Status.REJECTED
        self.approved_by = approved_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
