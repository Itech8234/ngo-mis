"""Finance views: accounts, budgets, transactions, expenses, advances."""
from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.audit.middleware import log_action
from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView
from apps.core.services import WorkflowService, notify, notify_many

from .forms import (
    AccountForm, AdvanceForm, AdvanceRetireForm, BankReconciliationForm,
    BudgetForm, BudgetLineForm, ExpenseRequestForm, TransactionForm,
)
from .models import (
    Account, Advance, AdvanceRetirement, BankReconciliation, Budget,
    BudgetLine, ExpenseRequest, Transaction,
)

User = get_user_model()


class AccountListView(GHDIListView):
    model = Account
    permission_required = "finance.view_account"
    search_fields = ("code", "name")
    title = "Chart of Accounts"


class AccountCreateView(GHDICreateView):
    model = Account
    form_class = AccountForm
    permission_required = "finance.add_account"
    template_name = "finance/account_form.html"
    title = "New Account"


class AccountUpdateView(GHDIUpdateView):
    model = Account
    form_class = AccountForm
    permission_required = "finance.change_account"
    template_name = "finance/account_form.html"
    title = "Edit Account"


class BudgetListView(GHDIListView):
    model = Budget
    permission_required = "finance.view_budget"
    search_fields = ("name",)
    title = "Budgets"

    def get_queryset(self):
        return super().get_queryset().select_related("program", "project", "donor").prefetch_related("lines")


class BudgetDetailView(GHDidDetailView):
    model = Budget
    permission_required = "finance.view_budget"
    template_name = "finance/budget_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["line_form"] = BudgetLineForm()
        context["accounts"] = Account.objects.filter(category=Account.Category.EXPENSE, is_active=True)
        return context


class BudgetCreateView(GHDICreateView):
    model = Budget
    form_class = BudgetForm
    permission_required = "finance.add_budget"
    template_name = "finance/budget_form.html"
    title = "New Budget"


class BudgetUpdateView(GHDIUpdateView):
    model = Budget
    form_class = BudgetForm
    permission_required = "finance.change_budget"
    template_name = "finance/budget_form.html"
    title = "Edit Budget"


