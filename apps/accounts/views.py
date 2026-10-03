"""Authentication and user management views."""
import logging

from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.cache import cache
from django.db import transaction
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.audit.middleware import log_action
from apps.core.middleware import get_client_ip
from apps.core.services import notify

from .forms import ProfileForm, UserAdminForm, UserCreateForm
from .models import Role, User

logger = logging.getLogger(__name__)


def _lockout_key(username, ip):
    return f"ghdi-login-fails:{username.lower()}:{ip}"


def login_view(request):
    """Login with brute-force lockout and audit logging."""
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    error = None
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        ip = get_client_ip(request)
        key = _lockout_key(username, ip)
        failures = cache.get(key, 0)
        if failures >= dj_settings.LOGIN_MAX_ATTEMPTS:
            error = (
                "Too many failed attempts. For security, this account is temporarily "
                "locked. Please try again later or contact the administrator."
            )
            log_action(None, "login_failed", module="accounts", object_repr=username, request=request)
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                cache.delete(key)
                log_action(user, "login", module="accounts", object_repr=user.username, request=request)
                next_url = request.POST.get("next") or request.GET.get("next")
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect("dashboard:index")
            failures += 1
            cache.set(key, failures, dj_settings.LOGIN_LOCKOUT_SECONDS)
            remaining = dj_settings.LOGIN_MAX_ATTEMPTS - failures
            log_action(None, "login_failed", module="accounts", object_repr=username, request=request)
            error = "Invalid email or password."
            if remaining <= 2:
                error += f" {remaining} attempt(s) remaining before temporary lockout."

    return render(request, "auth/login.html", {
        "error": error,
        "next": request.POST.get("next") or request.GET.get("next", ""),
    })


