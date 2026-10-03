from django.urls import path

from . import views

app_name = "risk"

urlpatterns = [
    path("risks/", views.RiskListView.as_view(), name="risk_list"),
    path("risks/new/", views.RiskCreateView.as_view(), name="risk_create"),
    path("risks/<int:pk>/", views.RiskDetailView.as_view(), name="risk_detail"),
    path("risks/<int:pk>/edit/", views.RiskUpdateView.as_view(), name="risk_edit"),
    path("incidents/", views.IncidentListView.as_view(), name="incident_list"),
    path("incidents/new/", views.IncidentCreateView.as_view(), name="incident_create"),
    path("incidents/<int:pk>/", views.IncidentDetailView.as_view(), name="incident_detail"),
    path("incidents/<int:pk>/edit/", views.IncidentUpdateView.as_view(), name="incident_edit"),
]
