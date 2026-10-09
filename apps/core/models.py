"""Core models: timestamps, workflow engine, organisation settings, locations."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.validators import FileSizeValidator


class TimeStampedModel(models.Model):
    """Abstract base providing creation/update audit timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OwnedModel(TimeStampedModel):
    """Abstract base that also tracks the creating/updating user."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        abstract = True


class WorkflowStatus(models.TextChoices):
    """Reusable approval workflow statuses shared across modules."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class WorkflowMixin(models.Model):
    """
    Reusable approval-workflow mixin.

    Provides a standard pipeline (Draft -> Submitted -> Under Review ->
    Approved/Rejected -> Completed) plus who acted and when. Combined with
    ``apps.core.services.WorkflowService`` this powers approvals for finance,
    procurement, leave, budgets and reports without duplicated logic.
    """

    Status = WorkflowStatus

    status = models.CharField(
        max_length=20, choices=WorkflowStatus.choices, default=WorkflowStatus.DRAFT, db_index=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    review_note = models.TextField(blank=True)

    class Meta:
        abstract = True

    @property
    def is_pending(self):
        return self.status in (WorkflowStatus.SUBMITTED, WorkflowStatus.UNDER_REVIEW)

    @property
    def is_editable(self):
        return self.status in (WorkflowStatus.DRAFT, WorkflowStatus.REJECTED)


class ApprovalStep(models.TextChoices):
    """Named steps of the GHDI approval pipeline."""

    SUBMIT = "submit", "Submission"
    SUPERVISOR = "supervisor", "Supervisor Review"
    FINANCE = "finance", "Finance Review"
    EXECUTIVE = "executive", "Executive Approval"
    PAYMENT = "payment", "Payment Processing"
    FINAL = "final", "Final Approval"


class ApprovalRecord(models.Model):
    """Immutable log of every action taken on a workflow object."""

    content_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    step = models.CharField(max_length=20, choices=ApprovalStep.choices)
    action = models.CharField(max_length=20)  # submit/approve/reject/cancel/complete
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("content_type", "object_id"))]

    def __str__(self):
        return f"{self.action} by {self.actor} at {self.created_at:%Y-%m-%d %H:%M}"


class OrganizationSetting(models.Model):
    """Singleton organisation profile editable from the settings module."""

    name = models.CharField(max_length=200, default="Garkuwa Humanitarian and Development Initiative")
    acronym = models.CharField(max_length=20, default="GHDI")
    tagline = models.CharField(
        max_length=200,
        default="Protecting Dignity. Strengthening Communities.",
    )
    logo = models.ImageField(upload_to="org/", blank=True, validators=[FileSizeValidator()])
    address = models.CharField(
        max_length=255, default="No. 1 Garkuwa Close, Damaturu, Yobe State, Nigeria"
    )
    email = models.EmailField(default="info@ghdi.org.ng")
    phone = models.CharField(max_length=50, default="+234 800 000 0000")
    website = models.URLField(default="https://ghdi.org.ng")
    registration_number = models.CharField(max_length=100, default="CAC/IT/NO-000000")
    mission = models.TextField(
        default=(
            "To protect, educate and empower vulnerable communities through "
            "locally led humanitarian and development solutions."
        )
    )
    vision = models.TextField(
        default="A society where every vulnerable person lives with dignity, safety and opportunity."
    )
    currency = models.CharField(max_length=3, default="NGN")
    fiscal_year_start = models.PositiveSmallIntegerField(
        default=1, help_text="Month the fiscal year starts (1-12)"
    )

    class Meta:
        verbose_name = "organization setting"
        verbose_name_plural = "organization settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Settings for {self.acronym}"


class SystemSetting(models.Model):
    """Simple key/value store for runtime system configuration."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("key",)

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default=""):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, description=""):
        cls.objects.update_or_create(key=key, defaults={"value": value, "description": description})


class Location(models.Model):
    """Operational location (community / ward / LGA) used across modules."""

    name = models.CharField(max_length=120)
    lga = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, default="Yobe")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("state", "lga", "name")
        unique_together = ("name", "lga", "state")

    def __str__(self):
        return f"{self.name} ({self.lga}, {self.state})" if self.lga else f"{self.name}, {self.state}"

