from django import forms

from consultations.models import RadiologyRequest


class RadiologyReportForm(forms.ModelForm):
    """Updates status + findings/impression/notes. Report/image files are
    handled separately in the view via request.FILES.getlist('report_files')
    so multiple files (PDF, scanned report, X-ray/CT/MRI/USG images) can be
    attached in one submission (spec 6: 'Support PDF Upload, Scanned Report,
    Image Upload')."""
    class Meta:
        model = RadiologyRequest
        fields = ['status', 'findings', 'impression', 'report_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'findings': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'impression': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'report_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Radiologist note'}),
        }


class ManualRadiologyRequestForm(forms.ModelForm):
    """Used by Radiology staff to open a record directly for a walk-in
    patient who arrives with a physical referral (spec 6, mirrors
    Laboratory spec 5: 'both workflows must be supported')."""
    class Meta:
        model = RadiologyRequest
        fields = [
            'service_type', 'custom_service_name', 'urgency', 'referred_by',
            'department_name', 'clinical_note', 'referral_letter',
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'form-select'}),
            'custom_service_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Only if Service Type = Other'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'referred_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Referring doctor name'}),
            'department_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Orthopedics'}),
            'clinical_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'referral_letter': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
