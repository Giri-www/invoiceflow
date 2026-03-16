from __future__ import annotations

from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context
from weasyprint import HTML


def _require_schema(task_request) -> str:
    schema_name = None
    try:
        schema_name = (task_request.headers or {}).get("schema_name")
    except Exception:
        schema_name = None
    if not schema_name:
        raise RuntimeError("Missing tenant schema context for task execution.")
    return schema_name


@shared_task(bind=True)
def generate_invoice_pdf(self, invoice_id: int) -> str:
    schema_name = _require_schema(self.request)
    from .models import Invoice

    with schema_context(schema_name):
        invoice = Invoice.objects.select_related("client", "created_by").prefetch_related(
            "items"
        ).get(pk=invoice_id)

        html = render_to_string("invoices/pdf.html", {"invoice": invoice})
        pdf_bytes = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()

        output_dir = Path(settings.MEDIA_ROOT) / "invoices" / "pdf"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{invoice.invoice_number}.pdf"
        output_path.write_bytes(pdf_bytes)
        return str(output_path)


@shared_task(bind=True)
def send_invoice_email(self, invoice_id: int) -> None:
    schema_name = _require_schema(self.request)
    from .models import Invoice

    with schema_context(schema_name):
        invoice = Invoice.objects.select_related("client", "created_by").prefetch_related(
            "items"
        ).get(pk=invoice_id)

        pdf_path = generate_invoice_pdf.apply(
            args=[invoice_id], headers={"schema_name": schema_name}
        ).get()

        subject = f"{invoice.invoice_number} from {invoice.created_by.full_name or 'InvoiceFlow'}"
        to_email = invoice.client.email
        if not to_email:
            return

        html_body = render_to_string("emails/invoice_email.html", {"invoice": invoice})
        message = EmailMessage(
            subject=subject,
            body=html_body,
            to=[to_email],
        )
        message.content_subtype = "html"
        message.attach_file(pdf_path)
        message.send(fail_silently=False)


@shared_task
def mark_overdue_invoices() -> int:
    Tenant = get_tenant_model()
    public_schema = get_public_schema_name()
    today = timezone.localdate()
    updated = 0

    with schema_context(public_schema):
        tenants = Tenant.objects.filter(is_active=True)

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            from apps.accounts.models import User
            from .models import Invoice

            qs = Invoice.objects.filter(status=Invoice.STATUS_SENT, due_date__lt=today)
            count = qs.update(status=Invoice.STATUS_OVERDUE, updated_at=timezone.now())
            if count:
                updated += count
                owner = (
                    User.objects.filter(role=User.ROLE_OWNER, is_active=True)
                    .order_by("date_joined")
                    .first()
                )
                if owner and owner.email:
                    send_mail(
                        subject="InvoiceFlow: invoices marked overdue",
                        message=f"{count} invoice(s) were marked overdue for {tenant.name}.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[owner.email],
                        fail_silently=True,
                    )

    return updated
