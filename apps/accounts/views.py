from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .forms import LoginForm, RegisterForm


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("dashboard:index")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            messages.success(request, "Welcome back.")
            return redirect("dashboard:index")
        return render(request, self.template_name, {"form": form}, status=400)


class RegisterView(View):
    template_name = "accounts/register.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("dashboard:index")
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account is ready.")
            return redirect("dashboard:index")
        return render(request, self.template_name, {"form": form}, status=400)


class LogoutView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        logout(request)
        messages.success(request, "Signed out.")
        return redirect(reverse("accounts:login"))
