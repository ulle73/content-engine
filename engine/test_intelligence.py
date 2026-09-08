from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from . import apify
from .competitors import collect_import, instagram_username, normalize, start_import
from .models import Company, Competitor, CompetitorImport, CompetitorPost, CompetitorSnapshot, ContentEvent
from .signals import build_signal, momentum


class IntelligenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner@example.test")
        self.company = Company.objects.create(owner=self.user, name="Golf")
        self.account = Competitor.objects.create(company=self.company, name="Reference", username="reference_golf")
        self.now = timezone.now()
        self.row = {
            "usuario": "@reference_golf",
            "codigo": "TestCode",
            "link_post": "https://www.instagram.com/p/TestCode/",
            "data_criacao_iso": (self.now - timedelta(days=2)).isoformat(),
            "media_type": 8,
            "caption": {"text": "A practical golf question."},
            "itens_carrossel": [{}, {}, {}],
            "curtidas": 100,
            "comentarios": None,
            "visualizacoes": None,
        }

    def test_adapter_preserves_absent_metrics_formats_and_account_identity(self):
        item = normalize(self.row, apify.PRIMARY_ACTOR, self.account.username)
        self.assertEqual((item["format"], item["slide_count"]), ("carousel", 3))
        self.assertIsNone(item["metrics"]["comments"])
        self.assertIsNone(item["metrics"]["views"])
        for kind, expected in ((1, "image"), (2, "reel")):
            self.assertEqual(
                normalize({**self.row, "media_type": kind}, apify.PRIMARY_ACTOR, self.account.username)["format"],
                expected,
            )
        with self.assertRaises(ValueError):
            normalize(self.row, apify.PRIMARY_ACTOR, "someone_else")
        with self.assertRaises(ValueError):
            instagram_username("https://instagram.com.evil.test/reference_golf/")
        self.assertEqual(instagram_username("https://www.instagram.com/reference_golf/"), "reference_golf")
        fallback = {
            "ownerUsername": "reference_golf",
            "shortCode": "TestCode",
            "url": self.row["link_post"],
            "timestamp": self.row["data_criacao_iso"],
            "type": "Video",
            "caption": "Golf.",
            "likesCount": -1,
            "commentsCount": 0,
            "videoPlayCount": 500,
        }
        normalized = normalize(fallback, apify.FALLBACK_ACTOR, self.account.username)
        self.assertIsNone(normalized["metrics"]["likes"])
        self.assertEqual(normalized["metrics"]["comments"], 0)
        self.assertEqual(normalized["metrics"]["views"], 500)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.api")
    @patch("engine.apify.get_run")
    def test_import_is_idempotent_but_later_runs_add_observations(self, remote, report, items):
        remote.return_value = {
            "status": "SUCCEEDED",
            "defaultDatasetId": "dataset",
            "defaultKeyValueStoreId": "store",
            "finishedAt": self.now.isoformat(),
            "usageTotalUsd": 0.00005,
        }
        report.return_value = {"ok": True, "users": [{"user": self.account.username, "count": 1}]}
        items.return_value = [self.row]
        first = CompetitorImport.objects.create(
            competitor=self.account, actor=apify.PRIMARY_ACTOR, actor_run_id="first", status="running"
        )
        collect_import(first)
        collect_import(first)  # stale object also cannot duplicate committed observations
        self.assertEqual(CompetitorPost.objects.count(), 1)
        self.assertEqual(CompetitorSnapshot.objects.count(), 1)
        second = CompetitorImport.objects.create(
            competitor=self.account, actor=apify.PRIMARY_ACTOR, actor_run_id="second", status="running"
        )
        remote.return_value["finishedAt"] = (self.now + timedelta(days=1)).isoformat()
        items.return_value = [{**self.row, "curtidas": 150}]
        collect_import(second)
        self.assertEqual(CompetitorPost.objects.count(), 1)
        self.assertEqual(list(CompetitorSnapshot.objects.values_list("likes", flat=True)), [100, 150])

    @patch("engine.competitors.start_import")
    @patch("engine.apify.dataset_items")
    @patch("engine.apify.api")
    @patch("engine.apify.get_run")
    def test_succeeded_actor_with_partial_report_is_not_silently_complete(self, remote, report, items, start):
        remote.return_value = {
            "status": "SUCCEEDED",
            "defaultDatasetId": "d",
            "defaultKeyValueStoreId": "s",
            "finishedAt": self.now.isoformat(),
            "usageTotalUsd": 0.0018,
        }
        report.return_value = {"ok": True, "users": [{"user": self.account.username, "erro": "pagination failed"}]}
        items.return_value = [self.row]
        run = CompetitorImport.objects.create(
            competitor=self.account, actor=apify.PRIMARY_ACTOR, actor_run_id="partial", status="running"
        )
        result = collect_import(run)
        self.assertEqual(result.status, "partial")
        self.assertEqual(CompetitorSnapshot.objects.count(), 1)
        self.assertEqual(start.call_args.kwargs["actor"], apify.FALLBACK_ACTOR)

    def test_momentum_uses_real_intervals_and_never_invents_daily_history(self):
        def snap(day, likes):
            return SimpleNamespace(pk=day, observed_at=self.now + timedelta(days=day), likes=likes, comments=0)

        result = momentum([snap(0, 500), snap(1, 900), snap(2, 1500), snap(3, 2600)])
        self.assertEqual(result["label"], "Fortfarande accelererande")
        self.assertAlmostEqual(result["likes_percent"], 73.3)
        self.assertEqual(
            momentum([snap(0, 500), snap(1, 900), snap(2, 910)])["label"], "Tillväxten håller på att plana ut"
        )
        self.assertIsNone(momentum([snap(0, 500), snap(0.01, 600)])["growth"])

    @patch("engine.competitors.start_import")
    @patch("engine.apify.dataset_items")
    @patch("engine.apify.api")
    @patch("engine.apify.get_run")
    def test_minor_gaps_do_not_start_paid_fallback_but_unusable_import_does(self, remote, report, items, start):
        remote.return_value = {
            "status": "SUCCEEDED",
            "defaultDatasetId": "d",
            "defaultKeyValueStoreId": "s",
            "finishedAt": self.now.isoformat(),
            "usageTotalUsd": 0.001,
        }
        report.return_value = {"ok": True, "users": [{"user": self.account.username}]}
        valid = [
            {**self.row, "codigo": f"post{i}", "link_post": f"https://www.instagram.com/p/post{i}/"} for i in range(10)
        ]
        # Missing duration/views/comments are optional; one malformed item and one empty caption are tolerable.
        items.return_value = valid + [{"broken": True}, {**valid[0], "caption": None}]
        run = CompetitorImport.objects.create(
            competitor=self.account, actor=apify.PRIMARY_ACTOR, actor_run_id="minor", status="running"
        )
        result = collect_import(run)
        self.assertEqual(result.status, "partial")
        start.assert_not_called()
        self.account.refresh_from_db()
        self.assertEqual(self.account.last_success_at, self.now)
        # Even a final-page error is tolerable if almost all requested useful rows arrived.
        report.return_value["users"][0]["erro"] = "final page failed"
        items.return_value = valid[:9]
        run = CompetitorImport.objects.create(
            competitor=self.account,
            actor=apify.PRIMARY_ACTOR,
            actor_run_id="almost-all",
            status="running",
            requested_limit=10,
        )
        self.assertEqual(collect_import(run).status, "partial")
        start.assert_not_called()
        items.return_value = [{**p, "caption": None} for p in valid]
        run = CompetitorImport.objects.create(
            competitor=self.account, actor=apify.PRIMARY_ACTOR, actor_run_id="unusable", status="running"
        )
        collect_import(run)
        start.assert_called_once()

    @patch("engine.apify.start_actor")
    def test_daily_fallback_keeps_small_limit_and_uncertain_start_is_not_repeated(self, start):
        previous = CompetitorImport.objects.create(
            competitor=self.account, actor=apify.PRIMARY_ACTOR, status="failed", requested_limit=30
        )
        start.side_effect = apify.ApifyError("Unconfirmed", uncertain=True)
        with self.assertRaises(apify.ApifyError):
            start_import(self.account, actor=apify.FALLBACK_ACTOR, fallback_of=previous)
        self.assertEqual(start.call_args.args[-1], 30)
        existing = start_import(self.account)
        self.assertEqual(existing.status, "unknown")
        start.assert_called_once()

    def test_cold_start_baseline_is_conservative_then_replaced_by_age_matched(self):
        target = SimpleNamespace(pk=0, competitor_id=1, format="reel", published_at=self.now - timedelta(hours=12))
        posts = [target]

        def snapshot(pk, observed, likes):
            return SimpleNamespace(pk=pk, observed_at=observed, likes=likes, comments=0, views=None, view_metric="")

        observations = {0: [snapshot(0, self.now, 300)]}
        for i in range(1, 7):
            peer = SimpleNamespace(pk=i, competitor_id=1, format="reel", published_at=self.now - timedelta(days=30 + i))
            posts.append(peer)
            observations[i] = [snapshot(i, self.now, 100)]
        result = build_signal(target, posts, observations, self.now)
        self.assertEqual(result["baseline_type"], "mature_low_confidence")
        self.assertEqual(result["relative"], 3)
        self.assertLessEqual(result["confidence"], 0.25)
        self.assertEqual(result["age_matched_sample_size"], 0)
        for peer in posts[1:]:
            observations[peer.pk].insert(0, snapshot(peer.pk + 10, peer.published_at + timedelta(hours=12), 50))
        result = build_signal(target, posts, observations, self.now)
        self.assertEqual(result["baseline_type"], "age_matched")
        self.assertEqual(result["relative"], 6)
        self.assertGreater(result["confidence"], 0.25)
        self.assertTrue(all(pk > 10 for pk in result["baseline_snapshot_ids"]))

    def test_relative_performance_compares_account_format_and_age(self):
        posts, observations = [], {}
        for index in range(7):
            p = SimpleNamespace(pk=index, competitor_id=1, format="image", published_at=self.now - timedelta(days=2))
            posts.append(p)
            observations[index] = [
                SimpleNamespace(
                    pk=index,
                    observed_at=self.now,
                    likes=300 if index == 0 else 100,
                    comments=0,
                    views=None,
                    view_metric="",
                )
            ]
        result = build_signal(posts[0], posts, observations, self.now)
        self.assertEqual(result["relative"], 3)
        posts[1].competitor_id = 2
        posts[2].format = "reel"
        posts[3].published_at = self.now - timedelta(days=30)
        result = build_signal(posts[0], posts, observations, self.now)
        self.assertIsNone(result["relative"])
        self.assertEqual(result["sample_size"], 3)

    def test_dashboard_and_actions_are_company_scoped(self):
        self.client.force_login(self.user)
        base = f"/company/{self.company.pk}/intelligence/"
        self.assertContains(self.client.get(base), "Konton att lära av")
        stranger = get_user_model().objects.create_user(username="other@example.test")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(base).status_code, 404)
        self.assertEqual(self.client.post(base + f"accounts/{self.account.pk}/", {"action": "toggle"}).status_code, 404)
        self.assertEqual(self.client.post(base + "refresh/").status_code, 404)
        self.assertEqual(ContentEvent.objects.count(), 0)