class PasswordResetViewG(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneG(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class PasswordResetConfirmG(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteG(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


@login_required
def logout_view(request):
    log_action(request.user, "logout", module="accounts", object_repr=request.user.username, request=request)
    logout(request)
    return redirect("accounts:login")


@login_required
def profile_view(request):
    from apps.hr.models import Employee

    employee = Employee.objects.filter(user=request.user).first()
    unread = request.user.notifications.filter(is_read=False)[:5]
    return render(
        request,
        "auth/profile.html",
        {"profile_user": request.user, "employee": employee, "recent_notifications": unread},
    )


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "auth/profile_form.html", {"form": form})


@login_required
def change_password(request):
    error = None
    if request.method == "POST":
        current = request.POST.get("current_password") or ""
        new1 = request.POST.get("new_password1") or ""
        new2 = request.POST.get("new_password2") or ""
        if not request.user.check_password(current):
            error = "Your current password is incorrect."
        elif new1 != new2:
            error = "The two new passwords do not match."
        else:
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError

            try:
                validate_password(new1, request.user)
            except ValidationError as exc:
                error = " ".join(exc.messages)
            else:
                request.user.set_password(new1)
                request.user.save(update_fields=["password"])
                update_session_auth_hash(request, request.user)
                log_action(
                    request.user, "password_change", module="accounts",
                    object_repr=request.user.username, request=request,
                )
                notify(
                    request.user, "security", "Password changed",
                    "Your GHDI account password was changed successfully.",
                    url="/app/profile/",
                )
                messages.success(request, "Your password has been changed.")
                return redirect("accounts:profile")
    return render(request, "auth/change_password.html", {"error": error})


@login_required
@permission_required("accounts.view_user", raise_exception=True)
def user_list(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    users = User.objects.all().order_by("first_name", "last_name")
    if query:
        users = users.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
            | Q(email__icontains=query) | Q(username__icontains=query)
        )
    if role:
        users = users.filter(role=role)
    return render(
        request,
        "auth/user_list.html",
        {"users": users, "roles": Role.choices, "query": query, "role": role},
    )


@login_required
@permission_required("accounts.add_user", raise_exception=True)
def user_create(request):
    """Create an active staff account and email a one-time password setup link."""
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        from apps.hr.models import Employee

        with transaction.atomic():
            user = form.save()
            employee = Employee.objects.create(
                user=user,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                position=user.job_title or "GHDI Staff",
                department=form.cleaned_data.get("department"),
            )
        email_sent = False
        email_captured_in_console = False
        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            setup_path = reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
            setup_url = request.build_absolute_uri(setup_path)
            login_url = request.build_absolute_uri(reverse("accounts:login"))
            logo_url = request.build_absolute_uri(static("img/garkuwa_logo.png"))
            full_name = user.get_full_name() or user.username
            send_mail(
                subject="Welcome to GHDI — set up your staff account",
                message=(
                    f"Hello {full_name},\n\n"
                    "Your GHDI staff account is ready. Use this secure, single-use link to set your password:\n"
                    f"{setup_url}\n\n"
                    f"Username: {user.email}\n"
                    f"Position: {user.job_title or 'GHDI Staff'}\n"
                    f"Staff ID: {employee.employee_id}\n"
                    f"Department: {employee.department.name if employee.department else 'To be assigned'}\n"
                    f"Sign in: {login_url}\n\n"
                    "For your security, do not share this link. If you did not expect this account, contact your administrator.\n\n"
                    "Garkuwa Humanitarian and Development Initiative\n"
                ),
                html_message=render_to_string("emails/staff_welcome.html", {
                    "full_name": full_name,
                    "email": user.email,
                    "job_title": user.job_title,
                    "employee_id": employee.employee_id,
                    "department": employee.department.name if employee.department else "To be assigned",
                    "setup_url": setup_url,
                    "login_url": login_url,
                    "logo_url": logo_url,
                }),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            email_captured_in_console = (
                dj_settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"
            )
            email_sent = not email_captured_in_console
        except Exception:
            # Keep account creation intact if SMTP is temporarily unavailable;
            # never include credentials or provider details in the UI.
            email_sent = False
            logger.exception("Staff password setup email could not be sent for user id %s", user.pk)
        log_action(request.user, "staff_account_created", module="accounts", object_id=user.pk,
                   object_repr=user.username, request=request)
        if email_sent:
            messages.success(request, f"Account created for {user.full_name}. A password setup link was sent to {user.email}.")
        elif email_captured_in_console:
            messages.warning(request, "Account created, but this development mail backend only writes the setup email to the server console; it does not deliver email. Configure EMAIL_BACKEND and SMTP credentials to send it to the staff member.")
        else:
            messages.warning(request, f"Account created for {user.full_name}, but the setup email could not be sent. Check mail settings and resend a password reset link.")
        return redirect("accounts:user_list")
    return render(request, "auth/user_form.html", {"form": form, "page_title": "Create staff account"})


@login_required
@permission_required("accounts.change_user", raise_exception=True)
@require_POST
def resend_staff_setup_email(request, pk):
    """Send a fresh single-use setup link to a staff account without a password."""
    user = get_object_or_404(User, pk=pk)
    if user.has_usable_password():
        messages.info(request, "This account already has a password. Use Reset password to issue a recovery link.")
        return redirect("accounts:user_list")
    employee = getattr(user, "employee_profile", None)
    try:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        setup_url = request.build_absolute_uri(
            reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        )
        login_url = request.build_absolute_uri(reverse("accounts:login"))
        full_name = user.get_full_name() or user.username
        send_mail(
            subject="Welcome to GHDI — set up your staff account",
            message=f"Hello {full_name},\n\nSet your password using this single-use link: {setup_url}\n\nSign in: {login_url}\nStaff ID: {employee.employee_id if employee else 'To be assigned'}\n\nFor your security, do not share this link.",
            html_message=render_to_string("emails/staff_welcome.html", {
                "full_name": full_name, "email": user.email, "job_title": user.job_title,
                "employee_id": employee.employee_id if employee else "To be assigned",
                "department": employee.department.name if employee and employee.department else "To be assigned",
                "setup_url": setup_url, "login_url": login_url,
                "logo_url": request.build_absolute_uri(static("img/garkuwa_logo.png")),
            }),
            from_email=None, recipient_list=[user.email], fail_silently=False,
        )
        if dj_settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
            messages.warning(request, "The setup email was written to the development server console only. Configure SMTP to deliver it to the staff member.")
        else:
            messages.success(request, f"A new setup email was sent to {user.email}.")
    except Exception:
        logger.exception("Staff password setup email could not be resent for user id %s", user.pk)
        messages.error(request, "The setup email could not be sent. Check the mail server configuration and try again.")
    log_action(request.user, "staff_setup_email_resent", module="accounts", object_id=user.pk,
               object_repr=user.username, request=request)
    return redirect("accounts:user_list")


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserAdminForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        old_role = User.objects.get(pk=user.pk).role
        form.save()
        if old_role != user.role:
            log_action(
                request.user, "permission_change", module="accounts",
                object_id=user.pk, object_repr=user.username,
                changes={"role": {"from": old_role, "to": user.role}}, request=request,
            )
        messages.success(request, f"Account for {user.full_name} updated.")
        return redirect("accounts:user_list")
    return render(request, "auth/user_form.html", {"form": form, "user_obj": user})


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def user_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = AdminPasswordChangeForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(
            request.user, "password_change", module="accounts",
            object_id=user.pk, object_repr=user.username, request=request,
        )
        notify(user, "security", "Your password was reset by an administrator",
               "An administrator set a new password for your GHDI account.")
        messages.success(request, f"Password updated for {user.full_name}.")
        return redirect("accounts:user_list")
    return render(request, "auth/user_password.html", {"form": form, "user_obj": user})

