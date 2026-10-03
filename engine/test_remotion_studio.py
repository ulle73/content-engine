"""Studio scene editing, immutable previews and timestamped source ownership."""
import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings

from . import test_assistant as assistant_test
from .assistant.contracts import MotionSceneEdit
from .media import store_asset
from .motion.models import MotionRender
from .motion.service import get_project, queue_render
from .test_media import movie, picture


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class RemotionStudioTests(TestCase):
    setUp = assistant_test.AssistantTests.setUp
    url = assistant_test.AssistantTests.url
    post = assistant_test.AssistantTests.post
    request = assistant_test.AssistantTests.request
    turn = assistant_test.AssistantTests.turn
    action = assistant_test.AssistantTests.action

    def prepared(self, **kwargs):
        plan = self.turn(model="remotion", **kwargs)
        self.assertEqual(self.action(plan).status_code, 200)
        plan.refresh_from_db()
        return plan, get_project(self.company, plan.prepared["project_id"])

    def output(self, plan, project):
        render = queue_render(self.company, self.user, project.pk, mode="preview", expected_revision=project.current_revision, key=str(uuid.uuid4()))
        render.generation.status = "completed"
        render.generation.save(update_fields=["status"])
        render.output_asset = store_asset(self.company, movie(), job=render.generation)
        render.save(update_fields=["output_asset"])
        plan.prepared["render_id"] = str(render.pk)
        plan.save(update_fields=["prepared"])
        return render

    def edit(self, plan, **extra):
        plan.refresh_from_db()
        scene = plan.prepared["compiled"]["motion_spec"]["scenes"][0]
        return self.action(plan, "edit_motion", edit_key=str(uuid.uuid4()), motion_revision=plan.prepared["motion_revision"],
                           motion_edits=[{"scene_id": scene["id"], "headline": "Mer golf!"}], **extra)

    def test_explicit_remotion_routes_to_motion_even_when_ai_suggests_video(self):
        self.proposal.workflow = "video"
        plan, _ = self.prepared()
        self.assertEqual(plan.spec["workflow"], "motion")
        self.assertEqual(plan.spec["options"]["model"], "")
        self.assertFalse(MotionRender.objects.exists())

    def test_edit_is_immutable_idempotent_and_preserves_logo_and_media(self):
        logo = store_asset(self.company, picture(), alt_text="Logo")
        plan, project = self.prepared(attachments=[{"asset_id": str(logo.pk), "role": "logo"}])
        old = project.revisions.get(number=1)
        scene = old.spec["scenes"][0]
        data = {"edit_key": str(uuid.uuid4()), "motion_revision": 1, "motion_edits": [{"scene_id": scene["id"], "headline": "Ny rubrik"}]}
        self.assertEqual(self.action(plan, "edit_motion", **data).status_code, 200)
        self.assertEqual(self.action(plan, "edit_motion", **data).status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.current_revision, 2)
        self.assertEqual(project.revisions.count(), 2)
        self.assertEqual(project.revisions.get(number=2).brand, old.brand)
        self.assertEqual(project.revisions.get(number=2).spec["scenes"][1:], old.spec["scenes"][1:])
        self.assertEqual(project.revisions.get(number=1).spec, old.spec)

    def test_edit_removes_approval_and_next_preview_uses_new_revision(self):
        plan, project = self.prepared()
        old = self.output(plan, project)
        project.approved_preview = old
        project.save(update_fields=["approved_preview"])
        self.assertEqual(self.edit(plan).status_code, 200)
        project.refresh_from_db()
        self.assertIsNone(project.approved_preview_id)
        with patch("engine.motion.jobs.worker_available", return_value=True):
            self.assertEqual(self.action(plan, "final").status_code, 422)
            response = self.action(plan, "preview")
        self.assertEqual(response.status_code, 200, response.content)
        plan.refresh_from_db()
        new = MotionRender.objects.get(pk=plan.prepared["render_id"])
        self.assertEqual(new.revision.number, 2)
        self.assertNotEqual(new.pk, old.pk)

    def test_edit_rejects_unknown_scene_bad_timing_and_stale_revision(self):
        plan, project = self.prepared()
        scene = project.revisions.get(number=1).spec["scenes"][0]
        for revision, edits in [(2, [{"scene_id": scene["id"], "headline": "Test"}]),
                                (1, [{"scene_id": "unknown", "headline": "Test"}]),
                                (1, [{"scene_id": scene["id"], "duration_seconds": "0.01"}])]:
            self.assertEqual(self.action(plan, "edit_motion", edit_key=str(uuid.uuid4()), motion_revision=revision, motion_edits=edits).status_code, 422)
        self.assertEqual(project.revisions.count(), 1)

    def test_timestamped_comment_uses_selected_immutable_video_version(self):
        plan, project = self.prepared()
        original = self.output(plan, project)
        self.assertEqual(self.edit(plan).status_code, 200)
        old_scene = original.revision.spec["scenes"][0]
        self.proposal.motion_edits = [MotionSceneEdit(scene_id=old_scene["id"], body="En kommenterad ändring")]
        comment = self.turn(model="remotion", motion_source_render=str(original.pk), message="Ändra beskrivningen vid 00:01.00")
        self.assertEqual(comment.spec["review"]["scene_changes"], [{"scene": 1, "field": "Beskrivning", "before": old_scene["props"].get("body", ""), "after": "En kommenterad ändring"}])
        self.assertEqual(self.action(comment).status_code, 200)
        comment.refresh_from_db()
        revised = comment.prepared["compiled"]["motion_spec"]
        self.assertEqual(revised["scenes"][0]["props"]["headline"], old_scene["props"]["headline"])
        self.assertEqual(revised["scenes"][0]["props"]["body"], "En kommenterad ändring")
        self.assertEqual(revised["scenes"][1:], original.revision.spec["scenes"][1:])
        self.assertTrue(self.planner.call_args.kwargs["payload"]["previous_motion_scenes"])

    def test_comment_without_supported_scene_changes_is_blocked(self):
        plan, project = self.prepared()
        original = self.output(plan, project)
        comment = self.turn(model="remotion", motion_source_render=str(original.pk), message="Ändra animationen")
        self.assertIn("Inga scenändringar", comment.spec["blocked"])
        self.assertEqual(self.action(comment).status_code, 422)

    def test_comment_cannot_reference_another_conversation_or_inject_renderer_code(self):
        plan, project = self.prepared()
        render = self.output(plan, project)
        from .models import AssistantConversation
        self.conversation = AssistantConversation.objects.create(company=self.company, author=self.user)
        response = self.post("assistant_send", self.request(model="remotion", motion_source_render=str(render.pk)))
        self.assertEqual(response.json()["turns"][-1]["status"], "failed")
        response = self.action(plan, "edit_motion", edit_key=str(uuid.uuid4()), motion_revision=1,
                               motion_edits=[{"scene_id": "beat-01", "code": "alert(1)"}])
        self.assertEqual(response.status_code, 422)

    def test_failed_preview_can_be_retried_without_reusing_failed_ledger_entry(self):
        plan, _ = self.prepared()
        with patch("engine.motion.jobs.worker_available", return_value=True):
            self.assertEqual(self.action(plan, "preview", render_key=str(uuid.uuid4())).status_code, 200)
            plan.refresh_from_db()
            failed = MotionRender.objects.get(pk=plan.prepared["render_id"])
            failed.generation.status = "failed"
            failed.generation.save(update_fields=["status"])
            self.assertEqual(self.action(plan, "preview", render_key=str(uuid.uuid4())).status_code, 200)
        plan.refresh_from_db()
        self.assertNotEqual(plan.prepared["render_id"], str(failed.pk))
