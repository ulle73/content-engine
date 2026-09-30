import os
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from . import market, virlo
from .apify import ApifyError
from .learning import attach_generation_evidence, dataset
from .models import (AnalysisMemo, Company, Competitor, CompetitorPost, ContentRun,
                     MarketItem, MarketObservation, ScrapeRequest)
from .provider_costs import cost_summary
from .sync import fingerprint, state_for


class MarketTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="market", password="test")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger",
            profile="Golf greenfee på svenska golfbanor.", current="Golf för alla.",
            voice="Saklig", source="https://example.com", valid_until=timezone.localdate()+timedelta(days=30))
        self.other = Company.objects.create(owner=self.user, name="Faiv", profile="Skincare hudvård serum.")
        self.client.force_login(self.user)

    def request(self, company=None):
        state = state_for(company or self.company, "virlo", "market")
        return ScrapeRequest.objects.create(state=state, key=uuid.uuid4().hex, actor="virlo/agents", mode="market",
            inputs={"keywords": ["golf greenfee"]}, max_cost_usd=".50", cost_usd=".50",
            actor_run_id="virlo:"+uuid.uuid4().hex, status="running", result={"remote_id": "agent-123"})

    def video(self, code="ABC", **changes):
        return {"id": "provider-id", "platform": "instagram", "url": f"https://www.instagram.com/reel/{code}/?tracking=1",
            "description": "Golf greenfee teknik för nästa runda", "views": 100000, "likes": 1200,
            "comments": 50, "author": {"username": "creator", "followers": 1000},
            "publish_date": (timezone.now()-timedelta(days=1)).isoformat(), **changes}

    def item(self, company=None, code="ABC", channel="organic"):
        run = self.request(company)
        if channel == "organic":
            market.ingest(run, [self.video(code)], [], [])
        else:
            market.ingest(run, [], [{"id": 123, "ad_archive_id": code, "url": "https://landing.example.com",
                "caption": "Golf greenfee teknik för nästa runda", "page_id": "456"}], [])
        item = MarketItem.objects.get(company=company or self.company, canonical_key=("instagram:" if channel == "organic" else "meta_ads:")+code)
        item.classification = {"profile_relevance": 3, "current_relevance": 2, "mechanisms": ["instruktion"],
            "hook": "Problem lösning", "why": "Relevant teknik", "adaptation": "Visa företagets egen golfidé."}
        item.classification_hash = market.classification_key(item, company or self.company)
        item.save()
        return item

    @patch.dict(os.environ, {"VIRLO_API_KEY": "test", "SCRAPER_DAILY_BUDGET_USD": "1"})
    @patch("engine.virlo.api")
    def test_start_uses_current_contract_and_is_deduplicated(self, api):
        api.side_effect = [({"keywords": ["golf greenfee", "golf teknik"], "quality": {"passes": True}}, Decimal(0)),
                           ({"id": "agent-123"}, Decimal(".50"))]
        run = market.start(self.company)
        self.assertEqual(market.start(self.company).pk, run.pk)
        payload = api.call_args.kwargs["json"]
        self.assertEqual(payload["platforms"], ["instagram"])
        self.assertTrue(payload["meta_ads_enabled"])
        self.assertFalse(payload["data_intelligence_enabled"])
        self.assertFalse(payload["is_recurring"])
        self.assertNotIn("_company_scope_hash", payload)
        self.assertEqual(run.cost_usd, Decimal(".50"))
        self.assertEqual(api.call_count, 2)

    @patch.dict(os.environ, {"VIRLO_API_KEY": "test", "SCRAPER_DAILY_BUDGET_USD": "1"})
    @patch("engine.virlo.api")
    def test_uncertain_post_is_never_redispatched(self, api):
        api.side_effect = [({"keywords": ["golf greenfee"], "quality": {"passes": True}}, None),
                           ApifyError("Virlo timeout", uncertain=True)]
        with self.assertRaises(ApifyError):
            market.start(self.company)
        run = market.start(self.company)
        self.assertEqual(run.status, "unknown")
        self.assertIsNone(run.cost_usd)
        self.assertEqual(api.call_count, 2)

    @patch.dict(os.environ, {"VIRLO_API_KEY": "test", "SCRAPER_DAILY_BUDGET_USD": ".49"})
    @patch("engine.virlo.api")
    def test_shared_budget_blocks_paid_call(self, api):
        api.return_value = ({"keywords": ["golf greenfee"], "quality": {"passes": True}}, None)
        with self.assertRaises(ApifyError):
            market.start(self.company)
        self.assertEqual(api.call_count, 1)  # free keyword suggestion only
        self.assertFalse(ScrapeRequest.objects.exists())

    def test_content_dedupe_and_company_isolation(self):
        first, second = self.request(), self.request()
        market.ingest(first, [self.video(), self.video(url="https://www.instagram.com/p/ABC/")], [], [])
        market.ingest(second, [self.video()], [], [])
        other = self.request(self.other)
        market.ingest(other, [self.video()], [], [])
        self.assertEqual(MarketItem.objects.count(), 2)
        self.assertEqual(MarketObservation.objects.count(), 3)
        self.assertEqual(len(market.candidates(self.company)), 1)

    def test_metrics_first_filters_irrelevant_normal_old_and_wrong_platform(self):
        run = self.request()
        rows = [self.video(), self.video("NORMAL", views=100, author={"followers": 10000}),
            self.video("NOISE", description="Celebrity gossip outfit"), self.video("TIKTOK", platform="tiktok"),
            self.video("OLD", publish_date=(timezone.now()-timedelta(days=50)).isoformat())]
        market.ingest(run, rows, [], [])
        self.assertEqual([i.canonical_key for i in market.candidates(self.company)], ["instagram:ABC"])
        self.assertFalse(MarketItem.objects.filter(canonical_key="instagram:TIKTOK").exists())

    def test_relative_performance_is_separate_from_follower_reach(self):
        caption, metrics, qualified = market.qualify(self.company, self.video(views=3000), "organic", [],
            {"median_views": 1000, "videos_analyzed": 8})
        self.assertEqual(metrics["creator_relative"], 3)
        self.assertEqual(metrics["views_per_follower"], 3)
        self.assertTrue(qualified["qualified"])
        _, sparse, _ = market.qualify(self.company, self.video(), "organic", [], {"median_views": 1000, "videos_analyzed": 2})
        self.assertIsNone(sparse["creator_relative"])

    def test_ads_use_archive_id_not_landing_url_and_have_no_fake_performance(self):
        item = self.item(code="12345", channel="paid")
        self.assertEqual(item.url, "https://www.facebook.com/ads/library/?id=12345")
        self.assertEqual(item.metrics, {})
        self.assertEqual(item.qualification["evidence_type"], "market_evidence")

    @patch("engine.virlo.api")
    @patch("engine.virlo.rows")
    def test_collect_only_finalized_and_resume_unknown_reads(self, rows, api):
        run = self.request()
        api.return_value = ({"finalized": False, "latest_run": {"status": "processing"}}, None)
        self.assertEqual(market.collect(run).status, "running")
        rows.assert_not_called()
        api.return_value = ({"finalized": True, "latest_run": {"status": "unexpected"}}, None)
        self.assertEqual(market.collect(run).status, "unknown")
        api.return_value = ({"finalized": True, "latest_run": {"status": "completed"}}, None)
        rows.side_effect = [[self.video()], [], []]
        self.assertEqual(market.collect(run).status, "succeeded")
        self.assertEqual(MarketItem.objects.count(), 1)
        self.assertEqual(market.collect(run).status, "succeeded")
        self.assertEqual(rows.call_count, 3)

    @patch("engine.virlo.api")
    @patch("engine.virlo.rows")
    def test_partial_provider_run_keeps_data_and_needs_attention(self, rows, api):
        run = self.request()
        api.return_value = ({"finalized": True, "latest_run": {"status": "partial_failure"}}, None)
        rows.side_effect = [[self.video()], [], []]
        self.assertEqual(market.collect(run).status, "partial")
        self.assertEqual(MarketItem.objects.count(), 1)

    def test_feedback_changes_future_relevance_without_performance_labels(self):
        item = self.item()
        item.preference, item.feedback_at = -1, timezone.now()
        item.save()
        _, _, qualified = market.qualify(self.company, self.video("NEW"), "organic", [])
        self.assertFalse(qualified["qualified"])
        self.assertEqual(market.preference_score(self.other, item.caption), 0)
        self.assertEqual(dataset(self.company, "organic"), [])
        snapshot = attach_generation_evidence({}, self.company, "organic")
        self.assertEqual(snapshot["generation_learning"]["performance"]["sample_size"], 0)
        self.assertEqual(len(snapshot["generation_learning"]["editorial"]["market_relevance_feedback"]), 1)

    def test_evidence_reaches_web_mcp_and_creative_studio(self):
        item = self.item()
        from .operator_content import _build_snapshot
        snapshot = _build_snapshot(self.company, "organic", f"market:{item.pk}")
        self.assertEqual(snapshot["competitor_signals"][0]["id"], f"market:{item.pk}")
        self.assertEqual(len(snapshot["generation_learning"]["external_viral_performance"]), 1)
        self.assertEqual(snapshot["generation_learning"]["performance"]["sample_size"], 0)
        token = uuid.uuid4()
        response = self.client.post(reverse("engine:media_new", args=[self.company.pk]), {"token": token, "market_id": item.pk})
        self.assertEqual(response.status_code, 302)
        run = ContentRun.objects.get(pk=token)
        self.assertEqual(run.ideas[0]["photo_brief"], item.classification["adaptation"])
        self.assertEqual(len(run.context["generation_learning"]["external_viral_performance"]), 1)
        from .creative_director import build_plan
        plan = build_plan(run, run.draft["photo_brief"], kind="image")
        self.assertIn("instruktion", plan.prompt)
        self.assertIn(f"market:{item.pk}", plan.inspiration_ids)
        with patch("engine.views.generate", return_value={"ideas": []}) as generate:
            response = self.client.post(reverse("engine:ideas", args=[self.company.pk]), {"market_id": item.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(generate.call_args.args[0]["competitor_signals"][0]["id"], f"market:{item.pk}")

    def test_apify_provenance_is_linked_and_generation_deduplicates(self):
        item = self.item()
        competitor = Competitor.objects.create(company=self.company, name="Tracked", username="creator")
        post = CompetitorPost.objects.create(competitor=competitor, shortcode="ABC", url=item.url,
            published_at=timezone.now(), format="reel")
        snapshot = attach_generation_evidence({"competitor_signals": [{"id": str(post.pk), "url": item.url}]}, self.company, "organic")
        self.assertEqual(len(snapshot["competitor_signals"]), 1)
        self.assertEqual(market.linked_sources(item), [{"provider": "apify", "post_id": post.pk}])

    def test_cross_company_urls_feedback_generation_and_studio_denied(self):
        item = self.item()
        response = self.client.post(reverse("engine:market_feedback", args=[self.other.pk, item.pk]), {"preference": "1"})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("engine:ideas", args=[self.other.pk]), {"market_id": item.pk})
        # Complete other company facts so ownership, rather than validation, is tested below.
        self.other.current, self.other.voice, self.other.valid_until = "Skincare idag.", "Saklig", self.company.valid_until
        self.other.source = "https://example.com"
        self.other.save()
        response = self.client.post(reverse("engine:ideas", args=[self.other.pk]), {"market_id": item.pk})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("engine:media_new", args=[self.other.pk]), {"market_id": item.pk, "token": uuid.uuid4()})
        self.assertEqual(response.status_code, 404)
        with self.assertRaises(ValueError):
            market.classify(item, self.other)

    def test_changed_profile_invalidates_analysis_and_inflight_research(self):
        item = self.item()
        run = self.request()
        run.inputs["_company_scope_hash"] = market.scope_hash(self.company)
        run.save()
        self.company.profile = "Hudvård serum skincare"
        self.company.save()
        self.assertEqual(market.signals(self.company, "organic"), [])
        market.ingest(run, [self.video("NEW")], [], [])
        self.assertFalse(MarketItem.objects.get(canonical_key="instagram:NEW").qualification["qualified"])

    def test_costs_keep_virlo_separate_from_apify(self):
        self.request()
        summary = cost_summary(self.company)
        self.assertEqual(summary["virlo_usd"], Decimal(".50"))
        self.assertEqual(summary["apify_usd"], 0)
        self.assertEqual(summary["total_usd"], Decimal(".50"))
        self.assertEqual(summary["recent"][0]["provider"], "Virlo")
        self.assertEqual(cost_summary(self.other)["total_usd"], 0)

    @patch("engine.generation.structured_generation")
    def test_actual_generation_prompt_receives_separated_evidence(self, provider):
        from .generation import DraftOutput, generate
        from .operator_content import _build_snapshot
        item = self.item()
        snapshot = _build_snapshot(self.company, "organic", f"market:{item.pk}")
        provider.return_value = (DraftOutput(instagram="Egen text", facebook="Egen text", photo_brief="Egen bild", checks=[]), {})
        generate(snapshot, idea={"title": "Egen idé", "angle": "Egen vinkel"})
        payload = provider.call_args.kwargs["payload"]["company_context"]
        self.assertNotIn("learning_profile", payload)
        self.assertEqual(payload["generation_learning"]["external_viral_performance"][0]["id"], f"market:{item.pk}")
        self.assertEqual(payload["generation_learning"]["performance"]["sample_size"], 0)
        self.assertIn("Egna verifierade resultat", provider.call_args.kwargs["system"])
        self.assertNotIn("Golfkuponger-performance", provider.call_args.kwargs["system"])

    @patch.dict(os.environ, {"VIRLO_API_KEY": ""})
    def test_missing_key_and_paused_company_do_not_dispatch(self):
        with self.assertRaises(ValueError):
            market.start(self.company)
        self.assertFalse(ScrapeRequest.objects.exists())
        self.assertEqual(market.daily_units(self.company)[0][1]().status, "skipped")
        self.company.market_intelligence_enabled = False
        self.assertEqual(market.daily_units(self.company), [])

    def test_feedback_can_be_undone_and_owner_is_required(self):
        item = self.item()
        url = reverse("engine:market_feedback", args=[self.company.pk, item.pk])
        self.client.post(url, {"preference": "-1"})
        self.assertEqual(market.candidates(self.company), [])
        self.client.post(url, {"preference": "0"})
        self.assertEqual(len(market.candidates(self.company)), 1)
        stranger = get_user_model().objects.create_user(username="stranger")
        self.client.force_login(stranger)
        self.assertEqual(self.client.post(url, {"preference": "1"}).status_code, 404)
        self.assertEqual(self.client.get(reverse("engine:market_intelligence", args=[self.company.pk])).status_code, 404)

    @patch.dict(os.environ, {"VIRLO_API_KEY": "test"})
    def test_cadence_reuses_completed_run_between_research_days(self):
        from datetime import date
        run = self.request()
        run.status = "succeeded"
        run.save()
        monday = date(2026, 9, 21)
        created = timezone.now().replace(year=2026, month=9, day=21, hour=12)
        ScrapeRequest.objects.filter(pk=run.pk).update(created_at=created)
        with patch("engine.market.timezone.localdate", return_value=monday+timedelta(days=1)):
            self.assertEqual(market.start(self.company).pk, run.pk)
            self.assertEqual(market.cycle_day(), monday)

    @patch("engine.virlo.api")
    def test_reconcile_unknown_start_requires_matching_company_config(self, api):
        from django.core.management import call_command, CommandError
        run = self.request()
        run.actor_run_id, run.status = None, "unknown"
        run.inputs.update(intent="Golf research")
        run.save()
        api.return_value = ({"id": "verified-agent", "is_recurring": False, "platforms": ["instagram"],
            "meta_ads_enabled": True, "intent": "Wrong company", "keywords": run.inputs["keywords"]}, None)
        with self.assertRaises(CommandError):
            call_command("reconcile_market", company=str(self.company.pk), request=run.pk, agent="verified-agent")
        api.return_value[0]["intent"] = "Golf research"
        call_command("reconcile_market", company=str(self.company.pk), request=run.pk, agent="verified-agent", verbosity=0)
        run.refresh_from_db()
        self.assertEqual(run.status, "running")
        self.assertIsNone(run.cost_usd)

    @patch("engine.openrouter.structured_analysis")
    def test_only_qualified_candidates_get_cached_analysis(self, analyze):
        run = self.request()
        market.ingest(run, [self.video(), self.video("NORMAL", views=1)], [], [])
        analyze.return_value = (Mock(model_dump=lambda: {"profile_relevance": 3, "mechanisms": ["instruktion"]}), {})
        self.assertEqual(market.analyze_top(self.company), 1)
        self.assertEqual(market.analyze_top(self.company), 0)
        self.assertEqual(analyze.call_count, 1)
        self.assertEqual(AnalysisMemo.objects.count(), 1)

    @patch("engine.openrouter.structured_analysis", side_effect=RuntimeError("secret response"))
    def test_unknown_analysis_is_not_repeated(self, analyze):
        analyze.side_effect.retryable = True  # OpenRouter marks routing errors retryable.
        run = self.request()
        market.ingest(run, [self.video()], [], [])
        with self.assertRaises(RuntimeError):
            market.analyze_top(self.company)
        AnalysisMemo.objects.update(last_attempt_at=timezone.now()-timedelta(days=1))
        with self.assertRaises(ValueError):
            market.analyze_top(self.company)
        self.assertEqual(analyze.call_count, 1)

    @patch.dict(os.environ, {"VIRLO_API_KEY": "test", "SCRAPER_DAILY_BUDGET_USD": "1"})
    @patch("engine.openrouter.structured_analysis")
    @patch("engine.virlo.rows")
    @patch("engine.virlo.api")
    def test_existing_daily_runner_completes_research_once(self, api, rows, analyze):
        from .daily import run_daily, Stage
        api.side_effect = [({"keywords": ["golf greenfee"], "quality": {"passes": True}}, Decimal(0)),
            ({"id": "agent-daily"}, Decimal(".50")),
            ({"finalized": True, "latest_run": {"status": "completed"}}, None)]
        rows.side_effect = [[self.video()], [], []]
        analyze.return_value = (Mock(model_dump=lambda: {"profile_relevance": 3, "mechanisms": ["instruktion"]}), {})
        stages = [Stage("market_intelligence", market.daily_units)]
        run = run_daily(company_id=self.company.pk, wait_seconds=0, stages=stages)
        self.assertEqual(run.status, "success")
        run_daily(company_id=self.company.pk, wait_seconds=0, stages=stages)
        self.assertEqual(api.call_count, 3)
        self.assertEqual(ScrapeRequest.objects.count(), 1)
        self.assertEqual(len(market.signals(self.company, "organic")), 1)

    def test_paid_generation_keeps_ads_in_market_evidence_only(self):
        from .operator_content import _build_snapshot
        item = self.item(code="8888", channel="paid")
        snapshot = _build_snapshot(self.company, "paid", f"market:{item.pk}")
        guidance = snapshot["generation_learning"]
        self.assertEqual(guidance["external_viral_performance"], [])
        self.assertEqual(guidance["market_evidence"][0]["id"], f"market:{item.pk}")
        self.assertEqual(guidance["performance"]["sample_size"], 0)

    def test_ui_renders_company_source_feedback_and_cost(self):
        self.item()
        response = self.client.get(reverse("engine:market_intelligence", args=[self.company.pk]))
        self.assertContains(response, "Marknadsinspiration")
        self.assertContains(response, "Inte relevant")
        self.assertContains(response, "Öppna original")
        self.assertContains(response, "$0.50")
        response = self.client.get(reverse("engine:market_intelligence", args=[self.other.pk]))
        self.assertNotContains(response, "Golfkuponger")


