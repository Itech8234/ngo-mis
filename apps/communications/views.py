"""Announcements and internal messages views."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.core.generic import GHDIListView, GHDICreateView, GHDidDetailView
from apps.core.services import notify, notify_many

from .forms import AnnouncementForm, MessageForm
from .models import Announcement, InternalMessage

User = get_user_model()


class AnnouncementListView(GHDIListView):
    model = Announcement
    permission_required = "communications.view_announcement"
    title = "Announcements"

    def get_queryset(self):
        return super().get_queryset().select_related("created_by")


class AnnouncementDetailView(GHDidDetailView):
    model = Announcement
    permission_required = "communications.view_announcement"
    template_name = "communications/announcement_detail.html"


class AnnouncementCreateView(GHDICreateView):
    model = Announcement
    form_class = AnnouncementForm
    permission_required = "communications.add_announcement"
    template_name = "communications/announcement_form.html"
    title = "New Announcement"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.status == Announcement.Status.PUBLISHED:
            self._broadcast(self.object)
        return response

    def _broadcast(self, announcement):
        roles = {
            Announcement.Audience.ALL: None,
            Announcement.Audience.PROGRAMS: ["pm", "meal", "staff"],
            Announcement.Audience.FINANCE: ["fin"],
            Announcement.Audience.HR: ["hr"],
            Announcement.Audience.ADMIN: ["admin", "exec"],
        }.get(announcement.audience)
        qs = User.objects.filter(is_active=True)
        if roles:
            qs = qs.filter(role__in=roles)
        notify_many(
            qs, "system", f"Announcement: {announcement.title}",
            announcement.body[:200], url=announcement.get_absolute_url(),
        )


@login_required
@permission_required("communications.publish_announcement", raise_exception=True)
@require_POST
def announcement_publish(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.status = Announcement.Status.PUBLISHED
    announcement.publish_at = announcement.publish_at or timezone.localdate()
    announcement.save(update_fields=["status", "publish_at", "updated_at"])
    messages.success(request, "Announcement published.")
    return redirect("communications:announcement_detail", pk)


@login_required
def inbox(request):
    """Internal messages inbox with compose."""
    received = InternalMessage.objects.filter(recipient=request.user).select_related("sender")[:50]
    sent = InternalMessage.objects.filter(sender=request.user).select_related("recipient")[:25]
    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.sender = request.user
        message.save()
        notify(
            message.recipient, "message", f"Message from {request.user.get_full_name()}",
            message.subject, url="/app/communications/inbox/",
        )
        messages.success(request, "Message sent.")
        return redirect("communications:inbox")
    unread_count = request.user.received_messages.filter(is_read=False).count()
    return render(
        request,
        "communications/inbox.html",
        {"received": received, "sent": sent, "form": form, "unread_count": unread_count,
         "page_title": "Inbox"},
    )


@login_required
def message_read(request, pk):
    message = get_object_or_404(InternalMessage, pk=pk, recipient=request.user)
    message.is_read = True
    message.save(update_fields=["is_read"])
    replies = InternalMessage.objects.filter(parent=message)
    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reply = form.save(commit=False)
        reply.sender = request.user
        reply.recipient = message.sender
        reply.parent = message
        reply.save()
        notify(
            reply.recipient, "message", f"Reply from {request.user.get_full_name()}",
            reply.subject, url="/app/communications/inbox/",
        )
        messages.success(request, "Reply sent.")
        return redirect("communications:message_detail", pk)
    return render(request, "communications/message_detail.html", {"message_obj": message, "replies": replies, "page_title": "Message", "form": form})
