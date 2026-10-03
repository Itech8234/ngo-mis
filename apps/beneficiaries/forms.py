"""Beneficiaries forms."""
from django import forms

from .models import AssistanceRecord, Beneficiary


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = [
            "full_name", "gender", "date_of_birth", "age_group", "phone",
            "location", "community", "vulnerability_category", "has_disability",
            "household_size", "project", "program", "photo", "notes",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class AssistanceRecordForm(forms.ModelForm):
    class Meta:
        model = AssistanceRecord
        # ``date`` is auto-set on creation (auto_now_add)
        fields = ["assistance_type", "project", "description", "value"]
