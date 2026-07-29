from django import forms

from operation_theatre.models import Surgery, OTRoom
from doctors.models import Doctor


class SurgeryScheduleForm(forms.ModelForm):
    class Meta:
        model = Surgery
        fields = [
            'surgery_name', 'surgeon', 'assistant_surgeons', 'ot_room', 'anesthesia_type',
            'scheduled_datetime', 'admission', 'pre_op_notes', 'charge_amount',
        ]
        widgets = {
            'surgery_name': forms.TextInput(attrs={'class': 'form-control'}),
            'surgeon': forms.Select(attrs={'class': 'form-select'}),
            'assistant_surgeons': forms.TextInput(attrs={'class': 'form-control'}),
            'ot_room': forms.Select(attrs={'class': 'form-select'}),
            'anesthesia_type': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'admission': forms.Select(attrs={'class': 'form-select'}),
            'pre_op_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'charge_amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['surgeon'].queryset = Doctor.objects.filter(is_active=True)
        self.fields['ot_room'].queryset = OTRoom.objects.filter(is_active=True)
        self.fields['admission'].required = False
        if patient is not None:
            self.fields['admission'].queryset = patient.admissions.all()


class SurgeryUpdateForm(forms.ModelForm):
    class Meta:
        model = Surgery
        fields = [
            'status', 'started_at', 'completed_at', 'operative_notes', 'post_op_notes', 'complications',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'started_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'completed_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'operative_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'post_op_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'complications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
