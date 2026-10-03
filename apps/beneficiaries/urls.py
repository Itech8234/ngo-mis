from django.urls import path

from . import views

app_name = "beneficiaries"

urlpatterns = [
    path("", views.BeneficiaryListView.as_view(), name="beneficiary_list"),
    path("new/", views.BeneficiaryCreateView.as_view(), name="beneficiary_create"),
    path("<int:pk>/", views.BeneficiaryDetailView.as_view(), name="beneficiary_detail"),
    path("<int:pk>/edit/", views.BeneficiaryUpdateView.as_view(), name="beneficiary_edit"),
    path("<int:pk>/assistance/", views.assistance_create, name="assistance_create"),
]
