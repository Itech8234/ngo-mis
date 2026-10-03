from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.IndicatorListView.as_view(), name="indicator_list"),
    path("indicators/new/", views.IndicatorCreateView.as_view(), name="indicator_create"),
    path("indicators/<int:pk>/", views.IndicatorDetailView.as_view(), name="indicator_detail"),
    path("indicators/<int:pk>/edit/", views.IndicatorUpdateView.as_view(), name="indicator_edit"),
    path("indicator-updates/new/", views.indicator_update_create, name="indicator_update_create"),
    path("indicators/<int:pk>/updates/new/", views.indicator_update_create, name="indicator_update_for"),
    path("reports/", views.ReportListView.as_view(), name="report_list"),
    path("reports/new/", views.ReportCreateView.as_view(), name="report_create"),
    path("reports/<int:pk>/", views.ReportDetailView.as_view(), name="report_detail"),
    path("reports/<int:pk>/edit/", views.ReportUpdateView.as_view(), name="report_edit"),
    path("reports/<int:pk>/review/", views.report_review, name="report_review"),
    path("feedback/", views.FeedbackListView.as_view(), name="feedback_list"),
    path("feedback/new/", views.FeedbackCreateView.as_view(), name="feedbackcase_create"),
    path("feedback/<int:pk>/", views.FeedbackDetailView.as_view(), name="feedback_detail"),
    path("feedback/<int:pk>/review/", views.feedback_review, name="feedback_review"),
]
