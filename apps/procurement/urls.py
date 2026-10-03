from django.urls import path

from . import views

app_name = "procurement"

urlpatterns = [
    path("", views.RequestListView.as_view(), name="request_list"),
    path("new/", views.RequestCreateView.as_view(), name="request_create"),
    path("<int:pk>/", views.RequestDetailView.as_view(), name="request_detail"),
    path("<int:pk>/edit/", views.RequestUpdateView.as_view(), name="request_edit"),
    path("<int:pk>/review/", views.request_review, name="request_review"),
    path("<int:pk>/quotations/add/", views.quotation_add, name="quotation_add"),
    path("<int:pk>/quotations/<int:quotation_id>/select/", views.quotation_select, name="quotation_select"),
    path("<int:pk>/pos/new/", views.po_create, name="po_create"),
    path("vendors/", views.VendorListView.as_view(), name="vendor_list"),
    path("vendors/new/", views.VendorCreateView.as_view(), name="vendor_create"),
    path("vendors/<int:pk>/", views.VendorDetailView.as_view(), name="vendor_detail"),
    path("vendors/<int:pk>/edit/", views.VendorUpdateView.as_view(), name="vendor_edit"),
    path("purchase-orders/", views.PurchaseOrderListView.as_view(), name="po_list"),
    path("purchase-orders/<int:pk>/", views.PurchaseOrderDetailView.as_view(), name="po_detail"),
    path("purchase-orders/<int:pk>/status/", views.po_update_status, name="po_status"),
]