class VirloContractTests(TestCase):
    @patch.dict(os.environ, {"VIRLO_API_KEY": "test"})
    @patch("engine.virlo.requests.request")
    def test_cost_header_and_status_safety(self, request):
        request.return_value = Mock(status_code=200, headers={"X-Cost": "0.50"}, json=lambda: {"data": {"id": "agent"}})
        data, cost = virlo.api("POST", "/agents", json={})
        self.assertEqual(cost, Decimal(".50"))
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        for status in (401, 402, 429, 500, 302):
            request.return_value.status_code = status
            with self.assertRaises(ApifyError) as caught:
                virlo.api("POST", "/agents", json={})
            self.assertEqual(caught.exception.uncertain, status >= 500 or status < 400)
        request.side_effect = requests.Timeout("secret")
        with self.assertRaises(ApifyError) as caught:
            virlo.api("POST", "/agents", json={})
        self.assertTrue(caught.exception.uncertain)
        self.assertNotIn("secret", str(caught.exception))

    def test_invalid_ids_and_urls_rejected(self):
        for value in (None, "", "../../anything"):
            with self.assertRaises(ValueError):
                virlo.agent_path(value)
        self.assertIsNone(market.canonical("https://instagram.com.evil.test/reel/ABC/", "organic"))
        self.assertIsNone(market.canonical("javascript:alert(1)", "organic"))


class MarketReservationConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    @patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "1"})
    def test_simultaneous_dispatch_reserves_one_paid_start(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier, Lock
        from django.db import close_old_connections
        from .sync import dispatch
        user = get_user_model().objects.create_user(username="concurrent")
        company = Company.objects.create(owner=user, name="Concurrent")
        state = state_for(company, "virlo", "market")
        barrier, lock = Barrier(2), Lock()
        calls = []

        def send():
            with lock:
                calls.append(True)
            return {"id": "one-agent", "cost_usd": Decimal(".50")}

        def work():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return dispatch(state, "virlo/agents", "market", {}, provider="virlo", sender=send, max_cost=".50").pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda _: work(), range(2)))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(len(calls), 1)
