"""Tasks and meetings views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView
from apps.core.services import notify

from .forms import ActionPointForm, MeetingForm, TaskForm, TaskStatusForm
from .models import ActionPoint, Meeting, Task


class TaskListView(GHDIListView):
    model = Task
    permission_required = "collaboration.view_task"
    search_fields = ("title", "description")
    title = "Tasks"

    def get_queryset(self):
        qs = super().get_queryset().select_related("assigned_to", "project", "program")
        status = self.request.GET.get("status")
        mine = self.request.GET.get("mine")
        if status:
            qs = qs.filter(status=status)
        if mine:
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Task.Status.choices
        context["priorities"] = Task.Priority.choices
        context["my_open"] = Task.objects.filter(assigned_to=self.request.user).exclude(status__in=[Task.Status.DONE, Task.Status.CANCELLED]).count()
        return context


class TaskDetailView(GHDidDetailView):
    model = Task
    permission_required = "collaboration.view_task"
    template_name = "collaboration/task_detail.html"


class TaskCreateView(GHDICreateView):
    model = Task
    form_class = TaskForm
    permission_required = "collaboration.add_task"
    template_name = "collaboration/task_form.html"
    title = "Create Task"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.assigned_to and self.object.assigned_to != self.request.user:
            notify(
                self.object.assigned_to, "reminder", f"New task assigned: {self.object.title}",
                f"{self.request.user.get_full_name()} assigned you a task due "
                f"{self.object.due_date or 'soon'}.",
                url=self.object.get_absolute_url(),
            )
        return response


class TaskUpdateView(GHDIUpdateView):
    model = Task
    form_class = TaskForm
    permission_required = "collaboration.change_task"
    template_name = "collaboration/task_form.html"
    title = "Edit Task"


@login_required
@permission_required("collaboration.change_task", raise_exception=True)
def task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskStatusForm(request.POST or None, instance=task)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Task status updated.")
        else:
            messages.error(request, "Could not update the task status.")
    return redirect("collaboration:task_detail", pk)


class MeetingListView(GHDIListView):
    model = Meeting
    permission_required = "collaboration.view_meeting"
    search_fields = ("title", "agenda")
    title = "Meetings"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("participants")


class MeetingDetailView(GHDidDetailView):
    model = Meeting
    permission_required = "collaboration.view_meeting"
    template_name = "collaboration/meeting_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_points"] = self.object.action_points.select_related("assignee")
        context["ap_form"] = ActionPointForm()
        return context


class MeetingCreateView(GHDICreateView):
    model = Meeting
    form_class = MeetingForm
    permission_required = "collaboration.add_meeting"
    template_name = "collaboration/meeting_form.html"
    title = "Schedule Meeting"

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        response = super().form_valid(form)
        if self.object.participants.exists():
            from apps.core.services import notify_many

            notify_many(
                self.object.participants.all(), "reminder",
                f"Meeting invitation: {self.object.title}",
                f"{self.request.user.get_full_name()} invited you to “{self.object.title}” on "
                f"{self.object.date}.",
                url=self.object.get_absolute_url(),
            )
        return response


class MeetingUpdateView(GHDIUpdateView):
    model = Meeting
    form_class = MeetingForm
    permission_required = "collaboration.change_meeting"
    template_name = "collaboration/meeting_form.html"
    title = "Edit Meeting"


@login_required
@permission_required("collaboration.change_meeting", raise_exception=True)
def action_point_create(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    form = ActionPointForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ap = form.save(commit=False)
        ap.meeting = meeting
        ap.save()
        if ap.assignee:
            notify(
                ap.assignee, "reminder", f"Action point from {meeting.title}",
                ap.description, url=meeting.get_absolute_url(),
            )
        messages.success(request, "Action point added.")
    return redirect("collaboration:meeting_detail", pk)


@login_required
@permission_required("collaboration.change_meeting", raise_exception=True)
@require_POST
def action_point_toggle(request, pk, ap_id):
    ap = get_object_or_404(ActionPoint, pk=ap_id, meeting_id=pk)
    ap.is_done = not ap.is_done
    ap.save(update_fields=["is_done"])
    return redirect("collaboration:meeting_detail", pk)
