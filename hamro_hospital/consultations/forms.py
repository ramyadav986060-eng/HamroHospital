from django import forms
from django.forms import inlineformset_factory

from consultations.models import Consultation, PrescriptionItem, LabTestRequest, RadiologyRequest


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['diagnosis', 'clinical_notes', 'follow_up_date', 'prescription_file', 'recommend_admission', 'recommend_surgery', 'recommended_surgery_name']
        widgets = {
            'diagnosis': forms.TextInput(attrs={'class': 'form-control'}),
            'clinical_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prescription_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'recommend_admission': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recommend_surgery': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_recommend_surgery'}),
            'recommended_surgery_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Appendectomy'}),
        }


PrescriptionItemFormSet = inlineformset_factory(
    Consultation, PrescriptionItem,
    fields=['medicine_name', 'dosage', 'frequency', 'duration', 'instructions'],
    widgets={
        'medicine_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine name'}),
        'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500mg'}),
        'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BID'}),
        'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5 days'}),
        'instructions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. After meals'}),
    },
    extra=2, can_delete=True,
)


class LabTestRequestForm(forms.ModelForm):
    class Meta:
        model = LabTestRequest
        fields = ['test_name', 'urgency']
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Complete Blood Count'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
        }


class RadiologyRequestForm(forms.ModelForm):
    class Meta:
        model = RadiologyRequest
        fields = ['service_type', 'custom_service_name', 'urgency']
        widgets = {
            'service_type': forms.Select(attrs={'class': 'form-select'}),
            'custom_service_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Only if "Other" selected'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
        }
