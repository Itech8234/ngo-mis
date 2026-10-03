"""Risk and incident forms."""
from django import forms

from .models import Incident, Risk


class RiskForm(forms.ModelForm):
    class Meta:
        model = Risk
        fields = ["title", "description", "category", "probability", "impact", "mitigation", "responsible", "review_date", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "mitigation": forms.Textarea(attrs={"rows": 3}),
            "review_date": forms.DateInput(attrs={"type": "date"}),
        }


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = [
            "title", "category", "date", "location", "description", "severity",
            "assigned_to", "actions_taken", "resolution", "status", "attachment", "follow_up_date",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "actions_taken": forms.Textarea(attrs={"rows": 3}),
            "resolution": forms.Textarea(attrs={"rows": 3}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }
