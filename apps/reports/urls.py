from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("hr/", views.hr_summary, name="hr_summary"),
    path("finance/", views.finance_summary, name="finance_summary"),
    path("programs/", views.program_summary, name="program_summary"),
    path("beneficiaries/", views.beneficiary_summary, name="beneficiary_summary"),
    path("indicators/", views.indicator_summary, name="indicator_summary"),
    path("donors/", views.donor_portfolio, name="donor_portfolio"),
]
