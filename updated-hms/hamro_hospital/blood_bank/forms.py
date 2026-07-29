from django import forms

from blood_bank.models import BloodUnit, BloodIssue, BloodRequest


class BloodUnitForm(forms.ModelForm):
    class Meta:
        model = BloodUnit
        fields = [
            'blood_group', 'component', 'quantity_ml', 'donor_name', 'donor_phone',
            'collection_date', 'expiry_date',
        ]
        widgets = {
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'quantity_ml': forms.NumberInput(attrs={'class': 'form-control'}),
            'donor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'donor_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'collection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class BloodIssueForm(forms.ModelForm):
    class Meta:
        model = BloodIssue
        fields = ['admission', 'purpose', 'cross_match_notes']
        widgets = {
            'admission': forms.Select(attrs={'class': 'form-select'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control'}),
            'cross_match_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['admission'].required = False
        if patient is not None:
            self.fields['admission'].queryset = patient.admissions.all()


class BloodRequestForm(forms.ModelForm):
    """Used by a doctor to request blood for a patient (spec 12)."""
    class Meta:
        model = BloodRequest
        fields = ['blood_group_needed', 'component', 'units_needed', 'urgency', 'clinical_note']
        widgets = {
            'blood_group_needed': forms.Select(attrs={'class': 'form-select'}),
            'component': forms.Select(attrs={'class': 'form-select'}),
            'units_needed': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'clinical_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
