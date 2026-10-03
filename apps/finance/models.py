"""Finance module: chart of accounts, budgets, transactions, expenses, advances."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import OwnedModel, WorkflowMixin
from apps.core.validators import FileSizeValidator, FileTypeValidator


class Account(models.Model):
    """Chart of accounts entry."""

    class Category(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        EQUITY = "equity", "Equity"

    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=12, choices=Category.choices, db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"


class BudgetStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REVISED = "revised", "Revised"
    CLOSED = "closed", "Closed"
    REJECTED = "rejected", "Rejected"


class Budget(WorkflowMixin, OwnedModel):
    """Program / project / annual budget with line items and variance analysis."""

    name = models.CharField(max_length=200)
    fiscal_year = models.PositiveIntegerField(default=timezone.localdate().year)
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="budgets")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="budgets")
    donor = models.ForeignKey("partners.Donor", null=True, blank=True, on_delete=models.SET_NULL, related_name="budgets")
    notes = models.TextField(blank=True)
    revision = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("-fiscal_year", "name")
        permissions = [("approve_budget", "Can approve budgets")]

    @property
    def total_amount(self):
        return sum(line.amount for line in self.lines.all())

    @property
    def total_actual(self):
        return sum(line.actual for line in self.lines.all())

    @property
    def utilisation(self):
        total = self.total_amount
        if not total:
            return 0
        return min(100.0, float(self.total_actual) / float(total) * 100)

    def get_absolute_url(self):
        return reverse("finance:budget_detail", args=[self.pk])

    def __str__(self):
        return f"{self.name} (FY{self.fiscal_year})"


class BudgetLine(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="budget_lines")
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ("account__code",)

    @property
    def actual(self):
        from apps.finance.models import Transaction

        return Transaction.objects.filter(
            account=self.account,
            direction=Transaction.Direction.EXPENSE,
            status=Transaction.Status.APPROVED,
        ).aggregate(t=models.Sum("amount"))["t"] or 0

    @property
    def variance(self):
        return float(self.amount) - float(self.actual)

    def __str__(self):
        return f"{self.budget.name}: {self.account.name}"


class Transaction(WorkflowMixin, OwnedModel):
    """Financial transaction: income or expense with full approval trail."""

    class Direction(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CHEQUE = "cheque", "Cheque"
        MOBILE_MONEY = "mobile_money", "Mobile Money"

    class Category(models.TextChoices):
        STAFF = "staff", "Staff Cost"
        TRAVEL = "travel", "Travel & Transport"
        ACTIVITY = "activity", "Activity / Program"
        EQUIPMENT = "equipment", "Equipment"
        RENT = "rent", "Rent & Utilities"
        TRAINING = "training", "Training"
        ADMIN = "admin", "Administration"
        OTHER = "other", "Other"

    date = models.DateField(default=timezone.localdate, db_index=True)
    reference = models.CharField(max_length=24, unique=True, editable=False)
    description = models.CharField(max_length=255)
    account = models.ForeignKey(Account, null=True, on_delete=models.SET_NULL, related_name="transactions")
    direction = models.CharField(max_length=8, choices=Direction.choices, db_index=True)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.OTHER, blank=True)
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    donor = models.ForeignKey("partners.Donor", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    payment_method = models.CharField(max_length=15, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    document = models.FileField(upload_to="transactions/", blank=True, validators=[FileSizeValidator(), FileTypeValidator()])

    class Meta:
        ordering = ("-date", "-created_at")
        permissions = [
            ("approve_payment", "Can approve payments"),
            ("approve_expense", "Can approve expenses"),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            prefix = f"TRN-{timezone.localdate():%Y%m}-"
            count = Transaction.objects.filter(reference__startswith=prefix).count() + 1
            self.reference = f"{prefix}{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("finance:transaction_detail", args=[self.pk])

    def __str__(self):
        return f"{self.reference} {self.direction} {self.amount} {self.currency}"


class ExpenseRequest(WorkflowMixin, OwnedModel):
    """Expense/payment request following: staff -> supervisor -> finance -> ED -> payment."""

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="expense_requests")
    purpose = models.CharField(max_length=255)
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="expense_requests")
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="expense_requests")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="expense_requests")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    date_needed = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=15, choices=Transaction.PaymentMethod.choices, default=Transaction.PaymentMethod.BANK_TRANSFER)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def get_absolute_url(self):
        return reverse("finance:expense_detail", args=[self.pk])

    def __str__(self):
        return f"{self.purpose} ({self.amount} {self.currency})"


class Advance(models.Model):
    """Staff advance with retirement tracking."""

    class Status(models.TextChoices):
        OUTSTANDING = "outstanding", "Outstanding"
        PARTIALLY_RETIRED = "partially_retired", "Partially Retired"
        RETIRED = "retired", "Retired"

    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="advances")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date_issued = models.DateField(default=timezone.localdate)
    purpose = models.CharField(max_length=255, blank=True)
    retired_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OUTSTANDING, db_index=True)
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="advances")

    class Meta:
        ordering = ("-date_issued",)

    @property
    def balance(self):
        return self.amount - self.retired_amount

    def save(self, *args, **kwargs):
        if self.retired_amount >= self.amount:
            self.status = self.Status.RETIRED
        elif self.retired_amount > 0:
            self.status = self.Status.PARTIALLY_RETIRED
        else:
            self.status = self.Status.OUTSTANDING
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("finance:advance_list")

    def __str__(self):
        return f"Advance {self.employee.full_name} {self.amount}"


class AdvanceRetirement(models.Model):
    advance = models.ForeignKey(Advance, on_delete=models.CASCADE, related_name="retirements")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.advance} retired {self.amount}"


class BankReconciliation(models.Model):
    account_name = models.CharField(max_length=160)
    period_end = models.DateField(db_index=True)
    book_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    reconciled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def difference(self):
        return float(self.book_balance) - float(self.bank_balance)

    class Meta:
        ordering = ("-period_end",)

    def __str__(self):
        return f"{self.account_name} - {self.period_end}"


