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
        self.assertContains(response, "Insikter")

        stylesheet = self.client.get("/static/css/app.css")
        self.assertEqual(stylesheet.status_code, 200)

    def test_workspace_shell_has_mobile_header_and_bottom_navigation(self):
        response = self.client.get(
            reverse("engine:home", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'class="mobile-header"')
        self.assertContains(response, 'class="mobile-bottom-nav"')
        self.assertContains(response, 'aria-label="Mobil navigation"')
        self.assertContains(response, ">Översikt<")
        self.assertContains(response, ">Insikter<")
        self.assertContains(response, ">Skapa<")
        self.assertContains(response, ">Inställningar<")

    def test_responsive_styles_include_touch_targets_safe_area_and_mobile_cards(self):
        stylesheet = self.client.get("/static/css/app.css")
        css = stylesheet.content.decode("utf-8")

        self.assertIn(".mobile-bottom-nav", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".mobile-table", css)
        self.assertIn("@media (max-width: 720px)", css)

    def test_settings_uses_mobile_friendly_table_contract(self):
        response = self.client.get(
            reverse("engine:settings", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'class="daily-table mobile-table"')
        self.assertContains(response, 'data-label="Status"')
        self.assertContains(response, 'data-label="Detaljer"')
