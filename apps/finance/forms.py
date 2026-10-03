"""Finance forms."""
from django import forms

from .models import (
    Account, Advance, BankReconciliation, Budget, BudgetLine, ExpenseRequest,
    Transaction,
)


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["code", "name", "category", "parent", "is_active"]


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["name", "fiscal_year", "program", "project", "donor", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ["account", "description", "amount"]


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "date", "description", "account", "direction", "category",
            "program", "project", "donor", "amount", "currency",
            "payment_method", "document",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(),
        }


class ExpenseRequestForm(forms.ModelForm):
    class Meta:
        model = ExpenseRequest
        fields = [
            "purpose", "account", "program", "project", "amount",
            "currency", "date_needed", "payment_method",
        ]
        widgets = {"date_needed": forms.DateInput(attrs={"type": "date"})}


class AdvanceForm(forms.ModelForm):
    class Meta:
        model = Advance
        fields = ["employee", "amount", "date_issued", "purpose", "project"]
        widgets = {"date_issued": forms.DateInput(attrs={"type": "date"})}


class AdvanceRetireForm(forms.Form):
    amount = forms.DecimalField(min_value=0.01, widget=forms.NumberInput(attrs={"class": "input", "step": "0.01"}))
    note = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "input"}))


class BankReconciliationForm(forms.ModelForm):
    class Meta:
        model = BankReconciliation
        fields = ["account_name", "period_end", "book_balance", "bank_balance", "notes"]
        widgets = {"period_end": forms.DateInput(attrs={"type": "date"})}
