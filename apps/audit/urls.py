from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    path("", views.log_list, name="log_list"),
    path("feed/", views.feed, name="feed"),
    path("export/", views.export_csv, name="export"),
]
