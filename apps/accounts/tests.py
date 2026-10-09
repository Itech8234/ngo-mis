import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role


class StaffAccountActivationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="account-admin", email="admin@example.org", password="SafePass123!",
        )
        self.client.force_login(self.admin)

    def test_created_staff_sets_password_from_email_then_logs_in(self):
        response = self.client.post(reverse("accounts:user_create"), {
            "first_name": "Amina", "last_name": "Staff", "email": "amina@example.org",
            "username": "amina-staff", "role": Role.STAFF, "job_title": "Field Officer",
            "department": "",
        })
        self.assertRedirects(response, reverse("accounts:user_list"))
        staff = get_user_model().objects.get(email="amina@example.org")
        self.assertTrue(staff.is_active)
        self.assertFalse(staff.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("amina@example.org", mail.outbox[0].body)

        setup_path = re.search(r"http://testserver(/reset/[^\s<]+)", mail.outbox[0].body).group(1)
        setup_response = self.client.get(setup_path, follow=True)
        self.assertEqual(setup_response.status_code, 200)
        setup_response = self.client.post(setup_response.request["PATH_INFO"], {
            "new_password1": "StrongPass!12345",
            "new_password2": "StrongPass!12345",
        })
        self.assertEqual(setup_response.status_code, 302)

        staff.refresh_from_db()
        self.assertTrue(staff.has_usable_password())
        self.assertTrue(staff.check_password("StrongPass!12345"))
        self.client.logout()
        login_response = self.client.post(reverse("accounts:login"), {
            "username": "amina@example.org", "password": "StrongPass!12345",
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(int(self.client.session.get("_auth_user_id")), staff.pk)
