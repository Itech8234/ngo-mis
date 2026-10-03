"""Audit views: log listing, activity feed, CSV export."""
import csv

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render

from .models import AuditLog

FEED_ACTIONS = ("login", "logout", "create", "update", "delete", "approve", "reject", "submit")


@login_required
def feed(request):
    """User-facing activity feed with module and date filters."""
    module = request.GET.get("module", "")
    action = request.GET.get("action", "")
    days = request.GET.get("days", "")
    entries = AuditLog.objects.filter(action__in=FEED_ACTIONS)
    if module:
        entries = entries.filter(module=module)
    if action:
        entries = entries.filter(action=action)
    if days.isdigit():
        import datetime
        from django.utils import timezone

        since = timezone.now() - datetime.timedelta(days=int(days))
        entries = entries.filter(created_at__gte=since)
    entries = entries[:80]
    modules = AuditLog.objects.values_list("module", flat=True).distinct().order_by("module")
    return render(
        request,
        "audit/feed.html",
        {"entries": entries, "modules": modules, "module": module, "action": action, "days": days},
    )


@login_required
@permission_required("audit.view_auditlog", raise_exception=True)
def log_list(request):
    query = request.GET.get("q", "").strip()
    module = request.GET.get("module", "")
    action = request.GET.get("action", "")
    entries = AuditLog.objects.all().select_related("user")
    filters = Q()
    if query:
        filters |= Q(username__icontains=query) | Q(object_repr__icontains=query)
    if module:
        filters &= Q(module=module)
    if action:
        filters &= Q(action=action)
    entries = entries.filter(filters)[:200]
    modules = AuditLog.objects.values_list("module", flat=True).distinct().order_by("module")
    return render(
        request,
        "audit/log_list.html",
        {
            "entries": entries,
            "modules": modules,
            "actions": AuditLog.Action.choices,
            "query": query,
            "module": module,
            "action": action,
        },
    )


@login_required
@permission_required("accounts.export_report", raise_exception=True)
def export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ghdi-audit-log.csv"'
    writer = csv.writer(response)
    writer.writerow(["Timestamp", "User", "Action", "Module", "Model", "Object", "IP"])
    for entry in AuditLog.objects.select_related("user")[:2000]:
        writer.writerow(
            [
                entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                entry.username,
                entry.action,
                entry.module,
                entry.model,
                entry.object_repr,
                entry.ip_address or "",
            ]
        )
    return response