@login_required
@permission_required("finance.change_budget", raise_exception=True)
@db_transaction.atomic
@require_POST
def budget_add_line(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    form = BudgetLineForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        line = form.save(commit=False)
        line.budget = budget
        line.save()
        messages.success(request, "Budget line added.")
    return redirect("finance:budget_detail", pk)


@login_required
@permission_required("finance.change_budget", raise_exception=True)
@require_POST
def budget_remove_line(request, pk, line_id):
    get_object_or_404(BudgetLine, pk=line_id, budget_id=pk).delete()
    messages.success(request, "Budget line removed.")
    return redirect("finance:budget_detail", pk)


@login_required
@permission_required("finance.approve_budget", raise_exception=True)
@require_POST
def budget_submit(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    WorkflowService(budget, request.user).submit(
        notify_users=User.objects.filter(role__in=["exec", "admin"], is_active=True)
    )
    messages.success(request, "Budget submitted for approval.")
    return redirect("finance:budget_detail", pk)


@login_required
@permission_required("finance.approve_budget", raise_exception=True)
@require_POST
def budget_approve(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    WorkflowService(budget, request.user).approve(step="executive", note=request.POST.get("note", ""))
    messages.success(request, "Budget approved.")
    return redirect("finance:budget_detail", pk)


@login_required
@permission_required("finance.approve_budget", raise_exception=True)
@require_POST
def budget_reject(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    WorkflowService(budget, request.user).reject(note=request.POST.get("note", ""))
    messages.warning(request, "Budget returned for revision.")
    return redirect("finance:budget_detail", pk)


class TransactionListView(GHDIListView):
    model = Transaction
    permission_required = "finance.view_transaction"
    search_fields = ("reference", "description")
    title = "Transactions"
    template_name = "finance/transaction_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("account", "program", "project", "donor")
        direction = self.request.GET.get("direction")
        status = self.request.GET.get("status")
        if direction:
            qs = qs.filter(direction=direction)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["directions"] = Transaction.Direction.choices
        context["statuses"] = Transaction.Status.choices
        return context


class TransactionDetailView(GHDidDetailView):
    model = Transaction
    permission_required = "finance.view_transaction"
    template_name = "finance/transaction_detail.html"


class TransactionCreateView(GHDICreateView):
    model = Transaction
    form_class = TransactionForm
    permission_required = "finance.add_transaction"
    template_name = "finance/transaction_form.html"
    title = "New Transaction"

    def form_valid(self, form):
        if form.instance.direction == Transaction.Direction.EXPENSE:
            # Expense transactions enter the approval pipeline
            form.instance.status = "draft"
        response = super().form_valid(form)
        if form.instance.direction == Transaction.Direction.EXPENSE:
            WorkflowService(self.object, self.request.user).submit(
                notify_users=User.objects.filter(role__in=["fin", "exec"], is_active=True),
                step="finance",
            )
            messages.success(self.request, "Transaction recorded and submitted for approval.")
        return response


class TransactionUpdateView(GHDIUpdateView):
    model = Transaction
    form_class = TransactionForm
    permission_required = "finance.change_transaction"
    template_name = "finance/transaction_form.html"
    title = "Edit Transaction"

    def dispatch(self, request, *args, **kwargs):
        transaction = self.get_object()
        if not transaction.is_editable:
            messages.error(request, "Only draft or returned transactions can be edited.")
            return redirect("finance:transaction_detail", transaction.pk)
        return super().dispatch(request, *args, **kwargs)


@login_required
@permission_required("finance.approve_payment", raise_exception=True)
@db_transaction.atomic
@require_POST
def transaction_review(request, pk):
    """Finance review step: submitted -> under_review."""
    txn = get_object_or_404(Transaction, pk=pk)
    WorkflowService(txn, request.user).review(step="finance", note=request.POST.get("note", ""))
    messages.success(request, "Transaction moved to financial review.")
    return redirect("finance:transaction_detail", pk)


@login_required
@permission_required("finance.approve_payment", raise_exception=True)
@db_transaction.atomic
@require_POST
def transaction_approve(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    service = WorkflowService(txn, request.user)
    threshold = dj_settings.GHDI_EXEC_APPROVAL_THRESHOLD
    if txn.direction == Transaction.Direction.EXPENSE and float(txn.amount) >= threshold and not request.user.has_perm("dashboard.view_executive"):
        messages.error(request, f"Amounts of {threshold:,} NGN or above require Executive Director approval.")
        return redirect("finance:transaction_detail", pk)
    service.approve(step="executive" if float(txn.amount) >= threshold else "final",
                    note=request.POST.get("note", ""))
    log_action(request.user, "approve", module="finance", model="transaction",
               object_id=txn.pk, object_repr=str(txn), request=request)
    messages.success(request, "Transaction approved.")
    return redirect("finance:transaction_detail", pk)


@login_required
@permission_required("finance.approve_payment", raise_exception=True)
@require_POST
def transaction_reject(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    WorkflowService(txn, request.user).reject(note=request.POST.get("note", ""))
    messages.warning(request, "Transaction rejected.")
    return redirect("finance:transaction_detail", pk)


@login_required
@permission_required("finance.approve_payment", raise_exception=True)
@db_transaction.atomic
@require_POST
def transaction_pay(request, pk):
    """Mark an approved expense transaction as paid/completed."""
    txn = get_object_or_404(Transaction, pk=pk)
    if txn.status != "approved":
        messages.error(request, "Only approved transactions can be marked as paid.")
        return redirect("finance:transaction_detail", pk)
    WorkflowService(txn, request.user).complete(note=request.POST.get("note", "Payment processed"))
    messages.success(request, "Payment recorded as completed.")
    return redirect("finance:transaction_detail", pk)


@login_required
@permission_required("finance.approve_expense", raise_exception=True)
@db_transaction.atomic
@require_POST
def expense_review(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    WorkflowService(expense, request.user).review(step="supervisor", note=request.POST.get("note", ""))
    messages.success(request, "Request moved to financial review.")
    return redirect("finance:expense_detail", pk)


@login_required
@permission_required("finance.approve_expense", raise_exception=True)
@db_transaction.atomic
@require_POST
def expense_approve(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    WorkflowService(expense, request.user).approve(step="finance", note=request.POST.get("note", ""))
    messages.success(request, "Request approved. Ready for payment processing.")
    return redirect("finance:expense_detail", pk)


@login_required
@permission_required("finance.approve_expense", raise_exception=True)
@require_POST
def expense_reject(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    WorkflowService(expense, request.user).reject(note=request.POST.get("note", ""))
    messages.warning(request, "Request rejected.")
    return redirect("finance:expense_detail", pk)


@login_required
@permission_required("finance.approve_payment", raise_exception=True)
@db_transaction.atomic
@require_POST
def expense_pay(request, pk):
    """Record payment: completes the request and creates the expense transaction."""
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    if expense.status != "approved":
        messages.error(request, "Only approved requests can be paid.")
        return redirect("finance:expense_detail", pk)
    Transaction.objects.create(
        date=timezone.localdate(),
        description=f"Payment: {expense.purpose}",
        account=expense.account,
        direction=Transaction.Direction.EXPENSE,
        program=expense.program,
        project=expense.project,
        amount=expense.amount,
        currency=expense.currency,
        payment_method=expense.payment_method,
        requested_by=expense.requested_by,
        approved_by=request.user,
        status="approved",
    )
    expense.status = "completed"
    expense.paid_at = timezone.now()
    expense.save(update_fields=["status", "paid_at", "updated_at"])
    WorkflowService(expense, request.user)._record("payment", "complete", "Payment processed")
    if expense.requested_by:
        notify(
            expense.requested_by, "finance", "Payment processed",
            f"Your payment request “{expense.purpose}” has been paid.",
            url=expense.get_absolute_url(),
        )
    messages.success(request, "Payment processed and recorded in the ledger.")
    return redirect("finance:expense_detail", pk)


class ExpenseRequestListView(GHDIListView):
    model = ExpenseRequest
    permission_required = "finance.view_expenserequest"
    search_fields = ("purpose",)
    title = "Payment Requests"
    template_name = "finance/expense_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("requested_by", "project", "program")
        if not self.request.user.has_perm("finance.view_transaction"):
            qs = qs.filter(requested_by=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = ExpenseRequest.Status.choices
        return context


class ExpenseRequestDetailView(GHDidDetailView):
    model = ExpenseRequest
    permission_required = "finance.view_expenserequest"
    template_name = "finance/expense_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history"] = WorkflowService(self.object, self.request.user).history()
        return context


class ExpenseRequestCreateView(GHDICreateView):
    model = ExpenseRequest
    form_class = ExpenseRequestForm
    permission_required = "finance.add_expenserequest"
    template_name = "finance/expense_form.html"
    title = "Request Payment"

    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        response = super().form_valid(form)
        WorkflowService(self.object, self.request.user).submit(
            notify_users=User.objects.filter(role__in=["fin", "exec"], is_active=True),
            step="supervisor",
        )
        messages.success(self.request, "Payment request submitted for approval.")
        return response


class AdvanceListView(GHDIListView):
    model = Advance
    permission_required = "finance.view_advance"
    title = "Staff Advances"

    def get_queryset(self):
        return super().get_queryset().select_related("employee", "project")


class AdvanceCreateView(GHDICreateView):
    model = Advance
    form_class = AdvanceForm
    permission_required = "finance.add_advance"
    template_name = "finance/advance_form.html"
    title = "Issue Advance"


@login_required
@permission_required("finance.change_advance", raise_exception=True)
@db_transaction.atomic
@require_POST
def advance_retire(request, pk):
    advance = get_object_or_404(Advance, pk=pk)
    form = AdvanceRetireForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        amount = form.cleaned_data["amount"]
        if amount > advance.balance:
            messages.error(request, "Retirement amount exceeds the outstanding balance.")
        else:
            AdvanceRetirement.objects.create(
                advance=advance, amount=amount, note=form.cleaned_data.get("note", ""),
                recorded_by=request.user,
            )
            advance.retired_amount += amount
            advance.save()
            messages.success(request, "Advance retirement recorded.")
            return redirect("finance:advance_list")
    return render(request, "finance/advance_retire.html", {"form": form, "advance": advance, "page_title": "Retire Advance"})


@login_required
@permission_required("finance.view_bankreconciliation", raise_exception=True)
def reconciliation_list(request):
    items = BankReconciliation.objects.order_by("-period_end")[:50]
    return render(request, "finance/reconciliation_list.html", {"items": items, "page_title": "Bank Reconciliation"})


@login_required
@permission_required("finance.add_bankreconciliation", raise_exception=True)
@require_POST
def reconciliation_create(request):
    form = BankReconciliationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.reconciled_by = request.user
        record.save()
        messages.success(request, "Reconciliation recorded.")
        return redirect("finance:reconciliation_list")
    return render(request, "finance/reconciliation_form.html", {"form": form, "page_title": "New Reconciliation"})


@login_required
def finance_home(request):
    """Finance dashboard lives in the dashboard app; keep URL stable."""
    return redirect("dashboard:finance")




