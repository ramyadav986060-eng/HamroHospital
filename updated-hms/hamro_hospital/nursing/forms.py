from django import forms

from nursing.models import NursingNote


class NursingNoteForm(forms.ModelForm):
    class Meta:
        model = NursingNote
        fields = [
            'note_type', 'content', 'temperature_c', 'pulse_bpm', 'blood_pressure',
            'respiratory_rate', 'spo2_percent', 'medication_given',
        ]
        widgets = {
            'note_type': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'temperature_c': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'pulse_bpm': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '120/80'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'spo2_percent': forms.NumberInput(attrs={'class': 'form-control'}),
            'medication_given': forms.TextInput(attrs={'class': 'form-control'}),
        }
