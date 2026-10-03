from django.urls import path

from . import views

app_name = "programs"

urlpatterns = [
    # Programs
    path("", views.ProgramListView.as_view(), name="program_list"),
    path("new/", views.ProgramCreateView.as_view(), name="program_create"),
    path("<int:pk>/", views.ProgramDetailView.as_view(), name="program_detail"),
    path("<int:pk>/edit/", views.ProgramUpdateView.as_view(), name="program_edit"),
    # Projects
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("projects/new/", views.ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("projects/<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_edit"),
    path("projects/<int:pk>/submit/", views.project_submit, name="project_submit"),
    path("projects/<int:pk>/approve/", views.project_approve, name="project_approve"),
    path("projects/<int:pk>/reject/", views.project_reject, name="project_reject"),
    # Activities
    path("activities/", views.ActivityListView.as_view(), name="activity_list"),
    path("activities/new/", views.ActivityCreateView.as_view(), name="activity_create"),
    path("activities/<int:pk>/", views.ActivityDetailView.as_view(), name="activity_detail"),
    path("activities/<int:pk>/edit/", views.ActivityUpdateView.as_view(), name="activity_edit"),
    path("activities/<int:pk>/update/", views.activity_inline_update, name="activity_update"),
]
