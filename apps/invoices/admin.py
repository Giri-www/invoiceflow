from django.contrib import admin

from .models import Invoice, InvoiceItem, InvoiceSequence


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "client", "status", "total", "issue_date", "due_date")
    list_filter = ("status", "issue_date", "due_date")
    search_fields = ("invoice_number", "client__name", "client__company")
    date_hierarchy = "issue_date"
    inlines = [InvoiceItemInline]


@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ("year", "current", "updated_at")
