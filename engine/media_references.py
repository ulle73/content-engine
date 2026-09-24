"""Canonical provider-neutral references for media generation."""
from __future__ import annotations

from django.db import transaction

from .creative_core import ReferenceRole
from .media_storage import MediaError
from .models import MediaAsset, MediaGeneration, MediaGenerationReference


def _role_value(role: ReferenceRole | str) -> str:
    try:
        return ReferenceRole(role).value
    except ValueError as exc:
        raise MediaError("Okänd referensroll.") from exc


def _snapshot(asset: MediaAsset) -> dict:
    return {"asset_id": str(asset.pk), "kind": asset.kind, "sha256": asset.sha256}


def add_generation_reference(
    generation: MediaGeneration,
    asset: MediaAsset,
    role: ReferenceRole | str,
    *,
    position: int = 0,
) -> MediaGenerationReference:
    """Persist one canonical slot without allowing cross-company or slot replacement."""
    role_value = _role_value(role)
    if position < 0 or position > 65535:
        raise MediaError("Referenspositionen är ogiltig.")
    if asset.company_id != generation.run.workspace_id:
        raise MediaError("Referensen ska tillhöra samma företag som generationen.")
    if role_value in {ReferenceRole.start_image.value, ReferenceRole.end_image.value} and (
        asset.kind != "image" or asset.purpose == "logo"
    ):
        raise MediaError("Start- och slutreferenser måste vara vanliga bilder.")
    if role_value == ReferenceRole.video_reference.value and asset.kind != "video":
        raise MediaError("Videoreferensen måste vara en video.")
    if role_value == ReferenceRole.audio_reference.value:
        raise MediaError("Ljudreferenser stöds inte av MediaAsset ännu.")

    with transaction.atomic():
        existing = MediaGenerationReference.objects.select_for_update().filter(
            generation=generation, role=role_value, position=position
        ).first()
        if existing:
            if existing.asset_id == asset.pk:
                return existing
            raise MediaError("Referensplatsen används redan av en annan fil.")
        return MediaGenerationReference.objects.create(
            generation=generation,
            asset=asset,
            role=role_value,
            position=position,
            asset_snapshot=_snapshot(asset),
        )


def ensure_source_reference(generation: MediaGeneration) -> MediaGenerationReference | None:
    """Mirror legacy source_asset into canonical START_IMAGE for new/old jobs."""
    if not generation.source_asset_id:
        return None
    return add_generation_reference(
        generation, generation.source_asset, ReferenceRole.start_image, position=0
    )


def reference_asset(
    generation: MediaGeneration, role: ReferenceRole | str, *, position: int = 0
) -> MediaAsset | None:
    role_value = _role_value(role)
    row = generation.references.select_related("asset").filter(role=role_value, position=position).first()
    if row and row.asset_id:
        return row.asset
    if role_value == ReferenceRole.start_image.value and position == 0 and generation.source_asset_id:
        return generation.source_asset
    return None


def serialize_generation_references(generation: MediaGeneration) -> list[dict]:
    """Safe provenance for UI/MCP; no provider URLs or storage keys."""
    rows = list(generation.references.select_related("asset").all())
    payload = []
    seen_start = False
    for row in rows:
        if row.role == ReferenceRole.start_image.value and row.position == 0:
            seen_start = True
        snapshot = dict(row.asset_snapshot or {})
        asset = row.asset
        payload.append({
            "role": row.role,
            "position": row.position,
            "asset_id": str(asset.pk) if asset else snapshot.get("asset_id"),
            "kind": asset.kind if asset else snapshot.get("kind"),
            "sha256": asset.sha256 if asset else snapshot.get("sha256", ""),
            "available": bool(asset),
            "source": "canonical",
        })
    if not seen_start and generation.source_asset_id:
        asset = generation.source_asset
        payload.append({
            "role": ReferenceRole.start_image.value,
            "position": 0,
            "asset_id": str(asset.pk),
            "kind": asset.kind,
            "sha256": asset.sha256,
            "available": True,
            "source": "legacy_source_asset",
        })
    return sorted(payload, key=lambda item: (item["role"], item["position"]))


__all__ = [
    "add_generation_reference",
    "ensure_source_reference",
    "reference_asset",
    "serialize_generation_references",
]
