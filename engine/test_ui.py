from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Company


class AppShellTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ui@example.test",
            password="test-only-password",
        )
        self.workspace = Company.objects.create(owner=self.user, name="Sänk Dig Golf")
        self.client.force_login(self.user)

    def test_workspace_pages_use_shared_app_shell_and_stylesheet(self):
        response = self.client.get(
            reverse("engine:intelligence", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'href="/static/css/app.css"')
        self.assertContains(response, 'class="app-sidebar"')
        self.assertContains(response, 'class="app-topbar"')
        self.assertContains(response, "Konkurrenssignaler")
