from django import forms
from django.conf import settings

from appointments.models import Appointment
from patients.models import District
from departments.models import Department
from doctors.models import Doctor


class DoctorSelect(forms.Select):
    """Select widget that stamps each <option> with data-* attributes so the
    booking page can filter doctors by department and show their fee /
    available days & hours client-side, without any extra AJAX call."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            try:
                doctor = Doctor.objects.select_related('department').get(pk=value.value if hasattr(value, 'value') else value)
                option['attrs']['data-department'] = doctor.department_id
                option['attrs']['data-fee'] = str(doctor.consultation_fee)
                option['attrs']['data-days'] = doctor.available_days
                option['attrs']['data-start'] = doctor.available_time_start.strftime('%H:%M') if doctor.available_time_start else ''
                option['attrs']['data-end'] = doctor.available_time_end.strftime('%H:%M') if doctor.available_time_end else ''
            except Doctor.DoesNotExist:
                pass
        return option


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'first_name', 'last_name', 'gender', 'age', 'date_of_birth', 'phone_number', 'email',
            'district', 'municipality', 'ward_number', 'local_address',
            'department', 'doctor', 'preferred_date', 'preferred_time', 'chief_complaint',
            'patient_type', 'payment_method',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age (Years)'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'pattern': r'[0-9+\- ]{7,20}'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'district': forms.Select(attrs={'class': 'form-select district-autocomplete'}),
            'municipality': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'local_address': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'doctor': DoctorSelect(attrs={'class': 'form-select', 'id': 'id_doctor'}),
            'preferred_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'patient_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_patient_type'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.extension_mode = kwargs.pop('extension_mode', False)
        super().__init__(*args, **kwargs)
        self.fields['district'].queryset = District.objects.select_related('province').order_by('name')
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['doctor'].queryset = Doctor.objects.filter(is_active=True, is_extension_service=True) if self.extension_mode else Doctor.objects.filter(is_active=True)
        for field in ['first_name', 'last_name', 'phone_number']:
            self.fields[field].required = True
        self.fields['doctor'].required = False
        self.fields['age'].required = False
        self.fields['date_of_birth'].required = False
        # Hospital Extension Service only offers Cash (default) or eSewa here
        # (spec section 14) - the model still supports the other gateways
        # elsewhere (e.g. the generic online_pay_simulate flow) unchanged.
        self.fields['payment_method'].choices = [
            (Appointment.PaymentMethod.CASH, Appointment.PaymentMethod.CASH.label),
            (Appointment.PaymentMethod.ESEWA, Appointment.PaymentMethod.ESEWA.label),
        ]
        self.fields['payment_method'].initial = Appointment.PaymentMethod.CASH
        for optional in ['email', 'municipality', 'ward_number', 'local_address', 'preferred_time', 'chief_complaint']:
            self.fields[optional].required = False

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if not phone:
            raise forms.ValidationError('Phone Number is required.')
        if len(phone) < 7:
            raise forms.ValidationError('Enter a valid phone number.')
        return phone

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

    def clean(self):
        cleaned_data = super().clean()
        age = cleaned_data.get('age')
        dob = cleaned_data.get('date_of_birth')
        if not age and not dob:
            raise forms.ValidationError("Please provide either Age or Date of Birth.")
        
        import datetime
        from dateutil.relativedelta import relativedelta
        today = datetime.date.today()
        if age and not dob:
            cleaned_data['date_of_birth'] = today - relativedelta(years=age)
        elif dob and not age:
            cleaned_data['age'] = relativedelta(today, dob).years

        patient_type = cleaned_data.get('patient_type')
        doctor = cleaned_data.get('doctor')
        if self.extension_mode and doctor:
            cleaned_data['registration_fee'] = doctor.extension_new_fee if patient_type == Appointment.PatientType.NEW else doctor.extension_old_fee
        elif patient_type == Appointment.PatientType.NEW:
            cleaned_data['registration_fee'] = settings.NEW_PATIENT_REGISTRATION_FEE
        else:
            cleaned_data['registration_fee'] = settings.OLD_PATIENT_REGISTRATION_FEE

        # Doctor Quota System (spec section 12): block booking if the chosen
        # doctor is on leave/holiday/off-duty, or already full, on this date.
        doctor = cleaned_data.get('doctor')
        preferred_date = cleaned_data.get('preferred_date')
        if doctor and preferred_date:
            if doctor.is_on_leave(preferred_date):
                self.add_error('doctor', f"Dr. {doctor.full_name} is on leave/unavailable on {preferred_date}. Please choose another date or doctor.")
            elif not doctor.is_available_for_date(preferred_date):
                self.add_error('doctor', f"Dr. {doctor.full_name}'s quota for {preferred_date} is already full. Please choose another date or doctor.")
        return cleaned_data
