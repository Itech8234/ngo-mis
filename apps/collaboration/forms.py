"""Collaboration forms: tasks, meetings, action points."""
from django import forms

from .models import ActionPoint, Meeting, Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "assigned_to", "priority", "due_date", "status", "program", "project"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status"]


class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ["title", "date", "start_time", "end_time", "location", "participants", "agenda", "minutes", "decisions", "status"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "agenda": forms.Textarea(attrs={"rows": 3}),
            "minutes": forms.Textarea(attrs={"rows": 4}),
            "decisions": forms.Textarea(attrs={"rows": 3}),
        }


class ActionPointForm(forms.ModelForm):
    class Meta:
        model = ActionPoint
        fields = ["description", "assignee", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}
