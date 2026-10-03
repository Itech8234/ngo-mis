"""Asset forms."""
from django import forms

from .models import Asset, AssetAssignment


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "name", "category", "description", "serial_number", "purchase_date",
            "purchase_value", "current_value", "location", "assigned_to",
            "condition", "status", "warranty_until", "document", "notes",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "warranty_until": forms.DateInput(attrs={"type": "date"}),
        }


class AssetAssignmentForm(forms.ModelForm):
    class Meta:
        model = AssetAssignment
        fields = ["employee", "condition_out", "notes"]
