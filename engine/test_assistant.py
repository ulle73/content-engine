"""Conversation integration and approval boundaries. All providers are mocked."""
import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from . import test_media as media_test
from .assistant import templates
from .assistant.contracts import Proposal, Question
from .models import (
    AssistantConversation,
    AssistantPlan,
    AssistantTemplate,
    AssistantTurn,
    Company,
    ContentRun,
    MediaAsset,
    MediaGeneration,
)
from .openrouter import OpenRouterError


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class AssistantTests(TestCase):
    def setUp(self):
        media_test.MediaTests.setUp(self)
        self.conversation = AssistantConversation.objects.create(company=self.company, author=self.user)
        self.proposal = Proposal(answer="Jag föreslår ett kort animerat budskap.", title="Mer golf", workflow="motion",
                                 brief="Animera texten Mer golf. Mer glädje.", headline="Mer golf. Mer glädje.", body="Ta med en vän.", cta="Upptäck Golf")
        self.planner = patch("engine.assistant.service.structured_assistant", return_value=(self.proposal, {"cost_usd": 0.001, "model": "test"})).start()
        self.addCleanup(patch.stopall)

    def url(self, name, **kwargs):
        if name in {"assistant_conversation", "assistant_state", "assistant_send", "assistant_action", "assistant_refresh"}:
            kwargs.setdefault("conversation_id", self.conversation.pk)
        return reverse("engine:" + name, kwargs={"workspace_id": self.company.pk, **kwargs})

    def post(self, name, data, **kwargs):
        return self.client.post(self.url(name, **kwargs), json.dumps(data), content_type="application/json")

    def request(self, **changes):
        self.conversation.refresh_from_db()
        return {"key": str(uuid.uuid4()), "expected_revision": self.conversation.revision, "message": "Animera Mer golf. Mer glädje.", **changes}

    def turn(self, **changes):
        response = self.post("assistant_send", self.request(**changes))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["turns"][-1]["status"], "completed", response.content)
        return AssistantPlan.objects.latest("created_at")

    def action(self, plan, action="prepare", **changes):
        self.conversation.refresh_from_db()
        return self.post("assistant_action", {"plan_id": str(plan.pk), "expected_revision": self.conversation.revision, "action": action, **changes})

    def test_main_workspace_and_navigation(self):
        response = self.client.get(self.url("assistant"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vad vill du skapa?")
        self.assertContains(response, "Promptmall")
        self.assertContains(response, "AI-samtal och bildanalys debiteras")
        self.assertContains(response, self.url("assistant"))

    def test_sending_compiles_without_creating_or_starting_media(self):
        with patch("engine.media_providers.start_video") as video, patch("engine.media_providers.generate_images") as images:
            plan = self.turn()
        video.assert_not_called()
        images.assert_not_called()
        self.assertEqual(plan.spec["workflow"], "motion")
        self.assertNotIn("compiled", plan.spec)
        self.assertEqual(plan.spec["review"]["total_usd"], "0")
        self.assertEqual(MediaGeneration.objects.count(), 0)

    def test_questions_block_preparation(self):
        self.proposal.questions = [Question(text="Vilket budskap?", options=["Mer golf", "Mer glädje"])]
        plan = self.turn()
        result = self.action(plan)
        self.assertEqual(result.status_code, 422)
        self.assertEqual(MediaGeneration.objects.count(), 0)

    def test_idempotent_message_and_conflicting_replay(self):
        data = self.request()
        first = self.post("assistant_send", data)
        second = self.post("assistant_send", data)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(self.planner.call_count, 1)
        self.assertEqual(AssistantTurn.objects.count(), 1)
        result = self.post("assistant_send", {**data, "message": "Något annat"})
        self.assertEqual(result.status_code, 422)

    def test_old_plan_cannot_prepare_after_new_message(self):
        first = self.turn()
        self.turn(message="Gör texten kortare")
        result = self.action(first)
        self.assertEqual(result.status_code, 422)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_followup_preserves_prior_brief_in_bounded_context(self):
        self.turn()
        self.turn(message="Gör avslutet lugnare")
        self.assertEqual(self.planner.call_args.kwargs["payload"]["previous_brief"], self.proposal.brief)
        self.assertEqual(len(self.planner.call_args.kwargs["payload"]["history"]), 1)

    def test_stale_revision_is_rejected_before_provider(self):
        self.turn()
        self.planner.reset_mock()
        response = self.post("assistant_send", self.request(expected_revision=0))
        self.assertEqual(response.status_code, 422)
        self.planner.assert_not_called()

    def test_inflight_turn_is_not_duplicated(self):
        AssistantTurn.objects.create(conversation=self.conversation, revision=1, request={})
        self.conversation.revision = 1
        self.conversation.save()
        result = self.post("assistant_send", self.request())
        self.assertEqual(result.status_code, 422)
        self.planner.assert_not_called()

    def test_failed_provider_is_saved_and_can_be_retried(self):
        self.planner.side_effect = OpenRouterError("Tillfälligt fel")
        response = self.post("assistant_send", self.request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["turns"][-1]["status"], "failed")
        self.planner.side_effect = None
        self.turn()
        self.assertEqual(AssistantTurn.objects.count(), 2)

    def test_expired_claim_recovers_and_late_response_is_fenced(self):
        old = AssistantTurn.objects.create(conversation=self.conversation, revision=1, request={})
        AssistantTurn.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(minutes=3))
        self.conversation.revision = 1
        self.conversation.save()
        self.turn()
        old.refresh_from_db()
        self.assertEqual(old.status, "failed")

    def test_cross_company_conversation_and_asset_are_rejected(self):
        other = Company.objects.create(owner=self.user, name="Other")
        foreign = AssistantConversation.objects.create(company=other, author=self.user)
        result = self.client.get(self.url("assistant_state", conversation_id=foreign.pk))
        self.assertEqual(result.status_code, 404)
        asset = media_test.store_asset(other, media_test.picture())
        result = self.post("assistant_send", self.request(attachments=[{"asset_id": str(asset.pk), "role": "start"}]))
        self.assertEqual(result.status_code, 422)
        self.planner.assert_not_called()

    def test_foreign_owner_cannot_read_workspace(self):
        outsider = media_test.get_user_model().objects.create_user(username="outsider")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(self.url("assistant")).status_code, 404)

    def test_csrf_is_required_for_actions(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        result = client.post(self.url("assistant_create"), json.dumps({"key": str(uuid.uuid4())}), content_type="application/json")
        self.assertEqual(result.status_code, 403)

    def test_unknown_fields_cannot_be_used_as_tool_commands(self):
        result = self.post("assistant_send", self.request(action="start", approved=True))
        self.assertEqual(result.status_code, 422)
        self.planner.assert_not_called()

    def test_modified_plan_fingerprint_is_rejected(self):
        plan = self.turn()
        plan.spec["brief"] = "Något annat"
        plan.save()
        self.assertEqual(self.action(plan).status_code, 422)

    def test_motion_preparation_is_idempotent_and_not_a_render(self):
        from .motion.models import MotionProject, MotionRender
        plan = self.turn()
        self.assertEqual(self.action(plan).status_code, 200)
        self.assertEqual(self.action(plan).status_code, 200)
        self.assertEqual(MotionProject.objects.count(), 1)
        self.assertEqual(MotionRender.objects.count(), 0)

    def test_motion_preview_requires_active_worker(self):
        plan = self.turn()
        self.action(plan)
        with patch("engine.motion.jobs.worker_available", return_value=False):
            result = self.action(plan, "preview")
        self.assertEqual(result.status_code, 422)
        self.assertContains(result, "dator", status_code=422)

    def test_motion_final_cannot_skip_approved_preview(self):
        plan = self.turn()
        self.action(plan)
        with patch("engine.motion.jobs.worker_available", return_value=True):
            result = self.action(plan, "final")
        self.assertEqual(result.status_code, 422)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_image_preparation_uses_compiler_and_never_generates(self):
        self.proposal.workflow, self.proposal.brief = "image", "En stiliserad illustration av en golfboll på grön bakgrund."
        plan = self.turn(workflow="image")
        with patch("engine.media_providers.generate_images") as images:
            result = self.action(plan)
        self.assertEqual(result.status_code, 200, result.content)
        images.assert_not_called()
        job = MediaGeneration.objects.get()
        self.assertEqual(job.status, "queued")
        plan.refresh_from_db()
        self.assertEqual(job.prompt, plan.prepared["compiled"]["prompt"])
        self.assertTrue(result.json()["turns"][-1]["plan"]["job"]["can_start"])

    def test_text_draft_is_saved_in_existing_content_flow(self):
        self.proposal.workflow, self.proposal.caption = "text", "Mer golf med en vän."
        plan = self.turn(workflow="text")
        self.assertEqual(self.action(plan).status_code, 200)
        plan.refresh_from_db()
        run = ContentRun.objects.get(pk=plan.prepared["run_id"])
        self.assertEqual(run.draft["instagram"], self.proposal.caption)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_templates_are_company_scoped_versioned_and_snapshotted(self):
        first = templates.save(self.company, self.user, {"title": "Min mall", "instructions": "Skapa {{brief}} för {{company_name}}", "kind": "motion"})
        plan = self.turn(template=str(first.pk))
        second = templates.save(self.company, self.user, {"key": first.key, "title": "Min mall", "instructions": "Ny instruktion {{brief}}", "kind": "motion"})
        self.assertEqual(second.version, 2)
        self.assertEqual(plan.spec["template"]["version"], 1)
        self.assertEqual(len([item for item in templates.catalog(self.company) if item["key"] == first.key]), 1)
        self.assertEqual(AssistantTemplate.objects.count(), 2)

    def test_unknown_template_variables_are_rejected_without_evaluation(self):
        result = self.post("assistant_template", {"title": "Bad", "instructions": "{{system}}", "kind": "auto"})
        self.assertEqual(result.status_code, 422)
        self.assertFalse(AssistantTemplate.objects.exists())

    def test_upload_deduplicates_only_inside_company(self):
        data = media_test.picture()
        other = Company.objects.create(owner=self.user, name="Other")
        media_test.store_asset(other, data)
        for _ in range(2):
            response = self.client.post(self.url("assistant_upload"), {"file": SimpleUploadedFile("golf.png", data)})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(MediaAsset.objects.filter(company=self.company).count(), 1)
        self.assertEqual(MediaAsset.objects.filter(company=other).count(), 1)

    def test_image_pixels_are_bounded_and_sent_to_vision(self):
        asset = media_test.store_asset(self.company, media_test.picture())
        self.turn(attachments=[{"asset_id": str(asset.pk), "role": "start"}])
        images = self.planner.call_args.kwargs["images"]
        self.assertTrue(images[0].startswith("data:image/jpeg;base64,"))
        self.assertLess(len(images[0]), 100_000)

    def test_asset_change_invalidates_preparation(self):
        asset = media_test.store_asset(self.company, media_test.picture())
        plan = self.turn(attachments=[{"asset_id": str(asset.pk), "role": "start"}])
        MediaAsset.objects.filter(pk=asset.pk).update(sha256="changed")
        self.assertEqual(self.action(plan).status_code, 422)

    def test_multiple_references_survive_in_sequence(self):
        first = media_test.store_asset(self.company, media_test.picture())
        second = media_test.store_asset(self.company, media_test.picture())
        plan = self.turn(workflow="sequence", attachments=[{"asset_id": str(first.pk), "role": "reference"}, {"asset_id": str(second.pk), "role": "reference"}])
        with patch("engine.media.preview_job"):
            result = self.action(plan)
        self.assertEqual(result.status_code, 200, result.content)
        from .models import SequenceProject
        self.assertEqual(SequenceProject.objects.get().anchors.count(), 2)

    def test_queued_job_is_never_started_by_polling(self):
        self.proposal.workflow, self.proposal.brief = "image", "En illustration av en golfboll."
        plan = self.turn(workflow="image")
        self.action(plan)
        with patch("engine.media.advance_job") as advance:
            result = self.post("assistant_refresh", {})
        self.assertEqual(result.status_code, 200)
        advance.assert_not_called()

    def test_manual_model_is_not_overridden_for_motion(self):
        response = self.post("assistant_send", self.request(model="some-video-model", workflow="motion"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["turns"][-1]["status"], "failed")
        self.assertFalse(AssistantPlan.objects.exists())

    def test_non_image_start_reference_is_rejected_before_planner(self):
        asset = MediaAsset.objects.create(company=self.company, kind="audio", origin="uploaded", provider="user", storage_backend="local", storage_key="unused.wav", mime_type="audio/wav", byte_size=1)
        response = self.post("assistant_send", self.request(attachments=[{"asset_id": str(asset.pk), "role": "start"}]))
        self.assertEqual(response.status_code, 422)
        self.planner.assert_not_called()

    def test_expired_template_and_invalid_id_are_safe_errors(self):
        response = self.post("assistant_send", self.request(template="not-a-uuid"))
        self.assertEqual(response.status_code, 422)
        self.planner.assert_not_called()

    def test_foreign_conversation_creation_key_does_not_leak(self):
        other = Company.objects.create(owner=self.user, name="Other")
        foreign = AssistantConversation.objects.create(company=other, author=self.user)
        response = self.post("assistant_create", {"key": str(foreign.pk)})
        self.assertEqual(response.status_code, 422)

    def test_expired_current_facts_are_excluded_from_planning(self):
        self.company.current = "Erbjudande som har gått ut"
        self.company.valid_until = timezone.localdate() - timedelta(days=1)
        self.company.save()
        self.turn()
        self.assertEqual(self.planner.call_args.kwargs["payload"]["company"]["current"], "")

    def test_late_provider_response_cannot_overwrite_newer_state(self):
        def late(**kwargs):
            AssistantConversation.objects.filter(pk=self.conversation.pk).update(revision=2)
            return self.proposal, {}
        self.planner.side_effect = late
        result = self.post("assistant_send", self.request())
        self.assertEqual(result.status_code, 200)
        self.assertFalse(AssistantPlan.objects.exists())
        self.assertEqual(AssistantTurn.objects.get().status, "failed")

    def test_rate_limit_is_checked_before_provider(self):
        AssistantTurn.objects.bulk_create([AssistantTurn(conversation=self.conversation, revision=i+1, request={}, status="completed") for i in range(60)])
        result = self.post("assistant_send", self.request())
        self.assertEqual(result.status_code, 422)
        self.planner.assert_not_called()

    def test_video_with_logo_prepares_only_the_video_then_original_logo(self):
        logo = media_test.store_asset(self.company, media_test.picture())
        self.proposal.workflow = "video"
        self.proposal.brief = "Skapa ett 4 sekunder långt klipp av en golfboll, följt av vår exakta logga."
        self.proposal.clip_brief = "4 sekunder. En golfboll på green i mjukt kvällsljus. Statisk kamera."
        plan = self.turn(workflow="video", attachments=[{"asset_id": str(logo.pk), "role": "logo"}])
        self.assertNotIn("compiled", plan.spec)
        with patch("engine.media_providers.estimate_video", return_value=("test-model", {}, {"estimate": {"usd": "0.10"}})), patch("engine.media_providers.start_video") as start:
            response = self.action(plan)
        self.assertEqual(response.status_code, 200, response.content)
        start.assert_not_called()
        job = MediaGeneration.objects.get()
        self.assertIsNone(job.logo_asset_id)
        self.assertEqual(job.brief, self.proposal.clip_brief)
        job.status = "completed"
        job.save()
        # Output metadata is independently verified by the existing ingestion pipeline.
        output = MediaAsset.objects.create(company=self.company, generation=job, kind="video", origin="generated", provider="higgsfield",
                                            storage_backend="local", storage_key="test.mp4", mime_type="video/mp4", byte_size=1,
                                            width=720, height=1280, duration_seconds=4, sha256="synthetic-output")
        response = self.action(plan, "compose")
        self.assertEqual(response.status_code, 200, response.content)
        plan.refresh_from_db()
        from .motion.models import MotionProject
        project = MotionProject.objects.get(pk=plan.prepared["finish_project_id"])
        revision = project.revisions.get()
        self.assertEqual(revision.brand["logo_asset_id"], str(logo.pk))
        self.assertEqual(revision.spec["scenes"][0]["props"]["asset_id"], str(output.pk))
        self.assertEqual(self.action(plan, "compose").status_code, 200)
        self.assertEqual(MotionProject.objects.count(), 1)

    def test_custom_logo_does_not_change_company_brand(self):
        logo = media_test.store_asset(self.company, media_test.picture())
        plan = self.turn(attachments=[{"asset_id": str(logo.pk), "role": "logo"}])
        self.assertEqual(self.action(plan).status_code, 200)
        self.company.refresh_from_db()
        self.assertIsNone(self.company.official_logo_id)
        from .motion.models import MotionProject
        self.assertEqual(MotionProject.objects.get().revisions.get().brand["logo_asset_id"], str(logo.pk))

    def test_audio_file_is_in_motion_spec(self):
        asset = MediaAsset.objects.create(company=self.company, kind="audio", origin="uploaded", provider="user", storage_backend="local", storage_key="unused.wav", mime_type="audio/wav", byte_size=1)
        plan = self.turn(attachments=[{"asset_id": str(asset.pk), "role": "audio"}])
        self.assertEqual(self.action(plan).status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.prepared["compiled"]["motion_spec"]["audio"]["music_asset_id"], str(asset.pk))

    def scroll_plan(self, **changes):
        import io

        from PIL import Image
        images = []
        for size in [(320, 480), (600, 400), (1080, 1920), (2048, 1024)]:
            stream = io.BytesIO()
            Image.new("RGB", size, "green").save(stream, "PNG")
            images.append(media_test.store_asset(self.company, stream.getvalue()))
        self.proposal.workflow = "sequence"
        self.proposal.brief = "Mjuk kamerafärd framåt mellan bilderna, ett sammanhängande scroll-klipp per övergång."
        return self.turn(**{"template": "animated-scroll", "model": "bytedance/seedance-2.5", "max_cost_usd": "5.00",
                         "attachments": [{"asset_id": str(asset.pk), "role": "reference"} for asset in images], **changes})

    def test_four_images_are_reviewed_before_optimization_and_paid_work(self):
        plan = self.scroll_plan()
        self.assertFalse(MediaGeneration.objects.exists())
        self.assertNotIn("compiled", plan.spec)
        review = plan.spec["review"]
        self.assertEqual(review["count"], 3)
        self.assertEqual(review["total_usd"], "3.0840")
        self.assertEqual(len(review["assets"]), 4)
        self.assertTrue(review["assets"][0]["warnings"])
        self.assertTrue(any("olika proportioner" in warning for warning in review["warnings"]))
        self.assertEqual(review["recommendation"]["model_id"], "bytedance/seedance-2.5")
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.10"}})), patch("engine.media_providers.start_video") as start:
            result = self.action(plan)
        self.assertEqual(result.status_code, 200, result.content)
        start.assert_not_called()
        self.assertEqual(MediaGeneration.objects.filter(status="queued").count(), 3)
        plan.refresh_from_db()
        self.assertEqual(len(plan.prepared["compiled"]["clips"]), 3)
        self.assertEqual(len(plan.prepared["normalized_assets"]), 3)
        from .models import SequenceProject
        project = SequenceProject.objects.get()
        self.assertEqual(project.anchors.filter(locked=True).count(), 4)
        self.assertEqual(project.clips.count(), 3)

    def test_max_cost_covers_all_transitions_and_blocks_changed_quote(self):
        plan = self.scroll_plan(max_cost_usd="3.10")
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.20"}})):
            response = self.action(plan)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["turns"][-1]["plan"]["budget"]["over_budget"])
        plan.refresh_from_db()
        with patch("engine.media.advance_job") as advance:
            response = self.action(plan, "start", job_id=plan.prepared["job_ids"][0])
        self.assertEqual(response.status_code, 422)
        advance.assert_not_called()

    def test_plan_over_user_budget_does_not_create_jobs(self):
        plan = self.scroll_plan(max_cost_usd="0")
        self.assertEqual(self.action(plan).status_code, 422)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_unknown_price_cannot_bypass_budget(self):
        self.proposal.workflow, self.proposal.brief = "image", "En golfboll på grön bakgrund."
        plan = self.turn(workflow="image")
        self.action(plan)
        with patch("engine.media.advance_job") as advance:
            response = self.action(plan, "start")
        self.assertEqual(response.status_code, 422)
        advance.assert_not_called()

    def test_sequence_requires_explicit_clip_and_rejects_foreign_job(self):
        plan = self.scroll_plan()
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.10"}})):
            self.action(plan)
        with patch("engine.media.advance_job") as advance:
            self.assertEqual(self.action(plan, "start").status_code, 422)
            self.assertEqual(self.action(plan, "start", job_id=str(uuid.uuid4())).status_code, 422)
        advance.assert_not_called()

    def test_unsupported_scroll_model_shows_compatible_recommendation(self):
        first = media_test.store_asset(self.company, media_test.picture())
        second = media_test.store_asset(self.company, media_test.picture())
        plan = self.turn(template="animated-scroll", model="kling-video/v2.5-turbo/pro", attachments=[{"asset_id": str(asset.pk), "role": "reference"} for asset in (first, second)])
        self.assertIn("stöder inte", plan.spec["blocked"])
        self.assertEqual(plan.spec["review"]["recommendation"]["model_id"], "bytedance/seedance-2.5")
        self.assertEqual(self.action(plan).status_code, 422)

    def test_budget_contract_rejects_negative_and_unbounded_values(self):
        for amount in ["-1", "NaN", "1001", "1.001"]:
            self.assertEqual(self.post("assistant_send", self.request(max_cost_usd=amount)).status_code, 422)
        self.planner.assert_not_called()

    def test_legacy_start_cannot_bypass_studio_order_budget(self):
        from .media import advance_job, start_reviewed_job
        from .media_storage import MediaError
        plan = self.scroll_plan()
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.0280"}})):
            self.action(plan)
        job = MediaGeneration.objects.first()
        with patch("engine.media_providers.start_video") as start:
            with self.assertRaises(MediaError):
                start_reviewed_job(job)
            with self.assertRaises(MediaError):
                advance_job(job)
        start.assert_not_called()

    def test_paid_start_pins_quote_even_if_usage_review_is_cleared(self):
        from .media_providers import start_video
        from .media_storage import MediaError
        plan = self.scroll_plan()
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.0280"}})):
            self.action(plan)
        plan.refresh_from_db()
        with patch("engine.media.advance_job") as advance:
            response = self.action(plan, "start", job_id=plan.prepared["job_ids"][0])
        self.assertEqual(response.status_code, 200, response.content)
        quoted = advance.call_args.args[0]
        self.assertEqual(quoted.parameters["assistant_approved_max_usd"], "1.0280")
        quoted.usage = {}
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.0500"}})), patch("engine.media_providers.higgs") as higgs:
            with self.assertRaises(MediaError):
                start_video(quoted)
        higgs.assert_not_called()

    def test_scroll_respects_duration_and_mounts_original_logo_after_clips(self):
        self.proposal.brief = "Fyra sekunder per övergång. Mjuk kamerafärd framåt."
        images = [media_test.store_asset(self.company, media_test.picture()) for _ in range(3)]
        logo = media_test.store_asset(self.company, media_test.picture())
        plan = self.turn(template="animated-scroll", max_cost_usd="5.00", attachments=[
            *[{"asset_id": str(asset.pk), "role": "reference"} for asset in images], {"asset_id": str(logo.pk), "role": "logo"}])
        self.assertEqual(plan.spec["review"]["count"], 2)
        self.assertEqual(plan.spec["review"]["clips"][0]["duration"], 4)
        with patch("engine.media_providers.estimate_video", return_value=("test", {}, {"estimate": {"usd": "1.8488"}})):
            response = self.action(plan)
        self.assertEqual(response.status_code, 200, response.content)
        for job in MediaGeneration.objects.all():
            job.status = "completed"
            job.save()
            MediaAsset.objects.create(company=self.company, generation=job, kind="video", origin="generated", provider="higgsfield",
                                      storage_backend="local", storage_key="fixture.mp4", mime_type="video/mp4", byte_size=1,
                                      width=720, height=1280, duration_seconds=4, sha256="test-result")
        response = self.action(plan, "compose")
        self.assertEqual(response.status_code, 200, response.content)
        from .motion.models import MotionProject
        revision = MotionProject.objects.get().revisions.get()
        self.assertEqual(len(revision.spec["scenes"]), 3)
        self.assertEqual(revision.brand["logo_asset_id"], str(logo.pk))


    def test_video_model_incompatibility_keeps_user_selection(self):
        self.proposal.workflow, self.proposal.brief = "video", "4 sekunder. Golfbollen ligger still på green."
        plan = self.turn(workflow="video", model="not-a-registered-video-model")
        self.assertEqual(plan.spec["options"]["model"], "not-a-registered-video-model")
        self.assertIn("blocked", plan.spec)
        self.assertEqual(self.action(plan).status_code, 422)

    def test_model_response_cannot_return_executable_fields(self):
        self.planner.return_value = ({**self.proposal.model_dump(), "execute": "start_paid_generation"}, {})
        response = self.post("assistant_send", self.request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["turns"][-1]["status"], "failed")
        self.assertFalse(AssistantPlan.objects.exists())


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
@skipUnlessDBFeature("has_select_for_update")
class AssistantConcurrencyTests(TransactionTestCase):
    setUp = AssistantTests.setUp
    request = AssistantTests.request
    turn = AssistantTests.turn
    url = AssistantTests.url
    post = AssistantTests.post

    def parallel(self, operation):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        from django.db import connections
        barrier = Barrier(2)
        def worker(_):
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, range(2)))

    def test_concurrent_replay_plans_once(self):
        from .assistant.service import send_turn
        data = self.request()
        results = self.parallel(lambda: send_turn(self.company, self.user, self.conversation.pk, data).pk)
        self.assertEqual(results[0], results[1])
        self.planner.assert_called_once()
        self.assertEqual(AssistantPlan.objects.count(), 1)
        self.assertEqual(AssistantTurn.objects.count(), 1)

    def test_concurrent_confirmation_creates_one_project(self):
        from .assistant.service import act
        from .motion.models import MotionProject
        plan = self.turn()
        data = {"plan_id": str(plan.pk), "expected_revision": 1, "action": "prepare"}
        self.parallel(lambda: act(self.company, self.user, self.conversation.pk, data).pk)
        self.assertEqual(MotionProject.objects.count(), 1)
        self.assertFalse(MediaGeneration.objects.exists())
