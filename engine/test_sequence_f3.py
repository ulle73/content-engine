import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .media import store_asset
from .models import Company, MediaGeneration, SequenceClipVersion
from .sequence import (
    SequenceError,
    add_anchor,
    available_clip_model_overrides,
    create_clip,
    create_sequence_project,
    prepare_anchor_chain_version,
    set_clip_model_override,
    sync_sequence_generation,
)


def picture(rgb=(24, 92, 58)):
    out = io.BytesIO()
    Image.new("RGB", (96, 64), rgb).save(out, "PNG")
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class SequenceClipControlsF3Tests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media_root = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.media_root.enable()
        self.addCleanup(self.media_root.disable)

        self.user = get_user_model().objects.create_user(
            username="sequence-f3@example.test",
            password="test-only-password",
        )
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golfkuponger profile",
            voice="Premium",
            current="Aktuellt",
            source="Test",
        )
        self.project = create_sequence_project(
            self.company,
            author=self.user,
            title="F3 clip project",
            brief="A premium continuous golf sequence",
            format="scroll_story",
            platform="web",
        )
        self.k0 = add_anchor(self.project, self.asset((10, 40, 25)), position=0, label="K0", locked=True)
        self.k1 = add_anchor(self.project, self.asset((40, 100, 60)), position=1, label="K1", locked=True)
        self.clip = create_clip(
            self.project,
            self.k0,
            self.k1,
            position=0,
            recipe_id="scroll_transition_bridge",
            label="Hero move",
            duration_seconds_target=5,
        )
        self.client.force_login(self.user)

    def asset(self, rgb=(24, 92, 58)):
        return store_asset(self.company, picture(rgb))

    def fake_preview(self, job):
        usage = dict(job.usage or {})
        usage.update({
            "estimate": {"usd": "0.42", "credits": 4},
            "reviewed_at": timezone.now().isoformat(),
        })
        MediaGeneration.objects.filter(pk=job.pk).update(usage=usage)
        job.refresh_from_db()
        return job

    def prepare(self, *, brief="Slow premium continuous camera move", model_override=""):
        if model_override:
            set_clip_model_override(self.clip, model_override, brief=brief)
            self.clip.refresh_from_db()
        return prepare_anchor_chain_version(
            self.clip,
            brief=brief,
            token=uuid.uuid4(),
        )

    def test_override_options_require_both_anchors_and_exact_duration(self):
        ids = {model.model_id for model in available_clip_model_overrides(self.clip)}
        self.assertIn("bytedance/seedance-2.5", ids)
        self.assertIn("bytedance/seedance-2.0", ids)
        self.assertNotIn("kling-video/v2.5-turbo/pro", ids)

        self.clip.duration_seconds_target = 20
        self.clip.save(update_fields=["duration_seconds_target", "updated_at"])
        ids = {model.model_id for model in available_clip_model_overrides(self.clip)}
        self.assertEqual(ids, {"bytedance/seedance-2.5"})

    def test_verified_manual_override_persists_on_exact_clip_candidate(self):
        version = self.prepare(model_override="bytedance/seedance-2.0")
        selection = version.generation.parameters["creative"]["selection"]
        self.assertEqual(self.clip.__class__.objects.get(pk=self.clip.pk).model_override, "bytedance/seedance-2.0")
        self.assertEqual(version.generation.parameters["model"], "bytedance/seedance-2.0")
        self.assertEqual(
            version.generation.parameters["provider_model"],
            "bytedance/seedance-2.0/image-to-video",
        )
        self.assertTrue(selection["manual_override"])
        self.assertIn("manual_override", selection["reason_codes"])

    def test_incompatible_manual_override_fails_before_candidate_or_provider(self):
        with patch("engine.media.providers.estimate_video") as estimate, patch("engine.media.providers.start_video") as start:
            with self.assertRaises(SequenceError):
                set_clip_model_override(
                    self.clip,
                    "kling-video/v2.5-turbo/pro",
                    brief="5 second bridge",
                )
        estimate.assert_not_called()
        start.assert_not_called()
        self.clip.refresh_from_db()
        self.assertEqual(self.clip.model_override, "")
        self.assertEqual(self.clip.versions.count(), 0)

    def test_sequence_prepare_view_creates_reviewable_candidate_without_paid_submit(self):
        token = uuid.uuid4()
        with patch("engine.sequence.preview_job", side_effect=self.fake_preview) as preview, patch(
            "engine.media.providers.start_video"
        ) as start:
            response = self.client.post(
                reverse(
                    "engine:sequence_clip_prepare",
                    kwargs={
                        "workspace_id": self.company.pk,
                        "project_id": self.project.pk,
                        "clip_id": self.clip.pk,
                    },
                ),
                {
                    "token": str(token),
                    "brief": "Slow premium continuous camera move",
                    "priority": "balanced",
                    "model_override": "",
                },
            )
        start.assert_not_called()
        preview.assert_called_once()
        self.assertEqual(response.status_code, 302)
        version = self.clip.versions.select_related("generation").get()
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.generation_id, token)
        self.assertEqual(version.generation.status, "queued")
        self.assertFalse(version.generation.provider_id)
        self.assertEqual(version.cost_snapshot["estimate_usd"], "0.42")
        self.assertIn(
            reverse(
                "engine:media_job",
                kwargs={
                    "workspace_id": self.company.pk,
                    "run_id": version.generation.run_id,
                    "job_id": version.generation_id,
                },
            ),
            response["Location"],
        )

    def test_regenerate_creates_new_candidate_without_replacing_selected_version(self):
        first = self.prepare()
        MediaGeneration.objects.filter(pk=first.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=first.pk).update(status="ready")
        first.refresh_from_db()
        first.generation.refresh_from_db()

        from .sequence import select_clip_version
        select_clip_version(self.clip, first)

        second = prepare_anchor_chain_version(
            self.clip,
            brief="Try a slower version",
            token=uuid.uuid4(),
        )
        self.clip.refresh_from_db()
        self.assertEqual(second.version_number, 2)
        self.assertEqual(self.clip.selected_version_id, first.pk)
        self.assertEqual(self.clip.versions.count(), 2)

    def test_completed_candidate_can_be_selected_from_workspace(self):
        version = self.prepare()
        MediaGeneration.objects.filter(pk=version.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=version.pk).update(status="ready")
        response = self.client.post(
            reverse(
                "engine:sequence_clip_select",
                kwargs={
                    "workspace_id": self.company.pk,
                    "project_id": self.project.pk,
                    "clip_id": self.clip.pk,
                    "version_id": version.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 302)
        self.clip.refresh_from_db()
        version.refresh_from_db()
        self.assertEqual(self.clip.selected_version_id, version.pk)
        self.assertEqual(self.clip.status, "selected")
        self.assertEqual(version.status, "selected")

    def test_queued_candidate_cancel_reuses_safe_media_cancel(self):
        version = self.prepare()
        with patch("engine.media.providers.cancel_video") as provider_cancel:
            response = self.client.post(
                reverse(
                    "engine:sequence_clip_cancel",
                    kwargs={
                        "workspace_id": self.company.pk,
                        "project_id": self.project.pk,
                        "clip_id": self.clip.pk,
                        "version_id": version.pk,
                    },
                )
            )
        provider_cancel.assert_not_called()
        self.assertEqual(response.status_code, 302)
        version.generation.refresh_from_db()
        version.refresh_from_db()
        self.assertEqual(version.generation.status, "canceled")
        self.assertEqual(version.status, "failed")

    def test_stale_candidate_never_becomes_ready_when_generation_later_completes(self):
        version = self.prepare()
        SequenceClipVersion.objects.filter(pk=version.pk).update(status="stale")
        MediaGeneration.objects.filter(pk=version.generation_id).update(status="completed")
        version.generation.refresh_from_db()

        synced = sync_sequence_generation(version.generation)
        self.assertEqual(synced.status, "stale")
        self.clip.refresh_from_db()
        self.assertIsNone(self.clip.selected_version_id)
        self.assertEqual(self.clip.status, "review")

    def test_workspace_compares_versions_and_exposes_diagnostics(self):
        first = self.prepare()
        second = prepare_anchor_chain_version(
            self.clip,
            brief="Second candidate",
            token=uuid.uuid4(),
        )
        response = self.client.get(
            reverse(
                "engine:sequence_workspace",
                kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F3 · Clip controls")
        self.assertContains(response, "Generera, jämför och välj clip")
        self.assertContains(response, "V1")
        self.assertContains(response, "V2")
        self.assertContains(response, "Diagnostik")
        self.assertContains(response, "Auto · rekommenderas")
        self.assertContains(response, str(first.generation_id))
        self.assertContains(response, str(second.generation_id))

    def test_media_job_page_identifies_sequence_clip_candidate(self):
        version = self.prepare()
        response = self.client.get(
            reverse(
                "engine:media_job",
                kwargs={
                    "workspace_id": self.company.pk,
                    "run_id": version.generation.run_id,
                    "job_id": version.generation_id,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F3 · Clip-kandidat V1")
        self.assertContains(response, "Hero move")
        self.assertContains(response, "← Sequence workspace")

    def test_clip_actions_are_company_scoped(self):
        outsider = get_user_model().objects.create_user(username="sequence-f3-other")
        other_company = Company.objects.create(owner=outsider, name="Other")
        other_project = create_sequence_project(other_company, author=outsider, title="Foreign")
        a0 = store_asset(other_company, picture((1, 2, 3)))
        a1 = store_asset(other_company, picture((4, 5, 6)))
        foreign_k0 = add_anchor(other_project, a0, position=0)
        foreign_k1 = add_anchor(other_project, a1, position=1)
        foreign_clip = create_clip(
            other_project,
            foreign_k0,
            foreign_k1,
            position=0,
            recipe_id="scroll_transition_bridge",
        )
        response = self.client.post(
            reverse(
                "engine:sequence_clip_prepare",
                kwargs={
                    "workspace_id": self.company.pk,
                    "project_id": other_project.pk,
                    "clip_id": foreign_clip.pk,
                },
            ),
            {
                "token": str(uuid.uuid4()),
                "brief": "Should never run",
                "priority": "balanced",
                "model_override": "",
            },
        )
        self.assertEqual(response.status_code, 404)
