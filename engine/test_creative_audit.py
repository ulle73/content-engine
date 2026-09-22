"""Regression cases found by the 2026-09-22 end-to-end audit. No live providers."""
import json
import uuid
from unittest.mock import Mock, patch

import httpx
from django.test import TestCase, override_settings
from django.urls import reverse

from . import media_providers as providers, prompt_library
from .creative_director import build_plan, parse_brief
from .media import advance_job, create_job
from .models import MediaGeneration
from . import test_media as fixtures
from .test_media import picture


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class CreativeAuditTests(TestCase):
    setUp = fixtures.MediaTests.setUp
    url = fixtures.MediaTests.url
    job = fixtures.MediaTests.job

    def test_long_valid_brief_does_not_crash_inspiration_search(self):
        job = create_job(self.run, token=uuid.uuid4(), kind="image", brief="golf " * 1100)
        self.assertEqual(len(job.brief), 5500)

    def test_timeline_does_not_turn_ten_second_video_into_two_seconds(self):
        brief = parse_brief("0–2 sek · Hook\n2–5 sek · Motiv\n5–10 sek · Avslut", kind="video")
        self.assertEqual(brief.duration_seconds, 10)

    def test_hyphenated_swedish_duration(self):
        self.assertEqual(parse_brief("En cinematic 5-sekunders video", kind="video").duration_seconds, 5)

    def test_explicit_image_ratio_controls_actual_dimensions(self):
        plan = build_plan(self.run, "En kvadratisk golfbild i 1:1", kind="image", shape="portrait")
        self.assertEqual(plan.parameters["size"], "1024x1024")

    def test_priority_changes_image_quality(self):
        low = build_plan(self.run, "Golf", kind="image", priority="economy")
        high = build_plan(self.run, "Golf", kind="image", priority="quality")
        self.assertEqual(low.parameters["quality"], "low")
        self.assertEqual(high.parameters["quality"], "high")

    @patch("engine.media.providers.generate_images")
    def test_status_poll_never_starts_queued_paid_generation(self, generate):
        generate.return_value = ([picture()], {})
        job = self.job()
        response = self.client.post(self.url("media_job_status", job_id=job.pk))
        self.assertEqual(response.status_code, 200)
        generate.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.status, "queued")

    def test_malformed_webhook_scalar_is_a_400_not_a_500(self):
        for payload in (None, [], 1, "hello", {"request_id": str(uuid.uuid4()), "status": []}):
            response = self.client.post("/webhooks/higgsfield/", json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 400)

    @patch.dict("os.environ", {"HIGGSFIELD_API_KEY_GK": "test-only"})
    @patch("engine.media_providers.httpx.request")
    def test_paid_timeout_response_is_unknown(self, request):
        request.return_value = httpx.Response(408, json={"detail": "timeout"})
        with self.assertRaises(providers.UncertainGeneration):
            providers.higgs("POST", "/model", billable=True)
        self.assertEqual(request.call_count, 1)

    @patch.dict("os.environ", {"HIGGSFIELD_API_KEY_GK": "test-only"})
    @patch("engine.media_providers.httpx.request")
    def test_paid_non_object_response_is_unknown(self, request):
        request.return_value = httpx.Response(200, json=[])
        with self.assertRaises(providers.UncertainGeneration):
            providers.higgs("POST", "/model", billable=True)

    @patch.dict("os.environ", {"HIGGSFIELD_API_KEY_GK": "gk-complete", "HIGGSFIELD_API_SECRET_GK": "", "HIGGSFIELD_API_SECRET": "legacy-other"})
    def test_primary_credential_is_never_combined_with_other_account_secret(self):
        self.assertEqual(providers._higgsfield_credential(), "gk-complete")

    def test_archive_has_explicit_restore_without_original_repaste(self):
        prompt, _ = prompt_library.save_prompt(self.user, self.company.pk, "Audit original")
        prompt_library.archive_prompt(self.user, self.company.pk, prompt.pk)
        url = reverse("engine:prompt_library", kwargs={"workspace_id": self.company.pk})
        self.assertContains(self.client.get(url, {"archived": "1"}), "Audit original")
        restore = reverse("engine:prompt_restore", kwargs={"workspace_id": self.company.pk, "prompt_id": prompt.pk})
        self.assertEqual(self.client.get(restore).status_code, 405)
        self.assertEqual(self.client.post(restore).status_code, 302)
        prompt.refresh_from_db()
        self.assertIsNone(prompt.archived_at)

    def test_generation_provenance_and_price_are_not_overwritten_by_duplicate(self):
        first = self.job("video")
        first.usage = {"estimate": {"usd": "0.7"}}
        first.status = "completed"
        first.save()
        saved, _ = prompt_library.save_from_generation(self.user, self.company.pk, first.pk)
        second = self.job("video")
        second.prompt = first.prompt
        second.save(update_fields=["prompt"])
        saved, _ = prompt_library.save_from_generation(self.user, self.company.pk, second.pk)
        self.assertEqual(saved.metadata["generation"]["id"], str(saved.generation_id))
        self.assertEqual(saved.metadata["generation"]["estimated_usd"], "0.7")

    def test_help_is_available_without_leaving_creative_pages(self):
        for url in (self.url("media"), reverse("engine:prompt_library", kwargs={"workspace_id": self.company.pk})):
            self.assertContains(self.client.get(url), "Hur fungerar det?")
            self.assertContains(self.client.get(url), "<dialog")

    @patch("engine.media.providers.generate_images")
    def test_storage_failure_after_paid_image_result_blocks_new_submit(self, generate):
        generate.return_value = ([picture()], {})
        job = self.job()
        with patch("engine.media.store_asset", side_effect=providers.MediaError("storage unavailable")):
            advance_job(job)
        self.assertEqual(job.status, "unknown")
        self.assertEqual(self.job().pk, job.pk)
        self.assertEqual(generate.call_count, 1)

    @patch("engine.media_providers.higgs")
    def test_preview_video_calls_only_estimate_and_persists_reviewable_price(self, higgs):
        higgs.return_value = {"usd": "0.35", "credits": "5.6"}
        response = self.client.post(self.url("media_generate"), {
            "token": str(uuid.uuid4()), "kind": "video", "brief": "Golf 5 sekunder", "count": "1"})
        self.assertEqual(response.status_code, 302)
        job = MediaGeneration.objects.get()
        self.assertEqual(job.status, "queued")
        self.assertEqual(job.usage["estimate"]["usd"], "0.35")
        self.assertEqual(higgs.call_count, 1)
        self.assertTrue(higgs.call_args.args[1].startswith("/estimate/"))
        page = self.client.get(self.url("media_job", job_id=job.pk))
        self.assertContains(page, "Starta betald generation")
        self.assertContains(page, "0.35")
        self.assertNotContains(page, "form.addEventListener('submit',check);check();")

    @patch("engine.media_providers.higgs")
    def test_price_increase_after_review_never_submits(self, higgs):
        job = self.job("video")
        job.usage = {"approved_max_usd": "0.35"}
        job.save()
        higgs.return_value = {"usd": "0.70"}
        with self.assertRaises(providers.MediaError):
            providers.start_video(job)
        self.assertEqual(higgs.call_count, 1)

    @patch("engine.media.providers.generate_images")
    def test_start_requires_review_and_is_company_scoped(self, generate):
        job = self.job()
        url = self.url("media_job_start", job_id=job.pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        generate.assert_not_called()
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)

    @patch("engine.media.providers.video_status")
    def test_webhook_acknowledges_without_slow_provider_network(self, status):
        job = self.job("video")
        remote_id = str(uuid.uuid4())
        MediaGeneration.objects.filter(pk=job.pk).update(status="running", provider_id=remote_id)
        response = self.client.post("/webhooks/higgsfield/", json.dumps({
            "request_id": remote_id, "status": "completed", "error": None, "payload": {}}), content_type="application/json")
        self.assertEqual(response.status_code, 204)
        status.assert_not_called()

    @patch("engine.media.providers.generate_images")
    def test_library_can_open_first_studio_without_paid_text_generation(self, generate):
        from .models import ContentRun
        url = reverse("engine:media_new", kwargs={"workspace_id": self.company.pk})
        token = str(uuid.uuid4())
        response = self.client.post(url, {"token": token})
        self.assertEqual(response.status_code, 302)
        run = ContentRun.objects.get(pk=token, workspace=self.company)
        self.assertTrue(run.context["media_only"])
        self.assertEqual(self.client.post(url, {"token": token}).status_code, 302)
        self.assertEqual(ContentRun.objects.filter(pk=token).count(), 1)
        generate.assert_not_called()

    def test_oauth_registration_malformed_url_or_grants_rejected(self):
        from django.test import RequestFactory
        from .mcp_oauth import ChatGPTDCRPermission
        for payload in ({"redirect_uris": ["https://[invalid"]},
                        {"redirect_uris": ["https://chatgpt.com:444/callback"]},
                        {"redirect_uris": ["https://chatgpt.com/callback"], "grant_types": [[]]}):
            request = RequestFactory().post("/oauth/register/", json.dumps(payload), content_type="application/json")
            self.assertFalse(ChatGPTDCRPermission().has_permission(request))

    @patch("engine.media.providers.generate_images")
    def test_openai_server_error_is_uncertain_not_safe_to_resubmit(self, generate):
        from openai import InternalServerError
        generate.side_effect = InternalServerError("provider error", response=httpx.Response(
            500, request=httpx.Request("POST", "https://api.openai.com/v1/images/generations")), body=None)
        job = self.job()
        advance_job(job)
        self.assertEqual(job.status, "unknown")

    @patch("engine.media.providers.generate_images")
    def test_reviewed_job_cannot_start_after_run_was_delivered(self, generate):
        from .media import preview_job, start_reviewed_job
        job = preview_job(self.job())
        self.run.delivery_status = "sent"
        self.run.save(update_fields=["delivery_status"])
        with self.assertRaises(providers.MediaError):
            start_reviewed_job(job)
        generate.assert_not_called()

    @patch("engine.media_providers.open_asset")
    @patch("engine.media_providers.public_url", side_effect=lambda value: value)
    @patch("engine.media_providers.public_stream")
    @patch("engine.media_providers.higgs")
    def test_image_to_video_uses_actual_visible_reference(self, higgs, put, public, opened):
        higgs.return_value = {"upload_url": "https://test.invalid/upload", "public_url": "https://test.invalid/image", "upload_headers": {}}
        opened.return_value.__enter__.return_value.read.return_value = b"visible-reference"
        providers.upload_input(Mock(mime_type="image/png"))
        self.assertNotEqual(opened.call_args.kwargs.get("unbranded"), True)

    @patch("engine.media_providers.higgs")
    def test_mcp_preview_is_scoped_and_cannot_submit(self, higgs):
        from . import mcp_server
        from mcp.server.mcpserver.exceptions import ToolError
        from django.contrib.auth import get_user_model
        higgs.return_value = {"usd": "0.35"}
        with patch("engine.mcp_server.current_django_user", return_value=self.user):
            result = mcp_server.preview_media(str(self.company.pk), str(self.run.pk), "audit-preview", 0,
                                             kind="video", brief="Golf 5 sekunder")
            self.assertEqual(result["status"], "queued")
            self.assertEqual(result["estimated_usd"], "0.35")
            self.assertEqual(higgs.call_count, 1)
        with patch("engine.mcp_server.current_django_user", return_value=get_user_model().objects.create_user(username="outsider")):
            with self.assertRaises(ToolError):
                mcp_server.preview_media(str(self.company.pk), str(self.run.pk), "audit-preview", 0, brief="x")
        self.assertEqual(higgs.call_count, 1)

    def test_mcp_prompt_save_search_and_restore_obey_owner(self):
        from . import mcp_server
        from mcp.server.mcpserver.exceptions import ToolError
        from django.contrib.auth import get_user_model
        with patch("engine.mcp_server.current_django_user", return_value=self.user):
            saved = mcp_server.save_creative_prompt(str(self.company.pk), "Golf audit original")
            mcp_server.update_creative_prompt(str(self.company.pk), saved["id"], action="archive")
            self.assertEqual(mcp_server.search_creative_prompts(str(self.company.pk)), [])
            mcp_server.update_creative_prompt(str(self.company.pk), saved["id"], action="restore")
            self.assertEqual(mcp_server.search_creative_prompts(str(self.company.pk))[0]["id"], saved["id"])
        with patch("engine.mcp_server.current_django_user", return_value=get_user_model().objects.create_user(username="otherprompt")):
            with self.assertRaises(ToolError):
                mcp_server.update_creative_prompt(str(self.company.pk), saved["id"], action="archive")

    def test_recovery_lifespan_preserves_original_and_stops_cleanly(self):
        import asyncio
        from contextlib import asynccontextmanager
        from types import SimpleNamespace
        from asgiref.sync import async_to_sync
        from .media_recovery import install_recovery
        events = []
        @asynccontextmanager
        async def original(app):
            events.append("startup")
            yield {"original": True}
            events.append("shutdown")
        async def loop(stop):
            events.append("recovery")
            await stop.wait()
            events.append("stopped")
        async def scenario():
            app = SimpleNamespace(router=SimpleNamespace(lifespan_context=original))
            install_recovery(app)
            async with app.router.lifespan_context(app) as state:
                self.assertEqual(state, {"original": True})
                await asyncio.sleep(0)
        with patch("engine.media_recovery.recovery_loop", loop):
            async_to_sync(scenario)()
        self.assertEqual(events, ["startup", "recovery", "stopped", "shutdown"])

    @patch("engine.media_providers.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.215.14", 443))])
    @patch("engine.media_providers.httpx.Client")
    def test_output_download_pins_public_ip_but_keeps_tls_hostname(self, client, dns):
        response = client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        response.iter_bytes.return_value = [b"bytes"]
        self.assertEqual(providers.download_output("https://cdn.example.test/result.png"), b"bytes")
        call = client.return_value.__enter__.return_value.stream.call_args
        self.assertEqual(str(call.args[1]), "https://93.184.215.14/result.png")
        self.assertEqual(call.kwargs["extensions"]["sni_hostname"], "cdn.example.test")
        self.assertEqual(call.kwargs["headers"]["Host"], "cdn.example.test")
        self.assertEqual(dns.call_count, 1)

    @patch("engine.media_providers.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))])
    def test_output_download_rejects_private_and_malformed_urls(self, dns):
        for url in ("https://example.test/file", "https://[invalid", "https://host.test:no/file", None):
            with self.assertRaises(providers.MediaError):
                providers.download_output(url)

    @patch("engine.media.providers.estimate_video")
    def test_failed_repreview_invalidates_prior_approval(self, estimate):
        from .media import preview_job, start_reviewed_job
        job = self.job(kind="video")
        estimate.return_value = ("model", {}, {"estimate": {"usd": "0.35"}})
        preview_job(job)
        estimate.side_effect = providers.MediaError("No estimate")
        with self.assertRaises(providers.MediaError):
            preview_job(job)
        job.refresh_from_db()
        self.assertNotIn("reviewed_at", job.usage)
        with self.assertRaises(providers.MediaError):
            start_reviewed_job(job)

    @patch("engine.media.providers.video_status", return_value={"status": []})
    def test_malformed_remote_status_is_recoverable(self, status):
        from .media import reconcile_video_job
        job = self.job(kind="video")
        job.status, job.provider_id = "running", str(uuid.uuid4())
        job.save()
        with self.assertRaises(providers.MediaError):
            reconcile_video_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "running")

    @patch("engine.media_providers.higgs", return_value={})
    def test_malformed_upload_preflight_fails_cleanly(self, higgs):
        with self.assertRaises(providers.MediaError):
            providers.upload_input(Mock(mime_type="image/png"))
