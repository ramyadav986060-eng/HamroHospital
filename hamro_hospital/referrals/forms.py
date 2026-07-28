from django import forms
from .models import Referral
from laboratory.models import LabTest
from radiology.models import RadiologyTest
from operation_theatre.models import OperationType


class ReferralForm(forms.ModelForm):
    lab_tests = forms.ModelMultipleChoiceField(queryset=LabTest.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label='Laboratory Investigations')
    radiology_tests = forms.ModelMultipleChoiceField(queryset=RadiologyTest.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label='Radiology Services')
    operation_types = forms.ModelMultipleChoiceField(queryset=OperationType.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label='OT / Procedures')

    class Meta:
        model = Referral
        fields = ['patient', 'referral_type', 'to_department', 'diagnosis', 'reason', 'clinical_notes', 'instructions', 'requested_items', 'attachment']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'referral_type': forms.Select(attrs={'class': 'form-select'}),
            'to_department': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Diagnosis / working impression'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Reason for referral'}),
            'clinical_notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Clinical notes and relevant history'}),
            'instructions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Instructions for receiving department'}),
            'requested_items': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional free-text requested services/items, one per line'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['to_department'].required = False
        self.fields['diagnosis'].required = False
        self.fields['clinical_notes'].required = False
        self.fields['instructions'].required = False
        self.fields['attachment'].required = False
        self.fields['requested_items'].required = False
        self.fields['lab_tests'].queryset = LabTest.objects.filter(is_active=True).order_by('name')
        self.fields['radiology_tests'].queryset = RadiologyTest.objects.filter(is_active=True).order_by('name')
        self.fields['operation_types'].queryset = OperationType.objects.filter(is_active=True).order_by('name')

    def clean(self):
        cleaned = super().clean()
        items = []
        for field in ['lab_tests', 'radiology_tests', 'operation_types']:
            for obj in cleaned.get(field) or []:
                items.append(str(obj.name))
        free_text = cleaned.get('requested_items') or ''
        if free_text.strip():
            items.extend([line.strip() for line in free_text.splitlines() if line.strip()])
        cleaned['requested_items'] = '\n'.join(dict.fromkeys(items))
        return cleaned
