from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView
from weasyprint import HTML

from apps.accounts.mixins import RoleRequiredMixin

from .filters import InvoiceFilter
from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "invoices/list.html"
    context_object_name = "invoices"
    paginate_by = 10

    def get_queryset(self):
        qs = Invoice.objects.select_related("client").order_by("-issue_date", "-created_at")
        self.filterset = InvoiceFilter(self.request.GET, queryset=qs)
        qs = self.filterset.qs

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(invoice_number__icontains=q) | qs.filter(client__name__icontains=q)

        allowed = {"issue_date", "-issue_date", "due_date", "-due_date", "total", "-total"}
        sort = self.request.GET.get("sort") or "-issue_date"
        if sort in allowed:
            qs = qs.order_by(sort, "-created_at")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Invoices", "filterset": self.filterset})
        return context


class InvoiceCreateView(LoginRequiredMixin, View):
    template_name = "invoices/create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = InvoiceForm()
        formset = InvoiceItemFormSet(prefix="items")
        return render(
            request,
            self.template_name,
            {"page_title": "New Invoice", "form": form, "formset": formset},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST, prefix="items")
        action = request.POST.get("action") or "draft"

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    invoice = form.save(commit=False)
                    invoice.created_by = request.user
                    invoice.status = Invoice.STATUS_DRAFT
                    invoice.save()
                    formset.instance = invoice
                    formset.save()
                    invoice.calculate_totals(save=True)

                if action == "send":
                    invoice.send_to_client()
                    messages.success(request, "Invoice sent to the client.")
                else:
                    messages.success(request, "Invoice saved as draft.")
                return redirect("invoices:detail", pk=invoice.pk)
            except Exception:
                messages.error(request, "We couldn't create the invoice. Please try again.")
        else:
            messages.error(request, "Please fix the errors in the form.")

        return render(
            request,
            self.template_name,
            {"page_title": "New Invoice", "form": form, "formset": formset},
            status=400,
        )


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "invoices/detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return (
            Invoice.objects.select_related("client", "created_by")
            .prefetch_related("items")
            .all()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice: Invoice = context["invoice"]
        activity = [
            {"label": "Created", "at": invoice.created_at},
        ]
        if invoice.sent_at:
            activity.append({"label": "Sent to client", "at": invoice.sent_at})
        if invoice.viewed_at:
            activity.append({"label": "Viewed by client", "at": invoice.viewed_at})
        if invoice.paid_at:
            activity.append({"label": "Marked paid", "at": invoice.paid_at})
        if invoice.cancelled_at:
            activity.append({"label": "Cancelled", "at": invoice.cancelled_at})
        activity = sorted(activity, key=lambda e: e["at"] or timezone.now())

        context.update(
            {
                "page_title": invoice.invoice_number,
                "activity": activity,
                "public_link": reverse("invoices:public", kwargs={"token": invoice.public_token}),
            }
        )
        return context


class InvoiceUpdateView(LoginRequiredMixin, View):
    template_name = "invoices/create.html"

    def get_object(self, pk: int) -> Invoice:
        return get_object_or_404(
            Invoice.objects.select_related("client", "created_by").prefetch_related("items"),
            pk=pk,
        )

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = self.get_object(pk)
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice, prefix="items")
        return render(
            request,
            self.template_name,
            {"page_title": "Edit Invoice", "form": form, "formset": formset, "invoice": invoice},
        )

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = self.get_object(pk)
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice, prefix="items")
        action = request.POST.get("action") or "draft"

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    invoice = form.save()
                    formset.save()
                    invoice.calculate_totals(save=True)
                if action == "send":
                    invoice.send_to_client()
                    messages.success(request, "Invoice sent to the client.")
                else:
                    messages.success(request, "Invoice updated.")
                return redirect("invoices:detail", pk=invoice.pk)
            except Exception:
                messages.error(request, "We couldn't update the invoice. Please try again.")
        else:
            messages.error(request, "Please fix the errors in the form.")

        return render(
            request,
            self.template_name,
            {"page_title": "Edit Invoice", "form": form, "formset": formset, "invoice": invoice},
            status=400,
        )


class InvoiceDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = ["owner"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            invoice.delete()
            messages.success(request, "Invoice deleted.")
        except Exception:
            messages.error(request, "We couldn't delete that invoice.")
        return redirect("invoices:list")


class SendInvoiceView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = ["owner", "admin"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            invoice.send_to_client()
            messages.success(request, "Invoice sent to the client.")
        except Exception:
            messages.error(request, "We couldn't send the invoice. Please try again.")
        return redirect("invoices:detail", pk=invoice.pk)


class MarkPaidView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = ["owner", "admin"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.status == Invoice.STATUS_PAID:
            messages.info(request, "This invoice is already marked as paid.")
            return redirect("invoices:detail", pk=invoice.pk)

        invoice.status = Invoice.STATUS_PAID
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=["status", "paid_at", "updated_at"])
        messages.success(request, "Invoice marked as paid.")
        return redirect("invoices:detail", pk=invoice.pk)


class CancelInvoiceView(LoginRequiredMixin, RoleRequiredMixin, View):
    required_roles = ["owner", "admin"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.status = Invoice.STATUS_CANCELLED
        invoice.cancelled_at = timezone.now()
        invoice.save(update_fields=["status", "cancelled_at", "updated_at"])
        messages.success(request, "Invoice cancelled.")
        return redirect("invoices:detail", pk=invoice.pk)


class DownloadPDFView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        invoice = get_object_or_404(
            Invoice.objects.select_related("client", "created_by").prefetch_related("items"),
            pk=pk,
        )
        html = render_to_string("invoices/pdf.html", {"invoice": invoice})
        pdf = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()
        filename = f"{invoice.invoice_number}.pdf"
        return FileResponse(
            pdf,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )


class PublicInvoiceView(View):
    template_name = "invoices/public.html"

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        invoice = get_object_or_404(
            Invoice.objects.select_related("client", "created_by").prefetch_related("items"),
            public_token=token,
        )
        if not invoice.viewed_at:
            invoice.viewed_at = timezone.now()
            invoice.save(update_fields=["viewed_at", "updated_at"])
        return render(request, self.template_name, {"invoice": invoice})
