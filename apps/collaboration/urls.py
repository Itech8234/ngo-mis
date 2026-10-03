from django.urls import path

from . import views

app_name = "collaboration"

urlpatterns = [
    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("tasks/new/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task_edit"),
    path("tasks/<int:pk>/status/", views.task_status, name="task_status"),
    path("meetings/", views.MeetingListView.as_view(), name="meeting_list"),
    path("meetings/new/", views.MeetingCreateView.as_view(), name="meeting_create"),
    path("meetings/<int:pk>/", views.MeetingDetailView.as_view(), name="meeting_detail"),
    path("meetings/<int:pk>/edit/", views.MeetingUpdateView.as_view(), name="meeting_edit"),
    path("meetings/<int:pk>/action-points/new/", views.action_point_create, name="action_point_create"),
    path("meetings/<int:pk>/action-points/<int:ap_id>/toggle/", views.action_point_toggle, name="action_point_toggle"),
]
