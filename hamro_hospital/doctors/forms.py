from django import forms
from doctors.models import Doctor, Weekday


class DoctorForm(forms.ModelForm):
    available_days = forms.MultipleChoiceField(
        choices=Weekday.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Doctor
        fields = [
            'department', 'full_name', 'qualification', 'specialization', 'experience_years',
            'consultation_fee', 'biography', 'photo', 'available_days',
            'available_time_start', 'available_time_end', 'is_active', 'is_featured',
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'consultation_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'biography': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'available_time_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'available_time_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.available_days:
            self.initial['available_days'] = [
                c.strip() for c in self.instance.available_days.split(',') if c.strip()
            ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.available_days = ','.join(self.cleaned_data.get('available_days', []))
        if commit:
            instance.save()
        return instance
