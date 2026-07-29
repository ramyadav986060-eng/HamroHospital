from django import forms
from django.conf import settings

from patients.models import Patient, Visit, District, InsuranceCompany
from patients.utils import parse_age_to_dob
from departments.models import Department
from doctors.models import Doctor


class PatientForm(forms.ModelForm):
    age_input = forms.CharField(
        required=True,
        label='Age',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "e.g. 24 Years, 11 Years 2 Months, 1 Month, 15 Days",
            'id': 'id_age_input',
        }),
        help_text='Date of Birth below is calculated automatically from this and can be edited manually.',
    )

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth', 'phone_number', 'district',
            'municipality', 'ward_number', 'local_address',
            'citizenship_number', 'email', 'blood_group', 'occupation', 'guardian_name',
            'emergency_contact_name', 'emergency_contact_phone', 'photo', 'remarks', 'known_allergies',
            'has_insurance', 'insurance_company', 'insurance_policy_number',
            'insurance_membership_number', 'insurance_card_number', 'insurance_expiry_date',
            'insurance_remarks',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'pattern': r'[0-9+\- ]{7,20}'}),
            'district': forms.Select(attrs={'class': 'form-select district-autocomplete'}),
            'municipality': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 35}),
            'local_address': forms.TextInput(attrs={'class': 'form-control'}),
            'citizenship_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'known_allergies': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Penicillin, Sulfa drugs, Latex'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'guardian_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'has_insurance': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_insurance'}),
            'insurance_company': forms.Select(attrs={'class': 'form-select autocomplete-select'}),
            'insurance_policy_number': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_membership_number': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_card_number': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_expiry_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'insurance_remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['first_name', 'last_name', 'phone_number']:
            self.fields[field].required = True
        self.fields['district'].queryset = District.objects.select_related('province').order_by('name')
        self.fields['insurance_company'].queryset = InsuranceCompany.objects.filter(is_active=True)
        self.fields['insurance_company'].required = False
        # Date of Birth is auto-calculated from the compulsory age_input field.
        self.fields['date_of_birth'].required = False
        if self.instance and self.instance.pk and self.instance.age_at_registration:
            self.fields['age_input'].initial = self.instance.age_at_registration
        for optional in ['citizenship_number', 'email', 'blood_group', 'occupation', 'guardian_name',
                         'emergency_contact_name', 'emergency_contact_phone', 'photo', 'remarks',
                         'municipality', 'ward_number', 'local_address']:
            self.fields[optional].required = False

    def clean_first_name(self):
        value = (self.cleaned_data.get('first_name') or '').strip()
        if not value:
            raise forms.ValidationError('First Name is required.')
        return value

    def clean_last_name(self):
        value = (self.cleaned_data.get('last_name') or '').strip()
        if not value:
            raise forms.ValidationError('Last Name is required.')
        return value

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if not phone:
            raise forms.ValidationError('Phone Number is required.')
        if len(phone) < 7:
            raise forms.ValidationError('Enter a valid phone number.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        has_insurance = cleaned_data.get('has_insurance')
        if not has_insurance:
            for field in ['insurance_company', 'insurance_policy_number', 'insurance_membership_number',
                          'insurance_card_number', 'insurance_expiry_date', 'insurance_remarks']:
                cleaned_data[field] = None if field in ['insurance_company', 'insurance_expiry_date'] else ''

        age_input = cleaned_data.get('age_input')
        if not cleaned_data.get('date_of_birth') and age_input:
            dob = parse_age_to_dob(age_input)
            if dob is None:
                self.add_error('age_input', "Could not understand this age. Try formats like '24 Years', "
                                             "'11 Years 2 Months', '1 Month', or '15 Days'.")
            else:
                cleaned_data['date_of_birth'] = dob
        elif not cleaned_data.get('date_of_birth') and not age_input:
            self.add_error('age_input', 'Age is compulsory.')
        return cleaned_data

    def save(self, commit=True):
        patient = super().save(commit=False)
        patient.date_of_birth = self.cleaned_data.get('date_of_birth') or patient.date_of_birth
        patient.age_at_registration = self.cleaned_data.get('age_input', '')
        if commit:
            patient.save()
        return patient


class VisitForm(forms.ModelForm):
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
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['doctor'].queryset = Doctor.objects.filter(is_active=True)
        self.fields['doctor'].required = False
        self.fields['payment_method'].choices = [
            (Visit.PaymentMethod.CASH, 'Cash'),
            (Visit.PaymentMethod.ESEWA, 'eSewa'),
        ]
        self.fields['payment_method'].initial = Visit.PaymentMethod.CASH

    def clean(self):
        cleaned_data = super().clean()
        patient_type = cleaned_data.get('patient_type')
        if patient_type == Visit.PatientType.NEW:
            cleaned_data['registration_fee'] = settings.NEW_PATIENT_REGISTRATION_FEE
        elif patient_type == Visit.PatientType.OLD:
            cleaned_data['registration_fee'] = settings.OLD_PATIENT_REGISTRATION_FEE
        return cleaned_data


class PatientSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by Patient ID, Name, Phone, QR Code, Barcode, Date, Province, Gender, or Age',
        }),
    )
