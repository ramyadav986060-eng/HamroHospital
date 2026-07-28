from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from accounts.models import User, Role, HospitalSetting


class StyledAuthenticationForm(AuthenticationForm):
    """Login form with Bootstrap classes applied."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Username', 'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Password',
        })

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
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class StaffEditForm(forms.ModelForm):
    """Used by Super Admin to edit an existing staff account (no password change here)."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'role', 'is_active_staff']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
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
        }
