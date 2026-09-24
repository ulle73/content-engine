"""Sequence Engine domain services.

E1 deliberately orchestrates existing MediaAsset and MediaGeneration records.
It does not generate media, call providers, or duplicate media storage.
"""
from __future__ import annotations

from copy import deepcopy

from django.db import IntegrityError, transaction
from django.db.models import Max

from .creative_recipes import get_recipe
from .media_references import serialize_generation_references
from .models import (
    Company,
    MediaAsset,
    MediaGeneration,
    SequenceAnchor,
    SequenceClip,
    SequenceClipVersion,
    SequenceProject,
)


class SequenceError(ValueError):
    pass


def _validate_anchor_asset(project: SequenceProject, asset: MediaAsset) -> None:
    if asset.company_id != project.company_id:
        raise SequenceError("Anchor-bilden måste tillhöra samma företag som sequence-projektet.")
    if asset.kind != "image" or asset.purpose == "logo":
        raise SequenceError("En sequence-anchor måste vara en vanlig bild.")


def create_sequence_project(
    company: Company,
    *,
    author=None,
    title: str,
    brief: str = "",
    goal: str = "",
    format: str = "",
    platform: str = "",
    blueprint_id: str = "",
    blueprint_version: str = "",
    notes: str = "",
) -> SequenceProject:
    title = (title or "").strip()
    if not title or len(title) > 200:
        raise SequenceError("Sequence-projektet behöver en titel på högst 200 tecken.")
    if author is not None and getattr(author, "pk", None) is None:
        raise SequenceError("Författaren måste vara en sparad användare.")
    return SequenceProject.objects.create(
        company=company,
        author=author,
        title=title,
        brief=brief,
        goal=goal,
        format=format,
        platform=platform,
        blueprint_id=blueprint_id,
        blueprint_version=blueprint_version,
        notes=notes,
    )


def add_anchor(
    project: SequenceProject,
    asset: MediaAsset,
    *,
    position: int,
    label: str = "",
    role: str = "",
    locked: bool = False,
    source_type: str = "existing",
    source_clip_version: SequenceClipVersion | None = None,
    notes: str = "",
) -> SequenceAnchor:
    if position < 0:
        raise SequenceError("Anchor-positionen kan inte vara negativ.")
    _validate_anchor_asset(project, asset)
    if source_clip_version and source_clip_version.clip.project_id != project.pk:
        raise SequenceError("Anchor-källan måste tillhöra samma sequence-projekt.")
    try:
        return SequenceAnchor.objects.create(
            project=project,
            position=position,
            asset=asset,
            label=label,
            role=role,
            locked=locked,
            source_type=source_type,
            source_clip_version=source_clip_version,
            notes=notes,
        )
    except (IntegrityError, ValueError) as exc:
        raise SequenceError("Det finns redan en anchor på den positionen.") from exc


def set_anchor_locked(anchor: SequenceAnchor, locked: bool) -> SequenceAnchor:
    with transaction.atomic():
        current = SequenceAnchor.objects.select_for_update().get(pk=anchor.pk)
        current.locked = bool(locked)
        current.save(update_fields=["locked", "updated_at"])
    return SequenceAnchor.objects.get(pk=anchor.pk)


def replace_anchor_asset(
    anchor: SequenceAnchor,
    asset: MediaAsset,
    *,
    source_type: str = "existing",
    source_clip_version: SequenceClipVersion | None = None,
) -> SequenceAnchor:
    with transaction.atomic():
        current = SequenceAnchor.objects.select_for_update().select_related("project").get(pk=anchor.pk)
        if current.locked:
            raise SequenceError("En låst anchor kan inte ersättas utan att först låsas upp.")
        _validate_anchor_asset(current.project, asset)
        if source_clip_version and source_clip_version.clip.project_id != current.project_id:
            raise SequenceError("Anchor-källan måste tillhöra samma sequence-projekt.")
        current.asset = asset
        current.source_type = source_type
        current.source_clip_version = source_clip_version
        current.save(update_fields=["asset", "source_type", "source_clip_version", "updated_at"])
    return SequenceAnchor.objects.select_related("asset").get(pk=anchor.pk)


def create_clip(
    project: SequenceProject,
    start_anchor: SequenceAnchor,
    end_anchor: SequenceAnchor,
    *,
    position: int,
    recipe_id: str,
    recipe_version: str | None = None,
    label: str = "",
    model_override: str = "",
    duration_seconds_target: int | None = None,
    aspect_ratio: str = "",
    notes: str = "",
) -> SequenceClip:
    if position < 0:
        raise SequenceError("Clip-positionen kan inte vara negativ.")
    if start_anchor.project_id != project.pk or end_anchor.project_id != project.pk:
        raise SequenceError("Båda anchors måste tillhöra samma sequence-projekt.")
    if start_anchor.position >= end_anchor.position:
        raise SequenceError("Start-anchor måste ligga före slut-anchor.")

    recipe = get_recipe(recipe_id)
    if not recipe or "video" not in recipe.kinds:
        raise SequenceError("Clip-receptet måste vara ett trusted video recipe.")
    if recipe_version and recipe_version != recipe.version:
        raise SequenceError("Den begärda recipe-versionen är inte den verifierade aktuella versionen.")

    try:
        return SequenceClip.objects.create(
            project=project,
            position=position,
            start_anchor=start_anchor,
            end_anchor=end_anchor,
            label=label,
            recipe_id=recipe.recipe_id,
            recipe_version=recipe.version,
            model_override=model_override,
            duration_seconds_target=duration_seconds_target,
            aspect_ratio=aspect_ratio,
            notes=notes,
        )
    except (IntegrityError, ValueError) as exc:
        raise SequenceError("Det finns redan ett clip på den positionen.") from exc


