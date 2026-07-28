from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from accounts.models import User, Role
from doctors.models import Doctor, Weekday


class DoctorForm(forms.ModelForm):
    available_days = forms.MultipleChoiceField(
        choices=Weekday.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    create_login_account = forms.BooleanField(
        required=False,
        initial=True,
        label='Create / link doctor login account',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    username = forms.CharField(
        required=False,
        label='Login Username',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to auto-generate'}),
    )
    password = forms.CharField(
        required=False,
        label='Temporary Password',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to auto-generate'}),
        help_text='Doctor can change this after logging in.',
    )

    class Meta:
        model = Doctor
        fields = [
            'department', 'unit', 'full_name', 'qualification', 'specialization', 'experience_years',
            'consultation_fee', 'biography', 'short_introduction', 'contact_number', 'esewa_id', 'esewa_phone', 'photo', 'available_days',
            'available_time_start', 'available_time_end', 'is_extension_service', 'extension_weekly_off_day', 'extension_morning_start', 'extension_morning_end', 'extension_morning_quota', 'extension_afternoon_start', 'extension_afternoon_end', 'extension_afternoon_quota', 'is_active', 'is_featured',
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'consultation_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'biography': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'short_introduction': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'esewa_id': forms.TextInput(attrs={'class': 'form-control'}),
            'esewa_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'available_time_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'available_time_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_extension_service': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extension_weekly_off_day': forms.Select(attrs={'class': 'form-select'}),
            'extension_morning_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_morning_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_morning_quota': forms.NumberInput(attrs={'class': 'form-control'}),
            'extension_afternoon_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_afternoon_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_afternoon_quota': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generated_credentials = None
        if self.instance and self.instance.pk and self.instance.available_days:
            self.initial['available_days'] = [c.strip() for c in self.instance.available_days.split(',') if c.strip()]
        if self.instance and self.instance.pk and self.instance.user_account_id:
            self.fields['create_login_account'].initial = True
            self.fields['username'].initial = self.instance.user_account.username
            self.fields['password'].help_text = 'Leave blank to keep the current password.'
        for optional in ['biography', 'short_introduction', 'contact_number', 'esewa_id', 'esewa_phone', 'photo', 'unit', 'available_time_start', 'available_time_end', 'extension_weekly_off_day', 'extension_morning_start', 'extension_morning_end', 'extension_afternoon_start', 'extension_afternoon_end']:
            self.fields[optional].required = False

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if username:
            qs = User.objects.filter(username__iexact=username)
            if self.instance and self.instance.user_account_id:
                qs = qs.exclude(pk=self.instance.user_account_id)
            if qs.exists():
                raise forms.ValidationError('This username is already taken.')
        return username

    def _unique_username(self, full_name):
        base = slugify(full_name).replace('-', '.') or 'doctor'
        username = base
        i = 1
        while User.objects.filter(username__iexact=username).exists():
            i += 1
            username = f'{base}{i}'
        return username

    def save(self, commit=True):
        doctor = super().save(commit=False)
        doctor.available_days = ','.join(self.cleaned_data.get('available_days', []))
        if commit:
            doctor.save()
            self.save_m2m()
            if self.cleaned_data.get('create_login_account'):
                username = self.cleaned_data.get('username') or self._unique_username(doctor.full_name)
                raw_password = self.cleaned_data.get('password') or f'Dr@{get_random_string(8)}'
                if doctor.user_account_id:
                    user = doctor.user_account
                    user.username = username
                else:
                    user = User(username=username)
                parts = doctor.full_name.strip().split(' ', 1)
                user.first_name = parts[0]
                user.last_name = parts[1] if len(parts) > 1 else ''
                user.role = Role.DOCTOR
                user.is_staff = True
                user.is_active = True
                user.is_active_staff = True
                user.phone_number = doctor.contact_number or user.phone_number
                if raw_password:
                    user.set_password(raw_password)
                user.save()
                if doctor.user_account_id != user.id:
                    doctor.user_account = user
                    doctor.save(update_fields=['user_account'])
                self.generated_credentials = (username, raw_password)
        return doctor


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['full_name', 'qualification', 'specialization', 'experience_years', 'biography', 'short_introduction', 'contact_number', 'esewa_id', 'esewa_phone', 'photo', 'available_days', 'available_time_start', 'available_time_end', 'is_extension_service', 'extension_weekly_off_day', 'extension_morning_start', 'extension_morning_end', 'extension_morning_quota', 'extension_afternoon_start', 'extension_afternoon_end', 'extension_afternoon_quota']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'biography': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'short_introduction': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'esewa_id': forms.TextInput(attrs={'class': 'form-control'}),
            'esewa_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'available_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mon,tue,wed'}),
            'available_time_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'available_time_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_extension_service': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extension_weekly_off_day': forms.Select(attrs={'class': 'form-select'}),
            'extension_morning_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_morning_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_morning_quota': forms.NumberInput(attrs={'class': 'form-control'}),
            'extension_afternoon_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_afternoon_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'extension_afternoon_quota': forms.NumberInput(attrs={'class': 'form-control'}),
        }
