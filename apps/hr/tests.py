from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Department


class DepartmentManagementTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="department-admin", email="admin@example.org", password="SafePass123!",
        )
        self.client.force_login(self.admin)

    def test_admin_can_create_deactivate_and_delete_department(self):
        response = self.client.post(reverse("hr:department_create"), {
            "name": "Community Programmes", "code": "CP", "description": "Local delivery teams.",
            "is_active": "on",
        })
        department = Department.objects.get(code="CP")
        self.assertRedirects(response, reverse("hr:department_list"))
        self.assertTrue(department.is_active)

        response = self.client.post(reverse("hr:department_edit", args=[department.pk]), {
            "name": department.name, "code": department.code, "description": department.description,
            "is_active": "",
        })
        department.refresh_from_db()
        self.assertRedirects(response, reverse("hr:department_list"))
        self.assertFalse(department.is_active)

        response = self.client.post(reverse("hr:department_delete", args=[department.pk]))
        self.assertRedirects(response, reverse("hr:department_list"))
        self.assertFalse(Department.objects.filter(pk=department.pk).exists())
