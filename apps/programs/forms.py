"""Programs forms."""
from django import forms

from .models import Activity, Program, Project


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            "title", "code", "thematic_area", "description", "objective",
            "manager", "funding_source", "budget", "target_beneficiaries",
            "start_date", "end_date", "locations", "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "objective": forms.Textarea(attrs={"rows": 3}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "program", "name", "code", "donor", "grant", "manager", "budget",
            "start_date", "end_date", "objectives", "outcomes", "outputs",
            "assumptions", "stakeholders", "target_beneficiaries", "locations", "status",
        ]
        widgets = {
            "objectives": forms.Textarea(attrs={"rows": 3}),
            "outcomes": forms.Textarea(attrs={"rows": 3}),
            "outputs": forms.Textarea(attrs={"rows": 3}),
            "assumptions": forms.Textarea(attrs={"rows": 2}),
            "stakeholders": forms.Textarea(attrs={"rows": 2}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "project", "name", "description", "location", "responsible",
            "start_date", "end_date", "budget", "expected_participants",
            "actual_participants", "status", "evidence", "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ActivityStatusForm(forms.ModelForm):
    """Compact form for inline status/participant updates."""

    class Meta:
        model = Activity
        fields = ["status", "actual_participants", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
