"""MEAL module: indicators, indicator updates and MEAL reports."""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import OwnedModel, WorkflowMixin
from apps.core.validators import FileSizeValidator, FileTypeValidator


class Indicator(OwnedModel):
    """MEAL indicator linked to a program and/or project."""

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        BIANNUAL = "biannual", "Bi-annual"
        ANNUAL = "annual", "Annual"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    definition = models.TextField(blank=True)
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="indicators")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="indicators")
    baseline = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=40, default="number")
    frequency = models.CharField(max_length=12, choices=Frequency.choices, default=Frequency.MONTHLY)
    data_source = models.CharField(max_length=160, blank=True)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="indicators_owned")

    class Meta:
        ordering = ("code",)

    @property
    def achievement(self):
        if not self.target:
            return 0.0
        return round(float(self.current) / float(self.target) * 100, 1)

    @property
    def is_below_target(self):
        return self.achievement < 70.0

    def get_absolute_url(self):
        return reverse("monitoring:indicator_detail", args=[self.pk])

    def __str__(self):
        return f"{self.code} - {self.name}"


class IndicatorUpdate(models.Model):
    """A reported data point for an indicator; updates Indicator.current."""

    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="updates")
    period = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-period", "-created_at")

    def __str__(self):
        return f"{self.indicator.code} {self.period}: {self.value}"


class MEALReport(WorkflowMixin, OwnedModel):
    """Monitoring report (monthly, quarterly, donor, etc.) with approval flow."""

    class ReportType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        PROJECT = "project", "Project"
        DONOR = "donor", "Donor"
        ACTIVITY = "activity", "Activity"
        OUTCOME = "outcome", "Outcome"

    report_type = models.CharField(max_length=12, choices=ReportType.choices, default=ReportType.MONTHLY)
    title = models.CharField(max_length=200)
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="meal_reports")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="meal_reports")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    summary = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    file = models.FileField(upload_to="meal_reports/", blank=True, validators=[FileSizeValidator(), FileTypeValidator()])

    class Meta:
        ordering = ("-created_at",)

    def get_absolute_url(self):
        return reverse("monitoring:report_detail", args=[self.pk])

    def __str__(self):
        return self.title


class FeedbackCase(OwnedModel):
    """Restricted record of community feedback and response actions."""

    class Category(models.TextChoices):
        COMPLAINT = "complaint", "Complaint"
        SUGGESTION = "suggestion", "Suggestion"
        QUESTION = "question", "Question"
        PRAISE = "praise", "Positive feedback"
        OTHER = "other", "Other"

    class Channel(models.TextChoices):
        IN_PERSON = "in_person", "In person"
        PHONE = "phone", "Phone"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"
        COMMUNITY = "community", "Community representative"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        UNDER_REVIEW = "under_review", "Under review"
        REFERRED = "referred", "Referred"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    reference = models.CharField(max_length=20, unique=True, editable=False)
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.OTHER, db_index=True)
    channel = models.CharField(max_length=12, choices=Channel.choices, default=Channel.OTHER)
    received_at = models.DateField(default=timezone.localdate, db_index=True)
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="feedback_cases")
    beneficiary = models.ForeignKey("beneficiaries.Beneficiary", null=True, blank=True, on_delete=models.SET_NULL, related_name="feedback_cases")
    is_anonymous = models.BooleanField(default=False)
    reporter_name = models.CharField(max_length=160, blank=True)
    reporter_phone = models.CharField(max_length=50, blank=True)
    details = models.TextField()
    consent_to_follow_up = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    response = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at", "-created_at")
        permissions = [("manage_feedbackcase", "Can triage and resolve feedback cases")]

    def save(self, *args, **kwargs):
        if not self.reference:
            last = type(self).objects.order_by("-pk").first()
            number = int(last.reference.split("-")[-1]) + 1 if last and last.reference.startswith("FDB-") else 1
            self.reference = f"FDB-{number:06d}"
        if self.is_anonymous:
            self.reporter_name = ""
            self.reporter_phone = ""
            self.beneficiary = None
            self.consent_to_follow_up = False
        if self.status in {self.Status.RESOLVED, self.Status.CLOSED} and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status not in {self.Status.RESOLVED, self.Status.CLOSED}:
            self.resolved_at = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("monitoring:feedback_detail", args=[self.pk])

    def __str__(self):
        return self.reference
