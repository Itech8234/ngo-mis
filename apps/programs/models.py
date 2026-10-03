"""Programs module: programs, projects and field activities."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import Location, OwnedModel, WorkflowMixin
from apps.core.validators import FileSizeValidator, FileTypeValidator


class ThematicArea(models.TextChoices):
    PROTECTION = "protection", "Protection"
    EDUCATION = "education", "Education"
    RESILIENCE = "resilience", "Community Resilience"
    LOCALLY_LED = "locally_led", "Locally Led Solutions"


class ProgramStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    COMPLETED = "completed", "Completed"
    CLOSED = "closed", "Closed"


class Program(OwnedModel):
    """Multi-year thematic program funded by one or more grants."""

    Status = ProgramStatus
    ThematicArea = ThematicArea

    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    thematic_area = models.CharField(max_length=20, choices=ThematicArea.choices, db_index=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_programs")
    funding_source = models.CharField(max_length=200, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    target_beneficiaries = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    locations = models.ManyToManyField(Location, blank=True, related_name="programs")
    status = models.CharField(max_length=12, choices=ProgramStatus.choices, default=ProgramStatus.ACTIVE, db_index=True)

    class Meta:
        ordering = ("title",)

    @property
    def actual_beneficiaries(self):
        return sum(p.reached_beneficiaries for p in self.projects.all())

    @property
    def spent(self):
        return sum(p.spent for p in self.projects.all())

    def get_absolute_url(self):
        return reverse("programs:program_detail", args=[self.pk])

    def __str__(self):
        return f"{self.title} ({self.code})"


class ProjectStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    AT_RISK = "at_risk", "At Risk"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


class Project(WorkflowMixin, OwnedModel):
    """Donor-funded project under a program. Budgets follow the approval workflow."""

    Status = ProjectStatus

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    donor = models.ForeignKey("partners.Donor", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects")
    grant = models.ForeignKey("partners.Grant", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_projects")
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    objectives = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    outputs = models.TextField(blank=True)
    assumptions = models.TextField(blank=True)
    stakeholders = models.TextField(blank=True)
    target_beneficiaries = models.PositiveIntegerField(default=0)
    locations = models.ManyToManyField(Location, blank=True, related_name="projects")
    status = models.CharField(max_length=12, choices=ProjectStatus.choices, default=ProjectStatus.PLANNED, db_index=True)

    class Meta:
        ordering = ("name",)
        permissions = [("approve_project", "Can approve project plans and budgets")]

    @property
    def spent(self):
        from apps.finance.models import Transaction

        total = Transaction.objects.filter(project=self, direction=Transaction.Direction.EXPENSE).aggregate(
            t=models.Sum("amount")
        )["t"]
        return total or 0

    @property
    def reached_beneficiaries(self):
        return self.beneficiaries.count()

    @property
    def budget_utilisation(self):
        if not self.budget:
            return 0
        return min(100.0, float(self.spent) / float(self.budget) * 100)

    @property
    def completion(self):
        total = self.activities.count()
        if not total:
            return 0
        done = self.activities.filter(status=Activity.Status.COMPLETED).count()
        return round(done / total * 100)

    def get_absolute_url(self):
        return reverse("programs:project_detail", args=[self.pk])

    def __str__(self):
        return f"{self.name} ({self.code})"


class Activity(OwnedModel):
    """Field activity under a project with inline status updates."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DELAYED = "delayed", "Delayed"
        CANCELLED = "cancelled", "Cancelled"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="responsible_activities")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expected_participants = models.PositiveIntegerField(default=0)
    actual_participants = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANNED, db_index=True)
    evidence = models.FileField(
        upload_to="activities/", blank=True,
        validators=[FileSizeValidator(), FileTypeValidator()],
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("start_date", "name")

    @property
    def is_delayed(self):
        return bool(self.end_date) and self.end_date < timezone_now() and self.status not in (
            self.Status.COMPLETED, self.Status.CANCELLED
        )

    def get_absolute_url(self):
        return reverse("programs:activity_detail", args=[self.pk])

    def __str__(self):
        return self.name


def timezone_now():
    from django.utils import timezone

    return timezone.localdate()

