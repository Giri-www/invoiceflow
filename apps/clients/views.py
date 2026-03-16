from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.accounts.mixins import RoleRequiredMixin
from apps.invoices.models import Invoice

from .forms import ClientForm
from .models import Client


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "clients/list.html"
    context_object_name = "clients"
    paginate_by = 12

    def get_queryset(self):
        qs = Client.objects.all().order_by("-created_at")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(company__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
            )

        qs = qs.annotate(
            total_invoiced=Sum("invoices__total"),
            outstanding=Sum(
                "invoices__total",
                filter=Q(invoices__status__in=[Invoice.STATUS_SENT, Invoice.STATUS_OVERDUE]),
            ),
        )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Clients"})
        return context


class ClientCreateView(LoginRequiredMixin, View):
    template_name = "clients/_client_form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = ClientForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, "Client added.")
            if getattr(request, "htmx", False):
                response = HttpResponse("")
                response["HX-Trigger"] = json.dumps(
                    {
                        "toast": {"message": "Client added.", "type": "success"},
                        "modalClose": {"id": "client-modal"},
                    }
                )
                return response
            return redirect("clients:list")
        messages.error(request, "Please fix the errors in the form.")
        return render(request, self.template_name, {"form": form}, status=400)


class ClientUpdateView(LoginRequiredMixin, View):
    template_name = "clients/edit.html"

    def get_object(self, pk: int) -> Client:
        return get_object_or_404(Client, pk=pk)

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        client = self.get_object(pk)
        form = ClientForm(instance=client)
        return render(request, self.template_name, {"page_title": "Edit Client", "form": form, "client": client})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        client = self.get_object(pk)
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client updated.")
            return redirect("clients:list")
        messages.error(request, "Please fix the errors in the form.")
        return render(
            request,
            self.template_name,
            {"page_title": "Edit Client", "form": form, "client": client},
            status=400,
        )


class ClientDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = ["owner", "admin"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        client = get_object_or_404(Client, pk=pk)
        try:
            client.delete()
            messages.success(request, "Client deleted.")
        except Exception:
            messages.error(request, "We couldn't delete that client.")
        return redirect("clients:list")


class ClientSearchOptionsView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        q = (request.GET.get("q") or "").strip()
        qs = Client.objects.all().order_by("name")[:50]
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q))

        options = ['<option value="">Select a client…</option>']
        for c in qs:
            label = f"{c.name} ({c.company})" if c.company else c.name
            options.append(f'<option value="{c.pk}">{label}</option>')
        return HttpResponse("".join(options))
