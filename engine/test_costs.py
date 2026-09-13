from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import apify
from .models import Company


class ApifyAdapterTests(TestCase):
    def test_primary_instagram_input_uses_current_actor_schema(self):
        data = apify.instagram_input("golfamore", apify.PRIMARY_ACTOR, 10)
        self.assertEqual(data["directUrls"], ["golfamore"])
        self.assertEqual(data["resultsType"], "posts")
        self.assertEqual(data["resultsLimit"], 10)
        self.assertIn("ownerUsername", data["selectedFields"])
        self.assertNotIn("usernames", data)


class CostScreenTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="costs@example.test")
        self.company = Company.objects.create(owner=self.user, name="Golf")
        self.client.force_login(self.user)

    @patch("engine.company_settings.apify.account_summary")
    def test_cost_screen_shows_apify_usage_without_exposing_credentials(self, summary):
        summary.return_value = {
            "plan": "FREE",
            "is_paying": False,
            "used_usd": 5.0,
            "hard_limit_usd": 5.0,
            "remaining_to_limit_usd": 0.0,
            "included_credits_usd": 5.0,
            "included_remaining_usd": 0.0,
            "hard_limit_reached": True,
            "cycle_start": "2026-09-01T00:00:00.000Z",
            "cycle_end": "2026-09-30T23:59:59.999Z",
        }
        response = self.client.get(reverse("engine:costs", kwargs={"workspace_id": self.company.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kostnadsgränsen är nådd")
        self.assertContains(response, "Använt denna period")
        self.assertContains(response, "$5.00")
        self.assertNotContains(response, "APIFY_API_TOKEN")
