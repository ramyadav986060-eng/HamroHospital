from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from accounts.models import User, Role, HospitalSetting, StaffAttendance, StaffLeaveRequest, StaffSalaryProfile


class StyledAuthenticationForm(AuthenticationForm):
    """Login form accepting username OR Staff ID (STFxxxxxx)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Username or Staff ID', 'autofocus': True,
        })
        self.fields['username'].label = 'Username / Staff ID'
        self.fields['password'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Password',
        })

    def clean(self):
        login_value = (self.cleaned_data.get('username') or '').strip()
        if login_value:
            staff = User.objects.filter(staff_id__iexact=login_value).first()
            if staff:
                self.cleaned_data['username'] = staff.get_username()
        return super().clean()

    def confirm_login_allowed(self, user):
        # Keep a deactivated hospital staff account out even if Django's auth
        # flag is still active; this fixes staff-login routing/access safely.
        super().confirm_login_allowed(user)
        if not user.is_active_staff:
            raise forms.ValidationError(
                'This staff account has been deactivated. Please contact an administrator.',
                code='inactive',
            )


class StaffCreateForm(UserCreationForm):
    """Used by Super Admin to create a new staff account for any role."""

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'department', 'designation', 'employment_type', 'staff_photo', 'address', 'emergency_contact', 'blood_group', 'is_department_head']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'staff_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'blood_group': forms.TextInput(attrs={'class': 'form-control'}),
            'is_department_head': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class StaffEditForm(forms.ModelForm):
    """Used by Super Admin to edit an existing staff account (no password change here)."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'role', 'department', 'designation', 'employment_type', 'staff_photo', 'address', 'emergency_contact', 'blood_group', 'is_department_head', 'is_active_staff']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'staff_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'blood_group': forms.TextInput(attrs={'class': 'form-control'}),
            'is_department_head': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NotificationForm(forms.ModelForm):
    class Meta:
        from accounts.models import Notification
        model = Notification
        fields = ['role', 'title', 'message']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class HospitalSettingForm(forms.ModelForm):
    class Meta:
        from accounts.models import Notification
        model = Notification
        fields = ['role', 'title', 'message']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    class Meta:
        model = HospitalSetting
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'twitter_url': forms.URLInput(attrs={'class': 'form-control'}),
            'footer_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'default_currency': forms.TextInput(attrs={'class': 'form-control'}),
            'default_timezone': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_settings': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'print_settings': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'theme_color': forms.TextInput(attrs={'class': 'form-control', 'style': 'height: 38px;'}),
            'staff_discount_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'staff_discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'required_daily_working_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'default_weekend_days': forms.TextInput(attrs={'class': 'form-control'}),
            'paid_leave_days_per_month': forms.NumberInput(attrs={'class': 'form-control'}),
            'paid_leave_days_per_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'ehs_new_ticket_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ehs_followup_ticket_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ehs_additional_charges_note': forms.TextInput(attrs={'class': 'form-control'}),
            'admission_base_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'icu_daily_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cabin_daily_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class StaffAttendanceForm(forms.ModelForm):
    class Meta:
        model = StaffAttendance
        fields = ['staff', 'date', 'check_in', 'check_out', 'status', 'source', 'device_log_id', 'remarks']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'check_out': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.TextInput(attrs={'class': 'form-control'}),
            'device_log_id': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StaffLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = StaffLeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'supporting_document']
        widgets = {
            'leave_type': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'supporting_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class StaffLeaveReviewForm(forms.ModelForm):
    class Meta:
        model = StaffLeaveRequest
        fields = ['status', 'review_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'review_notes': forms.TextInput(attrs={'class': 'form-control'}),
        }

class StaffSalaryProfileForm(forms.ModelForm):
    class Meta:
        model = StaffSalaryProfile
        fields = ['staff', 'bank_name', 'bank_account_name', 'bank_account_number', 'pan_number', 'salary_type', 'effective_date', 'base_monthly_salary', 'per_day_salary', 'bonus_amount', 'overtime_rate_per_hour', 'is_active']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_type': forms.Select(attrs={'class': 'form-select'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'base_monthly_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'per_day_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bonus_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime_rate_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
