from django import forms

from insurance.models import InsuranceClaim
from patients.models import InsuranceCompany


class InsuranceCompanyForm(forms.ModelForm):
    class Meta:
        model = InsuranceCompany
        fields = ['name', 'contact_person', 'phone_number', 'email', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClaimSubmitForm(forms.ModelForm):
    class Meta:
        model = InsuranceClaim
        fields = ['insurance_company', 'amount_claimed', 'co_payment_amount', 'is_cashless', 'remarks']
        widgets = {
            'insurance_company': forms.Select(attrs={'class': 'form-select'}),
            'amount_claimed': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'co_payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_cashless': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['insurance_company'].queryset = InsuranceCompany.objects.filter(is_active=True)


class ClaimReviewForm(forms.ModelForm):
    class Meta:
        model = InsuranceClaim
        fields = ['status', 'approved_amount', 'rejected_amount', 'review_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'approved_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rejected_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'review_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
