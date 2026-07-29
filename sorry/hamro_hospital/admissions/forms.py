from django import forms

from admissions.models import Admission, Ward, Bed, DischargeChecklist, AdmissionDeposit, BedTransfer
from departments.models import Department
from doctors.models import Doctor


class AdmissionForm(forms.ModelForm):
    admission_datetime = forms.DateTimeField(required=False, label='Admission Date & Time', widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    notes = forms.CharField(required=False, label='Notes (optional)', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
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
        ward_id = None
        if self.data.get('ward'):
            ward_id = self.data.get('ward')
        elif self.initial.get('ward'):
            ward_id = self.initial.get('ward')
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['admitting_doctor'].queryset = Doctor.objects.filter(is_active=True)
        self.fields['admitting_doctor'].required = False
        self.fields['ward'].queryset = Ward.objects.filter(is_active=True)
        bed_qs = Bed.objects.filter(is_occupied=False)
        if ward_id:
            bed_qs = bed_qs.filter(ward_id=ward_id)
        self.fields['bed'].queryset = bed_qs
        self.fields['bed'].required = False


class DischargeForm(forms.Form):
    discharge_condition = forms.ChoiceField(
        choices=Admission.DischargeCondition.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    discharge_summary = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=False,
    )
    follow_up_instructions = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)
    procedures_performed = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
    medicines_on_discharge = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
    diet_advice = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
    activity_recommendations = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
    emergency_instructions = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
    follow_up_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)
    follow_up_department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    follow_up_doctor = forms.ModelChoiceField(queryset=Doctor.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    recommended_investigations = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
    follow_up_additional_notes = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ['name', 'ward_type', 'floor', 'daily_rate', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_type': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.TextInput(attrs={'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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


class DischargeChecklistForm(forms.ModelForm):
    class Meta:
        model = DischargeChecklist
        fields = [
            'all_bills_paid', 'lab_reports_complete', 'radiology_reports_complete',
            'medicine_charges_complete', 'discharge_summary_prepared', 'nursing_clearance',
            'insurance_clearance', 'bed_release_ready', 'remarks',
        ]
        widgets = {
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'remarks':
                field.widget.attrs.update({'class': 'form-check-input'})

class AdmissionDepositForm(forms.ModelForm):
    class Meta:
        model = AdmissionDeposit
        fields = ['deposit_type', 'amount', 'payment_method', 'receipt_number', 'remarks']
        widgets = {
            'deposit_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BedTransferForm(forms.ModelForm):
    class Meta:
        model = BedTransfer
        fields = ['to_ward', 'to_bed', 'reason']
        widgets = {
            'to_ward': forms.Select(attrs={'class': 'form-select'}),
            'to_bed': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['to_ward'].queryset = Ward.objects.filter(is_active=True)
        self.fields['to_bed'].queryset = Bed.objects.filter(is_occupied=False)
        self.fields['to_bed'].required = False
