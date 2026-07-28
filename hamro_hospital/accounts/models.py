from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    REGISTRATION_COUNTER = 'registration_counter', 'Registration Counter'
    CASH_COUNTER = 'cash_counter', 'Cash Counter'
    DOCTOR = 'doctor', 'Doctor'
    PHARMACY = 'pharmacy', 'Pharmacy'
    LABORATORY = 'laboratory', 'Laboratory'
    RADIOLOGY = 'radiology', 'Radiology Counter'
    INSURANCE = 'insurance', 'Insurance Counter'
    # Added in Checkpoint 3
    WARD_ADMISSION = 'ward_admission', 'Ward / Admission'
    NURSING = 'nursing', 'Nursing'
    OPERATION_THEATRE = 'operation_theatre', 'Operation Theatre'
    BLOOD_BANK = 'blood_bank', 'Blood Bank'
    ACCOUNTS_DEPT = 'accounts_dept', 'Finance'
    MEDICAL_RECORDS = 'medical_records', 'Medical Records'


class User(AbstractUser):
    """
    Custom user model for all hospital staff.

    A Django superuser (is_superuser=True) is always treated as having
    full Super Admin access regardless of the stored `role` value - see
    accounts.decorators.role_required().
    """
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.REGISTRATION_COUNTER,
        help_text='Primary role used to route the dashboard and gate permissions.',
    )
    phone_number = models.CharField(max_length=20, blank=True)
    is_active_staff = models.BooleanField(
        default=True,
        help_text='Super Admin can deactivate a staff account without deleting it.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_user'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        full = self.get_full_name()
        return f"{full or self.username} ({self.get_role_display()})"

    @property
    def effective_role(self):
        """Superusers always resolve to Super Admin regardless of stored role."""
        return Role.SUPER_ADMIN if self.is_superuser else self.role

    def dashboard_url_name(self):
        mapping = {
            Role.SUPER_ADMIN: 'accounts:dashboard_super_admin',
            Role.REGISTRATION_COUNTER: 'patients:dashboard',
            Role.CASH_COUNTER: 'billing:dashboard',
            Role.DOCTOR: 'doctors:dashboard',
            Role.PHARMACY: 'pharmacy:dashboard',
            Role.LABORATORY: 'laboratory:dashboard',
            Role.RADIOLOGY: 'radiology:dashboard',
            Role.INSURANCE: 'insurance:dashboard',
            Role.WARD_ADMISSION: 'admissions:admission_list',
            Role.NURSING: 'nursing:dashboard',
            Role.OPERATION_THEATRE: 'operation_theatre:dashboard',
            Role.BLOOD_BANK: 'blood_bank:dashboard',
            Role.ACCOUNTS_DEPT: 'finance:dashboard',
            Role.MEDICAL_RECORDS: 'medical_records:dashboard',
        }
        return mapping.get(self.effective_role, 'accounts:dashboard_super_admin')


class AuditLog(models.Model):
    """
    System-wide, append-only audit trail.

    Every sensitive action across every module writes one row here via
    accounts.utils.write_audit_log(). Rows are never edited or deleted;
    corrections create a new row referencing the same patient/receipt.
    """

    class Action(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        PATIENT_REGISTER = 'patient_register', 'Patient Registered'
        PATIENT_UPDATE = 'patient_update', 'Patient Updated'
        VISIT_CORRECTION = 'visit_correction', 'New Visit (Correction)'
        APPOINTMENT_BOOKED = 'appointment_booked', 'Appointment Booked'
        APPOINTMENT_PAID = 'appointment_paid', 'Appointment Payment Confirmed'
        PAYMENT = 'payment', 'Payment Collected'
        REPRINT = 'reprint', 'Document Reprinted'
        REFUND = 'refund', 'Refund Issued'
        ADMISSION = 'admission', 'Patient Admitted'
        DISCHARGE = 'discharge', 'Patient Discharged'
        CLAIM_SUBMITTED = 'claim_submitted', 'Insurance Claim Submitted'
        CLAIM_REVIEWED = 'claim_reviewed', 'Insurance Claim Reviewed'
        STOCK_ADJUSTED = 'stock_adjusted', 'Medicine Stock Adjusted'
        PHARMACY_SALE = 'pharmacy_sale', 'Pharmacy Sale'
        LAB_RESULT = 'lab_result', 'Lab Result Uploaded'
        RADIOLOGY_RESULT = 'radiology_result', 'Radiology Report Uploaded'
        USER_CREATED = 'user_created', 'Staff Account Created'
        USER_DEACTIVATED = 'user_deactivated', 'Staff Account Deactivated'
        DOCUMENT_UPLOADED = 'document_uploaded', 'Document Uploaded'
        DOCUMENT_REPLACED = 'document_replaced', 'Document Replaced'
        DOCUMENT_DOWNLOADED = 'document_downloaded', 'Document Downloaded'
        DOCUMENT_DELETED = 'document_deleted', 'Document Deleted'
        NURSING_NOTE = 'nursing_note', 'Nursing Note Recorded'
        SURGERY_SCHEDULED = 'surgery_scheduled', 'Surgery Scheduled'
        SURGERY_UPDATED = 'surgery_updated', 'Surgery Record Updated'
        BLOOD_UNIT_ADDED = 'blood_unit_added', 'Blood Unit Added to Inventory'
        BLOOD_REQUESTED = 'blood_requested', 'Blood Requested'
        BLOOD_ISSUED = 'blood_issued', 'Blood Unit Issued'
        REFUND_REQUESTED = 'refund_requested', 'Refund Requested'
        REFUND_REVIEWED = 'refund_reviewed', 'Refund Reviewed'
        BACKUP_CREATED = 'backup_created', 'System Backup Created'
        RESTORE_PERFORMED = 'restore_performed', 'System Restore Performed'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs',
    )
    role_at_time = models.CharField(max_length=30, blank=True)
    action = models.CharField(max_length=30, choices=Action.choices)
    description = models.CharField(max_length=255)

    patient_id_text = models.CharField(max_length=50, blank=True, help_text='Patient code, if relevant')
    receipt_number = models.CharField(max_length=50, blank=True, help_text='Receipt/bill/claim number, if relevant')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=30, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['patient_id_text']),
        ]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.get_action_display()} - {self.description}"


