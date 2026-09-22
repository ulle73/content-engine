import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

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
