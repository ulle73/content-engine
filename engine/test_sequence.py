import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from .media import remove_asset, store_asset
from .media_storage import MediaError
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
    replace_anchor_asset,
    select_clip_version,
    sequence_snapshot,
    set_anchor_locked,
)


def picture(rgb=(24, 92, 58)):
    out = io.BytesIO()
    Image.new("RGB", (64, 96), rgb).save(out, "PNG")
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
