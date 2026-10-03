from django.urls import path

from . import views

app_name = "partners"

urlpatterns = [
    # Donors
    path("donors/", views.DonorListView.as_view(), name="donor_list"),
    path("donors/new/", views.DonorCreateView.as_view(), name="donor_create"),
    path("donors/<int:pk>/", views.DonorDetailView.as_view(), name="donor_detail"),
    path("donors/<int:pk>/edit/", views.DonorUpdateView.as_view(), name="donor_edit"),
    # Grants
    path("grants/", views.GrantListView.as_view(), name="grant_list"),
    path("grants/new/", views.GrantCreateView.as_view(), name="grant_create"),
    path("grants/<int:pk>/", views.GrantDetailView.as_view(), name="grant_detail"),
    path("grants/<int:pk>/edit/", views.GrantUpdateView.as_view(), name="grant_edit"),
    # Partners
    path("orgs/", views.PartnerListView.as_view(), name="partner_list"),
    path("orgs/new/", views.PartnerCreateView.as_view(), name="partner_create"),
    path("orgs/<int:pk>/", views.PartnerDetailView.as_view(), name="partner_detail"),
    path("orgs/<int:pk>/edit/", views.PartnerUpdateView.as_view(), name="partner_edit"),
]
