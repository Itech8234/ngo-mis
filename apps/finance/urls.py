from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.finance_home, name="dashboard"),
    # Accounts
    path("accounts/", views.AccountListView.as_view(), name="account_list"),
    path("accounts/new/", views.AccountCreateView.as_view(), name="account_create"),
    path("accounts/<int:pk>/edit/", views.AccountUpdateView.as_view(), name="account_edit"),
    # Budgets
    path("budgets/", views.BudgetListView.as_view(), name="budget_list"),
    path("budgets/new/", views.BudgetCreateView.as_view(), name="budget_create"),
    path("budgets/<int:pk>/", views.BudgetDetailView.as_view(), name="budget_detail"),
    path("budgets/<int:pk>/edit/", views.BudgetUpdateView.as_view(), name="budget_edit"),
    path("budgets/<int:pk>/lines/add/", views.budget_add_line, name="budget_add_line"),
    path("budgets/<int:pk>/lines/<int:line_id>/remove/", views.budget_remove_line, name="budget_remove_line"),
    path("budgets/<int:pk>/submit/", views.budget_submit, name="budget_submit"),
    path("budgets/<int:pk>/approve/", views.budget_approve, name="budget_approve"),
    path("budgets/<int:pk>/reject/", views.budget_reject, name="budget_reject"),
    # Transactions
    path("transactions/", views.TransactionListView.as_view(), name="transaction_list"),
    path("transactions/new/", views.TransactionCreateView.as_view(), name="transaction_create"),
    path("transactions/<int:pk>/", views.TransactionDetailView.as_view(), name="transaction_detail"),
    path("transactions/<int:pk>/edit/", views.TransactionUpdateView.as_view(), name="transaction_edit"),
    path("transactions/<int:pk>/review/", views.transaction_review, name="transaction_review"),
    path("transactions/<int:pk>/approve/", views.transaction_approve, name="transaction_approve"),
    path("transactions/<int:pk>/reject/", views.transaction_reject, name="transaction_reject"),
    path("transactions/<int:pk>/pay/", views.transaction_pay, name="transaction_pay"),
    # Payment requests
    path("payments/", views.ExpenseRequestListView.as_view(), name="expense_list"),
    path("payments/new/", views.ExpenseRequestCreateView.as_view(), name="expense_create"),
    path("payments/<int:pk>/", views.ExpenseRequestDetailView.as_view(), name="expense_detail"),
    path("payments/<int:pk>/review/", views.expense_review, name="expense_review"),
    path("payments/<int:pk>/approve/", views.expense_approve, name="expense_approve"),
    path("payments/<int:pk>/reject/", views.expense_reject, name="expense_reject"),
    path("payments/<int:pk>/pay/", views.expense_pay, name="expense_pay"),
    # Advances
    path("advances/", views.AdvanceListView.as_view(), name="advance_list"),
    path("advances/new/", views.AdvanceCreateView.as_view(), name="advance_create"),
    path("advances/<int:pk>/retire/", views.advance_retire, name="advance_retire"),
    # Reconciliation
    path("reconciliation/", views.reconciliation_list, name="reconciliation_list"),
    path("reconciliation/new/", views.reconciliation_create, name="reconciliation_create"),
]
