from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.DocumentListView.as_view(), name="document_list"),
    path("new/", views.DocumentCreateView.as_view(), name="document_create"),
    path("<int:pk>/", views.DocumentDetailView.as_view(), name="document_detail"),
    path("<int:pk>/download/", views.document_download, name="document_download"),
    path("<int:pk>/versions/<int:version_id>/download/", views.document_version_download, name="document_version_download"),
    path("<int:pk>/edit/", views.DocumentUpdateView.as_view(), name="document_edit"),
    path("<int:pk>/versions/new/", views.document_new_version, name="document_version"),
]
