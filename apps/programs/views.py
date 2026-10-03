"""Programs views: programs, projects (with approval workflow) and activities."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.audit.middleware import log_action
from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView
from apps.core.services import WorkflowService, notify, notify_many

from .forms import ActivityForm, ActivityStatusForm, ProgramForm, ProjectForm
from .models import Activity, Program, Project

User = get_user_model()


class ProgramListView(GHDIListView):
    model = Program
    permission_required = "programs.view_program"
    template_name = "programs/program_list.html"
    search_fields = ("title", "code", "description")
    title = "Programs"

    def get_queryset(self):
        qs = super().get_queryset().select_related("manager")
        status = self.request.GET.get("status")
        area = self.request.GET.get("area")
        if status:
            qs = qs.filter(status=status)
        if area:
            qs = qs.filter(thematic_area=area)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Program.Status.choices
        context["areas"] = Program.ThematicArea.choices
        return context


class ProgramDetailView(GHDidDetailView):
    model = Program
    permission_required = "programs.view_program"
    template_name = "programs/program_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.object
        context["projects"] = program.projects.all().select_related("donor", "manager")
        context["total_budget"] = sum(p.budget for p in context["projects"])
        context["total_spent"] = sum(p.spent for p in context["projects"])
        return context


class ProgramCreateView(GHDICreateView):
    model = Program
    form_class = ProgramForm
    permission_required = "programs.add_program"
    template_name = "programs/program_form.html"
    title = "Create Program"


class ProgramUpdateView(GHDIUpdateView):
    model = Program
    form_class = ProgramForm
    permission_required = "programs.change_program"
    template_name = "programs/program_form.html"
    title = "Edit Program"


class ProjectListView(GHDIListView):
    model = Project
    permission_required = "programs.view_project"
    template_name = "programs/project_list.html"
    search_fields = ("name", "code", "objectives")
    title = "Projects"

    def get_queryset(self):
        qs = super().get_queryset().select_related("program", "donor", "manager")
        status = self.request.GET.get("status")
        program = self.request.GET.get("program")
        if status:
            qs = qs.filter(status=status)
        if program:
            qs = qs.filter(program_id=program)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Project.Status.choices
        context["programs"] = Program.objects.all()
        return context


class ProjectDetailView(GHDidDetailView):
    model = Project
    permission_required = "programs.view_project"
    template_name = "programs/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        context["activities"] = project.activities.select_related("location", "responsible")
        context["indicators"] = project.indicators.select_related("program")
        from apps.documents.models import Document
        from django.contrib.contenttypes.models import ContentType

        context["documents"] = Document.objects.filter(
            content_type=ContentType.objects.get_for_model(Project), object_id=project.pk
        )
        context["beneficiaries_count"] = project.beneficiaries.count()
        context["risks"] = project.risks.all() if hasattr(project, "risks") else []
        return context


class ProjectCreateView(GHDICreateView):
    model = Project
    form_class = ProjectForm
    permission_required = "programs.add_project"
    template_name = "programs/project_form.html"
    title = "Create Project"

    def form_valid(self, form):
        response = super().form_valid(form)
        from apps.audit.middleware import log_action

        log_action(self.request.user, "create", module="programs", model="project", object_id=self.object.pk, object_repr=str(self.object), request=self.request)
        return response


class ProjectUpdateView(GHDIUpdateView):
    model = Project
    form_class = ProjectForm
    permission_required = "programs.change_project"
    template_name = "programs/project_form.html"
    title = "Edit Project"


@login_required
@permission_required("programs.approve_project", raise_exception=True)
@require_POST
def project_submit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    WorkflowService(project, request.user).submit(
        notify_users=User.objects.filter(role__in=["exec", "admin"], is_active=True)
    )
    messages.success(request, "Project submitted for executive approval.")
    return redirect("programs:project_detail", pk)


@login_required
@permission_required("programs.approve_project", raise_exception=True)
@require_POST
def project_approve(request, pk):
    project = get_object_or_404(Project, pk=pk)
    note = request.POST.get("note", "")
    WorkflowService(project, request.user).approve(step="executive", note=note)
    if project.status == Project.Status.PLANNED:
        project.status = Project.Status.ACTIVE
        project.save(update_fields=["status", "updated_at"])
    messages.success(request, "Project approved.")
    return redirect("programs:project_detail", pk)


@login_required
@permission_required("programs.approve_project", raise_exception=True)
@require_POST
def project_reject(request, pk):
    project = get_object_or_404(Project, pk=pk)
    WorkflowService(project, request.user).reject(note=request.POST.get("note", ""))
    messages.warning(request, "Project returned for revision.")
    return redirect("programs:project_detail", pk)


class ActivityListView(GHDIListView):
    model = Activity
    permission_required = "programs.view_activity"
    template_name = "programs/activity_list.html"
    search_fields = ("name", "description", "notes")
    title = "Activities"

    def get_queryset(self):
        qs = super().get_queryset().select_related("project", "location", "responsible")
        project = self.request.GET.get("project")
        status = self.request.GET.get("status")
        if project:
            qs = qs.filter(project_id=project)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Activity.Status.choices
        context["projects"] = Project.objects.order_by("name")
        return context


class ActivityDetailView(GHDidDetailView):
    model = Activity
    permission_required = "programs.view_activity"
    template_name = "programs/activity_detail.html"


class ActivityCreateView(GHDICreateView):
    model = Activity
    form_class = ActivityForm
    permission_required = "programs.add_activity"
    template_name = "programs/activity_form.html"
    title = "Create Activity"

    def get_initial(self):
        initial = super().get_initial()
        project = self.request.GET.get("project")
        if project:
            initial["project"] = project
        return initial


class ActivityUpdateView(GHDIUpdateView):
    model = Activity
    form_class = ActivityForm
    permission_required = "programs.change_activity"
    template_name = "programs/activity_form.html"
    title = "Edit Activity"


@login_required
@permission_required("programs.change_activity", raise_exception=True)
def activity_inline_update(request, pk):
    """Inline status/participants update from the project detail page.

    Plain POST with POST/Redirect/GET so the change is refresh-safe and does
    not depend on JavaScript.
    """
    activity = get_object_or_404(Activity, pk=pk)
    old_status = activity.status
    form = ActivityStatusForm(request.POST or None, instance=activity)
    if request.method == "POST":
        if form.is_valid():
            activity = form.save()
            if old_status != activity.status:
                log_action(
                    request.user, "update", module="programs", model="activity",
                    object_id=activity.pk, object_repr=str(activity),
                    changes={"status": {"from": old_status, "to": activity.status}},
                    request=request,
                )
                if activity.responsible and activity.responsible != request.user:
                    notify(
                        activity.responsible, "program",
                        f"Activity status updated: {activity.name}",
                        f"Status changed from {old_status.replace('_', ' ').title()} to "
                        f"{activity.status.replace('_', ' ').title()}.",
                        url=activity.get_absolute_url(),
                    )
            messages.success(request, "Activity updated.")
        else:
            messages.error(request, "Could not update the activity: invalid status.")
    return redirect("programs:project_detail", activity.project_id)


