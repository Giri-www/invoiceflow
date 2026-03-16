from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


class RoleRequiredMixin(AccessMixin):
    required_roles: list[str] = []

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.required_roles and getattr(request.user, "role", None) not in self.required_roles:
            messages.error(request, "You don't have permission to access that page.")
            return redirect("dashboard:index")

        return super().dispatch(request, *args, **kwargs)
