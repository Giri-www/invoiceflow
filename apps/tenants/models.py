from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Tenant(TenantMixin):
    PLAN_FREE = "free"
    PLAN_PRO = "pro"
    PLAN_BUSINESS = "business"

    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_PRO, "Pro"),
        (PLAN_BUSINESS, "Business"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="tenant_logos/", null=True, blank=True)
    plan = models.CharField(choices=PLAN_CHOICES, default=PLAN_FREE, max_length=20)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    auto_create_schema = True

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Domain(DomainMixin):
    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain
