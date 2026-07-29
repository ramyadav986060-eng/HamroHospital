from django import forms

from pharmacy.models import Medicine, StockAdjustment, PharmacySale
from patients.models import InsuranceCompany


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            'medicine_code', 'name', 'generic_name', 'brand_name', 'category', 'strength', 'unit',
            'purchase_price', 'selling_price', 'current_stock', 'minimum_stock',
            'batch_number', 'expiry_date', 'manufacturer', 'is_active',
        ]
        widgets = {
            'medicine_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'strength': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['quantity_change', 'reason', 'notes']
        widgets = {
            'quantity_change': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 100 or -5'}),
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PharmacySaleForm(forms.Form):
    prescription_source = forms.ChoiceField(
        choices=PharmacySale.PrescriptionSource.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    manual_prescription_copy = forms.FileField(
        required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )
    payment_method = forms.ChoiceField(
        choices=PharmacySale.PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_method'}),
    )
    insurance_company = forms.ModelChoiceField(
        queryset=InsuranceCompany.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
