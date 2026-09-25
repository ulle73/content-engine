import io
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from .creative_core import ReferenceRole
from .media import MediaError, start_reviewed_job, store_asset
from .media_references import generation_reference_signature, reference_asset
from .models import Company, MediaGeneration, SequenceAnchor, SequenceProject
from .sequence import (
    SequenceError,
    add_anchor,
    apply_generated_anchor_asset,
    create_clip,
    create_sequence_project,
    materialize_planned_anchor_asset,
    prepare_anchor_chain_version,
    prepare_planned_anchor_generation,
    sequence_plan_anchor_readiness,
)


def picture(rgb=(24, 92, 58)):
    out = io.BytesIO()
    Image.new("RGB", (96, 64), rgb).save(out, "PNG")
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class SequenceAIAnchorsG2Tests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        media = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        media.enable()
        self.addCleanup(media.disable)
        self.user = get_user_model().objects.create_user(username="g2@example.test")
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golfkuponger erbjuder golfrelaterade värdebevis.",
            current="Aktuellt fokus.",
        )
        self.project = create_sequence_project(
            self.company,
            author=self.user,
            title="G2 plan",
            brief="Premium 2-scene story",
            format="scroll_story",
            platform="web",
        )
        self.set_plan([
            {"position": 0, "label": "Opening", "description": "Premium golf opening.", "role": "opening", "reference_requirements": [], "reference_note": ""},
            {"position": 1, "label": "Product", "description": "Exact product hero.", "role": "product", "reference_requirements": ["product"], "reference_note": "Preserve the exact product."},
            {"position": 2, "label": "Brand close", "description": "Branded close.", "role": "closing", "reference_requirements": ["company"], "reference_note": "Exact company brand."},
        ])

    def asset(self, rgb=(24, 92, 58), *, job=None, purpose="content"):
        return store_asset(self.company, picture(rgb), job=job, purpose=purpose)

    def set_plan(self, anchors, revision=1):
        SequenceProject.objects.filter(pk=self.project.pk).update(
            plan={
                "planner_id": "sequence_planner",
                "planner_version": "1.1.0",
                "status": "draft",
                "scene_count": max(1, len(anchors) - 1),
                "anchors": anchors,
                "scenes": [],
            },
            plan_revision=revision,
        )
        self.project.refresh_from_db()

    def test_manual_materialization_uses_exact_planned_position_out_of_order(self):
        image = self.asset()
        anchor = materialize_planned_anchor_asset(
            self.project,
            image,
            position=2,
            source_type="existing",
            created_by=self.user,
        )
        self.assertEqual(anchor.position, 2)
        self.assertEqual(anchor.label, "Brand close")
        self.assertEqual(anchor.source_metadata["plan_revision"], 1)
        self.assertEqual(anchor.source_metadata["plan_anchor_position"], 2)
        self.assertFalse(self.project.anchors.filter(position=0).exists())
        self.assertEqual(sequence_plan_anchor_readiness(self.project)["missing_positions"], [0, 1])

    def test_product_reference_is_required_and_persisted_before_review_signature(self):
        with self.assertRaisesRegex(SequenceError, "produktreferens"):
            prepare_planned_anchor_generation(
                self.project,
                position=1,
                token=uuid.uuid4(),
                created_by=self.user,
            )

        product = self.asset((90, 120, 80))
        with patch("engine.media.providers.start_image") as start:
            target = prepare_planned_anchor_generation(
                self.project,
                position=1,
                reference_asset=product,
                token=uuid.uuid4(),
                created_by=self.user,
            )
        start.assert_not_called()
        target.generation.refresh_from_db()
        self.assertEqual(target.target_position, 1)
        self.assertEqual(target.plan_revision, 1)
        self.assertEqual(target.plan_anchor_snapshot["label"], "Product")
        self.assertEqual(target.generation.source_asset_id, product.pk)
        self.assertEqual(reference_asset(target.generation, ReferenceRole.product_reference).pk, product.pk)
        self.assertEqual(
            target.generation.usage["reviewed_reference_signature"],
            generation_reference_signature(target.generation),
        )
        self.assertFalse(target.generation.provider_id)

    def test_company_reference_reuses_official_logo_without_media_provider_start(self):
        logo = self.asset((245, 245, 245), purpose="logo")
        self.company.official_logo = logo
        self.company.save(update_fields=["official_logo"])
        with patch("engine.media.providers.start_image") as start:
            target = prepare_planned_anchor_generation(
                self.project,
                position=2,
                token=uuid.uuid4(),
                created_by=self.user,
            )
        start.assert_not_called()
        self.assertEqual(target.generation.logo_asset_id, logo.pk)
        self.assertIsNone(target.generation.source_asset_id)
        self.assertIn("company", target.generation.parameters["sequence"]["reference_requirements"])

    def test_stale_plan_ai_target_cannot_be_applied(self):
        target = prepare_planned_anchor_generation(
            self.project,
            position=0,
            token=uuid.uuid4(),
            created_by=self.user,
        )
        MediaGeneration.objects.filter(pk=target.generation_id).update(status="completed")
        target.generation.refresh_from_db()
        result = self.asset((210, 220, 200), job=target.generation)
        SequenceProject.objects.filter(pk=self.project.pk).update(plan_revision=2)
        with self.assertRaisesRegex(SequenceError, "planen har ändrats"):
            apply_generated_anchor_asset(target, result, created_by=self.user)
        self.assertFalse(self.project.anchors.filter(position=0).exists())

    def test_completed_ai_result_applies_to_exact_planned_position(self):
        target = prepare_planned_anchor_generation(
            self.project,
            position=0,
            token=uuid.uuid4(),
            created_by=self.user,
        )
        MediaGeneration.objects.filter(pk=target.generation_id).update(status="completed")
        target.generation.refresh_from_db()
        result = self.asset((210, 220, 200), job=target.generation)
        anchor = apply_generated_anchor_asset(target, result, created_by=self.user)
        self.assertEqual(anchor.position, 0)
        self.assertEqual(anchor.label, "Opening")
        self.assertEqual(anchor.source_metadata["mode"], "planned_ai")
        self.assertEqual(anchor.source_metadata["plan_revision"], 1)

    def test_video_candidate_is_blocked_until_all_planned_anchors_exist(self):
        k0 = materialize_planned_anchor_asset(self.project, self.asset(), position=0, source_type="existing")
        k1 = materialize_planned_anchor_asset(self.project, self.asset((50, 80, 60)), position=1, source_type="existing")
        clip = create_clip(
            self.project,
            k0,
            k1,
            position=0,
            recipe_id="scroll_transition_bridge",
        )
        with self.assertRaisesRegex(SequenceError, "Saknas: K2"):
            prepare_anchor_chain_version(clip, token=uuid.uuid4())
        self.assertEqual(clip.versions.count(), 0)

    def test_paid_video_start_rechecks_plan_readiness_centrally(self):
        k0 = materialize_planned_anchor_asset(self.project, self.asset(), position=0, source_type="existing")
        k1 = materialize_planned_anchor_asset(self.project, self.asset((50, 80, 60)), position=1, source_type="existing")
        k2 = materialize_planned_anchor_asset(self.project, self.asset((80, 110, 70)), position=2, source_type="existing")
        clip = create_clip(self.project, k0, k1, position=0, recipe_id="scroll_transition_bridge")
        version = prepare_anchor_chain_version(clip, token=uuid.uuid4())
        generation = version.generation
        usage = dict(generation.usage or {})
        usage.update({
            "reviewed_at": timezone.now().isoformat(),
            "reviewed_reference_signature": generation_reference_signature(generation),
            "estimate": {"usd": "0.42"},
        })
        MediaGeneration.objects.filter(pk=generation.pk).update(usage=usage)
        k2.delete()
        generation.refresh_from_db()
        with patch("engine.media.advance_job") as advance:
            with self.assertRaisesRegex(MediaError, "Saknas: K2"):
                start_reviewed_job(generation)
        advance.assert_not_called()
