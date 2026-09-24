import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .media import MediaError, remove_asset, store_asset
from .models import (
    Company,
    ContentRun,
    MediaAsset,
    MediaGeneration,
    SequenceAnchorGenerationTarget,
    SequenceAnchorRevision,
    SequenceBridgeVersion,
    SequenceClipVersion,
)
from .sequence import (
    SequenceError,
    add_anchor,
    anchor_change_impact,
    apply_generated_anchor_asset,
    change_anchor_asset,
    create_clip,
    create_sequence_project,
    create_transition_bridge,
    prepare_anchor_chain_version,
    prepare_anchor_image_generation,
    prepare_transition_bridge_version,
    restore_anchor_revision,
    select_clip_version,
    select_transition_bridge_version,
    set_anchor_locked,
)


def picture(rgb=(24, 92, 58)):
    out = io.BytesIO()
    Image.new("RGB", (96, 64), rgb).save(out, "PNG")
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class SequenceAnchorControlsF2Tests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media_root = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.media_root.enable()
        self.addCleanup(self.media_root.disable)

        self.user = get_user_model().objects.create_user(
            username="sequence-f2@example.test",
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
            title="F2 anchor project",
            brief="Premium sequence",
            format="scroll_story",
            platform="web",
        )
        self.client.force_login(self.user)

    def asset(self, rgb=(24, 92, 58), *, job=None):
        return store_asset(self.company, picture(rgb), job=job)

    def build_chain(self):
        k0 = add_anchor(self.project, self.asset((10, 40, 25)), position=0, label="K0", locked=True, created_by=self.user)
        k1 = add_anchor(self.project, self.asset((20, 70, 40)), position=1, label="K1", locked=True, created_by=self.user)
        k2 = add_anchor(self.project, self.asset((40, 100, 60)), position=2, label="K2", locked=True, created_by=self.user)
        clip1 = create_clip(self.project, k0, k1, position=0, recipe_id="scroll_transition_bridge")
        clip2 = create_clip(self.project, k1, k2, position=1, recipe_id="scroll_transition_bridge")
        return k0, k1, k2, clip1, clip2

    def complete_clip_version(self, clip):
        version = prepare_anchor_chain_version(clip, token=uuid.uuid4())
        MediaGeneration.objects.filter(pk=version.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=version.pk).update(status="ready")
        version.refresh_from_db()
        version.generation.refresh_from_db()
        select_clip_version(clip, version)
        return version

    def test_new_anchor_gets_revision_one_and_persists_asset(self):
        generated_run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={},
            ideas=[{"title": "image", "photo_brief": "image"}],
            selected=0,
            draft={"instagram": "draft"},
            model="test",
        )
        job = MediaGeneration.objects.create(
            run=generated_run,
            kind="image",
            provider="openai",
            brief="image",
            prompt="image",
            status="completed",
        )
        asset = self.asset(job=job)
        self.assertIsNotNone(asset.expires_at)

        anchor = add_anchor(
            self.project,
            asset,
            position=0,
            label="Generated baseline",
            source_type="generated",
            source_metadata={"generation_id": str(job.pk)},
            created_by=self.user,
        )

        asset.refresh_from_db()
        revision = anchor.revisions.get()
        self.assertEqual(revision.revision_number, 1)
        self.assertEqual(revision.asset_id, asset.pk)
        self.assertEqual(revision.source_type, "generated")
        self.assertEqual(revision.created_by_id, self.user.pk)
        self.assertIsNone(asset.expires_at)
        self.assertIsNotNone(asset.used_at)

    def test_locked_anchor_must_be_explicitly_unlocked_before_replace(self):
        anchor = add_anchor(self.project, self.asset(), position=0, locked=True)
        replacement = self.asset((80, 140, 80))
        with self.assertRaisesRegex(SequenceError, "låst"):
            change_anchor_asset(anchor, replacement, created_by=self.user)
        set_anchor_locked(anchor, False)
        changed = change_anchor_asset(anchor, replacement, created_by=self.user)
        self.assertEqual(changed.asset_id, replacement.pk)
        self.assertEqual(changed.revisions.count(), 2)

    def test_anchor_replace_requires_confirmation_and_marks_clip_versions_stale(self):
        _, k1, _, clip1, clip2 = self.build_chain()
        v1 = self.complete_clip_version(clip1)
        v2 = self.complete_clip_version(clip2)
        set_anchor_locked(k1, False)
        replacement = self.asset((90, 160, 95))

        impact = anchor_change_impact(k1)
        self.assertEqual(impact["clip_versions"], 2)
        self.assertEqual(impact["selected_segments"], 2)

        with self.assertRaisesRegex(SequenceError, "Bekräfta ändringen"):
            change_anchor_asset(k1, replacement, created_by=self.user)
        k1.refresh_from_db()
        self.assertNotEqual(k1.asset_id, replacement.pk)

        changed = change_anchor_asset(
            k1,
            replacement,
            source_type="existing",
            created_by=self.user,
            confirm_stale=True,
        )
        v1.refresh_from_db()
        v2.refresh_from_db()
        clip1.refresh_from_db()
        clip2.refresh_from_db()
        self.assertEqual(changed.asset_id, replacement.pk)
        self.assertEqual(v1.status, "stale")
        self.assertEqual(v2.status, "stale")
        self.assertIsNone(clip1.selected_version_id)
        self.assertIsNone(clip2.selected_version_id)
        self.assertEqual(clip1.status, "review")
        self.assertEqual(clip2.status, "review")
        self.assertEqual(changed.revisions.count(), 2)
        self.assertEqual(changed.revisions.order_by("-revision_number").first().reason, "replaced")

    def test_bridge_candidate_is_staled_together_with_clip_candidate(self):
        k0 = add_anchor(self.project, self.asset((10, 40, 25)), position=0)
        k1 = add_anchor(self.project, self.asset((20, 70, 40)), position=1)
        k2 = add_anchor(self.project, self.asset((40, 100, 60)), position=2)
        k3 = add_anchor(self.project, self.asset((60, 130, 75)), position=3)
        left = create_clip(self.project, k0, k1, position=0, recipe_id="scroll_transition_bridge")
        right = create_clip(self.project, k2, k3, position=2, recipe_id="scroll_transition_bridge")
        bridge = create_transition_bridge(self.project, left, right)
        version = prepare_transition_bridge_version(bridge, token=uuid.uuid4())
        MediaGeneration.objects.filter(pk=version.generation_id).update(status="completed")
        SequenceBridgeVersion.objects.filter(pk=version.pk).update(status="ready")
        version.refresh_from_db()
        version.generation.refresh_from_db()
        select_transition_bridge_version(bridge, version)

        replacement = self.asset((100, 170, 110))
        change_anchor_asset(k1, replacement, created_by=self.user, confirm_stale=True)

        version.refresh_from_db()
        bridge.refresh_from_db()
        self.assertEqual(version.status, "stale")
        self.assertIsNone(bridge.selected_version_id)
        self.assertEqual(bridge.status, "review")

    def test_restore_revision_creates_new_revision_instead_of_rewinding_history(self):
        anchor = add_anchor(self.project, self.asset((10, 40, 25)), position=0, created_by=self.user)
        original = anchor.revisions.get()
        replacement = self.asset((90, 160, 95))
        change_anchor_asset(anchor, replacement, created_by=self.user)
        anchor.refresh_from_db()

        restored = restore_anchor_revision(anchor, original, created_by=self.user)
        revisions = list(restored.revisions.order_by("revision_number"))
        self.assertEqual([item.revision_number for item in revisions], [1, 2, 3])
        self.assertEqual(restored.asset_id, original.asset_id)
        self.assertEqual(revisions[-1].reason, "restored")
        self.assertEqual(revisions[-1].source_metadata["restored_from_revision_number"], 1)

    def test_historical_revision_asset_is_protected_even_if_used_flag_is_cleared(self):
        anchor = add_anchor(self.project, self.asset((10, 40, 25)), position=0)
        old_asset = anchor.asset
        change_anchor_asset(anchor, self.asset((80, 140, 80)))
        MediaAsset.objects.filter(pk=old_asset.pk).update(used_at=None)
        old_asset.refresh_from_db()
        with self.assertRaises(MediaError):
            remove_asset(old_asset)
        self.assertTrue(MediaAsset.objects.filter(pk=old_asset.pk).exists())

    def test_stale_clip_or_bridge_candidate_cannot_be_selected_again(self):
        _, k1, _, clip1, _ = self.build_chain()
        version = self.complete_clip_version(clip1)
        set_anchor_locked(k1, False)
        change_anchor_asset(k1, self.asset((90, 160, 95)), confirm_stale=True)
        version.refresh_from_db()
        self.assertEqual(version.status, "stale")
        with self.assertRaisesRegex(SequenceError, "färdig"):
            select_clip_version(clip1, version)

    def test_prepare_ai_anchor_is_review_only_and_provider_free(self):
        anchor = add_anchor(self.project, self.asset(), position=0)
        with patch("engine.media.providers.generate_images") as generate, patch("engine.media.providers.start_video") as video:
            target = prepare_anchor_image_generation(
                self.project,
                brief="Premium close-up of a Swedish golf green at sunrise",
                target_anchor=anchor,
                shape="landscape",
                count=2,
                priority="balanced",
                token=uuid.uuid4(),
                created_by=self.user,
            )
        generate.assert_not_called()
        video.assert_not_called()
        target.generation.refresh_from_db()
        self.assertEqual(target.mode, "replace")
        self.assertEqual(target.target_anchor_id, anchor.pk)
        self.assertEqual(target.created_by_id, self.user.pk)
        self.assertEqual(target.generation.status, "queued")
        self.assertTrue(target.generation.usage.get("reviewed_at"))
        self.assertFalse(target.generation.provider_id)
        self.assertEqual(target.generation.run.model, "sequence-anchor-generation")

    def test_completed_ai_asset_can_replace_anchor_only_after_unlock(self):
        anchor = add_anchor(self.project, self.asset(), position=0, locked=True)
        target = prepare_anchor_image_generation(
            self.project,
            brief="A premium golf-course hero image",
            target_anchor=anchor,
            token=uuid.uuid4(),
            created_by=self.user,
        )
        MediaGeneration.objects.filter(pk=target.generation_id).update(status="completed")
        target.generation.refresh_from_db()
        generated = self.asset((220, 230, 210), job=target.generation)

        with self.assertRaisesRegex(SequenceError, "låst"):
            apply_generated_anchor_asset(target, generated, created_by=self.user)
        set_anchor_locked(anchor, False)
        applied = apply_generated_anchor_asset(target, generated, created_by=self.user)
        target.refresh_from_db()
        self.assertEqual(applied.asset_id, generated.pk)
        self.assertEqual(applied.source_type, "generated")
        self.assertEqual(applied.source_metadata["generation_id"], str(target.generation_id))
        self.assertEqual(target.applied_anchor_id, anchor.pk)
        self.assertEqual(applied.revisions.order_by("-revision_number").first().reason, "ai_generated")

    def test_completed_ai_asset_can_create_new_anchor_at_next_position(self):
        add_anchor(self.project, self.asset(), position=0, label="K0")
        target = prepare_anchor_image_generation(
            self.project,
            brief="A clean closing golf image",
            target_label="Closing image",
            token=uuid.uuid4(),
            created_by=self.user,
        )
        MediaGeneration.objects.filter(pk=target.generation_id).update(status="completed")
        target.generation.refresh_from_db()
        generated = self.asset((210, 220, 200), job=target.generation)

        applied = apply_generated_anchor_asset(target, generated, created_by=self.user)
        self.assertEqual(applied.position, 1)
        self.assertEqual(applied.label, "Closing image")
        self.assertEqual(applied.source_type, "generated")
        self.assertEqual(applied.revisions.count(), 1)

    def test_ai_target_model_rejects_cross_company_generation(self):
        outsider = get_user_model().objects.create_user(username="sequence-f2-other")
        other = Company.objects.create(owner=outsider, name="Other")
        run = ContentRun.objects.create(
            workspace=other,
            author=outsider,
            context={},
            ideas=[{"title": "x"}],
            selected=0,
            draft={"instagram": "draft"},
            model="test",
        )
        generation = MediaGeneration.objects.create(
            run=run,
            kind="image",
            provider="openai",
            brief="x",
            prompt="x",
        )
        with self.assertRaises(ValidationError):
            SequenceAnchorGenerationTarget(
                project=self.project,
                generation=generation,
                mode="create",
            ).save()

    def test_upload_replace_without_stale_confirmation_does_not_store_orphan_file(self):
        _, k1, _, clip1, _ = self.build_chain()
        prepare_anchor_chain_version(clip1, token=uuid.uuid4())
        set_anchor_locked(k1, False)
        before = self.company.media_assets.count()

        upload = io.BytesIO(picture((200, 210, 190)))
        upload.name = "replacement.png"
        response = self.client.post(
            reverse(
                "engine:sequence_anchor_replace_upload",
                kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk, "anchor_id": k1.pk},
            ),
            {"file": upload},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.company.media_assets.count(), before)
        self.assertContains(response, "Bekräfta ändringen")

    def test_workspace_exposes_f2_controls_provenance_and_revision_history(self):
        anchor = add_anchor(self.project, self.asset(), position=0, label="Hero", created_by=self.user)
        response = self.client.get(
            reverse(
                "engine:sequence_workspace",
                kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "F2 · Anchor controls")
        self.assertContains(response, "Lägg till anchor")
        self.assertContains(response, "Hantera K0")
        self.assertContains(response, "Versionshistorik · 1")
        self.assertContains(response, "Skapa ersättare med AI")
        self.assertContains(response, "Versioned")
        self.assertContains(response, str(anchor.asset.provider))

    def test_ai_job_page_links_back_to_sequence_and_can_apply_completed_asset(self):
        anchor = add_anchor(self.project, self.asset(), position=0, label="Hero")
        target = prepare_anchor_image_generation(
            self.project,
            brief="Premium hero",
            target_anchor=anchor,
            token=uuid.uuid4(),
            created_by=self.user,
        )
        MediaGeneration.objects.filter(pk=target.generation_id).update(status="completed")
        target.generation.refresh_from_db()
        generated = self.asset((220, 225, 215), job=target.generation)
        response = self.client.get(
            reverse(
                "engine:media_job",
                kwargs={
                    "workspace_id": self.company.pk,
                    "run_id": target.generation.run_id,
                    "job_id": target.generation_id,
                },
            )
        )
        self.assertContains(response, "F2 · AI-anchor")
        self.assertContains(response, "Ersätt K0")
        self.assertContains(response, "← Sequence workspace")
        self.assertContains(response, "Använd som K0")
        self.assertContains(
            response,
            reverse(
                "engine:sequence_anchor_apply_generated",
                kwargs={
                    "workspace_id": self.company.pk,
                    "project_id": self.project.pk,
                    "target_id": target.pk,
                    "asset_id": generated.pk,
                },
            ),
        )
