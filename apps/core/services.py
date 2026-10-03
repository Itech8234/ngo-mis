"""Core services: reusable approval workflow and notification dispatch.

Every module that needs approvals uses :class:`WorkflowService` so the
pipeline behaviour (permissions, records, notifications) lives in one place.
"""
import logging

from django.conf import settings as django_settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import ApprovalRecord, ApprovalStep, WorkflowStatus

logger = logging.getLogger(__name__)


def send_notification_email(subject, body, recipients):
    """Best-effort email dispatch; failures are logged, never raised."""
    recipients = [r for r in recipients if getattr(r, "email", "")]
    if not recipients:
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[r.email for r in recipients],
            fail_silently=True,
        )
    except Exception:  # pragma: no cover - mail server issues must not break UX
        logger.exception("Failed to send notification email: %s", subject)


def notify(recipient, ntype, title, body="", url=""):
    """Create an in-app notification."""
    from apps.notifications.models import Notification

    return Notification.objects.create(
        recipient=recipient, type=ntype, title=title, body=body, url=url
    )


def notify_many(recipients, ntype, title, body="", url="", email_subject=None):
    from apps.notifications.models import Notification

    Notification.objects.bulk_create(
        [
            Notification(recipient=r, type=ntype, title=title, body=body, url=url)
            for r in recipients
        ]
    )
    if email_subject:
        send_notification_email(email_subject, body or title, recipients)


class WorkflowService:
    """
    Applies workflow transitions to any model using ``WorkflowMixin``.

    Permission enforcement happens in views (via role checks) — this service
    guarantees consistent state changes, approval records and notifications.
    All transitions run inside a database transaction.
    """

    def __init__(self, obj, actor):
        self.obj = obj
        self.actor = actor

    def _record(self, step, action, note=""):
        ApprovalRecord.objects.create(
            content_type=ContentType.objects.get_for_model(self.obj),
            object_id=self.obj.pk,
            step=step,
            action=action,
            actor=self.actor,
            note=note or "",
        )

    def _obj_url(self):
        return getattr(self.obj, "get_absolute_url", lambda: "")()

    @transaction.atomic
    def submit(self, notify_users=None, step=ApprovalStep.SUBMIT, note=""):
        self.obj.status = WorkflowStatus.SUBMITTED
        self.obj.submitted_at = timezone.now()
        self.obj.submitted_by = self.actor
        self.obj.save(update_fields=["status", "submitted_at", "submitted_by", "updated_at"])
        self._record(step, "submit", note)
        if notify_users:
            notify_many(
                notify_users,
                "approval",
                f"{self.obj._meta.verbose_name.title()} submitted for approval",
                f"{self.actor.get_full_name() or self.actor.username} submitted "
                f"“{self.obj}” for approval.",
                url=self._obj_url(),
                email_subject=f"[GHDI] Approval required: {self.obj}",
            )
        return self.obj

    @transaction.atomic
    def review(self, step=ApprovalStep.SUPERVISOR, note=""):
        self.obj.status = WorkflowStatus.UNDER_REVIEW
        self.obj.save(update_fields=["status", "updated_at"])
        self._record(step, "review", note)
        return self.obj

    @transaction.atomic
    def approve(self, step=ApprovalStep.FINAL, note="", notify_users=None):
        self.obj.status = WorkflowStatus.APPROVED
        self.obj.approved_at = timezone.now()
        self.obj.approved_by = self.actor
        if note:
            self.obj.review_note = note
        self.obj.save(update_fields=["status", "approved_at", "approved_by", "review_note", "updated_at"])
        self._record(step, "approve", note)
        requester = self.obj.submitted_by
        if requester:
            notify(
                requester,
                "approval",
                f"Your {self.obj._meta.verbose_name} was approved",
                f"“{self.obj}” was approved by {self.actor.get_full_name() or self.actor.username}.",
                url=self._obj_url(),
            )
        if notify_users:
            notify_many(
                notify_users,
                "approval",
                f"{self.obj._meta.verbose_name.title()} approved",
                f"“{self.obj}” was approved.",
                url=self._obj_url(),
            )
        return self.obj

    @transaction.atomic
    def reject(self, note="", notify_users=None):
        self.obj.status = WorkflowStatus.REJECTED
        self.obj.rejected_at = timezone.now()
        self.obj.rejected_by = self.actor
        self.obj.review_note = note
        self.obj.save(update_fields=["status", "rejected_at", "rejected_by", "review_note", "updated_at"])
        self._record(ApprovalStep.FINAL, "reject", note)
        requester = self.obj.submitted_by
        if requester:
            notify(
                requester,
                "approval",
                f"Your {self.obj._meta.verbose_name} was returned",
                f"“{self.obj}” was not approved. Reason: {note or 'No reason given.'}",
                url=self._obj_url(),
            )
        return self.obj

    @transaction.atomic
    def complete(self, note=""):
        self.obj.status = WorkflowStatus.COMPLETED
        self.obj.save(update_fields=["status", "updated_at"])
        self._record(ApprovalStep.PAYMENT, "complete", note)
        return self.obj

    @transaction.atomic
    def cancel(self, note=""):
        self.obj.status = WorkflowStatus.CANCELLED
        self.obj.save(update_fields=["status", "updated_at"])
        self._record(ApprovalStep.SUBMIT, "cancel", note)
        return self.obj

    def history(self):
        ct = ContentType.objects.get_for_model(self.obj)
        return ApprovalRecord.objects.filter(content_type=ct, object_id=self.obj.pk).select_related("actor")

