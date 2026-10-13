from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from . import ads
from .models import AdAccount, AdObservation, Company, CompetitorAd, ScrapeRequest


def library_row(ad_id="2174315879717141", page_id="148068018677367", **extra):
    """Trimmed real row from curious_coder/facebook-ads-library-scraper (Xenonkungen, 2026-10-13)."""
    row = {
        "ad_archive_id": ad_id, "collation_count": 3, "is_active": True, "page_id": page_id,
        "page_name": "Xenonkungen", "start_date": 1755154800, "end_date": 1771660800,
        "publisher_platform": ["FACEBOOK", "INSTAGRAM"], "total": 228,
        "ad_library_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
        "snapshot": {
            "page_id": page_id, "page_name": "Xenonkungen", "caption": "www.xenonkungen.com",
            "cta_text": "Shop now", "cta_type": "SHOP_NOW", "display_format": "VIDEO",
            "body": {"text": "Bättre sikt, ökad säkerhet och en fantastisk körupplevelse"},
            "title": "Uppgradera din Bilbelysning", "link_description": "Säkerhet i fokus",
            "link_url": "https://www.xenonkungen.com/", "images": [], "cards": [],
            "videos": [{"video_hd_url": None, "video_sd_url": "https://video.fbcdn.net/v/abc.mp4?sig=1",
                        "video_preview_image_url": "https://scontent.fbcdn.net/p.jpg"}],
        },
        "aaa_info": {"eu_total_reach": 39199},
    }
    row.update(extra)
    return row


class LibraryActorTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="lib")
        self.company = Company.objects.create(owner=user, name="Faiv", profile="Extraljus.", current="Grillkit.")
        self.account = AdAccount.objects.create(company=self.company, name="Xenonkungen",
                                                page_url="https://www.facebook.com/148068018677367",
                                                page_id="148068018677367")
        self.now = timezone.now()

    def request(self, account, remote_id="r1", limit=50):
        state = ads.account_state(account)
        return ScrapeRequest.objects.create(state=state, key=remote_id, actor=ads.ACTOR, mode="backfill",
                                            max_cost_usd=.07, inputs={"count": limit}, status="running",
                                            actor_run_id=remote_id, dataset_id="d")

    def remote(self):
        return {"status": "SUCCEEDED", "finishedAt": self.now.isoformat(), "usageTotalUsd": .008}

    def test_row_gives_video_format_dates_and_reach(self):
        item = ads.normalize(library_row(), self.account)
        creative = item["creative"]
        self.assertEqual(creative["format"], "video")
        self.assertEqual(creative["video_url"], "https://video.fbcdn.net/v/abc.mp4?sig=1")
        self.assertEqual(creative["image_url"], "https://scontent.fbcdn.net/p.jpg")
        self.assertEqual(creative["variant_count"], 3)
        self.assertEqual(creative["advertiser"], "Xenonkungen")
        self.assertEqual(str(item["start_date"]), "2025-08-14")
        self.assertEqual(ads.metrics(library_row())["eu_total_reach"], 39199)
        self.assertEqual(ads.metrics(library_row())["advertiser_total_ads"], 228)
        # Signed CDN links change every fetch; the ad must not look changed because of them.
        resigned = library_row()
        resigned["snapshot"]["videos"][0]["video_sd_url"] = "https://video.fbcdn.net/v/abc.mp4?sig=2"
        self.assertEqual(ads.normalize(resigned, self.account)["creative_hash"], item["creative_hash"])
        with self.assertRaises(ValueError):
            ads.normalize(library_row(page_id="999"), self.account)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_reaching_the_limit_is_complete_for_top_by_impressions(self, remote, items):
        remote.return_value = self.remote()
        items.return_value = [library_row(ad_id=str(1000 + i)) for i in range(5)]
        run = ads.collect(self.request(self.account, limit=5), self.account)
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(ads.account_state(self.account).coverage, "top_impressions")
        self.assertEqual(AdObservation.objects.first().data["metrics"]["eu_total_reach"], 39199)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_page_url_account_learns_its_page_id(self, remote, items):
        account = AdAccount.objects.create(company=self.company, name="Lumise",
                                           page_url="https://www.facebook.com/Lumise.se")
        remote.return_value = self.remote()
        items.return_value = [library_row(ad_id="1", page_id="555"), library_row(ad_id="2", page_id="555")]
        ads.collect(self.request(account), account)
        account.refresh_from_db()
        self.assertEqual(account.page_id, "555")
        self.assertEqual(CompetitorAd.objects.filter(account=account).count(), 2)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_keyword_account_keeps_every_advertiser(self, remote, items):
        account = AdAccount.objects.create(company=self.company, name="Sökord: extraljus",
                                           page_url=ads.keyword_url("extraljus"))
        self.assertTrue(ads.is_keyword(account))
        self.assertIn("q=extraljus", ads.library_url(account))
        remote.return_value = self.remote()
        items.return_value = [library_row(ad_id="1", page_id="555"), library_row(ad_id="2", page_id="777")]
        run = ads.collect(self.request(account), account)
        account.refresh_from_db()
        self.assertEqual(account.page_id, "")
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(ads.account_state(account).coverage, "keyword_top_impressions")
        self.assertEqual(CompetitorAd.objects.filter(account=account).count(), 2)

    @patch("engine.apify.api")
    def test_start_uses_page_url_or_keyword_without_page_id(self, api):
        api.return_value = {"data": {"id": "x", "defaultDatasetId": "d"}}
        account = AdAccount.objects.create(company=self.company, name="Sökord",
                                           page_url=ads.keyword_url("friskvårdsbidrag"))
        request = ads.start(account)
        self.assertIn("q=friskv%C3%A5rdsbidrag", request.inputs["urls"][0]["url"])
        self.assertEqual(request.actor, ads.ACTOR)
        self.assertEqual(api.call_args.kwargs["params"]["maxTotalChargeUsd"], float(request.max_cost_usd))
        self.assertTrue(self.now - timedelta(minutes=1) < request.created_at)
