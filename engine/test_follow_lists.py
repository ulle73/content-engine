from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import follow_lists
from .models import AdAccount, Company, Competitor


class FollowListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", password="x")
        self.faiv = Company.objects.create(owner=self.user, name="FAIV")
        self.other = Company.objects.create(owner=self.user, name="Sänk Dig Golf")

    def test_matches_by_alias_or_brand_kit(self):
        self.assertEqual(follow_lists.for_company(self.faiv)["company"], "faiv")
        self.assertIsNone(follow_lists.for_company(self.other))
        self.other.brand = {"follow_list": "golfkuponger"}
        self.assertEqual(follow_lists.for_company(self.other)["company"], "golfkuponger")

    def test_apply_adds_only_missing_and_is_idempotent(self):
        Competitor.objects.create(company=self.faiv, name="Befintlig", username="vparts", active=False)
        with patch("engine.follow_lists.start_import") as start:
            result = follow_lists.apply(self.faiv)
        self.assertEqual(result["instagram"], 8)
        self.assertEqual(result["ad_pages"], 20)  # 18 pages + 2 keyword searches
        self.assertTrue(AdAccount.objects.filter(company=self.faiv, name__startswith="Sökord: extraljus",
                                                 page_url__contains="q=extraljus").exists())
        self.assertTrue(AdAccount.objects.filter(company=self.faiv, page_id="",
                                                 page_url="https://www.facebook.com/Lazerlamps/").exists())
        self.assertEqual(start.call_count, 8)
        self.assertFalse(Competitor.objects.get(company=self.faiv, username="vparts").active)
        self.assertTrue(AdAccount.objects.filter(company=self.faiv, page_id="133016172910", country="NO").exists())
        with patch("engine.follow_lists.start_import"):
            again = follow_lists.apply(self.faiv)
        self.assertEqual((again["instagram"], again["ad_pages"]), (0, 0))
        self.assertEqual(follow_lists.missing(self.faiv)["instagram"], [])
        self.assertEqual(follow_lists.missing(self.faiv)["ad_keywords"], [])

    def test_tiktok_accounts_live_next_to_instagram(self):
        golf = Company.objects.create(owner=self.user, name="Golfkuponger")
        with patch("engine.follow_lists.start_import"):
            result = follow_lists.apply(golf)
        self.assertEqual((result["instagram"], result["tiktok"]), (4, 9))
        self.assertTrue(Competitor.objects.filter(company=golf, platform="tiktok", username="standregolf").exists())
        self.assertTrue(Competitor.objects.filter(company=golf, platform="instagram", username="standregolf").exists())
        self.assertTrue(AdAccount.objects.filter(company=golf, page_url__contains="q=friskv").exists())
        with patch("engine.follow_lists.start_import"):
            self.assertEqual(follow_lists.apply(golf)["accounts"], 0)

    def test_view_requires_post_and_company_access(self):
        self.client.force_login(self.user)
        url = reverse("engine:apply_follow_list", kwargs={"workspace_id": self.faiv.pk})
        self.assertEqual(self.client.get(url).status_code, 405)
        with patch("engine.follow_lists.start_import"):
            response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.faiv.competitors.count(), 9)
        stranger = get_user_model().objects.create_user("stranger", password="x")
        self.client.force_login(stranger)
        self.assertIn(self.client.post(url).status_code, (302, 403, 404))
        self.assertEqual(self.faiv.competitors.count(), 9)

    def test_intelligence_page_shows_start_list_until_applied(self):
        self.client.force_login(self.user)
        page = reverse("engine:intelligence", kwargs={"workspace_id": self.faiv.pk})
        self.assertContains(self.client.get(page), "Lägg till startlistan")
        with patch("engine.follow_lists.start_import"):
            follow_lists.apply(self.faiv)
        self.assertNotContains(self.client.get(page), "Lägg till startlistan")
