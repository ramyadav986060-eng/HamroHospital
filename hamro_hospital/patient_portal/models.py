from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone


class PatientAccount(models.Model):
    """
    Self-service login for the Patient Portal on the public website.

    This is intentionally separate from accounts.User (staff logins) -
    patients are never staff and should never share the staff role/
    permission system. A patient signs up by proving they already have a
    hospital record: their Patient ID (patient_code) plus the phone number
    on file must match an existing patients.Patient row.

    Session-based auth (not Django's auth backend, since Patient is not
    AUTH_USER_MODEL): on successful login the view stores
    request.session['patient_account_id']; see patient_portal.decorators.
    """
    patient = models.OneToOneField(
        'patients.Patient', on_delete=models.CASCADE, related_name='portal_account',
    )
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'patient_portal_account'

    def __str__(self):
        return f"Portal account for {self.patient.patient_code}"

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def record_login(self):
        self.last_login_at = timezone.now()
        self.save(update_fields=['last_login_at'])
