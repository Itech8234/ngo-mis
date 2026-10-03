"""Tasks, meetings and meeting action points."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import OwnedModel


class Task(OwnedModel):
    """Task assignable to staff, optionally linked to a project."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tasks")
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO, db_index=True)
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("due_date", "-created_at")

    def save(self, *args, **kwargs):
        from django.utils import timezone

        if self.status == self.Status.DONE and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != self.Status.DONE:
            self.completed_at = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        from django.utils import timezone

        return bool(self.due_date) and self.due_date < timezone.localdate() and self.status not in (
            self.Status.DONE, self.Status.CANCELLED
        )

    def get_absolute_url(self):
        return reverse("collaboration:task_detail", args=[self.pk])

    def __str__(self):
        return self.title


class Meeting(OwnedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        HELD = "held", "Held"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="organized_meetings")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="meetings")
    agenda = models.TextField(blank=True)
    minutes = models.TextField(blank=True)
    decisions = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        ordering = ("-date",)

    def get_absolute_url(self):
        return reverse("collaboration:meeting_detail", args=[self.pk])

    def __str__(self):
        return f"{self.title} ({self.date})"


class ActionPoint(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="action_points")
    description = models.CharField(max_length=255)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="action_points")
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)

    class Meta:
        ordering = ("is_done", "due_date")

    def __str__(self):
        return self.description
