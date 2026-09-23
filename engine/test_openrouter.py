import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AnalysisMemo, Company
from .openrouter import OpenRouterError, structured_analysis, structured_generation
from .signals import Classification
from .sync import analysis


def classification_payload():
    return {
        "topic": "Kvällsträning",
        "hook": "Praktisk tillgänglighet efter jobbet",
        "mechanisms": ["instruktion"],
        "cta": "Läs mer",
        "why": "Tillgänglighet kan vara relevant för golfare med begränsad tid.",
        "adaptation": "Visa en egen verifierad Golfkuponger-vinkel utan att kopiera.",
        "profile_relevance": 2,
        "current_relevance": 2,
    }


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class OpenRouterAnalysisTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="openrouter@example.test")
        self.company = Company.objects.create(owner=user, name="Golf")

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_ANALYSIS_MODEL": "@preset/gk-free",
            "OPENROUTER_ANALYSIS_FALLBACK_MODEL": "z-ai/glm-5.3-flash",
        },
        clear=False,
    )
    @patch("engine.openrouter.httpx.post")
    def test_free_preset_is_used_first_and_valid_output_stops_routing(self, post):
        post.return_value = FakeResponse(
            body={
                "id": "gen-free",
                "model": "some/free-model",
                "choices": [{"message": {"content": __import__("json").dumps(classification_payload())}}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 80, "cost": 0},
            }
        )
        parsed, meta = structured_analysis(
            system="Analyze.",
            payload={"caption": "Golf"},
            schema=Classification,
            operation="competitor_analysis",
            max_tokens=5000,
            temperature=0.2,
        )
        self.assertEqual(parsed.topic, "Kvällsträning")
        request = post.call_args.kwargs["json"]
        self.assertEqual(request["max_tokens"], 5000)
        self.assertEqual(request["temperature"], 0.2)
        self.assertEqual(request["response_format"]["type"], "json_object")
        self.assertNotIn("require_parameters", request["provider"])
        self.assertEqual(request["provider"]["sort"], "throughput")
        self.assertEqual(request["plugins"], [{"id": "response-healing"}])
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["model"], "@preset/gk-free")
        self.assertEqual(meta["provider"], "openrouter")
        self.assertEqual(meta["model"], "some/free-model")
        self.assertEqual(meta["cost_usd"], 0)

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_ANALYSIS_FALLBACK_MODEL": "z-ai/glm-5.3-flash",
        },
        clear=False,
    )
    @patch("engine.openrouter.httpx.post")
    def test_generation_uses_glm_directly_with_reasoning_disabled(self, post):
        post.return_value = FakeResponse(
            body={
                "id": "gen-glm",
                "model": "z-ai/glm-5.3-flash",
                "choices": [{"message": {"content": __import__("json").dumps(classification_payload())}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 60, "cost": 0.0001},
            }
        )
        parsed, meta = structured_generation(
            system="Create.",
            payload={"topic": "Golf"},
            schema=Classification,
            operation="idea_1",
            max_tokens=1200,
            temperature=0.2,
        )
        self.assertEqual(parsed.topic, "Kvällsträning")
        request = post.call_args.kwargs["json"]
        self.assertEqual(request["model"], "z-ai/glm-5.3-flash")
        self.assertEqual(request["reasoning_effort"], "none")
        self.assertEqual(request["response_format"]["type"], "json_object")
        self.assertEqual(request["max_tokens"], 1200)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(meta["model"], "z-ai/glm-5.3-flash")

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_ANALYSIS_MODEL": "@preset/gk-free",
            "OPENROUTER_ANALYSIS_FALLBACK_MODEL": "z-ai/glm-5.3-flash",
        },
        clear=False,
    )
    @patch("engine.openrouter.httpx.post")
    def test_reasoning_details_response_is_accepted_like_n8n(self, post):
        post.return_value = FakeResponse(
            body={
                "id": "reasoning-only",
                "model": "some/free-model",
                "choices": [{"message": {"content": "", "reasoning_details": [{"text": __import__("json").dumps(classification_payload())}]}}],
                "usage": {"cost": 0},
            }
        )
        parsed, _ = structured_analysis(
            system="Analyze.",
            payload={"caption": "Golf"},
            schema=Classification,
        )
        self.assertEqual(parsed.topic, "Kvällsträning")
        request = post.call_args.kwargs["json"]
        self.assertEqual(request["temperature"], 0)
        self.assertEqual(request["max_tokens"], 4000)

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_ANALYSIS_MODEL": "@preset/gk-free",
            "OPENROUTER_ANALYSIS_FALLBACK_MODEL": "z-ai/glm-5.3-flash",
        },
        clear=False,
    )
    @patch("engine.openrouter.httpx.post")
    def test_invalid_free_output_falls_back_to_glm_53_flash(self, post):
        post.side_effect = [
            FakeResponse(
                body={
                    "id": "bad-free",
                    "model": "free",
                    "choices": [{"message": {"content": "not json"}}],
                    "usage": {"cost": 0},
                }
            ),
            FakeResponse(
                body={
                    "id": "paid-ok",
                    "model": "z-ai/glm-5.3-flash",
                    "choices": [{"message": {"content": __import__("json").dumps(classification_payload())}}],
                    "usage": {"prompt_tokens": 200, "completion_tokens": 80, "cost": 0.0001},
                }
            ),
        ]
        parsed, meta = structured_analysis(
            system="Analyze.",
            payload={"caption": "Golf"},
            schema=Classification,
            operation="competitor_analysis",
        )
        self.assertEqual(parsed.cta, "Läs mer")
        self.assertEqual(
            [call.kwargs["json"]["model"] for call in post.call_args_list],
            ["@preset/gk-free", "z-ai/glm-5.3-flash"],
        )
        free_request = post.call_args_list[0].kwargs["json"]
        fallback_request = post.call_args_list[1].kwargs["json"]
        self.assertEqual(free_request["response_format"]["type"], "json_object")
        self.assertNotIn("require_parameters", free_request["provider"])
        self.assertEqual(fallback_request["response_format"]["type"], "json_object")
        self.assertNotIn("require_parameters", fallback_request["provider"])
        self.assertGreaterEqual(fallback_request["max_tokens"], 1600)
        self.assertEqual(meta["model"], "z-ai/glm-5.3-flash")

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_ANALYSIS_MODEL": "@preset/gk-free",
            "OPENROUTER_ANALYSIS_FALLBACK_MODEL": "z-ai/glm-5.3-flash",
        },
        clear=False,
    )
    @patch("engine.openrouter.httpx.post")
    def test_rate_limited_free_route_uses_paid_fallback(self, post):
        post.side_effect = [
            FakeResponse(status_code=429, body={"error": {"message": "rate limited"}}),
            FakeResponse(
                body={
                    "id": "fallback",
                    "model": "z-ai/glm-5.3-flash",
                    "choices": [{"message": {"content": __import__("json").dumps(classification_payload())}}],
                    "usage": {"cost": 0.0001},
                }
            ),
        ]
        parsed, _ = structured_analysis(
            system="Analyze.",
            payload={"caption": "Golf"},
            schema=Classification,
        )
        self.assertEqual(parsed.topic, "Kvällsträning")
        self.assertEqual(post.call_count, 2)

    @patch("engine.sync.timezone.now")
    def test_stale_openrouter_started_memo_recovers_after_worker_restart(self, now):
        base = __import__("django.utils.timezone", fromlist=["now"]).now()
        now.return_value = base
        key_parts = ["organic", "stale"]
        model = "openrouter:@preset/gk-free>z-ai/glm-5.3-flash"
        from .sync import fingerprint
        memo = AnalysisMemo.objects.create(
            company=self.company,
            key=fingerprint([key_parts, model]),
            model=model,
            status="started",
            last_attempt_at=base - __import__("datetime").timedelta(seconds=45),
        )
        result = analysis(
            self.company,
            key_parts,
            model,
            lambda: {"ok": True},
        )
        self.assertEqual(result, {"ok": True})
        memo.refresh_from_db()
        self.assertEqual(memo.status, "completed")
        self.assertEqual(memo.attempts, 2)

    def test_retryable_provider_failure_does_not_lock_analysis_for_23_hours(self):
        with self.assertRaises(OpenRouterError):
            analysis(
                self.company,
                ["organic", "retryable"],
                "openrouter:@preset/gk-free>z-ai/glm-5.3-flash",
                lambda: (_ for _ in ()).throw(OpenRouterError("temporary", status_code=429)),
            )
        self.assertEqual(AnalysisMemo.objects.filter(company=self.company).count(), 0)

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False)
    def test_missing_key_has_safe_actionable_error(self):
        with self.assertRaisesRegex(OpenRouterError, "OPENROUTER_API_KEY"):
            structured_analysis(
                system="Analyze.",
                payload={"caption": "Golf"},
                schema=Classification,
            )
