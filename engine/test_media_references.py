import io
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from .creative_core import ReferenceRole
from .media import create_job, remove_asset, store_asset
from .media_references import (
    add_generation_reference,
    generation_reference_records,
    reference_assets,
    serialize_generation_references,
)
from .media_storage import MediaError
from .models import Company, ContentRun, MediaAsset, MediaGeneration, MediaGenerationReference


def picture():
    out = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(out, "PNG")
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class MediaGenerationReferenceTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_user(username="reference-owner")
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golf",
            current="Golf",
            source="Owner",
            valid_until=timezone.localdate() + timedelta(days=2),
        )
        self.run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={"profile": "Golf", "current": "Golf"},
            ideas=[{"title": "Golf"}],
            selected=0,
            draft={"instagram": "Text"},
            model="test",
        )

    def raw_job(self, *, source=None):
        return MediaGeneration.objects.create(
            run=self.run,
            kind="video",
            provider="higgsfield",
            brief="Video",
            prompt="Video",
            source_asset=source,
        )

    def image_asset(self, company=None):
        return store_asset(company or self.company, picture())

    def video_asset_row(self, company=None):
        company = company or self.company
        return MediaAsset.objects.create(
            company=company,
            kind="video",
            origin="uploaded",
            provider="user",
            storage_backend="local",
            storage_key=f"{company.pk}/{uuid.uuid4()}.mp4",
            mime_type="video/mp4",
            byte_size=100,
            duration_seconds=1,
            purpose="content",
            sha256="a" * 64,
        )

    def test_create_job_persists_start_image_reference_and_keeps_legacy_source(self):
        source = self.image_asset()
        job = create_job(
            self.run,
            token=uuid.uuid4(),
            kind="video",
            brief="Animera bilden i 8 sekunder och behåll motivet",
            source=source,
        )
        ref = job.references.get()
        self.assertEqual(ref.role, ReferenceRole.start_image.value)
        self.assertEqual(ref.position, 0)
        self.assertEqual(ref.asset_id, source.pk)
        self.assertEqual(job.source_asset_id, source.pk)
        serialized = serialize_generation_references(job)
        self.assertEqual(serialized[0]["role"], "START_IMAGE")
        self.assertFalse(serialized[0]["legacy_source_asset"])

    def test_legacy_source_asset_is_exposed_as_virtual_start_reference(self):
        source = self.image_asset()
        job = self.raw_job(source=source)
        self.assertFalse(job.references.exists())
        records = generation_reference_records(job)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["role"], "START_IMAGE")
        self.assertEqual(records[0]["asset"].pk, source.pk)
        self.assertTrue(records[0]["legacy_source_asset"])
        self.assertEqual(reference_assets(job, ReferenceRole.start_image), [source])

    def test_start_reference_added_to_legacy_empty_job_updates_source_asset(self):
        source = self.image_asset()
        job = self.raw_job()
        ref = add_generation_reference(job, source, ReferenceRole.start_image)
        job.refresh_from_db()
        self.assertEqual(job.source_asset_id, source.pk)
        self.assertEqual(ref.asset_id, source.pk)

    def test_cross_company_reference_is_rejected_by_service_and_model(self):
        outsider = get_user_model().objects.create_user(username="reference-outsider")
        other = Company.objects.create(owner=outsider, name="Other")
        foreign = self.image_asset(other)
        job = self.raw_job()
        with self.assertRaises(MediaError):
            add_generation_reference(job, foreign, ReferenceRole.style_reference)
        with self.assertRaises(ValidationError):
            MediaGenerationReference.objects.create(
                generation=job,
                asset=foreign,
                role=ReferenceRole.style_reference.value,
                position=0,
            )

    def test_start_and_end_references_are_singleton_position_zero(self):
        first = self.image_asset()
        second = self.image_asset()
        job = self.raw_job()
        with self.assertRaises(MediaError):
            add_generation_reference(job, first, ReferenceRole.start_image, position=1)
        with self.assertRaises(MediaError):
            add_generation_reference(job, second, ReferenceRole.end_image, position=2)
        with self.assertRaises(ValidationError):
            MediaGenerationReference.objects.create(
                generation=job,
                asset=first,
                role=ReferenceRole.end_image.value,
                position=1,
            )

    def test_typed_start_and_legacy_source_mismatch_is_rejected_and_read_still_fails_closed(self):
        legacy = self.image_asset()
        typed = self.image_asset()
        job = self.raw_job(source=legacy)
        with self.assertRaises(ValidationError):
            MediaGenerationReference.objects.create(
                generation=job,
                asset=typed,
                role=ReferenceRole.start_image.value,
                position=0,
            )
        # Simulate corrupted/pre-C1 bulk data that bypassed model validation.
        MediaGenerationReference.objects.bulk_create([
            MediaGenerationReference(
                generation=job,
                asset=typed,
                role=ReferenceRole.start_image.value,
                position=0,
            )
        ])
        with self.assertRaises(MediaError):
            generation_reference_records(job)

    def test_reference_roles_enforce_media_kind_and_reserve_audio(self):
        image = self.image_asset()
        video = self.video_asset_row()
        job = self.raw_job()
        with self.assertRaises(MediaError):
            add_generation_reference(job, video, ReferenceRole.start_image)
        with self.assertRaises(MediaError):
            add_generation_reference(job, image, ReferenceRole.video_reference)
        with self.assertRaises(MediaError):
            add_generation_reference(job, image, ReferenceRole.audio_reference)

    def test_ordered_references_are_stable_and_duplicate_positions_fail_closed(self):
        first = self.image_asset()
        second = self.image_asset()
        third = self.image_asset()
        job = self.raw_job()
        add_generation_reference(job, second, ReferenceRole.style_reference, position=1)
        add_generation_reference(job, first, ReferenceRole.style_reference, position=0)
        self.assertEqual(reference_assets(job, ReferenceRole.style_reference), [first, second])
        with self.assertRaises(MediaError):
            add_generation_reference(job, third, ReferenceRole.style_reference, position=0)
        with self.assertRaises(MediaError):
            add_generation_reference(job, first, ReferenceRole.style_reference, position=2)

    def test_future_expiring_reference_is_promoted_to_persistent_media(self):
        asset = self.image_asset()
        MediaAsset.objects.filter(pk=asset.pk).update(expires_at=timezone.now() + timedelta(days=1))
        asset.refresh_from_db()
        job = self.raw_job()
        add_generation_reference(job, asset, ReferenceRole.style_reference)
        asset.refresh_from_db()
        self.assertIsNone(asset.expires_at)

    def test_reference_asset_cannot_be_deleted_while_provenance_points_to_it(self):
        source = self.image_asset()
        job = self.raw_job()
        add_generation_reference(job, source, ReferenceRole.product_reference)
        with self.assertRaises(MediaError):
            remove_asset(source)
        self.assertTrue(MediaAsset.objects.filter(pk=source.pk).exists())

    def test_logo_and_expired_assets_cannot_become_generation_references(self):
        job = self.raw_job()
        logo = self.image_asset()
        MediaAsset.objects.filter(pk=logo.pk).update(purpose="logo")
        logo.refresh_from_db()
        with self.assertRaises(MediaError):
            add_generation_reference(job, logo, ReferenceRole.style_reference)

        expired = self.image_asset()
        MediaAsset.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        expired.refresh_from_db()
        with self.assertRaises(MediaError):
            add_generation_reference(job, expired, ReferenceRole.style_reference)
