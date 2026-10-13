from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from . import apify
from .competitors import collect_import, normalize_tiktok, start_import, tiktok_username
from .models import Company, Competitor, CompetitorImport, CompetitorPost


def tiktok_row(video_id="7679047540590857494", username="timeplango", views=203376, title=""):
    """Trimmed real row from apidojo/tiktok-scraper (Timeplan, 2026-10-13)."""
    return {
        "id": video_id, "title": title, "views": views, "likes": 8779, "comments": 13, "shares": 7856,
        "channel": {"username": username, "name": "Timeplan", "followers": 192},
        "uploadedAtFormatted": "2026-08-28T11:46:29.000Z",
        "video": {"width": 576, "height": 1024, "duration": 6.3, "url": "https://v45.tiktokcdn-eu.com/x.mp4"},
        "postPage": f"https://www.tiktok.com/@{username}/video/{video_id}",
    }


class TikTokTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="tt")
        self.company = Company.objects.create(owner=user, name="Golfkuponger")
        self.account = Competitor.objects.create(company=self.company, name="Timeplan", platform="tiktok",
                                                 username="timeplango")

    def test_usernames_and_platform_urls(self):
        self.assertEqual(tiktok_username("https://www.tiktok.com/@TimeplanGo"), "timeplango")
        self.assertEqual(tiktok_username("@melkersqueens"), "melkersqueens")
        with self.assertRaises(ValueError):
            tiktok_username("https://evil.example/@x")
        self.assertEqual(self.account.url, "https://www.tiktok.com/@timeplango")
        # The same handle may be followed on Instagram and TikTok.
        Competitor.objects.create(company=self.company, name="Timeplan IG", username="timeplango")

    def test_row_keeps_views_without_caption(self):
        item = normalize_tiktok(tiktok_row(), "timeplango")
        self.assertEqual(item["metrics"]["views"], 203376)
        self.assertEqual(item["format"], "reel")
        self.assertEqual(item["duration_seconds"], 6.3)
        self.assertEqual(item["url"], "https://www.tiktok.com/@timeplango/video/7679047540590857494")
        with self.assertRaises(ValueError):
            normalize_tiktok(tiktok_row(username="someoneelse"), "timeplango")

    @patch("engine.apify.start_actor")
    def test_start_uses_the_tiktok_actor_with_a_small_reservation(self, start):
        start.return_value = {"id": "run", "defaultDatasetId": "d"}
        run = start_import(self.account)
        self.assertEqual(run.actor, apify.TIKTOK_ACTOR)
        self.assertEqual(start.call_args.kwargs["inputs"], {"startUrls": ["https://www.tiktok.com/@timeplango"],
                                                            "maxItems": 100})
        self.assertLessEqual(run.scrape_request.max_cost_usd, 0.05)
        self.assertEqual(run.scrape_request.state.source, "tiktok")

    @patch("engine.competitors.start_import")
    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_collect_saves_videos_and_never_starts_the_instagram_fallback(self, remote, items, fallback):
        run = CompetitorImport.objects.create(competitor=self.account, actor=apify.TIKTOK_ACTOR, status="running",
                                              actor_run_id="run", requested_limit=10, sync_mode="backfill")
        remote.return_value = {"status": "SUCCEEDED", "finishedAt": timezone.now().isoformat(),
                               "usageTotalUsd": 0.001, "defaultDatasetId": "d"}
        items.return_value = [tiktok_row(), tiktok_row(video_id="1", views=900)]
        done = collect_import(run)
        self.assertEqual(done.status, "succeeded")
        self.assertEqual(CompetitorPost.objects.filter(competitor=self.account).count(), 2)
        post = CompetitorPost.objects.get(shortcode="7679047540590857494")
        self.assertEqual(post.snapshots.get().views, 203376)
        fallback.assert_not_called()


class InstagramFallbackTests(TestCase):
    @patch("engine.competitors.start_import")
    @patch("engine.apify.dataset_items")
    @patch("engine.apify.api")
    @patch("engine.apify.get_run")
    def test_expensive_fallback_is_off_by_default(self, remote, report, items, start):
        user = get_user_model().objects.create_user(username="ig")
        company = Company.objects.create(owner=user, name="Faiv")
        account = Competitor.objects.create(company=company, name="X", username="x")
        run = CompetitorImport.objects.create(competitor=account, actor=apify.PRIMARY_ACTOR, status="running",
                                              actor_run_id="r", requested_limit=10, sync_mode="discovery")
        remote.return_value = {"status": "FAILED", "finishedAt": (timezone.now() - timedelta(minutes=1)).isoformat(),
                               "usageTotalUsd": 0.0, "defaultDatasetId": "d"}
        items.return_value = []
        collect_import(run)
        start.assert_not_called()
