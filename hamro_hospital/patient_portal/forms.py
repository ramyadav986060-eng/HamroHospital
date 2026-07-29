from django import forms
from django.db.models import Q

from patient_portal.models import PatientAccount
from patients.models import Patient, Visit, District
from departments.models import Department
from doctors.models import Doctor


class PatientSignupForm(forms.Form):
    """
    Signup proves identity using data the hospital already has on file:
    Patient ID (hospital_id) + the phone number on the patient record.
    This does not create a new Patient - it only creates portal login
    access for a patient who was already registered at the hospital.
    """
    hospital_id = forms.CharField(
        label='Hospital / Patient ID',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HT-2026-000001'}),
    )
    phone_number = forms.CharField(
        label='Phone Number or Email',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number or email on your patient record'}),
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), min_length=8)
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        hospital_id = cleaned_data.get('hospital_id', '').strip()
        phone_number = cleaned_data.get('phone_number', '').strip()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')

        if hospital_id and phone_number:
            try:
                patient = Patient.objects.get(
                    Q(phone_number=phone_number) | Q(email__iexact=phone_number),
                    patient_code__iexact=hospital_id,
                )
            except Patient.DoesNotExist:
                raise forms.ValidationError(
                    'We could not find a patient record matching that Hospital ID and phone/email. '
                    'Please check the details on your patient card, or contact the Registration Counter.'
                )
            if PatientAccount.objects.filter(patient=patient).exists():
                raise forms.ValidationError(
                    'A portal account already exists for this patient. Please log in instead.'
                )
            cleaned_data['patient'] = patient
        return cleaned_data


class PatientLoginForm(forms.Form):
    hospital_id = forms.CharField(
        label='Hospital / Patient ID',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HT-2026-000001', 'autofocus': True}),
    )
    phone_number = forms.CharField(
        required=False,
        label='Phone Number or Email (optional after account creation)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional if Hospital ID + password are correct'}),
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class PatientVisitBookingForm(forms.ModelForm):
    """
    Used inside the portal so a logged-in patient can book their own
    visit - New (first-time-this-visit-type) or Follow-up (existing
    patient returning). This creates a real patients.Visit the same way
    the Registration Counter does, so token numbers, receipt numbers, and
    the OPD ticket are generated identically.
    """
    class Meta:
        model = Visit
        fields = ['department', 'doctor', 'patient_type', 'payment_method', 'chief_complaint']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'doctor': forms.Select(attrs={'class': 'form-select', 'id': 'id_doctor'}),
            'patient_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_patient_type'}),
            'payment_method': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_method'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.extension_mode = kwargs.pop('extension_mode', False)
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['doctor'].queryset = Doctor.objects.filter(is_active=True, is_extension_service=True) if self.extension_mode else Doctor.objects.filter(is_active=True)
        self.fields['doctor'].required = False
        self.fields['payment_method'].choices = [
            (Visit.PaymentMethod.CASH, 'Cash (Payment Pending at Hospital)'),
            (Visit.PaymentMethod.ESEWA, 'eSewa (Online Payment)'),
        ]
        self.fields['payment_method'].initial = Visit.PaymentMethod.CASH
        # Relabel to match how a patient thinks about it, while keeping the
        # same underlying New/Old values the fee logic already relies on.
        self.fields['patient_type'].choices = [
            (Visit.PatientType.NEW, 'New Visit (first time for this concern)'),
            (Visit.PatientType.OLD, 'Follow-up Visit'),
        ]

    def clean(self):
        from django.conf import settings
        cleaned_data = super().clean()
        patient_type = cleaned_data.get('patient_type')
        doctor = cleaned_data.get('doctor')
        if self.extension_mode:
            from accounts.models import HospitalSetting
            setting = HospitalSetting.get_solo()
            cleaned_data['registration_fee'] = setting.ehs_new_ticket_fee if patient_type == Visit.PatientType.NEW else setting.ehs_followup_ticket_fee
        elif patient_type == Visit.PatientType.NEW:
            cleaned_data['registration_fee'] = settings.NEW_PATIENT_REGISTRATION_FEE
        else:
            cleaned_data['registration_fee'] = settings.OLD_PATIENT_REGISTRATION_FEE
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    method = forms.ChoiceField(
        choices=[('email', 'Email Address'), ('phone', 'Phone Number')],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_reset_method'}),
        label='Choose Reset Method',
    )
    hospital_id = forms.CharField(
        label='Hospital ID',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HT-2026-000001'}),
    )
    contact_value = forms.CharField(
        label='Email or Phone Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter email or phone number matching your record'}),
    )


class ResetPasswordForm(forms.Form):
    otp_code = forms.CharField(
        required=False,
        label='OTP / Verification Code',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the 6-digit code received'}),
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'At least 8 characters'}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('new_password')
        pw2 = cleaned_data.get('confirm_password')
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


# --- New Patient self-registration (OTP-verified, creates a new Patient) ------
# Spec: Full Name / Phone / OTP / Password / Confirm Password, with an
# auto-generated Hospital Number. Patient.gender and .district are required
# by the schema and aren't optional there, so they're collected here too -
# the district field reuses the exact same searchable dropdown as the staff
# registration form (PatientForm), so typing "B" -> Bagmati etc. works here.

class PatientRegisterDetailsForm(forms.Form):
    full_name = forms.CharField(
        label='Full Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name', 'autofocus': True}),
    )
    phone_number = forms.CharField(
        label='Phone Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '98XXXXXXXX'}),
    )
    email = forms.EmailField(
        required=False,
        label='Email Address (optional)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
    )
    gender = forms.ChoiceField(
        choices=Patient.Gender.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    age_input = forms.CharField(
        label='Age',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "e.g. 24 Years, 11 Years 2 Months, 15 Days"}),
    )
    district = forms.ModelChoiceField(
        queryset=District.objects.select_related('province').order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select district-autocomplete'}),
    )

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if len(name.split()) < 2 or not name:
            raise forms.ValidationError('Please enter both First Name and Last Name.')
        return name





class PatientPortalPasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def __init__(self, account, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account

    def clean_current_password(self):
        value = self.cleaned_data['current_password']
        if not self.account.check_password(value):
            raise forms.ValidationError('Current password is incorrect.')
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') and cleaned.get('confirm_password') and cleaned['new_password'] != cleaned['confirm_password']:
            raise forms.ValidationError('New passwords do not match.')
        return cleaned

# Re-declared final portal forms (kept at end so imports remain stable after profile restrictions).
class PatientRegisterOTPForm(forms.Form):
    otp_code = forms.CharField(
        label='OTP / Verification Code',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': '••••••'}),
    )


class PatientRegisterPasswordForm(forms.Form):
    password = forms.CharField(
        label='Password', min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'At least 8 characters', 'autofocus': True}),
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter your password'}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') and cleaned.get('password_confirm') and cleaned['password'] != cleaned['password_confirm']:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class PatientProfileUpdateForm(forms.ModelForm):
    """Patient portal profile update: permitted contact/address/photo only.

    Patient ID, hospital registration number, registered name and registered phone
    are intentionally excluded; changes to those require authorized staff workflow.
    """
    class Meta:
        model = Patient
        fields = ['email', 'district', 'municipality', 'ward_number', 'local_address', 'photo', 'insurance_remarks']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'district': forms.Select(attrs={'class': 'form-select district-autocomplete'}),
            'municipality': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'local_address': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'insurance_remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['district'].queryset = District.objects.select_related('province').order_by('name')
        for f in ['email', 'municipality', 'ward_number', 'local_address', 'photo', 'insurance_remarks']:
            self.fields[f].required = False
