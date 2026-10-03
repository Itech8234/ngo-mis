"""Audit app: signal registration for automatic change logging."""
from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save, pre_save


class AuditConfig(AppConfig):
    name = "apps.audit"
    label = "audit"

    def ready(self):
        from django.apps import apps as django_apps
        from django.conf import settings as dj_settings

        from apps.core.middleware import get_current_request
        from .middleware import log_action, snapshot_instance

        AUDITED = [
            ("accounts", "User"),
            ("hr", "Employee"),
            ("hr", "LeaveRequest"),
            ("hr", "Vacancy"),
            ("hr", "Training"),
            ("programs", "Program"),
            ("programs", "Project"),
            ("programs", "Activity"),
            ("beneficiaries", "Beneficiary"),
            ("monitoring", "Indicator"),
            ("finance", "Transaction"),
            ("finance", "Budget"),
            ("finance", "ExpenseRequest"),
            ("partners", "Donor"),
            ("partners", "Partner"),
            ("procurement", "ProcurementRequest"),
            ("assets", "Asset"),
            ("documents", "Document"),
            ("collaboration", "Task"),
            ("risk", "Risk"),
            ("risk", "Incident"),
            ("cms", "Page"),
            ("cms", "NewsArticle"),
        ]

        def make_pre_receiver():
            def receiver(sender, instance, **kwargs):
                snapshot_instance(instance)
            return receiver

        def make_post_receiver(action):
            def receiver(sender, instance, **kwargs):
                key = f"{sender._meta.app_label}.{sender._meta.model_name}"
                if key in dj_settings.GHDI_AUDIT_EXEMPT:
                    return
                resolved = action
                if resolved in ("create", "update"):
                    resolved = "create" if kwargs.get("created") else "update"
                request = get_current_request()
                user = getattr(request, "user", None)
                if user is not None and not user.is_authenticated:
                    user = None
                changes = {}
                if resolved == "update":
                    changes = instance.__dict__.pop("_audit_changes_", {})
                    if not changes:
                        return
                log_action(
                    user=user,
                    action=resolved,
                    module=sender._meta.app_label,
                    model=sender._meta.model_name,
                    object_id=instance.pk,
                    object_repr=str(instance),
                    changes=changes,
                    request=request,
                )

            return receiver

        for app_label, model_name in AUDITED:
            try:
                model = django_apps.get_model(app_label, model_name)
            except LookupError:  # pragma: no cover
                continue
            pre_save.connect(
                make_pre_receiver(), sender=model, dispatch_uid=f"audit-pre-{app_label}-{model_name}"
            )
            post_save.connect(
                make_post_receiver("save"), sender=model, dispatch_uid=f"audit-post-{app_label}-{model_name}"
            )
            post_delete.connect(
                make_post_receiver("delete"), sender=model, dispatch_uid=f"audit-del-{app_label}-{model_name}"
            )
