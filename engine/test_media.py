import io
import base64
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock

import av
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .media import advance_job, cleanup_expired, create_job, describe_file, remove_asset, select_asset, store_asset
from .media_providers import UncertainGeneration, generate_images, start_video, upload_input
from .media_storage import MediaError, local_path
from .models import Company, ContentRun, MediaAsset, MediaGeneration


def picture():
    out = io.BytesIO()
    Image.new("RGB", (64, 96), "green").save(out, "PNG")
    return out.getvalue()


def movie():
    out = io.BytesIO()
    with av.open(out, mode="w", format="mp4") as container:
        stream = container.add_stream("libx264", rate=10)
        stream.width, stream.height, stream.pix_fmt = 64, 96, "yuv420p"
        for _ in range(10):
            for packet in stream.encode(av.VideoFrame.from_image(Image.new("RGB", (64, 96), "green"))):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class MediaTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_user(username="media-owner")
        self.company = Company.objects.create(owner=self.user, name="Golf", profile="Golf", current="Golf", source="Owner",
            valid_until=timezone.localdate()+timedelta(days=2), postiz_channels=[{"id":"ig", "identifier":"instagram"}])
        self.company.postiz_key = "test-only"
        self.company.save()
        self.run = ContentRun.objects.create(workspace=self.company, author=self.user, context={
            "profile":"Golf", "current":"Golf", "source":"Owner", "valid_until":self.company.valid_until.isoformat()},
            ideas=[{"title":"Golf", "photo_brief":"Egen illustration"}], selected=0, draft={"facebook":"FB", "instagram":"IG"}, model="test")
        self.client.force_login(self.user)

    def url(self, name, **kwargs):
        if name != "asset_file":
            kwargs.setdefault("run_id", self.run.pk)
        return reverse("engine:"+name, kwargs={"workspace_id":self.company.pk, **kwargs})

    def job(self, kind="image", **kwargs):
        return create_job(self.run, token=uuid.uuid4(), kind=kind, brief="Egen illustration", **kwargs)

    def test_upload_preview_select_and_used_history_survive_replacement(self):
        result = self.client.post(self.url("media_upload"), {"file":SimpleUploadedFile("golf.png", picture()), "use":"1"})
        self.assertEqual(result.status_code, 302)
        original = MediaAsset.objects.get()
        self.assertEqual((original.origin, original.width, original.height), ("uploaded", 64, 96))
        preview = self.client.get(self.url("asset_file", asset_id=original.pk))
        self.assertEqual(preview.status_code, 200)
        preview.close()
        next_asset = store_asset(self.company, picture())
        select_asset(self.run, next_asset)
        with self.assertRaises(MediaError):
            remove_asset(original)
        self.assertTrue(local_path(original.storage_key).exists())
        self.assertEqual(self.run.events.filter(action="media_selected").count(), 2)
        self.assertContains(self.client.get(self.url("review")), "Byt media")

    def test_expiry_cleanup_preserves_used_and_active_reference(self):
        job = self.job()
        used = store_asset(self.company, picture(), job=job)
        select_asset(self.run, used)
        unused = store_asset(self.company, picture(), job=job, index=1)
        source = store_asset(self.company, picture(), job=job, index=2)
        MediaGeneration.objects.create(run=self.run, kind="video", provider="higgsfield", source_asset=source)
        MediaAsset.objects.filter(pk__in=[unused.pk, source.pk]).update(expires_at=timezone.now()-timedelta(days=1))
        self.assertEqual(cleanup_expired(self.company), 1)
        self.assertTrue(MediaAsset.objects.filter(pk=used.pk).exists())
        self.assertTrue(MediaAsset.objects.filter(pk=source.pk).exists())
        self.assertFalse(local_path(unused.storage_key).exists())
        self.assertEqual(self.client.get(self.url("asset_file", asset_id=source.pk)).status_code, 410)

    @patch("engine.media.providers.generate_images")
    def test_generation_persists_options_and_double_submit_never_repeats_api(self, generate):
        generate.return_value = ([picture(), picture()], {"output_tokens":100})
        job = self.job()
        self.assertEqual(self.job().pk, job.pk)
        stale = MediaGeneration.objects.get(pk=job.pk)
        advance_job(job)
        advance_job(stale)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(job.assets.count(), 2)
        self.assertTrue(all(a.expires_at and a.origin == "generated" for a in job.assets.all()))
        self.assertContains(self.client.get(self.url("media_job", job_id=job.pk)), "Dina bildalternativ")
        self.assertContains(self.client.get(self.url("media")), "Förhandsvisning i 7 dagar", count=2)
        response = self.client.get(self.url("media")+f"?retry={job.pk}")
        self.assertContains(response, job.brief)

    @patch("engine.media.providers.start_video", side_effect=UncertainGeneration("unconfirmed"))
    def test_uncertain_start_retains_job_and_blocks_automatic_paid_retry(self, start):
        job = self.job("video")
        advance_job(job)
        advance_job(job)
        self.assertEqual(job.status, "unknown")
        self.assertEqual(self.job("video").pk, job.pk)
        self.assertEqual(start.call_count, 1)

    @patch("engine.media.providers.download_output")
    @patch("engine.media.providers.video_status")
    @patch("engine.media.providers.start_video")
    def test_durable_video_job_to_validated_file_and_selected_run(self, start, status, download):
        remote_id = str(uuid.uuid4())
        start.return_value = ({"request_id":remote_id}, {"estimate":{"usd":"0.70"}})
        status.return_value = {"status":"completed", "video":{"url":"https://example.test/video.mp4"}}
        download.return_value = movie()
        job = self.job("video")
        advance_job(job)
        self.assertEqual(job.provider_id, remote_id)
        reloaded = MediaGeneration.objects.get(pk=job.pk)
        advance_job(reloaded)
        asset = reloaded.assets.get()
        self.assertEqual((asset.kind, asset.width, asset.height), ("video", 64, 96))
        self.assertAlmostEqual(asset.duration_seconds, 1, places=1)
        select_asset(self.run, asset)
        self.run.refresh_from_db()
        self.assertEqual(self.run.media_asset_id, asset.pk)
        self.assertEqual(start.call_count, 1)
        response = self.client.get(self.url("asset_file", asset_id=asset.pk), HTTP_RANGE="bytes=0-15")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.content), 16)
        with self.assertRaises(MediaError):
            describe_file(b"\x00\x00\x00\x18ftypisomgarbage")

    def test_company_isolation_for_files_jobs_and_sources(self):
        outsider = get_user_model().objects.create_user(username="another-owner")
        other = Company.objects.create(owner=outsider, name="Other")
        asset = store_asset(other, picture())
        self.assertEqual(self.client.get(self.url("asset_file", asset_id=asset.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.url("media_use", asset_id=asset.pk)).status_code, 404)
        with self.assertRaises(MediaError):
            self.job(source=asset)
        job = self.job()
        self.client.force_login(outsider)
        self.assertEqual(self.client.post(self.url("media_job_status", job_id=job.pk)).status_code, 404)

    @patch("engine.postiz.request")
    def test_selected_mp4_streams_through_existing_postiz_draft_path(self, postiz):
        asset = store_asset(self.company, movie())
        select_asset(self.run, asset)
        seen = []
        def response(key, method, path, **kwargs):
            if path == "/upload":
                name, stream, mime = kwargs["files"]["file"]
                self.assertEqual(mime, "video/mp4")
                self.assertEqual(stream.read(), movie())
                return {"id":"file", "path":"https://example.test/video.mp4"}
            seen.append(kwargs["json"])
            return [{"postId":"draft", "integration":"ig"}]
        postiz.side_effect = response
        fields = {"facebook":"FB", "instagram":"IG", "channels":["ig"], "action":"send", "reviewed":"on"}
        self.client.post(self.url("review"), fields)
        self.client.post(self.url("review"), fields)
        self.run.refresh_from_db()
        self.assertEqual(self.run.delivery_status, "sent")
        self.assertEqual(postiz.call_count, 2)
        self.assertEqual(seen[0]["type"], "draft")
        self.assertEqual(seen[0]["posts"][0]["settings"]["post_type"], "post")

    @patch("engine.media_providers.higgs")
    def test_higgs_cost_limit_prevents_submission_and_retains_accepted_estimate(self, higgs):
        job = self.job("video")
        higgs.return_value = {"usd":"20.00", "credits":"320"}
        with self.assertRaises(MediaError):
            start_video(job)
        self.assertEqual(higgs.call_count, 1)
        higgs.reset_mock()
        higgs.side_effect = [{"usd":"0.70", "credits":"11.2"}, {"request_id":str(uuid.uuid4())}]
        start_video(job)
        job.refresh_from_db()
        self.assertEqual(job.usage["estimate"]["usd"], "0.70")
        self.assertEqual(higgs.call_args_list[1].kwargs["json"], {"prompt":job.prompt, "duration":10})

    @patch("engine.media_providers.OpenAI")
    def test_variant_uses_image_edit_with_stored_source(self, client):
        source = store_asset(self.company, picture())
        job = self.job(source=source)
        api = client.return_value.__enter__.return_value
        api.images.edit.return_value.data = [Mock(b64_json=base64.b64encode(picture()).decode())]
        api.images.edit.return_value.usage = None
        output, _ = generate_images(job)
        self.assertEqual(output, [picture()])
        self.assertEqual(api.images.edit.call_args.kwargs["model"], job.parameters["model"])
        self.assertEqual(api.images.edit.call_args.kwargs["n"], 2)
        self.assertEqual(api.images.edit.call_args.kwargs["image"][2], "image/png")
        api.images.generate.assert_not_called()

    @patch("engine.media_providers.public_url", side_effect=lambda url: url)
    @patch("engine.media_providers.httpx.put")
    @patch("engine.media_providers.higgs")
    def test_higgs_source_upload_keeps_auth_off_storage_request(self, higgs, put, validate):
        source = store_asset(self.company, picture())
        higgs.return_value = {"upload_url":"https://upload.example.test/signed", "public_url":"https://cdn.example.test/image",
            "upload_headers":{"Content-Type":"image/png", "x-amz-tagging":"input=true"}}
        self.assertEqual(upload_input(source), "https://cdn.example.test/image")
        self.assertEqual(put.call_args.kwargs["content"], picture())
        self.assertEqual(put.call_args.kwargs["headers"], higgs.return_value["upload_headers"])
        self.assertNotIn("Authorization", put.call_args.kwargs["headers"])

    @override_settings(MEDIA_STORAGE="r2")
    @patch.dict("os.environ", {"R2_BUCKET_NAME":"test-bucket"})
    @patch("engine.media_storage.r2")
    def test_r2_bytes_stay_out_of_database_and_preview_is_private(self, r2):
        asset = store_asset(self.company, picture())
        self.assertEqual(asset.storage_backend, "r2")
        args = r2.return_value.put_object.call_args.kwargs
        self.assertEqual(args["Body"], picture())
        self.assertNotIn("ACL", args)
        r2.return_value.generate_presigned_url.return_value = "https://storage.example.test/temporary"
        response = self.client.get(self.url("asset_file", asset_id=asset.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        remove_asset(asset)
        r2.return_value.delete_object.assert_called_once_with(Bucket="test-bucket", Key=asset.storage_key)
