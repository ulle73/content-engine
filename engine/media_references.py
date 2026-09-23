"""Typed provider-neutral media references for Creative Engine generations."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .creative_core import ReferenceRole
from .media_storage import MediaError
from .models import MediaAsset, MediaGeneration, MediaGenerationReference


_ALIASES = {
    "source_asset": ReferenceRole.start_image,
    "start_image": ReferenceRole.start_image,
    "end_image": ReferenceRole.end_image,
    "product_reference": ReferenceRole.product_reference,
    "character_reference": ReferenceRole.character_reference,
    "location_reference": ReferenceRole.location_reference,
    "style_reference": ReferenceRole.style_reference,
    "video_reference": ReferenceRole.video_reference,
    "audio_reference": ReferenceRole.audio_reference,
}


def normalize_reference_role(role: ReferenceRole | str) -> ReferenceRole:
    if isinstance(role, ReferenceRole):
        return role
    value = str(role or "").strip()
    if value in ReferenceRole._value2member_map_:
        return ReferenceRole(value)
    resolved = _ALIASES.get(value.casefold())
    if resolved is None:
        raise MediaError("Okänd mediareferensroll.")
    return resolved


def add_generation_reference(
    job: MediaGeneration,
    asset: MediaAsset,
    role: ReferenceRole | str,
    *,
    position: int = 0,
) -> MediaGenerationReference:
    """Persist one canonical reference without leaking provider field names."""
    role = normalize_reference_role(role)
    if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position <= 32767:
        raise MediaError("Referensens position är ogiltig.")
    if role in {ReferenceRole.start_image, ReferenceRole.end_image} and position != 0:
        raise MediaError("START_IMAGE och END_IMAGE måste använda position 0.")

    with transaction.atomic():
        locked_job = (
            MediaGeneration.objects.select_for_update()
            .select_related("run")
            .get(pk=job.pk)
        )
        locked_asset = MediaAsset.objects.select_for_update().get(pk=asset.pk)
        if locked_asset.company_id != locked_job.run.workspace_id:
            raise MediaError("Referensmedia ska tillhöra samma företag som generationen.")
        if locked_asset.purpose == "logo":
            raise MediaError("Företagets logga hanteras separat och kan inte vara generationreferens.")
        if locked_asset.expires_at and locked_asset.expires_at <= timezone.now():
            raise MediaError("Referensmediets förhandsvisning har gått ut.")
        if locked_asset.expires_at is not None:
            locked_asset.expires_at = None
            locked_asset.save(update_fields=["expires_at"])

        if role == ReferenceRole.start_image and position == 0:
            if locked_job.source_asset_id and locked_job.source_asset_id != locked_asset.pk:
                raise MediaError("START_IMAGE och legacy source_asset pekar på olika filer.")
            if not locked_job.source_asset_id:
                locked_job.source_asset = locked_asset
                locked_job.save(update_fields=["source_asset"])
                job.source_asset = locked_asset
                job.source_asset_id = locked_asset.pk

        existing = MediaGenerationReference.objects.filter(
            generation=locked_job,
            role=role.value,
            position=position,
        ).first()
        if existing:
            if existing.asset_id != locked_asset.pk:
                raise MediaError("Referenspositionen används redan av en annan fil.")
            return existing

        try:
            return MediaGenerationReference.objects.create(
                generation=locked_job,
                asset=locked_asset,
                role=role.value,
                position=position,
            )
        except ValidationError as exc:
            message = next(iter(exc.message_dict.values()))[0] if hasattr(exc, "message_dict") else str(exc)
            raise MediaError(message) from exc


def generation_reference_records(job: MediaGeneration, *, include_legacy=True) -> list[dict]:
    """Return typed refs plus a virtual START_IMAGE for pre-C1 legacy jobs."""
    records = [
        {
            "role": ref.role,
            "position": ref.position,
            "asset": ref.asset,
            "legacy_source_asset": False,
        }
        for ref in job.references.all()
    ]
    start_zero = next(
        (
            row for row in records
            if row["role"] == ReferenceRole.start_image.value and row["position"] == 0
        ),
        None,
    )
    has_start_zero = start_zero is not None
    if has_start_zero and job.source_asset_id and start_zero["asset"].pk != job.source_asset_id:
        raise MediaError("Typed START_IMAGE och legacy source_asset är inkonsekventa.")
    if include_legacy and job.source_asset_id and not has_start_zero:
        source = job.source_asset
        if source is None:
            source = MediaAsset.objects.filter(pk=job.source_asset_id).first()
        if source is not None:
            records.append(
                {
                    "role": ReferenceRole.start_image.value,
                    "position": 0,
                    "asset": source,
                    "legacy_source_asset": True,
                }
            )
    return sorted(records, key=lambda row: (row["role"], row["position"], str(row["asset"].pk)))


def reference_assets(job: MediaGeneration, role: ReferenceRole | str) -> list[MediaAsset]:
    canonical = normalize_reference_role(role).value
    return [
        row["asset"]
        for row in generation_reference_records(job)
        if row["role"] == canonical
    ]


def serialize_generation_references(job: MediaGeneration) -> list[dict]:
    return [
        {
            "role": row["role"],
            "position": row["position"],
            "asset_id": str(row["asset"].pk),
            "kind": row["asset"].kind,
            "sha256": row["asset"].sha256,
            "legacy_source_asset": row["legacy_source_asset"],
        }
        for row in generation_reference_records(job)
    ]


__all__ = [
    "add_generation_reference",
    "generation_reference_records",
    "normalize_reference_role",
    "reference_assets",
    "serialize_generation_references",
]
