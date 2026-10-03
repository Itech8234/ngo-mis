"""Donor and partner forms."""
from django import forms

from .models import Donor, Grant, Partner


class DonorForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = ["name", "donor_type", "contact_name", "email", "phone", "address", "website", "notes"]


class GrantForm(forms.ModelForm):
    class Meta:
        model = Grant
        fields = ["donor", "name", "code", "amount", "currency", "start_date", "end_date", "reporting_frequency", "next_report_due", "description", "is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "next_report_due": forms.DateInput(attrs={"type": "date"}),
        }


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "name", "partner_type", "contact_person", "email", "phone", "address",
            "state", "geographic_area", "partnership_type", "programs", "projects",
            "status", "show_on_website", "logo", "description",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
