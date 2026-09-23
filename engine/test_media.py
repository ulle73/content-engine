import io
import base64
import json
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock

import httpx

import av
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .media import advance_job, cancel_job, cleanup_expired, create_job, describe_file, recover_media_jobs, remove_asset, select_asset, store_asset
from .media_providers import ProviderUnavailableError, UncertainGeneration, estimate_video, generate_images, higgs, start_video, upload_input
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
        # Consume the streaming response through Django's test-client wrapper;
        # direct close() fires request_finished inside TestCase's DB transaction.
        self.assertEqual(b"".join(preview.streaming_content), picture())
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

    def test_generation_job_uses_shared_creative_plan_and_keeps_original_request(self):
        brief = "Premium reel cirka 8 sekunder i 9:16 med cinematic push-in"
        job = create_job(self.run, token=uuid.uuid4(), kind="video", brief=brief)
        self.assertEqual(job.brief, brief)
        self.assertEqual(job.provider, "higgsfield")
        self.assertEqual(job.parameters["duration"], 10)
        self.assertEqual(job.parameters["aspect_ratio"], "9:16")
        self.assertEqual(job.parameters["creative"]["brief"]["user_intent"], brief)
        self.assertEqual(job.parameters["creative"]["selection"]["model_id"], job.parameters["model"])
        self.assertEqual(job.parameters["creative"]["recipe"]["recipe_id"], "generic_video")
        self.assertEqual(job.parameters["creative"]["recipe"]["version"], "1.0.0")
        self.assertEqual(job.parameters["creative"]["recipe_registry_version"], "2026-09-23.1")
        self.assertIn("SCENE:", job.prompt)
        self.assertTrue(any(item["code"] == "duration_normalized" for item in job.parameters["creative"]["preflight"]))

    def test_reference_video_preservation_is_compiled_without_old_logo_ban(self):
        source = store_asset(self.company, picture())
        job = create_job(self.run, token=uuid.uuid4(), kind="video", source=source,
            brief="Animera bilden. Behåll klubbhuset, skylten och all text exakt. Låt flaggan röra sig.")
        self.assertIn("PRESERVE EXACTLY", job.prompt)
        self.assertIn("architecture", job.prompt)
        self.assertNotIn("Never draw, recreate or preserve logos", job.prompt)
        self.assertEqual(job.parameters["creative"]["brief"]["mode"], "image-to-video")

    def test_ai_studio_exposes_priority_format_and_safe_diagnostics(self):
        page = self.client.get(self.url("media"), {"kind": "video"})
        self.assertContains(page, "Bäst resultat")
        self.assertContains(page, "Balanserad")
        self.assertContains(page, "Spara kostnad")
        self.assertContains(page, "Stående / Reel")
        self.assertContains(page, "Auto väljer mellan verifierade videomodeller")
        self.assertContains(page, "Längd, upplösning och modell anpassas")
        self.assertNotContains(page, "Prioritet ändrar ännu inte videomodell")
        self.assertNotContains(page, "Bildförslag eller 10 sekunders video")

        brief = '<script>alert("x")</script> Premium reel cirka 8 sekunder'
        job = create_job(self.run, token=uuid.uuid4(), kind="video", brief=brief, priority="economy")
        detail = self.client.get(self.url("media_job", job_id=job.pk))
        self.assertContains(detail, "Avancerad diagnostik")
        self.assertContains(detail, "Provider-prompt")
        self.assertContains(detail, "Prompt som skickas till Higgsfield")
        body = detail.content.decode()
        self.assertLess(body.index("Prompt som skickas till Higgsfield"), body.index("Starta betald generation"))
        self.assertContains(detail, "economy")
        self.assertContains(detail, "kling-video/v2.5-turbo/pro/text-to-video")
        self.assertNotContains(detail, '<script>alert("x")</script>')
        self.assertContains(detail, '&lt;script&gt;')
        self.assertEqual(job.parameters["creative"]["brief"]["quality_preference"], "economy")

    def test_invalid_priority_is_rejected_before_job_creation(self):
        with self.assertRaises(MediaError):
            create_job(self.run, token=uuid.uuid4(), kind="video", brief="Video", priority="hidden-expensive-mode")
        self.assertEqual(MediaGeneration.objects.count(), 0)

    def test_cancel_view_is_company_scoped_and_only_post(self):
        job = self.job("video")
        url = self.url("media_job_cancel", job_id=job.pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, "canceled")

        outsider = get_user_model().objects.create_user(username="cancel-outsider")
        foreign_company = Company.objects.create(owner=outsider, name="Other")
        foreign_run = ContentRun.objects.create(workspace=foreign_company, author=outsider, context={}, ideas=[], draft={"instagram": "x"}, model="test")
        foreign_job = MediaGeneration.objects.create(run=foreign_run, kind="video", provider="higgsfield", brief="x", prompt="x")
        self.assertEqual(self.client.post(reverse("engine:media_job_cancel", kwargs={"workspace_id": self.company.pk, "run_id": foreign_run.pk, "job_id": foreign_job.pk})).status_code, 404)

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

    @patch("engine.media.providers.video_status")
    @patch("engine.media.providers.start_video")
    def test_terminal_higgsfield_error_is_preserved_and_can_be_refreshed(self, start, status):
        remote_id = str(uuid.uuid4())
        start.return_value = ({"request_id": remote_id}, {"estimate": {"usd": "0.30"}})
        status.return_value = {"status": "failed", "request_id": remote_id, "error": "Generation failed upstream"}
        job = self.job("video")
        advance_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "running")
        advance_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error, "Generation failed upstream")
        self.assertEqual(job.usage["provider_terminal"]["status"], "failed")

        MediaGeneration.objects.filter(pk=job.pk).update(error="Videoleverantören kunde inte slutföra generationen.")
        response = self.client.post(self.url("media_job_refresh_provider", job_id=job.pk))
        self.assertEqual(response.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.error, "Generation failed upstream")
        self.assertContains(self.client.get(self.url("media_job", job_id=job.pk)), "Generation failed upstream")


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

    @patch("engine.media_providers.higgs")
    def test_seedance_25_t2v_estimate_uses_exact_compiled_path_and_silent_payload(self, higgs):
        job = create_job(
            self.run,
            token=uuid.uuid4(),
            kind="video",
            brief="Premium cinematic reel cirka 8 sekunder i 9:16",
            priority="quality",
        )
        self.assertEqual(job.parameters["model"], "bytedance/seedance-2.5")
        higgs.return_value = {"usd": "0.70", "credits": "11"}
        model, body, _ = estimate_video(job)
        self.assertEqual(model, "bytedance/seedance-2.5/text-to-video")
        self.assertEqual(higgs.call_args.args[1], "/estimate/bytedance/seedance-2.5/text-to-video")
        self.assertEqual(body["duration"], 8)
        self.assertEqual(body["resolution"], "720p")
        self.assertEqual(body["aspect_ratio"], "9:16")
        self.assertFalse(body["generate_audio"])
        self.assertEqual(body["output_format"], "mp4")

    def test_seedance_25_i2v_uses_start_image_field_but_not_aspect_ratio(self):
        source = store_asset(self.company, picture())
        job = create_job(
            self.run,
            token=uuid.uuid4(),
            kind="video",
            source=source,
            brief="Animera denna bild i 8 sekunder i 9:16 och behåll motivet exakt",
            priority="quality",
        )
        with patch("engine.media_providers.upload_input", return_value="https://cdn.example.test/start.png") as upload:
            with patch("engine.media_providers.higgs", return_value={"usd": "0.80", "credits": "12"}) as provider:
                model, body, _ = estimate_video(job)
        self.assertEqual(model, "bytedance/seedance-2.5/image-to-video")
        self.assertEqual(body["image_url"], "https://cdn.example.test/start.png")
        self.assertNotIn("end_image_url", body)
        self.assertNotIn("aspect_ratio", body)
        self.assertEqual(body["resolution"], "720p")
        self.assertFalse(body["generate_audio"])
        upload.assert_called_once_with(source)
        self.assertEqual(provider.call_args.args[1], "/estimate/bytedance/seedance-2.5/image-to-video")

    @patch("engine.media_providers.higgs")
    def test_seedance_audio_intent_is_explicitly_forwarded(self, higgs):
        job = create_job(
            self.run,
            token=uuid.uuid4(),
            kind="video",
            brief="Skapa en 10 sekunders reel med ljud och ambient sound",
        )
        self.assertEqual(job.parameters["model"], "bytedance/seedance-2.5")
        higgs.return_value = {"usd": "0.90", "credits": "14"}
        _, body, _ = estimate_video(job)
        self.assertTrue(body["generate_audio"])

    @patch("engine.media_providers.higgs")
    def test_seedance_20_4k_uses_exact_model_and_resolution(self, higgs):
        job = create_job(
            self.run,
            token=uuid.uuid4(),
            kind="video",
            brief="Skapa en 10 sekunders premiumvideo i 4K",
        )
        self.assertEqual(job.parameters["model"], "bytedance/seedance-2.0")
        higgs.return_value = {"usd": "1.20", "credits": "18"}
        model, body, _ = estimate_video(job)
        self.assertEqual(model, "bytedance/seedance-2.0/text-to-video")
        self.assertEqual(body["resolution"], "4k")
        self.assertFalse(body["generate_audio"])

    @patch("engine.media_providers.higgs")
    def test_seedance_estimate_and_paid_submit_reuse_identical_body_and_path(self, higgs):
        job = create_job(
            self.run,
            token=uuid.uuid4(),
            kind="video",
            brief="Premium cinematic reel cirka 8 sekunder i 9:16",
            priority="quality",
        )
        remote_id = str(uuid.uuid4())
        higgs.side_effect = [
            {"usd": "0.70", "credits": "11"},
            {"request_id": remote_id},
        ]
        result, _ = start_video(job)
        self.assertEqual(result["request_id"], remote_id)
        estimate_call, submit_call = higgs.call_args_list
        self.assertEqual(estimate_call.args[1], "/estimate/bytedance/seedance-2.5/text-to-video")
        self.assertEqual(submit_call.args[1], "/bytedance/seedance-2.5/text-to-video")
        self.assertEqual(estimate_call.kwargs["json"], submit_call.kwargs["json"])
        self.assertFalse(submit_call.kwargs["json"]["generate_audio"])
        self.assertTrue(submit_call.kwargs["billable"])

    @override_settings(HIGGSFIELD_WEBHOOK_ENABLED=True, APP_URL="https://content-engine.example")
    @patch("engine.media_providers.higgs")
    def test_video_submit_uses_documented_webhook_query_parameter(self, higgs):
        job = self.job("video")
        higgs.side_effect = [{"usd": "0.70"}, {"request_id": str(uuid.uuid4())}]
        start_video(job)
        submit_path = higgs.call_args_list[1].args[1]
        self.assertIn("?hf_webhook=", submit_path)
        self.assertIn("https%3A%2F%2Fcontent-engine.example%2Fwebhooks%2Fhiggsfield%2F", submit_path)

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
    @patch("engine.media_providers.public_stream")
    @patch("engine.media_providers.higgs")
    def test_higgs_source_upload_keeps_auth_off_storage_request(self, higgs, put, validate):
        source = store_asset(self.company, picture())
        higgs.return_value = {"upload_url":"https://upload.example.test/signed", "public_url":"https://cdn.example.test/image",
            "upload_headers":{"Content-Type":"image/png", "x-amz-tagging":"input=true"}}
        self.assertEqual(upload_input(source), "https://cdn.example.test/image")
        self.assertEqual(put.call_args.kwargs["content"], picture())
        self.assertEqual(put.call_args.kwargs["headers"], higgs.return_value["upload_headers"])
        self.assertNotIn("Authorization", put.call_args.kwargs["headers"])


    @patch.dict("os.environ", {"HIGGSFIELD_API_KEY_GK": "test-key"}, clear=False)
    @patch("engine.media_providers.time.sleep")
    @patch("engine.media_providers.random.uniform", return_value=0)
    @patch("engine.media_providers.httpx.request")
    def test_higgs_get_retries_transient_failures_but_paid_post_never_retries(self, request, jitter, sleep):
        unavailable = Mock(status_code=503, is_error=True, headers={})
        unavailable.json.return_value = {"detail": "temporarily unavailable"}
        success = Mock(status_code=200, is_error=False, headers={})
        success.json.return_value = {"status": "processing"}
        request.side_effect = [unavailable, unavailable, success]
        self.assertEqual(higgs("GET", "/requests/abc/status"), {"status": "processing"})
        self.assertEqual(request.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

        request.reset_mock()
        request.side_effect = httpx.ReadTimeout("ambiguous")
        with self.assertRaises(UncertainGeneration):
            higgs("POST", "/some-generation", json={"prompt": "x"}, billable=True)
        self.assertEqual(request.call_count, 1)

    @patch("engine.media.providers.download_output")
    @patch("engine.media.providers.video_status")
    def test_higgs_webhook_is_untrusted_hint_and_duplicate_safe(self, status, download):
        remote_id = str(uuid.uuid4())
        job = self.job("video")
        MediaGeneration.objects.filter(pk=job.pk).update(status="running", provider_id=remote_id)
        status.return_value = {"status": "completed", "video": {"url": "https://trusted.example/result.mp4"}}
        download.return_value = movie()
        body = {
            "request_id": remote_id, "status": "completed", "error": None,
            "payload": {"video": {"url": "https://attacker.invalid/not-used.mp4"}},
        }
        response = self.client.post("/webhooks/higgsfield/", data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, 204)
        status.assert_not_called()
        recover_media_jobs(limit=5)
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.assets.count(), 1)
        download.assert_called_once_with("https://trusted.example/result.mp4")
        self.assertEqual(job.usage["webhook"]["deliveries"], 1)

        response = self.client.post("/webhooks/higgsfield/", data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, 204)
        job.refresh_from_db()
        self.assertEqual(job.assets.count(), 1)
        self.assertEqual(job.usage["webhook"]["deliveries"], 2)
        self.assertEqual(status.call_count, 1)

    def test_higgs_webhook_rejects_bad_envelope_and_hides_unknown_request(self):
        self.assertEqual(self.client.post("/webhooks/higgsfield/", data="{}", content_type="application/json").status_code, 400)
        body = {"request_id": str(uuid.uuid4()), "status": "failed", "error": "x", "payload": None}
        self.assertEqual(self.client.post("/webhooks/higgsfield/", data=json.dumps(body), content_type="application/json").status_code, 204)

    @patch("engine.media.providers.video_status", side_effect=ProviderUnavailableError("temporary"))
    def test_higgs_webhook_records_hint_while_authoritative_status_is_unavailable(self, status):
        remote_id = str(uuid.uuid4())
        job = self.job("video")
        MediaGeneration.objects.filter(pk=job.pk).update(status="running", provider_id=remote_id)
        body = {"request_id": remote_id, "status": "completed", "error": None, "payload": {"video": {"url": "https://ignored"}}}
        response = self.client.post("/webhooks/higgsfield/", data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, 204)
        status.assert_not_called()
        self.assertEqual(recover_media_jobs(limit=5)["errors"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, "running")

    @patch("engine.media.providers.download_output")
    @patch("engine.media.providers.video_status")
    def test_stale_saving_job_recovers_result_without_new_paid_submit(self, status, download):
        remote_id = str(uuid.uuid4())
        job = self.job("video")
        MediaGeneration.objects.filter(pk=job.pk).update(status="running", provider_id=remote_id)
        status.return_value = {"status": "completed", "video": {"url": "https://trusted.example/result.mp4"}}
        download.side_effect = [MediaError("storage/download temporary"), movie()]
        with self.assertRaises(MediaError):
            advance_job(MediaGeneration.objects.get(pk=job.pk))
        job.refresh_from_db()
        self.assertEqual(job.status, "saving")
        MediaGeneration.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=11))
        result = recover_media_jobs(limit=5)
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.assets.count(), 1)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(download.call_count, 2)

    @patch("engine.media.providers.cancel_video", return_value=True)
    def test_cancel_job_never_submits_generation(self, cancel):
        queued = self.job("video")
        cancel_job(queued)
        queued.refresh_from_db()
        self.assertEqual(queued.status, "canceled")
        cancel.assert_not_called()

        # Active-job cancel uses only the provider cancel endpoint for a known request id.
        active = create_job(self.run, token=uuid.uuid4(), kind="video", brief="Ny video")
        MediaGeneration.objects.filter(pk=active.pk).update(status="running", provider_id=str(uuid.uuid4()))
        cancel_job(active)
        active.refresh_from_db()
        self.assertEqual(active.status, "canceled")
        cancel.assert_called_once()

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
