from django.urls import path

from . import views

app_name = "assets"

urlpatterns = [
    path("", views.AssetListView.as_view(), name="asset_list"),
    path("new/", views.AssetCreateView.as_view(), name="asset_create"),
    path("<int:pk>/", views.AssetDetailView.as_view(), name="asset_detail"),
    path("<int:pk>/edit/", views.AssetUpdateView.as_view(), name="asset_edit"),
    path("<int:pk>/assign/", views.asset_assign, name="asset_assign"),
    path("<int:pk>/assignments/<int:assignment_id>/return/", views.asset_return, name="asset_return"),
]
