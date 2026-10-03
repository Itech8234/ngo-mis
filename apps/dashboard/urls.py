from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("executive/", views.executive, name="executive"),
    path("admin/", views.admin_dashboard, name="admin"),
    path("hr/", views.hr_dashboard, name="hr"),
    path("program/", views.program_dashboard, name="program"),
    path("finance/", views.finance_dashboard, name="finance"),
    path("meal/", views.meal_dashboard, name="meal"),
    path("procurement/", views.procurement_dashboard, name="procurement"),
    path("staff/", views.staff_dashboard, name="staff"),
]
