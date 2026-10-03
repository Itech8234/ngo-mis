from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("password/change/", views.change_password, name="change_password"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/setup-email/", views.resend_staff_setup_email, name="user_setup_email"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/password/", views.user_password, name="user_password"),
    # Django password reset (templates under templates/registration/)
    path("password-reset/", views.PasswordResetViewG.as_view(), name="password_reset"),
    path("password-reset/done/", views.PasswordResetDoneG.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.PasswordResetConfirmG.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.PasswordResetCompleteG.as_view(), name="password_reset_complete"),
]
