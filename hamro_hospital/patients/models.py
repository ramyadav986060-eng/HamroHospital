import datetime

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Province(models.Model):
    """One of Nepal's 7 federal provinces."""
    number = models.PositiveSmallIntegerField(unique=True, help_text='1 to 7')
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'patients_province'
        ordering = ['number']

    def __str__(self):
        return f"Province {self.number}: {self.name}"


class District(models.Model):
    """One of Nepal's 77 districts, each belonging to one province."""
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name='districts')
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'patients_district'
        ordering = ['name']
        unique_together = [('province', 'name')]
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return f"{self.name} ({self.province.name})"


class InsuranceCompany(models.Model):
    """
    Minimal insurer directory needed here so Patient can reference it at
    registration time. The full Insurance app (companies management UI,
    claims workflow) is built out in a later checkpoint; this model stays
    the single source of truth and will simply grow more fields/views then.
    """
    name = models.CharField(max_length=150, unique=True)
    contact_person = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'insurance_company'
        ordering = ['name']

    def __str__(self):
        return self.name


class InsuranceCategory(models.Model):
    """
    A coverage tier offered by an insurance company (spec section 6), e.g.
    "Gold - 80% coverage". Used to auto-calculate the insurance-covered
    amount and the patient's payable amount on a bill/operation:
        approved_amount = total * coverage_percent / 100
        patient_payable  = total - approved_amount
    """
    company = models.ForeignKey(InsuranceCompany, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100, help_text="e.g. 'Gold', 'Silver', 'Government Employee'")
    coverage_percent = models.DecimalField(
        max_digits=5, decimal_places=2, help_text='Percentage of the bill covered by insurance, e.g. 80.00',
    )
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'insurance_category'
        ordering = ['company__name', 'name']
        unique_together = [('company', 'name')]

    def __str__(self):
        return f"{self.company.name} - {self.name} ({self.coverage_percent}%)"

    def split_amount(self, total_amount):
        """Return (approved_amount, patient_payable_amount) for a given bill total."""
        import decimal
        total = decimal.Decimal(total_amount)
        approved = (total * self.coverage_percent / decimal.Decimal('100')).quantize(decimal.Decimal('0.01'))
        payable = total - approved
        return approved, payable


