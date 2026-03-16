from __future__ import annotations

import json
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.generic import TemplateView

from apps.invoices.models import Invoice


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        paid_qs = Invoice.objects.filter(status=Invoice.STATUS_PAID)
        total_revenue = paid_qs.aggregate(total=Sum("total")).get("total") or 0
        paid_count = paid_qs.count()

        pending_qs = Invoice.objects.filter(status__in=[Invoice.STATUS_SENT, Invoice.STATUS_OVERDUE])
        pending_amount = pending_qs.aggregate(total=Sum("total")).get("total") or 0

        overdue_count = Invoice.objects.filter(status=Invoice.STATUS_OVERDUE).count()

        recent_invoices = (
            Invoice.objects.select_related("client")
            .order_by("-issue_date", "-created_at")[:10]
        )

        now = timezone.localdate()
        start_month = date(now.year, now.month, 1)
        labels = []
        values = []
        for i in range(5, -1, -1):
            m = (start_month.month - i - 1) % 12 + 1
            y = start_month.year + ((start_month.month - i - 1) // 12)
            labels.append(f"{y}-{m:02d}")
            values.append(0)

        monthly = (
            paid_qs.annotate(month=TruncMonth("paid_at"))
            .values("month")
            .annotate(total=Sum("total"))
            .order_by("month")
        )
        index = {label: idx for idx, label in enumerate(labels)}
        for row in monthly:
            if not row["month"]:
                continue
            key = row["month"].date().strftime("%Y-%m")
            if key in index:
                values[index[key]] = float(row["total"] or 0)

        context.update(
            {
                "page_title": "Dashboard",
                "total_revenue": total_revenue,
                "paid_count": paid_count,
                "pending_amount": pending_amount,
                "overdue_count": overdue_count,
                "recent_invoices": recent_invoices,
                "monthly_labels_json": json.dumps(labels),
                "monthly_values_json": json.dumps(values),
            }
        )
        return context
