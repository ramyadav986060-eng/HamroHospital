from django.db import models
from django.conf import settings
from django.utils import timezone

class Referral(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("acknowledged", "Acknowledged"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    class ReferralType(models.TextChoices):
        GENERAL = 'general', 'General Department'
        LABORATORY = 'laboratory', 'Laboratory'
        RADIOLOGY = 'radiology', 'Radiology'
        PHARMACY = 'pharmacy', 'Pharmacy'
        NURSING = 'nursing', 'Nursing'
        ADMISSION = 'admission', 'Admission / Ward'
        OPERATION_THEATRE = 'operation_theatre', 'Operation Theatre (OT)'
        BLOOD_BANK = 'blood_bank', 'Blood Bank'

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="referrals")
    referred_by = models.ForeignKey("doctors.Doctor", on_delete=models.SET_NULL, null=True, related_name="referrals_made")
    to_department = models.ForeignKey("departments.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals_received")
    referral_type = models.CharField(max_length=30, choices=ReferralType.choices, default=ReferralType.GENERAL)
    diagnosis = models.CharField(max_length=255, blank=True)
    reason = models.TextField()
    clinical_notes = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    attachment = models.FileField(upload_to='referrals/attachments/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_acknowledged')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_completed')
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'referrals_referral'
        ordering = ['-created_at']

    def __str__(self):
        return f"Referral for {self.patient} to {self.to_department}"

    def acknowledge(self, user):
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at', 'updated_at'])

    def complete(self, user):
        self.status = 'completed'
        self.completed_by = user
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_by', 'completed_at', 'updated_at'])
