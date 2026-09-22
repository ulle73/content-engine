from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import apify
from .models import Company, ContentRun, ScraperState
from .provider_costs import openai_text_cost
from .sync import dispatch


class ApifyAdapterTests(TestCase):
    def test_primary_instagram_input_uses_current_actor_schema(self):
        data = apify.instagram_input("golfamore", apify.PRIMARY_ACTOR, 10)
        self.assertEqual(data["directUrls"], ["golfamore"])
        self.assertEqual(data["resultsType"], "posts")
        self.assertEqual(data["resultsLimit"], 10)
        self.assertIn("ownerUsername", data["selectedFields"])
        self.assertNotIn("usernames", data)

    def test_dispatch_preserves_definite_provider_error_for_the_ui(self):
        user = get_user_model().objects.create_user(username="apify-error@example.test")
        company = Company.objects.create(owner=user, name="Golf")
        state = ScraperState.objects.create(company=company, source="instagram", external_key="golfamore")

        def rejected():
            raise apify.ApifyError(
                "Apify: Monthly usage hard limit exceeded. (monthly-usage-hard-limit-exceeded)",
                status_code=402,
                error_type="monthly-usage-hard-limit-exceeded",
            )

        with self.assertRaisesRegex(apify.ApifyError, "Monthly usage hard limit exceeded"):
            dispatch(state, "actor/test", "discovery", {"x": 1}, max_cost="0.05", sender=rejected)
        request = state.requests.get()
        self.assertEqual(request.status, "failed")
        self.assertIn("Monthly usage hard limit exceeded", request.result["error"])
        self.assertEqual(request.result["error_type"], "monthly-usage-hard-limit-exceeded")
        self.assertEqual(request.result["http_status"], 402)


class PricingTests(TestCase):
    def test_luna_cost_uses_actual_input_cached_and_output_tokens(self):
        cost = openai_text_cost(
            {
                "model": "gpt-5.6-luna",
                "usage": {
                    "input_tokens": 1000,
                    "input_tokens_details": {"cached_tokens": 100},
                    "output_tokens": 500,
                },
            }
        )
        self.assertEqual(cost, Decimal("0.00078200"))


class CostScreenTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="costs@example.test")
        self.company = Company.objects.create(owner=self.user, name="Golf")
        self.client.force_login(self.user)

    @patch("engine.company_settings.apify.account_summary")
    def test_cost_screen_shows_all_provider_sections_and_apify_limit(self, summary):
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
        ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            model="gpt-5.6-luna",
            context={
                "_provider_usage_ideas": {
                    "provider": "openai",
                    "service": "text",
                    "operation": "ideas",
                    "model": "gpt-5.6-luna",
                    "response_id": "resp-test",
                    "usage": {"input_tokens": 1000, "output_tokens": 500},
                }
            },
            ideas=[],
            draft={},
        )
        response = self.client.get(reverse("engine:costs", kwargs={"workspace_id": self.company.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kostnadsgränsen är nådd")
        self.assertContains(response, "Använt denna Apify-period")
        self.assertContains(response, "OpenAI · text")
        self.assertContains(response, "OpenAI · bilder")
        self.assertContains(response, "Higgsfield · video")
        self.assertContains(response, "Totalt registrerat")
        self.assertContains(response, "$5,00")
        self.assertNotContains(response, "APIFY_API_TOKEN")
