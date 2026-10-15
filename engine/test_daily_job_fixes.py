"""Failures seen in the daily job (run 38727560527, 2026-10-15) and what they should look like now."""
import json
import os
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from . import apify
from .ads import AdClassification
from .daily import Result
from .models import Company, Competitor, CompetitorImport, DailyRun, DailyStep, ScrapeRequest
from .openrouter import structured_analysis
from .sync import dispatch, state_for

ROUTE = {
    "OPENROUTER_API_KEY": "test-key",
    "OPENROUTER_ANALYSIS_MODEL": "@preset/gk-free",
    "OPENROUTER_ANALYSIS_FALLBACK_MODEL": "z-ai/glm-5.3-flash",
    "OPENROUTER_ANALYSIS_LAST_RESORT_MODEL": "",
}
CLASSIFICATION = {"message": "Ljus för mörka vägar", "hook": "fråga", "cta": "Köp", "offer": "okänt",
                  "themes": ["säkerhet"], "mechanisms": ["demo"], "adaptation": "Visa vår egen montering.", "unknowns": []}


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.is_error = status_code >= 400

    def json(self):
        return self._body


def answer(model, content, finish_reason="stop", reasoning_tokens=0):
    return FakeResponse(body={
        "id": "gen", "model": model,
        "choices": [{"finish_reason": finish_reason, "message": {"content": content}}],
        "usage": {"completion_tokens": 1800, "completion_tokens_details": {"reasoning_tokens": reasoning_tokens}, "cost": 0},
    })


class AdClassificationRouteTests(TestCase):
    @patch.dict(os.environ, ROUTE, clear=False)
    @patch("engine.openrouter.httpx.post")
    def test_cut_off_answer_is_not_parsed_and_glm_reasons_at_low_effort(self, post):
        # The free model ran out of tokens mid-object; GLM used to spend all 1800 on reasoning at default effort "max".
        cut_off = json.dumps({k: v for k, v in CLASSIFICATION.items() if k != "unknowns"})
        post.side_effect = [answer("cohere/north-mini-code:free", cut_off, "length", 1500),
                            answer("z-ai/glm-5.3-flash", json.dumps(CLASSIFICATION))]
        parsed, meta = structured_analysis(system="s", payload={}, schema=AdClassification, max_tokens=1800)
        self.assertEqual(parsed.message, "Ljus för mörka vägar")
        self.assertEqual(meta["model"], "z-ai/glm-5.3-flash")
        free, glm = (call.kwargs["json"] for call in post.call_args_list)
        self.assertNotIn("reasoning", free)  # the free preset's models ignore effort
        self.assertEqual(glm["reasoning"], {"effort": "low"})
        self.assertGreaterEqual(free["max_completion_tokens"], 6000)
        self.assertGreaterEqual(glm["max_completion_tokens"], 6000)

    @patch.dict(os.environ, ROUTE, clear=False)
    @patch("engine.openrouter.httpx.post")
    def test_reasoning_text_is_never_taken_as_the_answer_of_a_cut_off_reply(self, post):
        cut_off = {"id": "gen", "model": "z-ai/glm-5.3-flash", "usage": {},
                   "choices": [{"finish_reason": "length", "message": {"content": "", "reasoning": json.dumps(CLASSIFICATION)}}]}
        post.side_effect = [answer("free", "not json"), FakeResponse(body=cut_off)]
        with self.assertRaisesRegex(Exception, "klipptes av"):
            structured_analysis(system="s", payload={}, schema=AdClassification)

    @patch.dict(os.environ, ROUTE, clear=False)
    @patch("engine.openrouter.httpx.post")
    def test_vision_route_keeps_the_callers_budget_and_default_reasoning(self, post):
        post.return_value = answer("google/gemini-3.1-flash-lite", json.dumps(CLASSIFICATION))
        structured_analysis(system="s", payload={}, schema=AdClassification, max_tokens=1800, images=["data:image/png;base64,AA=="])
        request = post.call_args.kwargs["json"]
        self.assertEqual(request["max_completion_tokens"], 1800)
        self.assertNotIn("reasoning", request)


class PostizSubscriptionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="postiz-daily")
        self.company = Company.objects.create(owner=user, name="Sänk Dig", postiz_channels=[{"id": "ig", "identifier": "instagram"}])
        self.company.postiz_key = "test-key"
        self.company.save()

    @patch("engine.postiz.httpx.request")
    def test_lapsed_postiz_plan_is_named_and_needs_attention(self, request):
        from .daily_stages import own_discovery_units
        from .postiz import PostizError

        request.return_value = FakeResponse(401, {"msg": "No subscription found"})
        [(key, work)] = own_discovery_units(self.company)
        result = work()
        self.assertEqual((key, result.status), ("published", "attention"))
        self.assertIn("saknar aktivt abonnemang", result.message)
        self.assertEqual(result.data, {"http_status": 401})

        from .postiz import request as postiz_request
        request.return_value = FakeResponse(401, {"msg": "Invalid API key"})
        with self.assertRaisesRegex(PostizError, "godkänner inte API-nyckeln") as caught:
            postiz_request("bad", "GET", "/integrations")
        self.assertEqual(caught.exception.status_code, 401)

    @patch("engine.postiz.httpx.request")
    def test_server_errors_still_fail_for_a_retry(self, request):
        from .daily_stages import own_discovery_units
        from .postiz import PostizError

        request.return_value = FakeResponse(502)
        [(_, work)] = own_discovery_units(self.company)
        with self.assertRaises(PostizError):
            work()


class ScraperBudgetTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="budget-daily")
        self.company = Company.objects.create(owner=user, name="Faiv")

    def reserve(self, n, cap="0.02"):
        for i in range(n):
            ScrapeRequest.objects.create(state=state_for(self.company, "instagram", f"ig{i}"), key=f"ig{i}", actor="a",
                                         mode="backfill", status="running", actor_run_id=f"run{i}", max_cost_usd=Decimal(cap))

    @patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "0.20"}, clear=False)
    def test_finished_runs_release_their_reserved_cap(self):
        self.reserve(9)  # 0.18 reserved, like nine Instagram backfills
        get_run = Mock(return_value={"status": "SUCCEEDED", "usageTotalUsd": 0.005})
        sender = Mock(return_value={"id": "ads", "defaultDatasetId": "d"})
        with patch("engine.sync.apify.get_run", get_run):
            request = dispatch(state_for(self.company, "meta_ads", "page:SE"), "ads", "backfill", {}, max_cost="0.059", sender=sender)
        self.assertEqual(request.status, "running")
        self.assertEqual(get_run.call_count, 9)
        # Collection still records the cost; the check only reads it.
        self.assertEqual(ScrapeRequest.objects.filter(cost_usd=None).count(), 10)

    @patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "0.20"}, clear=False)
    def test_running_jobs_keep_their_cap_and_the_refusal_is_a_budget_error(self):
        self.reserve(9)
        sender = Mock()
        with patch("engine.sync.apify.get_run", Mock(return_value={"status": "RUNNING", "usageTotalUsd": 0.001})):
            with self.assertRaisesRegex(apify.BudgetExceeded, r"0\.180 av 0\.20 USD"):
                dispatch(state_for(self.company, "meta_ads", "page:SE"), "ads", "backfill", {}, max_cost="0.059", sender=sender)
        sender.assert_not_called()

    @patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "0.20"}, clear=False)
    def test_daily_ad_check_is_blocked_not_failed_when_the_ceiling_is_reached(self):
        from .daily_stages import import_ads
        from .models import AdAccount

        self.reserve(9)
        account = AdAccount.objects.create(company=self.company, name="Lumise.se", page_url="https://www.facebook.com/191824684489032",
                                           page_id="191824684489032")
        with patch("engine.sync.apify.get_run", Mock(side_effect=apify.ApifyError("down"))):
            result = import_ads(account)
        self.assertEqual(result.status, "blocked")
        self.assertIn("kostnadsgräns", result.message)


class AnalysisWaitTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="await-daily")
        self.company = Company.objects.create(owner=user, name="Golf", profile="Golf", current="Kuponger")
        self.competitor = Competitor.objects.create(company=self.company, name="Klubb", username="klubb")
        self.run = CompetitorImport.objects.create(competitor=self.competitor, actor="a", actor_run_id="r1", status="running")
        DailyStep.objects.create(run=DailyRun.objects.create(day=__import__("django.utils.timezone", fromlist=["x"]).localdate()),
                                 company=self.company, stage="competitor_import", key="1:first", status="pending")

    def test_finished_import_is_collected_so_analysis_runs_in_the_same_pass(self):
        from .daily_stages import analysis_units

        def collect(run, **kwargs):
            CompetitorImport.objects.filter(pk=run.pk).update(status="succeeded")
            return run

        with patch("engine.daily_stages.collect_import", side_effect=collect) as collected, \
                patch("engine.daily_stages.analysis_candidates", return_value=[]):
            units = analysis_units(self.company)
        collected.assert_called_once()
        self.assertEqual(units[0][1]().status, "skipped")

    def test_running_import_still_waits(self):
        from .daily_stages import analysis_units

        with patch("engine.daily_stages.collect_import", return_value=self.run):
            [(key, work)] = analysis_units(self.company)
        self.assertEqual((key, work().status), ("await_imports", "pending"))
        self.assertIsInstance(work(), Result)
