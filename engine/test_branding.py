import hashlib
import base64
import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .branding import replace_logo
from .media import advance_job, create_job, remove_asset, store_asset
from .media_storage import MediaError, open_asset
from .models import Company, ContentRun


def png(color, size=(20, 10)):
    output = io.BytesIO()
    Image.new("RGBA", size, color).save(output, "PNG")
    return output.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class LogoTests(TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        settings = override_settings(MEDIA_ROOT=Path(tmp.name))
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = get_user_model().objects.create_user(username="logo-owner")
        self.company = Company.objects.create(owner=self.owner, name="Logo test")
        self.run = ContentRun.objects.create(workspace=self.company, context={}, draft={"instagram":"Text"})
        self.client.force_login(self.owner)

    def job(self, **kwargs):
        return create_job(self.run, token=uuid.uuid4(), kind="image", brief="Logga i hörnet", **kwargs)

    def test_settings_upload_keeps_original_bytes_and_replacement_versions(self):
        url = reverse("engine:settings", kwargs={"workspace_id":self.company.pk})
        first = png("red")
        self.client.post(url, {"logo":SimpleUploadedFile("official.png", first, content_type="image/png")})
        self.company.refresh_from_db()
        old = self.company.official_logo
        with open_asset(old) as source:
            self.assertEqual(source.read(), first)
        self.assertEqual(old.sha256, hashlib.sha256(first).hexdigest())
        self.assertEqual(old.purpose, "logo")
        same = replace_logo(self.company, first, "same.png")
        self.assertEqual(same.pk, old.pk)
        new = replace_logo(self.company, png("blue"), "new.png")
        self.assertNotEqual(new.pk, old.pk)
        self.assertContains(self.client.get(url), "new.png")
        with self.assertRaises(MediaError):
            remove_asset(old)
        self.client.force_login(get_user_model().objects.create_user(username="other"))
        self.assertEqual(self.client.post(url, {"logo":SimpleUploadedFile("bad.png", first)}).status_code, 404)

    @patch("engine.media.providers.generate_images")
    def test_logo_is_composited_from_exact_file_and_clean_source_survives_edit(self, generate):
        logo = replace_logo(self.company, png("red"), "official.png")
        base = png("green", (200, 300))
        generate.return_value = ([base], {})
        job = self.job(include_logo=True)
        replace_logo(self.company, png("blue"), "new.png")
        advance_job(job)
        asset = job.assets.get()
        self.assertEqual(job.logo_asset_id, logo.pk)
        self.assertEqual(job.parameters["logo_sha256"], logo.sha256)
        with open_asset(asset) as output:
            image = Image.open(output).convert("RGBA")
        # 8 px outside margin and 4 px panel padding: original 20x10 mark isn't resampled.
        self.assertEqual(image.crop((168,278,188,288)).tobytes(), Image.open(io.BytesIO(png("red"))).tobytes())
        with open_asset(asset, unbranded=True) as source:
            self.assertEqual(source.read(), base)
        next_job = self.job(source=asset, include_logo=True)
        self.company.refresh_from_db()
        self.assertEqual(next_job.logo_asset_id, self.company.official_logo_id)
        self.assertNotEqual(next_job.logo_asset_id, job.logo_asset_id)
        from .media_providers import generate_images
        with patch("engine.media_providers.OpenAI") as client:
            def edited(**kwargs):
                self.assertEqual(kwargs["image"][1].read(), base)
                return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(base).decode())], usage=None)
            client.return_value.__enter__.return_value.images.edit.side_effect = edited
            generate_images(next_job)

    def test_missing_logo_and_logo_as_ai_source_are_rejected(self):
        with self.assertRaises(MediaError):
            self.job(include_logo=True)
        logo = replace_logo(self.company, png("red"), "official.png")
        with self.assertRaises(MediaError):
            self.job(source=logo)
        job = self.job()
        self.assertIsNone(job.logo_asset_id)
        self.assertIn("Never draw, recreate or preserve logos", job.prompt)

    @patch("engine.media.providers.generate_images")
    def test_corrupted_logo_fails_closed_without_substitution(self, generate):
        from .media_storage import local_path
        logo = replace_logo(self.company, png("red"), "official.png")
        local_path(logo.storage_key).write_bytes(png("blue"))
        generate.return_value = ([png("green", (200,300))], {})
        job = self.job(include_logo=True)
        advance_job(job)
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.assets.count(), 0)
        generate.assert_not_called()
