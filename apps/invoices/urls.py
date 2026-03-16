from django.urls import path

from .views import (
    CancelInvoiceView,
    DownloadPDFView,
    InvoiceCreateView,
    InvoiceDeleteView,
    InvoiceDetailView,
    InvoiceListView,
    InvoiceUpdateView,
    MarkPaidView,
    PublicInvoiceView,
    SendInvoiceView,
)

app_name = "invoices"

urlpatterns = [
    path("", InvoiceListView.as_view(), name="list"),
    path("new/", InvoiceCreateView.as_view(), name="create"),
    path("<int:pk>/", InvoiceDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InvoiceUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", InvoiceDeleteView.as_view(), name="delete"),
    path("<int:pk>/send/", SendInvoiceView.as_view(), name="send"),
    path("<int:pk>/paid/", MarkPaidView.as_view(), name="mark_paid"),
    path("<int:pk>/cancel/", CancelInvoiceView.as_view(), name="cancel"),
    path("<int:pk>/pdf/", DownloadPDFView.as_view(), name="pdf"),
    path("public/<str:token>/", PublicInvoiceView.as_view(), name="public"),
]
