from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceOrder(models.Model):
    """Universal order/request row for all hospital services.

    This is the HIS backbone recommended in the roadmap. It does not replace
    existing module records yet; it links them together so referrals, bills,
    department work queues and patient timelines can share one lifecycle.
    """
    class ServiceType(models.TextChoices):
        OPD = 'opd', 'OPD'
        LABORATORY = 'laboratory', 'Laboratory'
        RADIOLOGY = 'radiology', 'Radiology'
        PHARMACY = 'pharmacy', 'Pharmacy'
        ADMISSION = 'admission', 'Admission'
        NURSING = 'nursing', 'Nursing'
        OPERATION_THEATRE = 'operation_theatre', 'Operation Theatre'
        BLOOD_BANK = 'blood_bank', 'Blood Bank'
        INSURANCE = 'insurance', 'Insurance'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        ACCEPTED = 'accepted', 'Accepted'
        PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
        PAID = 'paid', 'Paid'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REJECTED = 'rejected', 'Rejected'

    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = 'not_required', 'No Payment Required'
        PENDING = 'pending', 'Payment Pending'
        PAID = 'paid', 'Payment Paid'
        INSURANCE_PENDING = 'insurance_pending', 'Insurance Pending'
        INSURANCE_APPROVED = 'insurance_approved', 'Insurance Approved'

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='service_orders')
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_orders_created')
    source_role = models.CharField(max_length=30, blank=True)
    destination_role = models.CharField(max_length=30, blank=True)
    destination_department = models.ForeignKey('departments.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_orders')
    service_type = models.CharField(max_length=30, choices=ServiceType.choices, default=ServiceType.OTHER)
    service_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    payment_status = models.CharField(max_length=25, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    referral = models.ForeignKey('referrals.Referral', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_orders')
    bill = models.ForeignKey('billing.Bill', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_orders')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_service_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'created_at']),
            models.Index(fields=['service_type', 'status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['bill']),
            models.Index(fields=['referral']),
        ]

    def __str__(self):
        return f'{self.service_name} for {self.patient.patient_code} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        self.total_amount = (self.unit_price or Decimal('0')) * self.quantity
        super().save(*args, **kwargs)

    def mark_accepted(self):
        self.status = self.Status.ACCEPTED
        self.accepted_at = self.accepted_at or timezone.now()
        self.save(update_fields=['status', 'accepted_at', 'updated_at'])

    def mark_paid(self):
        self.payment_status = self.PaymentStatus.PAID
        if self.status in [self.Status.REQUESTED, self.Status.PENDING_PAYMENT]:
            self.status = self.Status.PAID
        self.save(update_fields=['payment_status', 'status', 'updated_at'])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = self.completed_at or timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])


class PaymentEvent(models.Model):
    """Append-only payment event for professional finance reconciliation."""
    bill = models.ForeignKey('billing.Bill', on_delete=models.CASCADE, related_name='payment_events')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_events_received')
    transaction_reference = models.CharField(max_length=120, blank=True)
    gateway_response = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workflow_payment_event'
        ordering = ['-paid_at']
        indexes = [models.Index(fields=['bill', 'paid_at']), models.Index(fields=['payment_method'])]

    def __str__(self):
        return f'{self.bill.bill_number} - {self.amount} ({self.payment_method})'


class PatientTimeline(models.Model):
    """Single chronological patient event stream across the HIS."""
    class EventType(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        VISIT = 'visit', 'OPD Visit'
        CONSULTATION = 'consultation', 'Consultation'
        REFERRAL = 'referral', 'Referral'
        ORDER = 'order', 'Service Order'
        BILL = 'bill', 'Bill'
        PAYMENT = 'payment', 'Payment'
        LAB = 'lab', 'Laboratory'
        RADIOLOGY = 'radiology', 'Radiology'
        PHARMACY = 'pharmacy', 'Pharmacy'
        ADMISSION = 'admission', 'Admission'
        DISCHARGE = 'discharge', 'Discharge'
        DOCUMENT = 'document', 'Document'
        BLOOD_BANK = 'blood_bank', 'Blood Bank'
        OTHER = 'other', 'Other'

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=30, choices=EventType.choices, default=EventType.OTHER)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='timeline_events')
    source_app = models.CharField(max_length=60, blank=True)
    source_model = models.CharField(max_length=60, blank=True)
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_url = models.CharField(max_length=255, blank=True)
    event_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workflow_patient_timeline'
        ordering = ['-event_at']
        indexes = [
            models.Index(fields=['patient', '-event_at']),
            models.Index(fields=['event_type']),
            models.Index(fields=['source_app', 'source_model', 'source_object_id']),
        ]

    def __str__(self):
        return f'{self.patient.patient_code} - {self.title}'
