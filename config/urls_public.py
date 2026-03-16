# from django.http import HttpResponse
# from django.urls import path


# def landing(_request):
#     return HttpResponse("InvoiceFlow")


# urlpatterns = [path("", landing, name="public-landing")]

from django.shortcuts import render
from django.urls import include, path


def landing(request):
    return render(request, "public/landing.html")


urlpatterns = [
    path("", landing, name="public-landing"),

    path("accounts/" , include("apps.accounts.urls")),
    path("clients/" , include("apps.clients.urls")),
    path("invoices/" , include("apps.invoices.urls")),
]