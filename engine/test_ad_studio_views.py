import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .ad_studio import service
from .media import store_asset
from .models import Company


def png(color="green"):
    out = io.BytesIO()
    Image.new("RGB", (1080, 1920), color).save(out, "PNG")
    return out.getvalue()


class AdStudioWorkbenchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="studio", password="x-Strong-pass-2026")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger", profile="Golf")
        self.client.force_login(self.user)
        self.asset = store_asset(self.company, png(), alt_text="Golfare i morgonljus")

    def url(self, name, **kw):
        return reverse("engine:" + name, kwargs={"workspace_id": self.company.pk, **kw})

    def test_list_and_create(self):
        self.assertContains(self.client.get(self.url("ad_list")), "Ny annons")
        response = self.client.post(self.url("ad_list"), {"message": "Friskvård brinner inne"})
        draft = self.company.ad_drafts.get()
        self.assertRedirects(response, self.url("ad_workspace", draft_id=draft.pk))
        self.assertContains(self.client.get(self.url("ad_list")), "Friskvård brinner inne")

    def test_template_lays_out_scenes_and_text_saves(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        self.client.post(self.url("ad_update", draft_id=draft.pk),
                         {"revision": 1, "template_id": "friskvard-portal-ad", "message": "Test", "headline": "Golf"})
        draft.refresh_from_db()
        self.assertEqual([s["id"] for s in draft.brief["scenes"]], ["hook", "portal", "purchase", "app", "proof", "end"])
        self.client.post(self.url("ad_update", draft_id=draft.pk),
                         {"revision": draft.revision, "template_id": "friskvard-portal-ad", "message": "Test",
                          "scene_hook_text": "DITT BIDRAG BRINNER INNE", "headline": "Golf"})
        draft.refresh_from_db()
        self.assertEqual(draft.brief["scenes"][0]["on_screen_text"], "DITT BIDRAG BRINNER INNE")
        page = self.client.get(self.url("ad_workspace", draft_id=draft.pk))
        self.assertContains(page, "DITT BIDRAG BRINNER INNE")
        self.assertContains(page, "Välj bild")

    def test_stale_revision_shows_error_not_crash(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        response = self.client.post(self.url("ad_update", draft_id=draft.pk), {"revision": 9, "message": "x"}, follow=True)
        self.assertContains(response, "ändrats")

    def test_pick_existing_and_upload(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        draft = service.apply_template(self.company, draft.pk, template_id="friskvard-portal-ad", expected_revision=1)
        page = self.client.get(self.url("ad_pick", draft_id=draft.pk, scene_id="hook"))
        self.assertContains(page, str(self.asset.pk))
        self.client.post(self.url("ad_pick", draft_id=draft.pk, scene_id="hook"),
                         {"revision": draft.revision, "asset_id": str(self.asset.pk)})
        draft.refresh_from_db()
        self.assertEqual(draft.brief["scenes"][0]["asset_id"], str(self.asset.pk))
        self.assertEqual(draft.brief["assets"][0]["asset_id"], str(self.asset.pk))
        upload = SimpleUploadedFile("portal.png", png("white"), content_type="image/png")
        self.client.post(self.url("ad_pick", draft_id=draft.pk, scene_id="portal"),
                         {"revision": draft.revision, "file": upload, "description": "Epassi-portalen"})
        draft.refresh_from_db()
        portal_asset = draft.brief["scenes"][1]["asset_id"]
        self.assertTrue(portal_asset)
        self.assertEqual(self.company.media_assets.get(pk=portal_asset).ad_tags.roles, ["screen"])

    def test_storyboard_image_endpoint(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        response = self.client.get(self.url("ad_storyboard", draft_id=draft.pk))
        self.assertEqual(response.status_code, 409)
        service.apply_template(self.company, draft.pk, template_id="friskvard-portal-ad", expected_revision=1)
        response = self.client.get(self.url("ad_storyboard", draft_id=draft.pk))
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_other_users_company_is_404(self):
        other = get_user_model().objects.create_user(username="other")
        company = Company.objects.create(owner=other, name="Annat", profile="x")
        draft = service.start_draft(company, other, message="Hemligt")
        url = reverse("engine:ad_workspace", kwargs={"workspace_id": company.pk, "draft_id": draft.pk})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_lock_disabled_until_ready_and_action_errors_are_messages(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        self.assertContains(self.client.get(self.url("ad_workspace", draft_id=draft.pk)), "disabled")
        response = self.client.post(self.url("ad_action", draft_id=draft.pk), {"action": "lock", "revision": 1}, follow=True)
        self.assertContains(response, "kan inte låsas")

    def test_mcp_payload_has_studio_link(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        self.assertTrue(service.serialize(draft)["studio_url"].endswith(self.url("ad_workspace", draft_id=draft.pk)))

    def test_fact_verification_checkbox(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        draft = service.update_draft(self.company, draft.pk, expected_revision=1,
                                     changes={"facts": [{"claim": "Finns i portaler", "source": "skill F1"},
                                                        {"claim": "300+ klubbar", "source": "mall"}]})
        self.client.post(self.url("ad_update", draft_id=draft.pk),
                         {"revision": draft.revision, "message": "Test", "facts_present": "1", "fact_verified": ["0"]})
        draft.refresh_from_db()
        self.assertEqual([f["verified"] for f in draft.brief["facts"]], [True, False])
