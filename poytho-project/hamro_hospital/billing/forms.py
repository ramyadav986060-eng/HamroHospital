from django import forms

from billing.models import Bill, PaymentMethod
from patients.models import InsuranceCompany


class PatientLookupForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Patient ID, QR value, phone, or name',
        }),
    )


class BillPaymentForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_method'}),
    )
    counter_name = forms.CharField(
        required=False, initial='Main Cash Counter',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='e.g. "Main Cash Counter", "Laboratory Counter", "Radiology Counter"',
    )
    insurance_company = forms.ModelChoiceField(
        queryset=InsuranceCompany.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    insurance_coverage_amount = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Amount covered by insurance (only relevant when Payment Method = Insurance).',
    )


class RefundRequestForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    reason = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


class RefundReviewForm(forms.Form):
    review_notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class DiscountRequestForm(forms.Form):
    """Cash Counter's 'Poor Patient' discount request (spec section 7)."""
    discount_amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Amount to be waived off the bill total.',
    )
    reason = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "e.g. 'Financially weak patient', 'Charity case'",
        }),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': "e.g. Patient is financially weak. Operation completed for Rs. 10,000 instead of Rs. 50,000.",
        }),
    )


class DiscountReviewForm(forms.Form):
    review_notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