class Notification(models.Model):
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True, help_text="Specific user for this notification, or null for all users of a certain role."
    )
    role = models.CharField(
        max_length=30, choices=Role.choices, null=True, blank=True,
        help_text="Target role (e.g. all Laboratory staff)."
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_notification'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.message[:30]}"


class HospitalSetting(models.Model):
    """
    Hospital Settings model for configuring name, logo, address, PAN, social links, etc.
    Supports a singleton pattern for current hospital configuration.
    """
    name = models.CharField(max_length=200, default='Hamro Hospital')
    logo = models.ImageField(upload_to='hospital/', blank=True, null=True)
    address = models.CharField(max_length=255, default='Maharajgunj, Kathmandu, Nepal')
    phone = models.CharField(max_length=50, default='01-4412345')
    email = models.EmailField(default='info@hamrohospital.example.np')
    website = models.URLField(default='https://www.hamrohospital.example.np')
    pan_number = models.CharField(max_length=50, blank=True, default='300123456')
    registration_number = models.CharField(max_length=50, blank=True, default='REG-100234')
    opening_hours = models.CharField(max_length=255, default='24/7 for Emergency, OPD: Sun-Fri 8 AM - 2 PM')
    emergency_contact = models.CharField(max_length=100, default='01-4412346')
    facebook_url = models.URLField(blank=True, default='https://facebook.com')
    twitter_url = models.URLField(blank=True, default='https://twitter.com')
    footer_information = models.TextField(default='Hamro Hospital Maharajgunj. All rights reserved.')
    default_currency = models.CharField(max_length=10, default='NPR')
    default_timezone = models.CharField(max_length=50, default='Asia/Kathmandu')
    receipt_settings = models.TextField(blank=True, default='Fit on half A4. Print barcode on top-right.')
    print_settings = models.TextField(blank=True, default='Standard A4 Portrait')
    theme_color = models.CharField(max_length=20, default='#1a365d')

    class Meta:
        db_table = 'accounts_hospital_setting'

    def __str__(self):
        return self.name

    @classmethod
    def get_solo(cls):
        """Return the solo configuration or create it if missing."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
