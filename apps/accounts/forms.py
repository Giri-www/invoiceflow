from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), strip=False
    )

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise forms.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is disabled.")
            cleaned["user"] = user
        return cleaned


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        strip=False,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        strip=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "role",
            "avatar",
            "is_active",
            "is_staff",
        ]


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
