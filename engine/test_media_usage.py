from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .media_storage import MediaError
from .media_usage import registered_usage, storage_usage
from .models import Company, MediaAsset


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class MediaStorageUsageTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        settings = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        settings.enable()
        self.addCleanup(settings.disable)
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user(username="storage-owner")
        self.company = Company.objects.create(owner=self.user, name="Golf")
        self.other = Company.objects.create(owner=self.user, name="Annat företag")
        self.client.force_login(self.user)

    def asset(self, company=None, backend="local", size=100, **kwargs):
        return MediaAsset.objects.create(company=company or self.company, kind="image", origin="uploaded", provider="user",
                                         storage_backend=backend, storage_key="unused", mime_type="image/png", byte_size=size, **kwargs)

    def url(self, company=None):
        return reverse("engine:media_library_storage", kwargs={"workspace_id": (company or self.company).pk})

    def test_database_totals_include_hidden_expired_media_and_ignore_other_companies(self):
        self.asset(size=10)
        self.asset(size=20, expires_at=timezone.now())
        self.asset(self.other, size=999)
        usage = registered_usage(self.company)
        self.assertEqual((usage["registered_files"], usage["registered_bytes"]), (2, 30))
        self.assertFalse(usage["measured"])
        with patch("engine.media_usage.r2") as cloud:
            page = self.client.get(reverse("engine:media_library", kwargs={"workspace_id": self.company.pk}))
        cloud.assert_not_called()
        self.assertContains(page, "Medielagring")
        self.assertEqual(page.context["storage_usage"]["registered_files"], 2)

    @patch("engine.media_usage.shutil.disk_usage", return_value=Mock(total=10000, free=7000))
    def test_local_measures_company_files_and_extra_originals_and_volume_capacity(self, disk):
        folder = Path(self.tmp.name) / str(self.company.pk)
        folder.mkdir()
        (folder / "final.png").write_bytes(b"x" * 100)
        (folder / "base.png").write_bytes(b"x" * 40)
        (folder / "orphan.mp4").write_bytes(b"x" * 20)
        other = Path(self.tmp.name) / str(self.other.pk)
        other.mkdir()
        (other / "private.png").write_bytes(b"x" * 999)
        self.asset(size=100)
        usage = storage_usage(self.company)
        self.assertTrue(usage["measured"])
        self.assertEqual((usage["used_bytes"], usage["stored_files"]), (160, 3))
        self.assertEqual((usage["capacity_bytes"], usage["free_bytes"]), (10000, 7000))
        self.assertIn("hela disken", usage["detail"])
        disk.assert_called_once()

    @override_settings(MEDIA_STORAGE="r2")
    @patch.dict("os.environ", {"R2_BUCKET_NAME": "test-bucket"})
    @patch("engine.media_usage.r2")
    def test_r2_paginates_company_prefix_and_counts_bases_without_inventing_free_space(self, r2):
        self.asset(backend="r2", size=100)
        prefix = str(self.company.pk) + "/"
        r2.return_value.list_objects_v2.side_effect = [
            {"Contents": [{"Key": prefix + "final.png", "Size": 100}], "IsTruncated": True, "NextContinuationToken": "next"},
            {"Contents": [{"Key": prefix + "base.png", "Size": 40}, {"Key": prefix + "extra.png", "Size": 20}]},
        ]
        response = self.client.get(self.url())
        usage = response.json()
        self.assertTrue(usage["measured"])
        self.assertEqual((usage["used_bytes"], usage["stored_files"]), (160, 3))
        self.assertIsNone(usage["capacity_bytes"])
        self.assertIsNone(usage["free_bytes"])
        self.assertEqual(usage["capacity_label"], "Ingen fast diskstorlek")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        calls = r2.return_value.list_objects_v2.call_args_list
        self.assertTrue(all(call.kwargs["Prefix"] == prefix for call in calls))
        self.assertEqual(calls[1].kwargs["ContinuationToken"], "next")
        self.assertNotIn("final.png", response.content.decode())
        self.assertNotIn("test-bucket", response.content.decode())

    @override_settings(MEDIA_STORAGE="r2")
    @patch.dict("os.environ", {"R2_BUCKET_NAME": "test-bucket"})
    @patch("engine.media_usage.r2")
    def test_cache_is_scoped_and_refresh_remeasures_after_deletion(self, r2):
        def objects(**params):
            return {"Contents": [{"Key": params["Prefix"] + "file.png", "Size": 40 if params["Prefix"].startswith(str(self.company.pk)) else 90}]}
        r2.return_value.list_objects_v2.side_effect = objects
        self.assertEqual(storage_usage(self.company)["used_bytes"], 40)
        self.assertEqual(storage_usage(self.other)["used_bytes"], 90)
        storage_usage(self.company)
        self.assertEqual(r2.return_value.list_objects_v2.call_count, 2)
        r2.return_value.list_objects_v2.side_effect = None
        r2.return_value.list_objects_v2.return_value = {}
        self.assertEqual(self.client.get(self.url() + "?refresh=1").json()["used_bytes"], 0)
        self.assertEqual(r2.return_value.list_objects_v2.call_count, 3)

    @override_settings(MEDIA_STORAGE="r2")
    @patch("engine.media_usage.r2", side_effect=MediaError("Never expose a provider secret"))
    def test_storage_failure_uses_labelled_database_fallback(self, _r2):
        self.asset(backend="r2", size=200)
        usage = self.client.get(self.url()).json()
        self.assertFalse(usage["measured"])
        self.assertEqual(usage["registered_bytes"], 200)
        self.assertIn("kunde inte mätas", usage["detail"])
        self.assertNotIn("used_bytes", usage)
        self.assertNotIn("secret", str(usage))

    @override_settings(MEDIA_STORAGE="r2")
    @patch.dict("os.environ", {"R2_BUCKET_NAME": "test-bucket"})
    @patch("engine.media_usage.r2")
    def test_incomplete_scan_is_a_lower_bound_and_untrusted_prefix_is_rejected(self, r2):
        prefix = str(self.company.pk) + "/"
        r2.return_value.list_objects_v2.side_effect = [
            {"Contents": [{"Key": prefix + f"{i}.png", "Size": 10}], "IsTruncated": True, "NextContinuationToken": str(i)}
            for i in range(10)
        ]
        usage = storage_usage(self.company)
        self.assertFalse(usage["complete"])
        self.assertTrue(usage["used_label"].startswith("Minst "))
        self.assertEqual(usage["used_bytes"], 100)
        r2.return_value.list_objects_v2.side_effect = None
        r2.return_value.list_objects_v2.return_value = {"Contents": [{"Key": str(self.other.pk) + "/private.png", "Size": 999}]}
        self.assertFalse(storage_usage(self.company, refresh=True)["measured"])

    @patch("engine.media_usage.shutil.disk_usage", side_effect=OSError("Volume offline"))
    def test_local_disk_failure_never_claims_zero_free_space(self, _disk):
        usage = storage_usage(self.company)
        self.assertFalse(usage["measured"])
        self.assertEqual(usage["free_label"], "Kan inte mätas")

    def test_storage_endpoint_requires_company_ownership_and_login(self):
        foreign_user = get_user_model().objects.create_user(username="foreign-storage-owner")
        foreign = Company.objects.create(owner=foreign_user, name="Privat")
        self.assertEqual(self.client.get(self.url(foreign)).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
