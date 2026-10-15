"""Monitoring v2: one Apify run per company, a start phase before the full run, and a readiness checklist."""
import os
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import apify
from .models import AdAccount, Company, Competitor, CompetitorImport, CompetitorPost, DailyRun, ScrapeRequest


def ig_row(username, code, now):
    return {"usuario": f"@{username}", "codigo": code, "link_post": f"https://www.instagram.com/reel/{code}/",
            "data_criacao_iso": (now - timedelta(days=3)).isoformat(), "media_type": 2,
            "caption": {"text": "Extraljus i mörkret."}, "curtidas": 50, "comentarios": 2, "visualizacoes": None}


class FakeApify:
    """Routes apify.api calls: one POST starts a run, OUTPUT reports every user as fine."""

    def __init__(self):
        self.posts = []

    def __call__(self, method, path, **kwargs):
        if method == "POST":
            self.posts.append(kwargs)
            return {"data": {"id": f"run{len(self.posts)}", "defaultDatasetId": f"ds{len(self.posts)}"}}
        if path.endswith("/records/OUTPUT"):
            return {"ok": True, "users": [{"user": u} for u in ("ljusgiganten.se", "vparts", "xenonkungen.se")]}
        raise AssertionError(path)


@patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "0.50"}, clear=False)
class InstagramBatchTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="batch-ig")
        self.company = Company.objects.create(owner=user, name="Faiv")
        self.accounts = [Competitor.objects.create(company=self.company, name=n, username=n)
                         for n in ("ljusgiganten.se", "vparts", "xenonkungen.se")]
        self.now = timezone.now()

    def test_due_accounts_share_one_run_and_each_collects_its_own_rows(self):
        from .competitors import collect_import, start_batch

        fake = FakeApify()
        with patch("engine.apify.api", fake):
            started = start_batch(self.accounts)
        self.assertEqual(len(fake.posts), 1)
        body = fake.posts[0]["json"]
        self.assertEqual(body["directUrls"], ["ljusgiganten.se", "vparts", "xenonkungen.se"])
        self.assertEqual(body["resultsLimitPerProfile"], {"ljusgiganten.se": 100, "vparts": 100, "xenonkungen.se": 100})
        self.assertNotIn("_max_items", body)
        self.assertEqual(fake.posts[0]["params"]["maxTotalChargeUsd"], 0.06)  # three 0.02 caps
        self.assertEqual(fake.posts[0]["params"]["timeout"], 300 + 3 * 90)  # room for every account, not 300 s
        self.assertEqual({r.actor_run_id for r in started}, {"run1"})
        self.assertEqual(ScrapeRequest.objects.filter(actor_run_id="run1").count(), 3)

        rows = [ig_row("ljusgiganten.se", f"a{i}", self.now) for i in range(6)] + \
               [ig_row("vparts", f"b{i}", self.now) for i in range(4)]  # xenonkungen got nothing
        remote = {"status": "SUCCEEDED", "defaultDatasetId": "ds1", "defaultKeyValueStoreId": "kv",
                  "finishedAt": self.now.isoformat(), "usageTotalUsd": 0.001}
        apify._finished_datasets.clear()
        with patch("engine.apify.api", fake), patch("engine.apify.get_run", return_value=remote), \
                patch("engine.apify._read_dataset", return_value=rows) as read:
            done = {run.competitor.username: collect_import(run) for run in started}
        read.assert_called_once()  # one read of the shared dataset serves all three accounts
        self.assertEqual(CompetitorPost.objects.filter(competitor=self.accounts[0]).count(), 6)
        self.assertEqual(CompetitorPost.objects.filter(competitor=self.accounts[1]).count(), 4)
        self.assertEqual(done["ljusgiganten.se"].skipped_count, 0)  # other accounts' rows are not "skipped"
        self.assertEqual(done["ljusgiganten.se"].cost_usd, Decimal("0.000600"))
        self.assertEqual(done["vparts"].cost_usd, Decimal("0.000400"))

    def test_an_account_with_an_open_import_keeps_it_and_a_batch_of_one_is_an_ordinary_start(self):
        from .competitors import start_batch

        CompetitorImport.objects.create(competitor=self.accounts[0], actor=apify.PRIMARY_ACTOR, actor_run_id="old",
                                        status="running")
        CompetitorImport.objects.create(competitor=self.accounts[1], actor=apify.PRIMARY_ACTOR, actor_run_id="old2",
                                        status="running")
        fake = FakeApify()
        with patch("engine.apify.api", fake), patch("engine.apify.start_actor",
                                                     return_value={"id": "single", "defaultDatasetId": "d"}) as single:
            started = start_batch(self.accounts)
        self.assertEqual(fake.posts, [])
        single.assert_called_once()
        self.assertEqual([r.actor_run_id for r in started], ["single"])

    def test_budget_counts_the_whole_batch_and_refuses_it_whole(self):
        from .competitors import start_batch

        with patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "0.05"}), patch("engine.apify.api", FakeApify()):
            with self.assertRaises(apify.BudgetExceeded):
                start_batch(self.accounts)
        self.assertFalse(ScrapeRequest.objects.exists())
        self.assertEqual(set(CompetitorImport.objects.values_list("status", flat=True)), {"failed"})

    def test_daily_unit_starts_the_batch_before_the_accounts_collect(self):
        from .daily_stages import competitor_units

        units = competitor_units(self.company)
        self.assertEqual(units[0][0], "batch")
        self.assertEqual(len(units), 4)
        with patch("engine.apify.api", FakeApify()):
            result = units[0][1]()
        self.assertEqual((result.status, result.data["runs"]), ("success", ["run1"]))


