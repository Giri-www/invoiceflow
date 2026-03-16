from __future__ import annotations

import django_filters

from .models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    issue_date_after = django_filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issue_date_before = django_filters.DateFilter(field_name="issue_date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["status", "client", "issue_date_after", "issue_date_before"]
