from django import forms
from .models import Referral


class ReferralForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = ['patient', 'referral_type', 'to_department', 'diagnosis', 'reason', 'clinical_notes', 'instructions', 'attachment']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'referral_type': forms.Select(attrs={'class': 'form-select'}),
            'to_department': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Diagnosis / working impression'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Reason for referral'}),
            'clinical_notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Clinical notes and relevant history'}),
            'instructions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Instructions for receiving department'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['to_department'].required = False
        self.fields['diagnosis'].required = False
        self.fields['clinical_notes'].required = False
        self.fields['instructions'].required = False
        self.fields['attachment'].required = False