@patch.dict(os.environ, {"SCRAPER_DAILY_BUDGET_USD": "0.50"}, clear=False)
class AdsBatchTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="batch-ads")
        self.company = Company.objects.create(owner=user, name="Faiv")
        self.se = [AdAccount.objects.create(company=self.company, name=f"S{i}", country="SE", page_id=str(1000 + i),
                                            page_url=f"https://www.facebook.com/{1000 + i}") for i in range(3)]
        self.no = AdAccount.objects.create(company=self.company, name="N", country="NO", page_id="2000",
                                           page_url="https://www.facebook.com/2000")
        self.keyword = AdAccount.objects.create(
            company=self.company, name="Sökord", country="SE",
            page_url="https://www.facebook.com/ads/library/?active_status=active&q=extraljus&search_type=keyword_unordered")

    def test_pages_share_a_run_per_country_and_keyword_searches_stay_single(self):
        from . import ads

        fake = FakeApify()
        with patch("engine.apify.api", fake):
            started = ads.start_batch([*self.se, self.no, self.keyword])
        self.assertEqual(len(fake.posts), 1)  # Norway alone and the keyword search use the ordinary start
        body = fake.posts[0]["json"]
        self.assertEqual(len(body["urls"]), 3)
        self.assertEqual((body["scrapePageAds.countryCode"], body["limitPerSource"], body["count"]), ("SE", 50, 150))
        self.assertEqual(len(started), 3)

        now = timezone.now()
        rows = [{"ad_archive_id": f"{p.page_id}{i}", "page_id": p.page_id, "start_date": int((now - timedelta(days=40)).timestamp()),
                 "snapshot": {"body": {"text": "Ljus"}, "display_format": "VIDEO", "page_name": p.name}}
                for p, n in zip(self.se, (5, 3, 0)) for i in range(n)]
        remote = {"status": "SUCCEEDED", "finishedAt": now.isoformat(), "usageTotalUsd": 0.008}
        apify._finished_datasets.clear()
        with patch("engine.apify.get_run", return_value=remote), patch("engine.apify._read_dataset", return_value=rows):
            collected = {p.pk: ads.collect(started[i], p) for i, p in enumerate(self.se)}
        self.assertEqual(collected[self.se[0].pk].result["saved"], 5)
        self.assertEqual(collected[self.se[0].pk].result["excluded_other_advertisers"], 0)
        self.assertEqual(collected[self.se[1].pk].result["saved"], 3)
        self.assertEqual(collected[self.se[0].pk].cost_usd, Decimal("0.005000"))
        self.assertEqual(collected[self.se[1].pk].cost_usd, Decimal("0.003000"))


class StartPhaseTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="phase")
        self.company = Company.objects.create(owner=user, name="Golf", profile="Golf", current="Kuponger")

    def test_start_phase_runs_only_the_import_stages_once(self):
        from .daily_stages import START_STAGES

        self.assertEqual([s.name for s in START_STAGES], ["competitor_import", "ads_import"])
        with patch("engine.management.commands.run_daily.run_daily", wraps=None) as run:
            run.return_value = DailyRun.objects.create(day=timezone.localdate(), status="partial", summary={})
            call_command("run_daily", "--phase", "start", stdout=StringIO())
        self.assertEqual(run.call_args.kwargs["wait_seconds"], 0)
        self.assertEqual(run.call_args.kwargs["stages"], START_STAGES)

    def test_full_phase_resumes_the_days_ledger_and_collects_what_the_start_phase_left_pending(self):
        from .daily import Result, Stage, run_daily

        calls = []

        def units(company):
            def work():
                calls.append(len(calls))
                return Result("pending" if len(calls) == 1 else "success", "x")
            return [("job", work)]

        stages = [Stage("competitor_import", units)]
        first = run_daily(wait_seconds=0, stages=stages)
        second = run_daily(wait_seconds=0, stages=stages)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.steps.get(key="job").status, "success")


class ReadinessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ready")
        self.company = Company.objects.create(owner=self.user, name="Faiv")
        Competitor.objects.create(company=self.company, name="Ljus", username="ljus")
        AdAccount.objects.create(company=self.company, name="S", page_id="1", page_url="https://www.facebook.com/1")

    def test_missing_profile_is_a_visible_attention_step_not_a_silent_zero(self):
        from .daily_stages import ads_analysis_units, analysis_units

        for factory in (analysis_units, ads_analysis_units):
            [(key, work)] = factory(self.company)
            result = work()
            self.assertEqual((key, result.status), ("needs-profile", "attention"))
            self.assertIn("Företagsprofil och Aktuellt", result.message)

    def test_checklist_names_what_is_missing(self):
        from .readiness import checklist

        items = {i["key"]: i for i in checklist(self.company)}
        self.assertFalse(items["profile"]["ok"])
        self.assertFalse(items["own"]["ok"])
        self.assertIn("1 av minst 10", items["accounts"]["detail"])
        self.company.profile, self.company.current = "FAIV säljer extraljus.", "Mörkerperioden."
        self.company.save()
        items = {i["key"]: i for i in checklist(self.company)}
        self.assertTrue(items["profile"]["ok"] and items["current"]["ok"])

    def test_settings_and_insights_show_it(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("engine:settings", kwargs={"workspace_id": self.company.pk}))
        self.assertContains(page, "Redo för bevakning")
        self.assertContains(page, "Saknas")
        page = self.client.get(reverse("engine:intelligence", kwargs={"workspace_id": self.company.pk}))
        self.assertContains(page, "Analysen är pausad")
