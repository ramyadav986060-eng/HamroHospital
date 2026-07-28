from django import forms

from consultations.models import LabTestRequest, RequestStatus, Urgency


class LabResultForm(forms.ModelForm):
    """Updates status + summary/comment. File upload is handled separately
    in the view via request.FILES.getlist('report_files') so multiple files
    can be attached in one submission (spec 5: 'Upload multiple files')."""
    class Meta:
        model = LabTestRequest
        fields = ['status', 'result_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'result_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4, 'placeholder': 'Report summary / comment',
            }),
        }


class ManualLabRequestForm(forms.ModelForm):
    """Used by Laboratory staff to open a record directly for a walk-in
    patient who arrives with a physical referral (spec 5: 'both workflows
    must be supported')."""
    class Meta:
        model = LabTestRequest
        fields = [
            'test_name', 'urgency', 'referred_by', 'department_name',
            'clinical_note', 'referral_letter',
        ]
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CBC, Blood Sugar Fasting'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'referred_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Referring doctor name'}),
            'department_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. General Medicine'}),
            'clinical_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'referral_letter': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
