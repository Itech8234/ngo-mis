"""Reusable generic CBVs for GHDI CRUD.

Some legacy views import ``GHCICreateView`` (with the letters H and C
transposed); keep an alias so those imports do not fail at runtime.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.views.generic import (
    CreateView as DjangoCreateView,
    DeleteView as DjangoDeleteView,
    DetailView as DjangoDetailView,
    ListView as DjangoListView,
    UpdateView as DjangoUpdateView,
)


class GHDIViewMixin(LoginRequiredMixin):
    title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", self.title or self.__class__.__name__.replace("View", ""))
        return context

    def handle_no_permission(self):
        # raise_exception is enabled for PermissionRequiredMixin, but that must
        # not convert an anonymous visitor into a 403 — they should be sent to
        # the login page. Authenticated users short on permissions still get 403.
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied(self.get_permission_denied_message())


class GHDIListView(GHDIViewMixin, PermissionRequiredMixin, DjangoListView):
    permission_required = ()
    raise_exception = True
    paginate_by = 25
    search_fields = ()
    template_name = "ghdi/generic_list.html"

    def get_permission_required(self):
        # permission_required may be a string
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required

    def get_search_terms(self):
        return (self.request.GET.get("q") or "").strip()

    def get_queryset(self):
        qs = super().get_queryset()
        term = self.get_search_terms()
        if term and self.search_fields:
            from django.db.models import Q

            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": term})
            qs = qs.filter(query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.get_search_terms()
        context["create_url"] = self._auto_create_url()
        if context["create_url"]:
            context["create_label"] = f"New {self.model._meta.verbose_name.title()}"
        return context

    def _auto_create_url(self):
        """Derive a create URL from the conventional app:model_create route."""
        if not self.model:
            return None
        model_name = self.model._meta.model_name
        perm = f"{self.model._meta.app_label}.add_{model_name}"
        if not self.request.user.has_perm(perm):
            return None
        try:
            from django.urls import reverse

            return reverse(f"{self.model._meta.app_label}:{model_name}_create")
        except Exception:
            return None


class GHDidDetailView(GHDIViewMixin, PermissionRequiredMixin, DjangoDetailView):
    permission_required = ()
    raise_exception = True
    template_name = "ghdi/generic_detail.html"

    def get_permission_required(self):
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required


class GHDIFormMixin:
    def form_valid(self, form):
        if hasattr(form.instance, "created_by_id") and form.instance._state.adding:
            form.instance.created_by = self.request.user
        if hasattr(form.instance, "updated_by_id"):
            form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        verb = "created" if form.instance._state.adding else "updated"
        messages.success(self.request, f"{form.instance._meta.verbose_name.title()} {verb} successfully.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the highlighted errors and try again.")
        return super().form_invalid(form)


class GHDIFormView(GHDIViewMixin, PermissionRequiredMixin, GHDIFormMixin, DjangoCreateView):
    """Create view (base implementation for all GHDI create views)."""

    permission_required = ()
    raise_exception = True
    template_name = "ghdi/generic_form.html"

    def get_permission_required(self):
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required


class GHDICreateView(GHDIFormView):
    """Create view (canonical name used across GHDI apps)."""


# Legacy aliases kept for transposed/old import names in older modules.
GHCICreateView = GHDICreateView
MHDICreateView = GHDICreateView


class GHDIUpdateView(GHDIViewMixin, PermissionRequiredMixin, GHDIFormMixin, DjangoUpdateView):
    """Update view."""

    permission_required = ()
    raise_exception = True
    template_name = "ghdi/generic_form.html"

    def get_permission_required(self):
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required


class GHDIDeleteView(GHDIViewMixin, PermissionRequiredMixin, DjangoDeleteView):
    permission_required = ()
    raise_exception = True
    success_message = "Deleted successfully."

    def get_permission_required(self):
        if isinstance(self.permission_required, str):
            return (self.permission_required,)
        return self.permission_required

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
