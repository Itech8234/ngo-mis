"""Document forms."""
from django import forms

from .models import Document, DocumentVersion


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            "title", "description", "file", "category", "access_level",
            "tags", "expires_at",
        ]
        widgets = {"expires_at": forms.DateInput(attrs={"type": "date"})}


class DocumentVersionForm(forms.ModelForm):
    class Meta:
        model = DocumentVersion
        fields = ["file", "note"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "note": forms.TextInput(attrs={"class": "form-input"}),
        }
