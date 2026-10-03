"""HR forms."""
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import (
    AttendanceRecord, DisciplinaryRecord, Employee, HRDocument, LeaveBalance, LeaveRequest, PerformanceReview,
    Training, Vacancy,
)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "user", "first_name", "last_name", "photo", "gender", "date_of_birth", "email",
            "phone", "address", "emergency_contact_name", "emergency_contact_phone",
            "position", "department", "program", "employment_type", "hire_date",
            "contract_start", "contract_end", "salary", "bank_name",
            "bank_account_number", "qualifications", "skills", "certifications",
            "previous_experience", "job_description", "supervisor", "status",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "hire_date": forms.DateInput(attrs={"type": "date"}),
            "contract_start": forms.DateInput(attrs={"type": "date"}),
            "contract_end": forms.DateInput(attrs={"type": "date"}),
            "qualifications": forms.Textarea(attrs={"rows": 2}),
            "skills": forms.Textarea(attrs={"rows": 2}),
            "certifications": forms.Textarea(attrs={"rows": 2}),
            "previous_experience": forms.Textarea(attrs={"rows": 2}),
            "job_description": forms.Textarea(attrs={"rows": 3}),
            "address": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.filter(is_active=True).order_by("first_name", "last_name", "email")
        self.fields["user"].required = False
        self.fields["user"].help_text = "Link an existing login so this staff member can use attendance, leave and document self-service."


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason", "attachment"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }


class LeaveReviewForm(forms.Form):
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "input"}))


class VacancyForm(forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = ["title", "department", "location", "employment_type", "description", "requirements", "closing_date", "status", "is_public"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "closing_date": forms.DateInput(attrs={"type": "date"}),
        }


class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        fields = ["title", "category", "provider", "start_date", "end_date", "location", "description", "cost", "participants", "status"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ["employee", "date", "status", "check_in", "check_out", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "check_in": forms.TimeInput(attrs={"type": "time"}),
            "check_out": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        check_in, check_out = cleaned.get("check_in"), cleaned.get("check_out")
        if check_in and check_out and check_out < check_in:
            self.add_error("check_out", "Check-out must be later than check-in for the same workday.")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].label = "Staff member"
        staff = Employee.objects.filter(status=Employee.Status.ACTIVE)
        if self.instance.pk and self.instance.employee_id:
            staff = Employee.objects.filter(
                Q(status=Employee.Status.ACTIVE) | Q(pk=self.instance.employee_id)
            )
        self.fields["employee"].queryset = staff.select_related("department").order_by("first_name", "last_name")
        self.fields["employee"].empty_label = "Choose a staff member"
        self.fields["date"].initial = self.instance.date or timezone.localdate()


class HRDocumentForm(forms.ModelForm):
    class Meta:
        model = HRDocument
        fields = ["title", "document_type", "file", "issued_at", "expires_at", "verification", "is_confidential", "note"]
        widgets = {
            "issued_at": forms.DateInput(attrs={"type": "date"}),
            "expires_at": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"maxlength": 255}),
        }

    def clean(self):
        cleaned = super().clean()
        issued, expires = cleaned.get("issued_at"), cleaned.get("expires_at")
        if issued and expires and expires < issued:
            self.add_error("expires_at", "Expiry date cannot be before the issue date.")
        return cleaned


class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = ["employee", "leave_type", "year", "entitled_days", "carry_forward_days", "note"]
        widgets = {"note": forms.TextInput(attrs={"maxlength": 255})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].label = "Staff member"


class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = ["employee", "period", "goals", "achievements", "strengths", "areas_for_improvement", "rating", "status"]
        widgets = {
            "goals": forms.Textarea(attrs={"rows": 2}),
            "achievements": forms.Textarea(attrs={"rows": 2}),
            "strengths": forms.Textarea(attrs={"rows": 2}),
            "areas_for_improvement": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].label = "Staff member"


class DisciplinaryRecordForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryRecord
        fields = ["employee", "date", "category", "description", "action_taken", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "description": forms.Textarea(attrs={"rows": 4}), "action_taken": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].label = "Staff member"
