"""Audit middleware and signal receivers.

``AuditRequestMiddleware`` makes the current request (user, IP, agent)
available to signal handlers. ``connect_audited_models`` registers
post_save/post_delete receivers for every audited model.
"""
import threading

from django.core.signals import request_finished

from .models import AuditLog

_state = threading.local()


def get_audit_context():
    return getattr(_state, "context", {})


class AuditRequestMiddleware:
    """Captures request context for audit signal handlers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        _state.context = {
            "user": user if (user and user.is_authenticated) else None,
            "ip": request.META.get("REMOTE_ADDR", ""),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
        }
        try:
            return self.get_response(request)
        finally:
            _state.context = {}


def log_action(user, action, module="", model="", object_id="", object_repr="", changes=None, request=None):
    """Central helper for explicit audit logging from services/views."""
    context = {}
    if request is not None:
        from apps.core.middleware import get_client_ip

        context = {
            "ip": get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
        }
    else:
        context = get_audit_context()
    AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        username=getattr(user, "username", "") or "",
        action=action,
        module=module,
        model=model,
        object_id=str(object_id or ""),
        object_repr=str(object_repr or "")[:255],
        changes=changes or {},
        ip_address=context.get("ip") or None,
        user_agent=context.get("user_agent", ""),
    )


def _diff(old, new):
    """Compute a shallow field-level diff between tracked fields."""
    changes = {}
    tracked = (
        "status", "title", "name", "code", "amount", "budget", "start_date",
        "end_date", "approved_by_id", "assigned_to_id", "value", "current",
        "role", "is_active",
    )
    for field in tracked:
        before = getattr(old, field, None)
        after = getattr(new, field, None)
        if before != after:
            changes[field] = {"from": str(before), "to": str(after)}
    return changes


def snapshot_instance(instance):
    """Cache pre-save values (thread-local) so post_save can diff updates."""
    import threading

    _state = threading.local()
    if instance.pk is None:
        return
    old = type(instance).objects.filter(pk=instance.pk).first()
    if old is None:
        return
    changes = _diff(old, instance)
    instance._audit_changes_ = changes
