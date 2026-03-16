from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import secrets

from django.conf import settings
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone


Money = Decimal


class InvoiceSequence(models.Model):
    year = models.PositiveIntegerField(unique=True)
    current = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"{self.year}: {self.current}"


class Invoice(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_CANCELLED = "cancelled"

    STATUS = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    public_token = models.CharField(max_length=32, unique=True, blank=True)
    client = models.ForeignKey(
        "clients.Client", on_delete=models.PROTECT, related_name="invoices"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices_created",
    )
    status = models.CharField(choices=STATUS, default=STATUS_DRAFT, max_length=20)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)

    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]

    def __str__(self) -> str:
        return self.invoice_number or f"Invoice #{self.pk}"

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_totals(self, save: bool = True) -> None:
        items = list(self.items.all())
        subtotal = sum((item.amount for item in items), Decimal("0.00"))
        subtotal = self._money(subtotal)

        tax_rate = self.tax_rate or Decimal("0.00")
        tax_amount = self._money(subtotal * (tax_rate / Decimal("100")))

        discount = self.discount or Decimal("0.00")
        discount = self._money(discount)

        total = self._money(subtotal + tax_amount - discount)

        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total = total

        if save:
            self.save(update_fields=["subtotal", "tax_amount", "total", "updated_at"])

    def generate_invoice_number(self) -> str:
        year = int(self.issue_date.year if self.issue_date else timezone.now().year)

        with transaction.atomic():
            seq, _created = InvoiceSequence.objects.select_for_update().get_or_create(
                year=year, defaults={"current": 0}
            )
            seq.current += 1
            seq.save(update_fields=["current", "updated_at"])
            return f"INV-{year}-{seq.current:04d}"

    def mark_overdue(self, save: bool = True) -> bool:
        if self.status != self.STATUS_SENT:
            return False
        if self.due_date >= timezone.localdate():
            return False
        self.status = self.STATUS_OVERDUE
        if save:
            self.save(update_fields=["status", "updated_at"])
        return True

    def send_to_client(self) -> None:
        from django.db import connection

        from .tasks import send_invoice_email

        if self.status == self.STATUS_DRAFT:
            self.status = self.STATUS_SENT
            self.sent_at = timezone.now()
            self.save(update_fields=["status", "sent_at", "updated_at"])

        send_invoice_email.apply_async(args=[self.pk], headers={"schema_name": connection.schema_name})

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        if not self.public_token:
            self.public_token = secrets.token_hex(16)
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.description

    def save(self, *args, **kwargs):
        quantity = Decimal(self.quantity or 0)
        unit_price = Decimal(self.unit_price or 0)
        self.amount = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)
        self.invoice.calculate_totals(save=True)

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        result = super().delete(*args, **kwargs)
        invoice.calculate_totals(save=True)
        return result
