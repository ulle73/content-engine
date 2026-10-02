import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .media import select_asset, store_asset
from .media_storage import MediaError, local_path
from .models import Company, ContentRun, MediaAsset, MediaGeneration


def picture():
    out = io.BytesIO()
    Image.new("RGB", (80, 120), "green").save(out, "PNG")
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class MediaLibraryTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_user(username="library-owner")
        self.company = Company.objects.create(owner=self.user, name="Golf")
        self.client.force_login(self.user)

    def url(self, name, **kwargs):
        return reverse("engine:" + name, kwargs={"workspace_id": self.company.pk, **kwargs})

    def test_uploaded_library_asset_is_persistent_and_available_in_run_picker(self):
        response = self.client.post(
            self.url("media_library_upload"),
            {
                "file": SimpleUploadedFile("green.png", picture(), content_type="image/png"),
                "alt_text": "Green i kvällsljus",
            },
        )
        self.assertEqual(response.status_code, 302)
        asset = MediaAsset.objects.get(company=self.company)
        self.assertEqual(asset.origin, "uploaded")
        self.assertEqual(asset.purpose, "content")
        self.assertIsNone(asset.expires_at)

        library = self.client.get(self.url("media_library"))
        self.assertContains(library, "Green i kvällsljus")
        self.assertContains(library, str(asset.pk))
        self.assertContains(library, "asset-preview-dialog")

        run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={},
            ideas=[],
            draft={"facebook": "FB", "instagram": "IG"},
            model="test",
        )
        picker = self.client.get(self.url("media", run_id=run.pk))
        self.assertContains(picker, self.url("asset_file", asset_id=asset.pk))

    def test_library_deletion_requires_confirmation_and_removes_row_and_bytes(self):
        asset = store_asset(self.company, picture(), alt_text="Filen att radera")
        path = local_path(asset.storage_key)
        url = self.url("media_library_delete", asset_id=asset.pk)
        self.assertContains(self.client.get(self.url("media_library")), url)
        preview = self.client.get(url + "?filter=uploaded")
        self.assertContains(preview, "Filen att radera")
        self.assertContains(preview, "Radera permanent")
        self.assertTrue(path.exists())
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertTrue(MediaAsset.objects.filter(pk=asset.pk).exists())
        self.assertTrue(path.exists())
        result = self.client.post(url, {"confirm_delete": "1", "filter": "uploaded"})
        self.assertRedirects(result, self.url("media_library") + "?filter=uploaded")
        self.assertFalse(MediaAsset.objects.filter(pk=asset.pk).exists())
        self.assertFalse(path.exists())
        self.assertEqual(self.client.get(self.url("asset_file", asset_id=asset.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url("assistant_assets")).json()["assets"], [])

    def test_delete_rechecks_use_after_confirmation_page_was_opened(self):
        asset = store_asset(self.company, picture())
        url = self.url("media_library_delete", asset_id=asset.pk)
        self.assertContains(self.client.get(url), "Radera permanent")
        run = ContentRun.objects.create(workspace=self.company, author=self.user, context={}, draft={})
        select_asset(run, asset)
        response = self.client.post(url, {"confirm_delete": "1"})
        self.assertContains(response, "sparat inlägg", status_code=409)
        self.assertNotContains(response, "Radera permanent", status_code=409)
        self.assertTrue(MediaAsset.objects.filter(pk=asset.pk).exists())
        self.assertTrue(local_path(asset.storage_key).exists())

    def test_library_delete_is_company_scoped_and_requires_login_and_csrf(self):
        asset = store_asset(self.company, picture())
        other = Company.objects.create(owner=self.user, name="Annat företag")
        wrong_url = reverse("engine:media_library_delete", kwargs={"workspace_id": other.pk, "asset_id": asset.pk})
        self.assertEqual(self.client.get(wrong_url).status_code, 404)
        self.assertEqual(self.client.post(wrong_url, {"confirm_delete": "1"}).status_code, 404)
        url = self.url("media_library_delete", asset_id=asset.pk)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(url, {"confirm_delete": "1"}).status_code, 403)
        self.client.force_login(get_user_model().objects.create_user(username="delete-other-owner"))
        self.assertEqual(self.client.post(url, {"confirm_delete": "1"}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.post(url, {"confirm_delete": "1"}).status_code, 302)
        self.assertTrue(MediaAsset.objects.filter(pk=asset.pk).exists())

    def test_library_delete_keeps_generation_history_and_costs(self):
        run = ContentRun.objects.create(workspace=self.company, author=self.user, context={}, draft={})
        job = MediaGeneration.objects.create(run=run, kind="image", provider="openai", status="completed", usage={"cost_usd": "0.10"})
        asset = store_asset(self.company, picture(), job=job)
        result = self.client.post(self.url("media_library_delete", asset_id=asset.pk), {"confirm_delete": "1"})
        self.assertEqual(result.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.usage, {"cost_usd": "0.10"})
        self.assertEqual(job.status, "completed")
        self.assertFalse(job.assets.exists())

    def test_active_generation_and_branding_cannot_be_deleted(self):
        asset = store_asset(self.company, picture())
        run = ContentRun.objects.create(workspace=self.company, author=self.user, context={}, draft={})
        MediaGeneration.objects.create(run=run, kind="video", provider="higgsfield", status="queued", source_asset=asset)
        response = self.client.post(self.url("media_library_delete", asset_id=asset.pk), {"confirm_delete": "1"})
        self.assertContains(response, "pågående generation", status_code=409)
        logo = store_asset(self.company, picture(), purpose="logo")
        response = self.client.get(self.url("media_library_delete", asset_id=logo.pk))
        self.assertContains(response, "varumärkesmaterial")
        self.assertNotContains(response, "Radera permanent")
        self.assertTrue(local_path(asset.storage_key).exists())

    @patch("engine.media.delete_file", side_effect=MediaError("Filen kunde inte tas bort. Försök igen."))
    def test_storage_failure_does_not_remove_database_row(self, _delete):
        asset = store_asset(self.company, picture())
        result = self.client.post(self.url("media_library_delete", asset_id=asset.pk), {"confirm_delete": "1"})
        self.assertContains(result, "Försök igen", status_code=409)
        self.assertTrue(MediaAsset.objects.filter(pk=asset.pk).exists())
        self.assertTrue(local_path(asset.storage_key).exists())

    @patch.dict("os.environ", {"R2_BUCKET_NAME": "test-bucket"})
    @patch("engine.media_storage.r2")
    def test_library_delete_removes_r2_file_and_clean_generation_base(self, r2):
        asset = MediaAsset.objects.create(company=self.company, kind="image", origin="generated", provider="openai", storage_backend="r2",
                                          storage_key="test/final.png", generation_base_key="test/base.png", mime_type="image/png", byte_size=10)
        response = self.client.post(self.url("media_library_delete", asset_id=asset.pk), {"confirm_delete": "1"})
        self.assertEqual(response.status_code, 302)
        keys = [call.kwargs["Key"] for call in r2.return_value.delete_object.call_args_list]
        self.assertEqual(keys, ["test/final.png", "test/base.png"])
        self.assertFalse(MediaAsset.objects.filter(pk=asset.pk).exists())

    def test_generated_video_asset_preview_shows_saved_prompt(self):
        run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={},
            draft={},
            model="test",
        )
        prompt = "LOCK_GK_AND_SWIRL_PROMPT"
        job = MediaGeneration.objects.create(
            run=run,
            kind="video",
            provider="higgsfield",
            brief="Golfkuponger logo animation",
            prompt=prompt,
            parameters={"model": "bytedance/seedance-2.5"},
            status="completed",
        )
        MediaAsset.objects.create(
            company=self.company,
            kind="video",
            origin="generated",
            provider="higgsfield",
            storage_backend="local",
            storage_key="test/generated.mp4",
            mime_type="video/mp4",
            byte_size=10,
            width=960,
            height=960,
            duration_seconds=5,
            generation=job,
        )

        response = self.client.get(self.url("media_library"))
        self.assertContains(response, "Visa prompt")
        self.assertContains(response, prompt)

    @patch("engine.company_settings.apify.account_summary", return_value={})
    def test_image_cost_event_opens_generated_asset_preview(self, _account):
        run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={},
            draft={},
            model="test",
        )
        job = MediaGeneration.objects.create(
            run=run,
            kind="image",
            provider="openai",
            brief="En riktig bild från golfbanan",
            prompt="prompt",
            parameters={"model": "gpt-image-2"},
            usage={"output_tokens": 100},
            status="completed",
        )
        asset = MediaAsset.objects.create(
            company=self.company,
            kind="image",
            origin="generated",
            provider="openai",
            storage_backend="local",
            storage_key="test/generated.png",
            mime_type="image/png",
            byte_size=10,
            width=80,
            height=120,
            generation=job,
        )

        response = self.client.get(self.url("costs"))
        self.assertContains(response, "Visa genererad media")
        self.assertContains(response, "cost-media-dialog")
        self.assertContains(response, self.url("asset_file", asset_id=asset.pk))
        self.assertContains(response, str(job.pk)[:11])
