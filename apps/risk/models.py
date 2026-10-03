"""Risk register and incident management."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import OwnedModel
from apps.core.validators import FileSizeValidator, FileTypeValidator


class Risk(OwnedModel):
    """Organisational risk register entry (score = probability x impact)."""

    class Category(models.TextChoices):
        FINANCIAL = "financial", "Financial"
        OPERATIONAL = "operational", "Operational"
        PROGRAMMATIC = "programmatic", "Programmatic"
        SECURITY = "security", "Security"
        REPUTATIONAL = "reputational", "Reputational"
        COMPLIANCE = "compliance", "Compliance"
        HR = "hr", "Human Resources"
        PROCUREMENT = "procurement", "Procurement"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATING = "mitigating", "Mitigating"
        ESCALATED = "escalated", "Escalated"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=15, choices=Category.choices, db_index=True)
    probability = models.PositiveSmallIntegerField(default=3, help_text="1 (rare) - 5 (almost certain)")
    impact = models.PositiveSmallIntegerField(default=3, help_text="1 (negligible) - 5 (severe)")
    mitigation = models.TextField(blank=True)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="risks_owned")
    review_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True)

    class Meta:
        ordering = ("-probability", "-impact", "title")

    @property
    def score(self):
        return self.probability * self.impact

    @property
    def level(self):
        if self.score >= 15:
            return "high"
        if self.score >= 8:
            return "medium"
        return "low"

    def get_absolute_url(self):
        return reverse("risk:risk_detail", args=[self.pk])

    def __str__(self):
        return self.title


class Incident(OwnedModel):
    """Security/safety/safeguarding incident with follow-up tracking."""

    class Category(models.TextChoices):
        SECURITY = "security", "Security"
        SAFETY = "safety", "Safety"
        SAFEGUARDING = "safeguarding", "Safeguarding"
        FRAUD = "fraud", "Fraud / Corruption"
        PROGRAM = "program", "Program"
        IT = "it", "IT / Data"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=15, choices=Category.choices, db_index=True)
    date = models.DateField(db_index=True)
    location = models.CharField(max_length=160, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reported_incidents")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_incidents")
    actions_taken = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN, db_index=True)
    attachment = models.FileField(upload_to="incidents/", blank=True, validators=[FileSizeValidator(), FileTypeValidator()])
    follow_up_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("-date",)

    def get_absolute_url(self):
        return reverse("risk:incident_detail", args=[self.pk])

    def __str__(self):
        return self.title
