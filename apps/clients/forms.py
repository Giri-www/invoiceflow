from __future__ import annotations

from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "company", "email", "phone", "tax_id", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Client name"}),
            "company": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Company (optional)"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email (optional)"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone (optional)"}
            ),
            "tax_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Tax ID (optional)"}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Address (optional)"}
            ),
        }
