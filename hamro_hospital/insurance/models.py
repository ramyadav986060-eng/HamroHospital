from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


def _generate_claim_number():
    year = timezone.now().year
    prefix = f"CLAIM-{year}-"
    with transaction.atomic():
        last = (
            InsuranceClaim.objects.select_for_update()
            .filter(claim_number__startswith=prefix)
            .order_by('-claim_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.claim_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = InsuranceClaim.objects.filter(claim_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class InsuranceClaim(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SETTLED = 'settled', 'Settled'

    claim_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='insurance_claims')
    insurance_company = models.ForeignKey(
        'patients.InsuranceCompany', on_delete=models.PROTECT, related_name='claims',
    )

    # Optional link back to whichever record generated this claim.
    related_bill = models.ForeignKey(
        'billing.Bill', on_delete=models.SET_NULL, null=True, blank=True, related_name='insurance_claims',
    )
    related_pharmacy_sale = models.ForeignKey(
        'pharmacy.PharmacySale', on_delete=models.SET_NULL, null=True, blank=True, related_name='insurance_claims',
    )

    amount_claimed = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rejected_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    co_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_cashless = models.BooleanField(default=False)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    remarks = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='claims_submitted',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='claims_reviewed',
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    barcode = models.ImageField(upload_to='insurance/barcodes/', blank=True, null=True)

    class Meta:
        db_table = 'insurance_claim'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.claim_number} - {self.patient.full_name}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.claim_number:
            self.claim_number = _generate_claim_number()
        super().save(*args, **kwargs)
        if is_new or not self.barcode:
            self._generate_barcode()

    def _generate_barcode(self):
        """Own unique Insurance module barcode for this claim."""
        from accounts.qr_utils import generate_barcode_file
        self.barcode.save(f"{self.claim_number}.png", generate_barcode_file(self.claim_number), save=False)
        InsuranceClaim.objects.filter(pk=self.pk).update(barcode=self.barcode.name)
