from django.db import models
from django.conf import settings

class Referral(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("completed", "Completed")
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="referrals")
    referred_by = models.ForeignKey("doctors.Doctor", on_delete=models.SET_NULL, null=True, related_name="referrals_made")
    to_department = models.ForeignKey("departments.Department", on_delete=models.SET_NULL, null=True, related_name="referrals_received")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'referrals_referral'
        ordering = ['-created_at']

    def __str__(self):
        return f"Referral for {self.patient} to {self.to_department}"
