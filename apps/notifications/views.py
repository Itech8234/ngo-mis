"""Notification views: badge/panel, list, mark-as-read."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()[:60]
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def notification_panel(request):
    """Latest notifications for the topbar dropdown."""
    notifications = request.user.notifications.all()[:8]
    unread = request.user.notifications.filter(is_read=False).count()
    return render(
        request,
        "notifications/_panel.html",
        {"notifications": notifications, "unread": unread},
    )


@login_required
def notification_badge(request):
    """Returns the current unread count badge."""
    unread = request.user.notifications.filter(is_read=False).count()
    return render(request, "notifications/_badge.html", {"unread_notifications": unread})


@login_required
@require_POST
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_read()
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")