def _generate_patient_code():
    """
    Generate the next sequential Patient ID as <HOSPITAL_CODE>-<YEAR>-000001,
    inside an atomic, row-locked transaction so concurrent registrations
    from different counters can never collide or duplicate a number.
    """
    year = timezone.now().year
    prefix = f"{settings.HOSPITAL_CODE}-{year}-"
    with transaction.atomic():
        last = (
            Patient.objects.select_for_update()
            .filter(patient_code__startswith=prefix)
            .order_by('-patient_code')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.patient_code.split('-')[-1]) + 1
            except ValueError:
                next_seq = Patient.objects.filter(patient_code__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:06d}"


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'

    class BloodGroup(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'
        UNKNOWN = '', 'Unknown'

    patient_code = models.CharField(max_length=30, unique=True, editable=False, db_index=True)

    # Required
    first_name = models.CharField(max_length=100, blank=False, null=False)
    last_name = models.CharField(max_length=100, blank=False, null=False)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField()
    age_at_registration = models.CharField(
        max_length=50, blank=True,
        help_text="How the age was entered at registration, e.g. '24 Years', '11 Years 2 Months', '15 Days'. "
                   "Date of Birth above is auto-calculated from this and can be corrected manually.",
    )
    phone_number = models.CharField(max_length=20, blank=False, null=False)
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name='patients')

    # Optional address detail (Nepal has 753 local levels - kept free-text by design)
    municipality = models.CharField(max_length=150, blank=True, help_text='Municipality / Rural Municipality')
    ward_number = models.PositiveSmallIntegerField(null=True, blank=True)
    local_address = models.CharField(max_length=200, blank=True, help_text='Tole / Street')

    # Optional identity/medical fields
    citizenship_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    guardian_name = models.CharField(max_length=150, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='patients/photos/', blank=True, null=True)
    remarks = models.TextField(blank=True)
    known_allergies = models.CharField(max_length=255, blank=True, help_text='e.g. Penicillin, Sulfa drugs, Latex')

    # Insurance (optional; shown/hidden dynamically in the registration form)
    has_insurance = models.BooleanField(default=False)
    insurance_company = models.ForeignKey(
        InsuranceCompany, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients',
    )
    insurance_category = models.ForeignKey(
        InsuranceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients',
        help_text='Coverage tier used to auto-calculate insurance billing splits.',
    )
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_membership_number = models.CharField(max_length=100, blank=True)
    insurance_card_number = models.CharField(max_length=100, blank=True)
    insurance_expiry_date = models.DateField(null=True, blank=True)
    insurance_remarks = models.CharField(max_length=255, blank=True)

    qr_code = models.ImageField(upload_to='patients/qrcodes/', blank=True, null=True)
    barcode = models.ImageField(upload_to='patients/barcodes/', blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='patients_registered',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patients_patient'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f"{self.patient_code} - {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = datetime.date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def is_within_free_edit_window(self):
        """Registration Counter can correct details free of charge within 24 hours."""
        return (timezone.now() - self.created_at) <= datetime.timedelta(hours=24)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.patient_code:
            self.patient_code = _generate_patient_code()
        super().save(*args, **kwargs)
        if is_new or not self.qr_code:
            self._generate_qr_code()
        if is_new or not self.barcode:
            self._generate_barcode()

    def _generate_qr_code(self):
        """Generate and attach a QR code encoding this patient's code."""
        import io
        import qrcode
        from django.core.files.base import ContentFile

        qr_img = qrcode.make(self.patient_code)
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        filename = f"{self.patient_code}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        Patient.objects.filter(pk=self.pk).update(qr_code=self.qr_code.name)

    def _generate_barcode(self):
        """Generate and attach a Code128 barcode encoding this patient's hospital number."""
        import io
        import barcode
        from barcode.writer import ImageWriter
        from django.core.files.base import ContentFile

        rv = io.BytesIO()
        Code128 = barcode.get_barcode_class('code128')
        Code128(self.patient_code, writer=ImageWriter()).write(rv, options={'write_text': False, 'module_height': 10})
        filename = f"{self.patient_code}_barcode.png"
        self.barcode.save(filename, ContentFile(rv.getvalue()), save=False)
        Patient.objects.filter(pk=self.pk).update(barcode=self.barcode.name)


def _generate_receipt_number():
    """REC-YYYYMMDD-00001, atomic per-day counter."""
    today_str = timezone.now().strftime('%Y%m%d')
    prefix = f"REC-{today_str}-"
    with transaction.atomic():
        last = (
            Visit.objects.select_for_update()
            .filter(receipt_number__startswith=prefix)
            .order_by('-receipt_number')
            .first()
        )
        next_seq = 1
        if last:
            try:
                next_seq = int(last.receipt_number.split('-')[-1]) + 1
            except ValueError:
                next_seq = Visit.objects.filter(receipt_number__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:05d}"


class Visit(models.Model):
    """
    One OPD registration/visit. Created at the Registration Counter.
    A correction made more than 24 hours after the original patient
    registration creates a *new* Visit (is_correction_of points back to
    the original) rather than silently editing history.
    """
    class PatientType(models.TextChoices):
        NEW = 'new', 'New Patient'
        OLD = 'old', 'Old Patient'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        ESEWA = 'esewa', 'eSewa'
        FONEPAY = 'fonepay', 'FonePay'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CARD = 'card', 'Card Payment'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Registered - Payment Pending'
        PAID = 'paid', 'Registered - Payment Completed'

    receipt_number = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    barcode = models.ImageField(upload_to='visits/barcodes/', blank=True, null=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='visits')
    department = models.ForeignKey('departments.Department', on_delete=models.PROTECT, related_name='visits')
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='visits',
    )

    patient_type = models.CharField(max_length=10, choices=PatientType.choices)
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2)
    chief_complaint = models.CharField(max_length=255, blank=True)
    
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    payment_status = models.CharField(
        max_length=255, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )

    token_number = models.PositiveIntegerField(editable=False)
    visit_date = models.DateField(default=datetime.date.today)
    visit_time = models.TimeField(auto_now_add=True)

    is_correction_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='corrections',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='visits_registered',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'patients_visit'
        ordering = ['-visit_date', '-visit_time']

    def __str__(self):
        return f"{self.receipt_number} - {self.patient.full_name}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = _generate_receipt_number()
        if not self.token_number:
            with transaction.atomic():
                last_token = (
                    Visit.objects.select_for_update()
                    .filter(department=self.department, visit_date=self.visit_date)
                    .order_by('-token_number')
                    .first()
                )
                self.token_number = (last_token.token_number + 1) if last_token else 1
        super().save(*args, **kwargs)
        if not self.barcode:
            self._generate_barcode()
            
    def _generate_barcode(self):
        import io
        import barcode
        from barcode.writer import ImageWriter
        from django.core.files.base import ContentFile

        rv = io.BytesIO()
        Code128 = barcode.get_barcode_class('code128')
        Code128(self.receipt_number, writer=ImageWriter()).write(rv, options={'write_text': False, 'module_height': 10})
        self.barcode.save(f"{self.receipt_number}_barcode.png", ContentFile(rv.getvalue()), save=True)
