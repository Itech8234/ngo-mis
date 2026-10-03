"""MEAL forms."""
from django import forms

from .models import FeedbackCase, Indicator, IndicatorUpdate, MEALReport


class IndicatorForm(forms.ModelForm):
    class Meta:
        model = Indicator
        fields = [
            "code", "name", "definition", "program", "project", "baseline",
            "target", "current", "unit", "frequency", "data_source", "responsible",
        ]
        widgets = {"definition": forms.Textarea(attrs={"rows": 2})}


class IndicatorUpdateForm(forms.ModelForm):
    class Meta:
        model = IndicatorUpdate
        fields = ["period", "value", "notes"]
        widgets = {"period": forms.DateInput(attrs={"type": "date"})}


class MEALReportForm(forms.ModelForm):
    class Meta:
        model = MEALReport
        fields = [
            "report_type", "title", "program", "project", "period_start",
            "period_end", "summary", "achievements", "challenges", "lessons", "file",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "achievements": forms.Textarea(attrs={"rows": 3}),
            "challenges": forms.Textarea(attrs={"rows": 2}),
            "lessons": forms.Textarea(attrs={"rows": 2}),
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
        }


class FeedbackCaseForm(forms.ModelForm):
    class Meta:
        model = FeedbackCase
        fields = [
            "category", "channel", "received_at", "project", "beneficiary",
            "is_anonymous", "reporter_name", "reporter_phone", "consent_to_follow_up", "details",
        ]
        widgets = {
            "received_at": forms.DateInput(attrs={"type": "date"}),
            "details": forms.Textarea(attrs={"rows": 5}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_anonymous") or not cleaned.get("consent_to_follow_up"):
            cleaned["reporter_name"] = ""
            cleaned["reporter_phone"] = ""
            cleaned["beneficiary"] = None
        return cleaned


class FeedbackReviewForm(forms.ModelForm):
    class Meta:
        model = FeedbackCase
        fields = ["status", "response"]
        widgets = {"response": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") in {FeedbackCase.Status.RESOLVED, FeedbackCase.Status.CLOSED} and not cleaned.get("response", "").strip():
            self.add_error("response", "Add a resolution note before resolving or closing a case.")
        return cleaned