def _cost_snapshot(generation: MediaGeneration) -> dict:
    usage = generation.usage or {}
    estimate = usage.get("estimate") if isinstance(usage, dict) else None
    result = {}
    if isinstance(estimate, dict):
        for key in ("usd", "credits", "currency"):
            value = estimate.get(key)
            if isinstance(value, (str, int, float)):
                result["estimate_" + key] = value
    for key in ("actual_usd", "cost_usd", "usd"):
        value = usage.get(key) if isinstance(usage, dict) else None
        if isinstance(value, (str, int, float)):
            result[key] = value
    return result


def attach_generation_to_clip(
    clip: SequenceClip,
    generation: MediaGeneration,
    *,
    review_notes: str = "",
) -> SequenceClipVersion:
    if generation.run.workspace_id != clip.project.company_id:
        raise SequenceError("Generationens företag matchar inte sequence-projektet.")
    if generation.kind != "video":
        raise SequenceError("Sequence clips kan bara kopplas till videogenerationer.")
    if hasattr(generation, "sequence_clip_version"):
        raise SequenceError("Generationens provenance är redan kopplad till en clip-version.")

    creative = (generation.parameters or {}).get("creative") or {}
    recipe = creative.get("recipe") if isinstance(creative, dict) else {}
    recipe = recipe if isinstance(recipe, dict) else {}

    with transaction.atomic():
        locked = SequenceClip.objects.select_for_update().select_related("project").get(pk=clip.pk)
        latest = locked.versions.aggregate(value=Max("version_number"))["value"] or 0
        status = "ready" if generation.status == "completed" else "failed" if generation.status in {"failed", "nsfw", "canceled"} else "queued"
        return SequenceClipVersion.objects.create(
            clip=locked,
            version_number=latest + 1,
            generation=generation,
            status=status,
            recipe_id=recipe.get("recipe_id") or locked.recipe_id,
            recipe_version=recipe.get("version") or locked.recipe_version,
            model_id=(generation.parameters or {}).get("model", ""),
            provider_model=(generation.parameters or {}).get("provider_model", ""),
            prompt_snapshot=generation.prompt,
            reference_snapshot=serialize_generation_references(generation),
            usage_snapshot=deepcopy(generation.usage or {}),
            cost_snapshot=_cost_snapshot(generation),
            review_notes=review_notes,
        )


def select_clip_version(clip: SequenceClip, version: SequenceClipVersion) -> SequenceClip:
    with transaction.atomic():
        locked = SequenceClip.objects.select_for_update().get(pk=clip.pk)
        selected = SequenceClipVersion.objects.select_for_update().select_related("generation").get(pk=version.pk)
        if selected.clip_id != locked.pk:
            raise SequenceError("Clip-versionen tillhör ett annat clip.")
        if selected.generation.status != "completed" or selected.status in {"failed", "rejected"}:
            raise SequenceError("Endast en färdig, godkänd kandidat kan väljas.")
        previous_id = locked.selected_version_id
        if previous_id and previous_id != selected.pk:
            SequenceClipVersion.objects.filter(pk=previous_id, status="selected").update(status="ready")
        SequenceClipVersion.objects.filter(pk=selected.pk).update(status="selected")
        locked.selected_version = selected
        locked.status = "selected"
        locked.save(update_fields=["selected_version", "status", "updated_at"])
    return SequenceClip.objects.select_related("selected_version").get(pk=clip.pk)


def reject_clip_version(version: SequenceClipVersion, *, review_notes: str = "") -> SequenceClipVersion:
    with transaction.atomic():
        current = SequenceClipVersion.objects.select_for_update().get(pk=version.pk)
        clip = SequenceClip.objects.select_for_update().get(pk=current.clip_id)
        if clip.selected_version_id == current.pk:
            raise SequenceError("Den valda clip-versionen måste avmarkeras genom att välja en annan kandidat först.")
        current.status = "rejected"
        if review_notes:
            current.review_notes = review_notes
        current.save(update_fields=["status", "review_notes"])
    return SequenceClipVersion.objects.get(pk=version.pk)


def sequence_snapshot(project: SequenceProject) -> dict:
    anchors = list(project.anchors.select_related("asset").order_by("position"))
    clips = list(
        project.clips.select_related("start_anchor", "end_anchor", "selected_version").order_by("position")
    )
    return {
        "project_id": str(project.pk),
        "anchors": [
            {
                "id": str(anchor.pk),
                "position": anchor.position,
                "asset_id": str(anchor.asset_id),
                "locked": anchor.locked,
            }
            for anchor in anchors
        ],
        "clips": [
            {
                "id": str(clip.pk),
                "position": clip.position,
                "start_anchor_id": str(clip.start_anchor_id),
                "end_anchor_id": str(clip.end_anchor_id),
                "recipe_id": clip.recipe_id,
                "recipe_version": clip.recipe_version,
                "selected_version_id": str(clip.selected_version_id) if clip.selected_version_id else None,
            }
            for clip in clips
        ],
    }


__all__ = [
    "SequenceError",
    "create_sequence_project",
    "add_anchor",
    "set_anchor_locked",
    "replace_anchor_asset",
    "create_clip",
    "attach_generation_to_clip",
    "select_clip_version",
    "reject_clip_version",
    "sequence_snapshot",
]
