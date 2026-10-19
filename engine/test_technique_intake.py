"""Acceptance checks for link -> review -> company-scoped Content Library techniques."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from engine.ad_studio import library as catalog
from engine.models import Company
from engine.techniques import service
from engine.techniques.models import StoredTechnique, TechniqueImport


def suggestion(name="Handheld follow"):
    return service.Suggestion(
        name=name, role="kamera", medium="video",
        description="Följ golfaren med lätt naturlig handkamera i rörelse.",
        how="En person följer golfaren med små mänskliga korrigeringar.",
        when="När klippet ska kännas som äkta vardagsfilm.",
        camera_prompt="natural handheld tracking with slight micro shake",
        timing="3–5 sekunder", example="En golfare går från fairway mot green.",
        evidence="Handhållen kamerarörelse illustreras i källmaterialet.",
        tags=["handheld", "kamera", "realism"],
    )


class TechniqueIntakeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="techowner", password="test-owner")
        cls.other_user = User.objects.create_user(username="othertech", password="test-other")
        cls.company = Company.objects.create(name="Golfkuponger", owner=cls.user, profile="Golfklubbar")
        cls.other_company = Company.objects.create(name="Annan", owner=cls.other_user)

    def _propose(self, name="Handheld follow"):
        with patch("engine.techniques.service._page_text", return_value="En artikel om filmteknik. " * 20), patch(
            "engine.techniques.service.structured_generation",
            return_value=(service.Suggestions(techniques=[suggestion(name)]), {"cost_usd": 0.002}),
        ) as model:
            batch = service.propose(self.company, self.user, "https://example.org/techniques")
        return batch, model

    def test_suggestions_are_staged_without_saving_and_reused_without_another_charge(self):
        batch, model = self._propose()
        self.assertEqual(batch.status, "review")
        self.assertEqual(batch.analysis_cost_usd, Decimal("0.002"))
        self.assertEqual(StoredTechnique.objects.count(), 0)
        self.assertEqual(model.call_count, 1)
        with patch("engine.techniques.service._page_text", side_effect=AssertionError("refetch")):
            again = service.propose(self.company, self.user, batch.source_url)
        self.assertEqual(batch.pk, again.pk)

    def test_only_selected_approved_techniques_enter_catalog_and_idempotent(self):
        batch, _ = self._propose()
        saved = service.approve(self.company, self.user, str(batch.pk), [0])
        self.assertEqual(len(saved["added"]), 1)
        self.assertEqual(StoredTechnique.objects.count(), 1)
        results = catalog.search("Handheld", type="technique", company=self.company)["results"]
        self.assertIn(saved["added"][0], [item["id"] for item in results])
        item = catalog.get(saved["added"][0], company=self.company)
        self.assertIn("natural handheld", item["technique_detail"]["camera_prompt"])
        self.assertEqual(service.approve(self.company, self.user, str(batch.pk), [0])["saved"], saved["saved"])
        self.assertEqual(StoredTechnique.objects.count(), 1)

    def test_tenant_isolation_in_batch_approval_and_search(self):
        batch, _ = self._propose()
        with self.assertRaises(ValueError):
            service.owned(self.other_company, str(batch.pk))
        with self.assertRaises(ValueError):
            service.approve(self.other_company, self.other_user, str(batch.pk), [0])
        service.approve(self.company, self.user, str(batch.pk), [0])
        self.assertEqual(
            [x for x in catalog.search("Handheld", type="technique", company=self.other_company)["results"]
             if x["id"].startswith("teknik.company.")], [],
        )
        with self.assertRaises(ValueError):
            catalog.get("teknik.company.handheld-follow", company=self.other_company)

    def test_invalid_selections_cannot_approve(self):
        batch, _ = self._propose()
        for bad in ([], [-1], [1], [True], ["0"]):
            with self.assertRaises(ValueError):
                service.approve(self.company, self.user, str(batch.pk), bad)
        self.assertEqual(StoredTechnique.objects.count(), 0)

    def test_duplicate_is_flagged_then_not_saved(self):
        with patch("engine.techniques.service._existing", return_value=[
            {"id": "teknik.handheld-follow", "name": "Handheld follow", "description": "Kamera"}
        ]), patch("engine.techniques.service.structured_generation",
                    return_value=(service.Suggestions(techniques=[suggestion()]), {"cost_usd": 0})) as model:
            items, _ = service._propose(self.company, "Handheld from video", "https://example.org/")
            self.assertEqual(items[0]["duplicate_of"], "teknik.handheld-follow")
        batch = TechniqueImport.objects.create(
            company=self.company, author=self.user, source_url="https://another.example/", source_kind="page",
            suggestions=items,
        )
        self.assertEqual(service.approve(self.company, self.user, str(batch.pk), [0])["added"], [])
        self.assertEqual(StoredTechnique.objects.count(), 0)

    def test_ssrf_protections_reject_ip_credentials_and_non_public_dns(self):
        for url in (
            "http://example.com/", "https://127.0.0.1/admin", "https://localhost/admin",
            "https://user:password@example.com/", "https://example.com:8443/",
        ):
            with self.assertRaises(ValueError, msg=url):
                service.normalize_url(url)
        with patch("engine.techniques.service.socket.getaddrinfo",
                   return_value=[(2, 1, 6, "", ("10.0.0.1", 443))]):
            with self.assertRaises(ValueError):
                service._page_text("https://example.org/test")

    def test_web_ui_requires_approval_and_scopes_company(self):
        self.client.force_login(self.user)
        url = reverse("engine:techniques", kwargs={"workspace_id": self.company.pk})
        with patch("engine.techniques.service._page_text", return_value="Beskrivning av en kamera. " * 20), patch(
            "engine.techniques.service.structured_generation",
            return_value=(service.Suggestions(techniques=[suggestion("Crash zoom")]), {"cost_usd": 0.001}),
        ):
            start = self.client.post(url, {"action": "suggest", "url": "https://example.org/zoom"})
        self.assertEqual(start.status_code, 302)
        self.assertEqual(StoredTechnique.objects.count(), 0)
        batch = TechniqueImport.objects.get(company=self.company)
        review = self.client.get(url + "?review=" + str(batch.pk))
        self.assertContains(review, "Crash zoom")
        approved = self.client.post(url, {"action": "approve", "import_id": str(batch.pk), "selected": ["0"]})
        self.assertEqual(approved.status_code, 302)
        self.assertEqual(StoredTechnique.objects.filter(company=self.company).count(), 1)
        cross = reverse("engine:techniques", kwargs={"workspace_id": self.other_company.pk})
        self.assertEqual(self.client.get(cross).status_code, 404)
