from django import forms

from admissions.models import Admission, Ward, Bed
from departments.models import Department
from doctors.models import Doctor


class AdmissionForm(forms.ModelForm):
    class Meta:
        model = Admission
        fields = [
            'department', 'admitting_doctor', 'ward', 'bed',
            'reason_for_admission', 'diagnosis',
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'admitting_doctor': forms.Select(attrs={'class': 'form-select'}),
            'ward': forms.Select(attrs={'class': 'form-select', 'id': 'id_ward'}),
            'bed': forms.Select(attrs={'class': 'form-select', 'id': 'id_bed'}),
            'reason_for_admission': forms.TextInput(attrs={'class': 'form-control'}),
            'diagnosis': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['admitting_doctor'].queryset = Doctor.objects.filter(is_active=True)
        self.fields['admitting_doctor'].required = False
        self.fields['ward'].queryset = Ward.objects.filter(is_active=True)
        self.fields['bed'].queryset = Bed.objects.filter(is_occupied=False)
        self.fields['bed'].required = False


class DischargeForm(forms.Form):
    discharge_condition = forms.ChoiceField(
        choices=Admission.DischargeCondition.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    discharge_summary = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=False,
    )
    follow_up_instructions = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False,
    )


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ['name', 'ward_type', 'floor', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_type': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BedForm(forms.ModelForm):
    class Meta:
        model = Bed
        fields = ['ward', 'bed_number']
        widgets = {
            'ward': forms.Select(attrs={'class': 'form-select'}),
            'bed_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
