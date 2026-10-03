from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("panel/", views.notification_panel, name="panel"),
    path("badge/", views.notification_badge, name="badge"),
    path("<int:pk>/read/", views.mark_read, name="mark_read"),
    path("read-all/", views.mark_all_read, name="mark_all_read"),
]
