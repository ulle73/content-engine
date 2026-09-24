import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import av
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from .media import remove_asset, store_asset
from .media_storage import MediaError, open_asset
from .models import (
    Company,
    ContentRun,
    MediaGeneration,
    SequenceAnchor,
    SequenceClip,
    SequenceClipVersion,
)
from .sequence import (
    SequenceError,
    add_anchor,
    attach_generation_to_clip,
    create_clip,
    create_sequence_project,
    prepare_anchor_chain_version,
    preview_anchor_chain_version,
    promote_output_chain_final_frame,
    regenerate_anchor_chain_clip,
    replace_anchor_asset,
    select_clip_version,
    sequence_snapshot,
    set_anchor_locked,
)


def picture(rgb=(24, 92, 58)):
    out = io.BytesIO()
    Image.new("RGB", (64, 96), rgb).save(out, "PNG")
    return out.getvalue()


def sequence_movie(colors=((0, 0, 0), (255, 255, 255))):
    out = io.BytesIO()
    with av.open(out, mode="w", format="mp4") as container:
        stream = container.add_stream("libx264", rate=10)
        stream.width, stream.height, stream.pix_fmt = 64, 96, "yuv420p"
        for rgb in colors:
            image = Image.new("RGB", (64, 96), rgb)
            for _ in range(3):
                for packet in stream.encode(av.VideoFrame.from_image(image)):
                    container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class SequenceEngineE1Tests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media_root = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.media_root.enable()
        self.addCleanup(self.media_root.disable)

        self.user = get_user_model().objects.create_user(username="sequence-owner")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger", profile="Golf", current="Current")
        self.run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={"profile": "Golf", "current": "Current"},
            ideas=[{"title": "Sequence"}],
            selected=0,
            draft={"instagram": "draft"},
            model="test",
        )
        self.project = create_sequence_project(
            self.company,
            author=self.user,
            title="Premium scroll story",
            brief="Three connected scenes",
            format="scroll_story",
            platform="web",
        )

    def asset(self, rgb=(24, 92, 58)):
        return store_asset(self.company, picture(rgb))

    def generation(self, *, status="completed", company=None, prompt="bridge"):
        company = company or self.company
        run = self.run
        if company.pk != self.company.pk:
            run = ContentRun.objects.create(
                workspace=company,
                author=company.owner,
                context={},
                ideas=[{"title": "Other"}],
                selected=0,
                draft={"instagram": "draft"},
                model="test",
            )
        return MediaGeneration.objects.create(
            run=run,
            kind="video",
            provider="higgsfield",
            brief="bridge",
            prompt=prompt,
            status=status,
            parameters={
                "model": "bytedance/seedance-2.5",
                "provider_model": "bytedance/seedance-2.5/image-to-video",
                "creative": {
                    "recipe": {
                        "recipe_id": "scroll_transition_bridge",
                        "version": "1.0.0",
                    }
                },
            },
            usage={"estimate": {"usd": "1.6180"}},
        )

    def build_three_anchor_chain(self):
        k0 = add_anchor(self.project, self.asset((10, 50, 30)), position=0, label="K0", locked=True)
        k1 = add_anchor(self.project, self.asset((20, 80, 45)), position=1, label="K1", locked=True)
        k2 = add_anchor(self.project, self.asset((30, 110, 60)), position=2, label="K2", locked=True)
        clip1 = create_clip(
            self.project, k0, k1, position=0, recipe_id="scroll_transition_bridge", label="Clip 1"
        )
        clip2 = create_clip(
            self.project, k1, k2, position=1, recipe_id="scroll_transition_bridge", label="Clip 2"
        )
        return k0, k1, k2, clip1, clip2

    def test_can_persist_k0_clip1_k1_clip2_k2_with_shared_canonical_k1(self):
        k0, k1, k2, clip1, clip2 = self.build_three_anchor_chain()
        self.assertEqual(clip1.end_anchor_id, k1.pk)
        self.assertEqual(clip2.start_anchor_id, k1.pk)
        snapshot = sequence_snapshot(self.project)
        self.assertEqual([item["position"] for item in snapshot["anchors"]], [0, 1, 2])
        self.assertEqual([item["position"] for item in snapshot["clips"]], [0, 1])
        self.assertEqual(snapshot["clips"][0]["end_anchor_id"], snapshot["clips"][1]["start_anchor_id"])

    def test_anchor_position_is_unique_in_database(self):
        first = self.asset()
        second = self.asset((40, 90, 50))
        add_anchor(self.project, first, position=0)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SequenceAnchor.objects.bulk_create([
                    SequenceAnchor(project=self.project, asset=second, position=0)
                ])

    def test_clip_position_is_unique_in_database(self):
        k0 = add_anchor(self.project, self.asset(), position=0)
        k1 = add_anchor(self.project, self.asset((40, 90, 50)), position=1)
        k2 = add_anchor(self.project, self.asset((60, 120, 70)), position=2)
        create_clip(self.project, k0, k1, position=0, recipe_id="scroll_transition_bridge")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SequenceClip.objects.bulk_create([
                    SequenceClip(
                        project=self.project,
                        position=0,
                        start_anchor=k1,
                        end_anchor=k2,
                        recipe_id="scroll_transition_bridge",
                        recipe_version="1.0.0",
                    )
                ])

    def test_anchor_rejects_cross_company_and_non_image_assets(self):
        other_user = get_user_model().objects.create_user(username="sequence-other")
        other_company = Company.objects.create(owner=other_user, name="Other")
        foreign = store_asset(other_company, picture())
        with self.assertRaises(SequenceError):
            add_anchor(self.project, foreign, position=0)
        with self.assertRaises(ValidationError):
            SequenceAnchor(project=self.project, asset=foreign, position=0).save()

    def test_clip_requires_same_project_and_forward_anchor_order(self):
        k0 = add_anchor(self.project, self.asset(), position=0)
        k1 = add_anchor(self.project, self.asset((40, 90, 50)), position=1)
        other = create_sequence_project(self.company, author=self.user, title="Other")
        other_anchor = add_anchor(other, self.asset((60, 120, 70)), position=0)
        with self.assertRaises(SequenceError):
            create_clip(self.project, k0, other_anchor, position=0, recipe_id="scroll_transition_bridge")
        with self.assertRaises(SequenceError):
            create_clip(self.project, k1, k0, position=0, recipe_id="scroll_transition_bridge")
        with self.assertRaises(ValidationError):
            SequenceClip(
                project=self.project,
                position=0,
                start_anchor=k1,
                end_anchor=k0,
                recipe_id="scroll_transition_bridge",
                recipe_version="1.0.0",
            ).save()

    def test_clip_only_accepts_trusted_video_recipe(self):
        k0 = add_anchor(self.project, self.asset(), position=0)
        k1 = add_anchor(self.project, self.asset((40, 90, 50)), position=1)
        with self.assertRaisesRegex(SequenceError, "trusted video recipe"):
            create_clip(self.project, k0, k1, position=0, recipe_id="not_a_recipe")
        with self.assertRaisesRegex(SequenceError, "trusted video recipe"):
            create_clip(self.project, k0, k1, position=0, recipe_id="generic_image")

    def test_attach_generation_versions_increment_and_snapshot_provenance(self):
        _, _, _, clip1, _ = self.build_three_anchor_chain()
        first = attach_generation_to_clip(clip1, self.generation(prompt="first"))
        second = attach_generation_to_clip(clip1, self.generation(prompt="second"))
        self.assertEqual((first.version_number, second.version_number), (1, 2))
        self.assertEqual(first.recipe_id, "scroll_transition_bridge")
        self.assertEqual(first.model_id, "bytedance/seedance-2.5")
        self.assertEqual(first.provider_model, "bytedance/seedance-2.5/image-to-video")
        self.assertEqual(first.prompt_snapshot, "first")
        self.assertEqual(first.cost_snapshot["estimate_usd"], "1.6180")
        self.assertEqual(first.status, "ready")

    def test_generation_can_belong_to_only_one_clip_version(self):
        _, _, _, clip1, clip2 = self.build_three_anchor_chain()
        generation = self.generation()
        attach_generation_to_clip(clip1, generation)
        with self.assertRaises(SequenceError):
            attach_generation_to_clip(clip2, generation)

    def test_cross_company_generation_is_rejected_by_service_and_model(self):
        _, _, _, clip1, _ = self.build_three_anchor_chain()
        other_user = get_user_model().objects.create_user(username="sequence-generation-other")
        other_company = Company.objects.create(owner=other_user, name="Other generation")
        foreign = self.generation(company=other_company)
        with self.assertRaises(SequenceError):
            attach_generation_to_clip(clip1, foreign)
        with self.assertRaises(ValidationError):
            SequenceClipVersion(
                clip=clip1,
                version_number=1,
                generation=foreign,
                recipe_id="scroll_transition_bridge",
                recipe_version="1.0.0",
            ).save()

    def test_selecting_version_is_non_destructive_and_only_one_version_is_selected(self):
        _, _, _, clip1, _ = self.build_three_anchor_chain()
        v1 = attach_generation_to_clip(clip1, self.generation(prompt="v1"))
        v2 = attach_generation_to_clip(clip1, self.generation(prompt="v2"))
        select_clip_version(clip1, v1)
        clip1.refresh_from_db()
        v1.refresh_from_db()
        self.assertEqual(clip1.selected_version_id, v1.pk)
        self.assertEqual(v1.status, "selected")

        select_clip_version(clip1, v2)
        clip1.refresh_from_db()
        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertEqual(clip1.selected_version_id, v2.pk)
        self.assertEqual(v1.status, "ready")
        self.assertEqual(v2.status, "selected")
        self.assertEqual(clip1.versions.count(), 2)

    def test_selected_version_must_belong_to_same_clip(self):
        _, _, _, clip1, clip2 = self.build_three_anchor_chain()
        foreign_version = attach_generation_to_clip(clip2, self.generation())
        clip1.selected_version = foreign_version
        with self.assertRaises(ValidationError):
            clip1.save()

    def test_locked_anchor_cannot_be_replaced_until_explicitly_unlocked(self):
        anchor = add_anchor(self.project, self.asset(), position=0, locked=True)
        replacement = self.asset((80, 140, 80))
        with self.assertRaisesRegex(SequenceError, "låst anchor"):
            replace_anchor_asset(anchor, replacement)
        set_anchor_locked(anchor, False)
        updated = replace_anchor_asset(anchor, replacement)
        self.assertEqual(updated.asset_id, replacement.pk)

    def test_anchor_asset_is_protected_from_media_cleanup(self):
        asset = self.asset()
        add_anchor(self.project, asset, position=0)
        with self.assertRaisesRegex(MediaError, "sequence-anchor"):
            remove_asset(asset)

    def test_project_delete_keeps_existing_media_and_generation_but_removes_sequence_rows(self):
        k0, k1, _, clip1, _ = self.build_three_anchor_chain()
        generation = self.generation()
        version = attach_generation_to_clip(clip1, generation)
        anchor_asset_id = k0.asset_id
        generation_id = generation.pk
        project_id = self.project.pk

        self.project.delete()

        self.assertFalse(type(self.project).objects.filter(pk=project_id).exists())
        self.assertTrue(MediaGeneration.objects.filter(pk=generation_id).exists())
        self.assertTrue(k0.asset.__class__.objects.filter(pk=anchor_asset_id).exists())
        self.assertFalse(SequenceClipVersion.objects.filter(pk=version.pk).exists())

    def test_generation_used_by_clip_version_is_protected(self):
        _, _, _, clip1, _ = self.build_three_anchor_chain()
        generation = self.generation()
        attach_generation_to_clip(clip1, generation)
        with self.assertRaises(ProtectedError):
            generation.delete()


    def test_e2_prepare_uses_exact_canonical_anchors_without_provider_call(self):
        k0, k1, _, clip1, _ = self.build_three_anchor_chain()
        with patch("engine.media.providers.estimate_video") as estimate, patch("engine.media.providers.start_video") as start:
            version = prepare_anchor_chain_version(
                clip1,
                brief="Create a calm premium bridge between these anchors with no audio",
                token=uuid.uuid4(),
            )
        estimate.assert_not_called()
        start.assert_not_called()

        generation = version.generation
        generation.refresh_from_db()
        refs = {row.role: row.asset_id for row in generation.references.all()}
        self.assertEqual(generation.source_asset_id, k0.asset_id)
        self.assertEqual(refs["START_IMAGE"], k0.asset_id)
        self.assertEqual(refs["END_IMAGE"], k1.asset_id)
        self.assertEqual(generation.parameters["sequence"]["mode"], "anchor_chain")
        self.assertEqual(generation.parameters["sequence"]["clip_id"], str(clip1.pk))
        self.assertEqual(generation.parameters["sequence"]["start_anchor_id"], str(k0.pk))
        self.assertEqual(generation.parameters["sequence"]["end_anchor_id"], str(k1.pk))
        self.assertEqual(generation.parameters["sequence"]["version_number"], 1)
        self.assertEqual(generation.run.context["sequence"]["clip_id"], str(clip1.pk))
        self.assertEqual(version.version_number, 1)
        clip1.refresh_from_db()
        self.assertEqual(clip1.status, "review")
        self.assertIsNone(clip1.selected_version_id)

    def test_e2_adjacent_clip_jobs_share_exact_same_k1_asset(self):
        _, k1, _, clip1, clip2 = self.build_three_anchor_chain()
        v1 = prepare_anchor_chain_version(clip1, token=uuid.uuid4())
        v2 = prepare_anchor_chain_version(clip2, token=uuid.uuid4())

        clip1_end = v1.generation.references.get(role="END_IMAGE")
        clip2_start = v2.generation.references.get(role="START_IMAGE")
        self.assertEqual(clip1_end.asset_id, k1.asset_id)
        self.assertEqual(clip2_start.asset_id, k1.asset_id)
        self.assertEqual(clip1.end_anchor_id, clip2.start_anchor_id)
        self.assertEqual(clip1.end_anchor_id, k1.pk)

    def test_e2_regenerating_clip2_does_not_mutate_anchors_clip1_or_selected_v1(self):
        k0, k1, k2, clip1, clip2 = self.build_three_anchor_chain()
        clip1_version = prepare_anchor_chain_version(clip1, token=uuid.uuid4())
        clip2_v1 = prepare_anchor_chain_version(clip2, token=uuid.uuid4())

        MediaGeneration.objects.filter(pk=clip2_v1.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=clip2_v1.pk).update(status="ready")
        clip2_v1.refresh_from_db()
        select_clip_version(clip2, clip2_v1)

        anchor_state = {
            k0.pk: (k0.asset_id, k0.locked),
            k1.pk: (k1.asset_id, k1.locked),
            k2.pk: (k2.asset_id, k2.locked),
        }
        clip1_generation_ids = list(clip1.versions.values_list("generation_id", flat=True))

        clip2_v2 = regenerate_anchor_chain_clip(
            clip2,
            brief="Try a smoother, slower bridge while keeping the same anchors",
            token=uuid.uuid4(),
        )

        for anchor in (k0, k1, k2):
            anchor.refresh_from_db()
            self.assertEqual((anchor.asset_id, anchor.locked), anchor_state[anchor.pk])
        self.assertEqual(list(clip1.versions.values_list("generation_id", flat=True)), clip1_generation_ids)
        self.assertEqual(clip1.versions.count(), 1)
        self.assertEqual(clip2.versions.count(), 2)
        self.assertNotEqual(clip2_v1.generation_id, clip2_v2.generation_id)
        clip2.refresh_from_db()
        self.assertEqual(clip2.selected_version_id, clip2_v1.pk)
        self.assertEqual(clip2.status, "selected")

    def test_e2_prepare_is_idempotent_for_same_token(self):
        _, _, _, clip1, _ = self.build_three_anchor_chain()
        token = uuid.uuid4()
        first = prepare_anchor_chain_version(clip1, token=token)
        second = prepare_anchor_chain_version(clip1, token=token)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.generation_id, token)
        self.assertEqual(clip1.versions.count(), 1)

    def test_e2_idempotency_token_cannot_cross_clips(self):
        _, _, _, clip1, clip2 = self.build_three_anchor_chain()
        token = uuid.uuid4()
        prepare_anchor_chain_version(clip1, token=token)
        with self.assertRaisesRegex(SequenceError, "annat sequence-clip"):
            prepare_anchor_chain_version(clip2, token=token)

    def test_e2_preview_is_nonbillable_and_refreshes_snapshot(self):
        _, _, _, clip1, _ = self.build_three_anchor_chain()
        version = prepare_anchor_chain_version(clip1, token=uuid.uuid4())

        def fake_preview(job):
            self.assertEqual(job.status, "queued")
            self.assertFalse(job.provider_id)
            job.usage = {
                "estimate": {"usd": "0.42", "credits": 4},
                "reviewed_at": "2026-09-24T10:00:00+00:00",
            }
            job.save(update_fields=["usage"])
            return job

        with patch("engine.sequence.preview_job", side_effect=fake_preview) as preview:
            refreshed = preview_anchor_chain_version(version)

        preview.assert_called_once()
        refreshed.generation.refresh_from_db()
        self.assertEqual(refreshed.generation.status, "queued")
        self.assertFalse(refreshed.generation.provider_id)
        self.assertEqual(refreshed.cost_snapshot["estimate_usd"], "0.42")
        self.assertEqual(refreshed.usage_snapshot["estimate"]["credits"], 4)
        self.assertEqual(
            {item["role"] for item in refreshed.reference_snapshot},
            {"START_IMAGE", "END_IMAGE"},
        )

    def test_e2_preview_fails_closed_if_current_anchor_asset_changed(self):
        _, _, k2, _, clip2 = self.build_three_anchor_chain()
        version = prepare_anchor_chain_version(clip2, token=uuid.uuid4())
        set_anchor_locked(k2, False)
        replacement = self.asset((90, 160, 95))
        replace_anchor_asset(k2, replacement)

        with patch("engine.sequence.preview_job") as preview:
            with self.assertRaisesRegex(SequenceError, "anchors har ändrats"):
                preview_anchor_chain_version(version)
        preview.assert_not_called()

    def test_e2_duration_and_aspect_ratio_are_compiled_from_clip_targets(self):
        k0 = add_anchor(self.project, self.asset(), position=0)
        k1 = add_anchor(self.project, self.asset((50, 100, 70)), position=1)
        clip = create_clip(
            self.project,
            k0,
            k1,
            position=0,
            recipe_id="scroll_transition_bridge",
            duration_seconds_target=8,
            aspect_ratio="16:9",
        )
        version = prepare_anchor_chain_version(clip, token=uuid.uuid4())
        creative_brief = version.generation.parameters["creative"]["brief"]
        self.assertEqual(creative_brief["duration_seconds"], 8)
        self.assertEqual(creative_brief["aspect_ratio"], "16:9")

    def test_e2_model_override_fails_closed_until_b4_exists(self):
        k0 = add_anchor(self.project, self.asset(), position=0)
        k1 = add_anchor(self.project, self.asset((50, 100, 70)), position=1)
        clip = create_clip(
            self.project,
            k0,
            k1,
            position=0,
            recipe_id="scroll_transition_bridge",
            model_override="manual-model",
        )
        with self.assertRaisesRegex(SequenceError, "B4"):
            prepare_anchor_chain_version(clip, token=uuid.uuid4())
        self.assertEqual(clip.versions.count(), 0)
        self.assertFalse(ContentRun.objects.filter(model="sequence-anchor-chain").exists())


    def selected_completed_sequence_version_with_video(self, clip):
        version = prepare_anchor_chain_version(clip, token=uuid.uuid4())
        MediaGeneration.objects.filter(pk=version.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=version.pk).update(status="ready")
        version.refresh_from_db()
        version.generation.refresh_from_db()
        video = store_asset(
            self.company,
            sequence_movie(),
            job=version.generation,
            alt_text="Sequence output",
        )
        select_clip_version(clip, version)
        version.refresh_from_db()
        return version, video

    def test_e3_output_chain_requires_explicit_unlock_and_selected_completed_version(self):
        _, k1, _, clip1, _ = self.build_three_anchor_chain()
        version, _ = self.selected_completed_sequence_version_with_video(clip1)
        with patch("engine.media.providers.estimate_video") as estimate, patch("engine.media.providers.start_video") as start:
            with self.assertRaisesRegex(SequenceError, "låst"):
                promote_output_chain_final_frame(version)
        estimate.assert_not_called()
        start.assert_not_called()
        k1.refresh_from_db()
        self.assertNotEqual(k1.source_type, "output_chain")

    def test_e3_promotes_actual_final_frame_to_shared_next_anchor_with_structured_provenance(self):
        _, k1, _, clip1, clip2 = self.build_three_anchor_chain()
        old_asset_id = k1.asset_id
        version, video = self.selected_completed_sequence_version_with_video(clip1)
        set_anchor_locked(k1, False)

        with patch("engine.media.providers.estimate_video") as estimate, patch("engine.media.providers.start_video") as start:
            promoted = promote_output_chain_final_frame(version)
        estimate.assert_not_called()
        start.assert_not_called()

        promoted.refresh_from_db()
        clip1.refresh_from_db()
        clip2.refresh_from_db()
        self.assertEqual(promoted.pk, k1.pk)
        self.assertNotEqual(promoted.asset_id, old_asset_id)
        self.assertEqual(clip1.end_anchor_id, promoted.pk)
        self.assertEqual(clip2.start_anchor_id, promoted.pk)
        self.assertEqual(promoted.source_type, "output_chain")
        self.assertEqual(promoted.source_clip_version_id, version.pk)
        self.assertEqual(promoted.source_metadata["mode"], "output_chain")
        self.assertEqual(promoted.source_metadata["frame_selector"], "final")
        self.assertEqual(promoted.source_metadata["source_video_asset_id"], str(video.pk))
        self.assertEqual(promoted.source_metadata["source_generation_id"], str(version.generation_id))
        self.assertEqual(promoted.source_metadata["previous_anchor_asset_id"], str(old_asset_id))
        self.assertEqual(promoted.source_metadata["derived_asset_id"], str(promoted.asset_id))
        self.assertEqual(promoted.source_metadata["frame"]["frame_selector"], "final")
        self.assertGreaterEqual(promoted.source_metadata["frame"]["frame_index"], 0)
        self.assertTrue(MediaAsset.objects.filter(pk=old_asset_id).exists())

        derived = promoted.asset
        self.assertEqual(derived.kind, "image")
        self.assertEqual(derived.origin, "generated")
        self.assertEqual(derived.generation_id, version.generation_id)
        self.assertIsNone(derived.expires_at)
        with open_asset(derived) as file:
            with Image.open(file) as image:
                pixel = image.convert("RGB").getpixel((32, 48))
        self.assertTrue(all(channel > 235 for channel in pixel), pixel)

    def test_e3_promotion_is_idempotent_for_same_selected_version(self):
        _, k1, _, clip1, _ = self.build_three_anchor_chain()
        version, _ = self.selected_completed_sequence_version_with_video(clip1)
        set_anchor_locked(k1, False)
        first = promote_output_chain_final_frame(version)
        asset_id = first.asset_id
        count = MediaAsset.objects.count()

        set_anchor_locked(first, True)
        second = promote_output_chain_final_frame(version)
        self.assertEqual(second.asset_id, asset_id)
        self.assertEqual(MediaAsset.objects.count(), count)

    def test_e3_refuses_unselected_source_version(self):
        _, k1, _, clip1, _ = self.build_three_anchor_chain()
        version = prepare_anchor_chain_version(clip1, token=uuid.uuid4())
        MediaGeneration.objects.filter(pk=version.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=version.pk).update(status="ready")
        version.refresh_from_db()
        version.generation.refresh_from_db()
        store_asset(self.company, sequence_movie(), job=version.generation)
        set_anchor_locked(k1, False)

        with self.assertRaisesRegex(SequenceError, "Välj clip-versionen"):
            promote_output_chain_final_frame(version)

    def test_e3_refuses_to_invalidate_selected_downstream_clip(self):
        _, k1, _, clip1, clip2 = self.build_three_anchor_chain()
        source_version, _ = self.selected_completed_sequence_version_with_video(clip1)
        downstream_version = prepare_anchor_chain_version(clip2, token=uuid.uuid4())
        MediaGeneration.objects.filter(pk=downstream_version.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=downstream_version.pk).update(status="ready")
        downstream_version.refresh_from_db()
        select_clip_version(clip2, downstream_version)
        set_anchor_locked(k1, False)
        asset_count = MediaAsset.objects.count()

        with self.assertRaisesRegex(SequenceError, "efterföljande clip"):
            promote_output_chain_final_frame(source_version)
        self.assertEqual(MediaAsset.objects.count(), asset_count)
        k1.refresh_from_db()
        self.assertNotEqual(k1.source_type, "output_chain")

    def test_e3_refuses_promotion_when_end_anchor_is_not_next_clip_start(self):
        k0 = add_anchor(self.project, self.asset(), position=0, locked=False)
        k1 = add_anchor(self.project, self.asset((60, 120, 70)), position=1, locked=False)
        clip = create_clip(
            self.project,
            k0,
            k1,
            position=0,
            recipe_id="scroll_transition_bridge",
        )
        version, _ = self.selected_completed_sequence_version_with_video(clip)
        with self.assertRaisesRegex(SequenceError, "efterföljande clip"):
            promote_output_chain_final_frame(version)

    def test_e3_old_downstream_candidate_becomes_stale_without_being_deleted(self):
        _, k1, _, clip1, clip2 = self.build_three_anchor_chain()
        source_version, _ = self.selected_completed_sequence_version_with_video(clip1)
        old_downstream = prepare_anchor_chain_version(clip2, token=uuid.uuid4())
        old_generation_id = old_downstream.generation_id
        set_anchor_locked(k1, False)

        promote_output_chain_final_frame(source_version)

        self.assertTrue(SequenceClipVersion.objects.filter(pk=old_downstream.pk).exists())
        self.assertTrue(MediaGeneration.objects.filter(pk=old_generation_id).exists())
        with patch("engine.sequence.preview_job") as preview:
            with self.assertRaisesRegex(SequenceError, "anchors har ändrats"):
                preview_anchor_chain_version(old_downstream)
        preview.assert_not_called()

    def test_e3_output_chain_anchor_validation_requires_source_and_final_frame_metadata(self):
        asset = self.asset()
        with self.assertRaises(ValidationError):
            SequenceAnchor(
                project=self.project,
                position=9,
                asset=asset,
                source_type="output_chain",
                source_metadata={"mode": "output_chain", "frame_selector": "final"},
            ).save()
