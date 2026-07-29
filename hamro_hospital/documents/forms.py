from django import forms

from documents.models import PatientDocument


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ['category', 'title', 'file', 'remarks']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DocumentReplaceForm(forms.Form):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    remarks = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        help_text='Optional note on why this file is being replaced.',
    )
