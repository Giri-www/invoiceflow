from django.http import HttpResponse
from django.urls import path


def landing(_request):
    return HttpResponse("InvoiceFlow")


urlpatterns = [path("", landing, name="public-landing")]
