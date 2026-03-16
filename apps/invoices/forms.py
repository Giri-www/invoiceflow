from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "issue_date", "due_date", "tax_rate", "discount", "notes", "terms"]
        widgets = {
            "client": forms.Select(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "tax_rate": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}
            ),
            "discount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "terms": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["description", "quantity", "unit_price", "amount"]
        widgets = {
            "description": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Description"}
            ),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}
            ),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "readonly": "readonly"}
            ),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
)
