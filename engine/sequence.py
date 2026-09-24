"""Sequence Engine domain services.

E1 deliberately orchestrates existing MediaAsset and MediaGeneration records.
It does not generate media, call providers, or duplicate media storage.
"""
from __future__ import annotations

from copy import deepcopy
import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from .creative_core import ReferenceRole
from .creative_recipes import get_recipe
from .media import create_job, extract_video_frame_png, preview_job, remove_asset, store_derived_image
from .media_references import reference_asset, serialize_generation_references
from .models import (
    Company,
    ContentRun,
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
    source_metadata: dict | None = None,
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
            source_metadata=deepcopy(source_metadata or {}),
            notes=notes,
        )
    except (IntegrityError, ValidationError, ValueError) as exc:
        raise SequenceError("Anchor-kunde inte sparas på den positionen.") from exc


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
    source_metadata: dict | None = None,
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
        current.source_metadata = deepcopy(source_metadata or {})
        current.save(update_fields=["asset", "source_type", "source_clip_version", "source_metadata", "updated_at"])
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
    except (IntegrityError, ValidationError, ValueError) as exc:
        raise SequenceError("Clip kunde inte sparas på den positionen.") from exc



def _sequence_generation_brief(clip: SequenceClip, override: str = "") -> str:
    text = (override or clip.project.brief or clip.notes or clip.label or clip.project.title).strip()
    if not text:
        text = "Create a smooth continuous transition between the supplied start and end anchors."
    suffix = []
    if clip.duration_seconds_target:
        suffix.append(f"Duration: {clip.duration_seconds_target} seconds.")
    if clip.aspect_ratio:
        suffix.append(f"Aspect ratio: {clip.aspect_ratio}.")
    suffix.append("Use the supplied start and end anchors as fixed canonical visual anchors.")
    result = " ".join([text, *suffix]).strip()
    if len(result) > 6000:
        raise SequenceError("Clip-briefen blir längre än 6000 tecken.")
    return result


def _sequence_run(clip: SequenceClip, *, brief: str) -> ContentRun:
    project = clip.project
    return ContentRun.objects.create(
        workspace=project.company,
        author=project.author or project.company.owner,
        context={
            "profile": project.company.profile,
            "voice": project.company.voice,
            "current": project.company.current,
            "sequence": {
                "mode": "anchor_chain",
                "project_id": str(project.pk),
                "clip_id": str(clip.pk),
                "clip_position": clip.position,
                "start_anchor_id": str(clip.start_anchor_id),
                "end_anchor_id": str(clip.end_anchor_id),
            },
        },
        ideas=[{
            "title": clip.label or project.title,
            "angle": brief,
        }],
        selected=0,
        draft={"instagram": brief[:1800], "sequence": brief},
        model="sequence-anchor-chain",
    )


def _normalize_generation_token(token) -> uuid.UUID:
    if token is None:
        return uuid.uuid4()
    try:
        return token if isinstance(token, uuid.UUID) else uuid.UUID(str(token))
    except (ValueError, TypeError, AttributeError) as exc:
        raise SequenceError("Ogiltig idempotency-token för sequence-generationen.") from exc


def _assert_generation_matches_current_anchors(version: SequenceClipVersion) -> None:
    clip = SequenceClip.objects.select_related(
        "start_anchor__asset", "end_anchor__asset"
    ).get(pk=version.clip_id)
    generation = MediaGeneration.objects.get(pk=version.generation_id)
    start = reference_asset(generation, ReferenceRole.start_image)
    end = reference_asset(generation, ReferenceRole.end_image)
    if not start or not end:
        raise SequenceError("Clip-generationen saknar canonical START_IMAGE eller END_IMAGE.")
    if start.pk != clip.start_anchor.asset_id or end.pk != clip.end_anchor.asset_id:
        raise SequenceError(
            "Sequence-anchors har ändrats sedan versionen skapades. Förbered en ny clip-version."
        )


def _sync_clip_version_provenance(version: SequenceClipVersion) -> SequenceClipVersion:
    generation = MediaGeneration.objects.get(pk=version.generation_id)
    status = (
        "ready" if generation.status == "completed"
        else "failed" if generation.status in {"failed", "nsfw", "canceled", "unknown"}
        else version.status
    )
    SequenceClipVersion.objects.filter(pk=version.pk).update(
        status=status,
        model_id=(generation.parameters or {}).get("model", ""),
        provider_model=(generation.parameters or {}).get("provider_model", ""),
        prompt_snapshot=generation.prompt,
        reference_snapshot=serialize_generation_references(generation),
        usage_snapshot=deepcopy(generation.usage or {}),
        cost_snapshot=_cost_snapshot(generation),
    )
    return SequenceClipVersion.objects.select_related("generation", "clip").get(pk=version.pk)


def prepare_anchor_chain_version(
    clip: SequenceClip,
    *,
    brief: str = "",
    priority: str = "balanced",
    token=None,
) -> SequenceClipVersion:
    """Create one reviewable clip candidate from the clip's canonical anchors.

    This function never calls a media provider. It reuses the existing MediaGeneration
    planning/reference pipeline and keeps all anchor mutation outside generation.
    """
    job_token = _normalize_generation_token(token)
    existing = SequenceClipVersion.objects.filter(generation_id=job_token).select_related("clip").first()
    if existing:
        if existing.clip_id != clip.pk:
            raise SequenceError("Idempotency-token används redan av ett annat sequence-clip.")
        return existing
    if MediaGeneration.objects.filter(pk=job_token).exists():
        raise SequenceError("Idempotency-token används redan av en annan mediageneration.")

    with transaction.atomic():
        locked = (
            SequenceClip.objects.select_for_update()
            .select_related(
                "project__company",
                "start_anchor__asset",
                "end_anchor__asset",
            )
            .get(pk=clip.pk)
        )
        if locked.model_override:
            raise SequenceError(
                "Model override är ännu inte aktiverat för Sequence Engine. Använd Auto tills B4 är implementerad."
            )
        _validate_anchor_asset(locked.project, locked.start_anchor.asset)
        _validate_anchor_asset(locked.project, locked.end_anchor.asset)

        request = _sequence_generation_brief(locked, brief)
        run = _sequence_run(locked, brief=request)
        try:
            generation = create_job(
                run,
                token=job_token,
                kind="video",
                brief=request,
                count=1,
                shape="portrait",
                source=locked.start_anchor.asset,
                end_source=locked.end_anchor.asset,
                include_logo=False,
                priority=priority,
                recipe_id=locked.recipe_id,
            )
        except Exception:
            # The surrounding transaction rolls back the internal ContentRun as well.
            raise

        sequence_meta = {
            "mode": "anchor_chain",
            "project_id": str(locked.project_id),
            "clip_id": str(locked.pk),
            "clip_position": locked.position,
            "start_anchor_id": str(locked.start_anchor_id),
            "end_anchor_id": str(locked.end_anchor_id),
            "start_asset_id": str(locked.start_anchor.asset_id),
            "end_asset_id": str(locked.end_anchor.asset_id),
            "recipe_id": locked.recipe_id,
            "recipe_version": locked.recipe_version,
        }
        params = deepcopy(generation.parameters or {})
        params["sequence"] = sequence_meta
        MediaGeneration.objects.filter(pk=generation.pk).update(parameters=params)
        generation.parameters = params

        version = attach_generation_to_clip(locked, generation)
        params["sequence"]["version_id"] = str(version.pk)
        params["sequence"]["version_number"] = version.version_number
        MediaGeneration.objects.filter(pk=generation.pk).update(parameters=params)

        if not locked.selected_version_id and locked.status != "review":
            SequenceClip.objects.filter(pk=locked.pk).update(status="review")
        return SequenceClipVersion.objects.select_related("generation", "clip").get(pk=version.pk)


def regenerate_anchor_chain_clip(
    clip: SequenceClip,
    *,
    brief: str = "",
    priority: str = "balanced",
    token=None,
) -> SequenceClipVersion:
    """Create another non-destructive candidate from the clip's current canonical anchors."""
    return prepare_anchor_chain_version(
        clip,
        brief=brief,
        priority=priority,
        token=token,
    )


def preview_anchor_chain_version(version: SequenceClipVersion) -> SequenceClipVersion:
    """Run the existing non-billable provider estimate for an exact anchor-chain candidate."""
    _assert_generation_matches_current_anchors(version)
    generation = preview_job(MediaGeneration.objects.get(pk=version.generation_id))
    version = _sync_clip_version_provenance(version)
    clip = SequenceClip.objects.get(pk=version.clip_id)
    if not clip.selected_version_id and clip.status != "review":
        SequenceClip.objects.filter(pk=clip.pk).update(status="review")
    return version



def promote_output_chain_final_frame(version: SequenceClipVersion) -> SequenceAnchor:
    """Explicitly replace the clip's end/next-start anchor with the selected output's final frame.

    This is local media derivation only: no provider call and no paid generation.
    Locked anchors or already-selected downstream clips fail closed.
    """
    candidate = (
        SequenceClipVersion.objects.select_related(
            "clip__project__company",
            "clip__end_anchor__asset",
            "generation",
        )
        .get(pk=version.pk)
    )
    clip = candidate.clip
    target = clip.end_anchor

    existing_meta = target.source_metadata if isinstance(target.source_metadata, dict) else {}
    if (
        target.source_type == "output_chain"
        and target.source_clip_version_id == candidate.pk
        and existing_meta.get("frame_selector") == "final"
    ):
        return target

    if clip.selected_version_id != candidate.pk:
        raise SequenceError("Välj clip-versionen innan dess slutbild kan användas i Output Chain.")
    if candidate.generation.status != "completed":
        raise SequenceError("Endast en färdig videogeneration kan användas i Output Chain.")
    if candidate.status not in {"ready", "selected"}:
        raise SequenceError("Clip-versionen är inte redo för Output Chain.")
    if target.locked:
        raise SequenceError("Nästa anchor är låst. Lås upp den explicit innan Output Chain-promotion.")
    if not target.starting_clips.filter(project_id=clip.project_id).exists():
        raise SequenceError("Clipets slut-anchor används inte som start-anchor för något efterföljande clip.")
    if target.starting_clips.filter(project_id=clip.project_id, selected_version__isnull=False).exists():
        raise SequenceError("Ett efterföljande clip har redan en vald version. Byt inte dess canonical start-anchor i efterhand.")

    _assert_generation_matches_current_anchors(candidate)

    video_assets = list(
        candidate.generation.assets.filter(kind="video", company_id=clip.project.company_id).order_by("created_at", "pk")[:2]
    )
    if len(video_assets) != 1:
        raise SequenceError("Output Chain kräver exakt en sparad video för den valda clip-versionen.")
    source_video = video_assets[0]
    if source_video.expires_at and source_video.expires_at <= timezone.now():
        raise SequenceError("Källvideon har gått ut och kan inte användas för Output Chain.")

    frame_png, frame_meta = extract_video_frame_png(source_video, selector="final")
    derived = store_derived_image(
        clip.project.company,
        frame_png,
        generation=candidate.generation,
        alt_text=f"Output Chain slutbild från {clip.label or 'clip'}",
        brief=f"Final frame derived from sequence clip {clip.pk}, version {candidate.version_number}",
    )
    provenance = {
        "mode": "output_chain",
        "frame_selector": "final",
        "source_project_id": str(clip.project_id),
        "source_clip_id": str(clip.pk),
        "source_clip_version_id": str(candidate.pk),
        "source_generation_id": str(candidate.generation_id),
        "source_video_asset_id": str(source_video.pk),
        "source_video_sha256": source_video.sha256,
        "previous_anchor_asset_id": str(target.asset_id),
        "derived_asset_id": str(derived.pk),
        "derived_asset_sha256": derived.sha256,
        "frame": frame_meta,
    }

    try:
        with transaction.atomic():
            locked_clip = SequenceClip.objects.select_for_update().get(pk=clip.pk)
            locked_target = SequenceAnchor.objects.select_for_update().get(pk=target.pk)
            locked_version = SequenceClipVersion.objects.select_for_update().select_related("generation").get(pk=candidate.pk)

            locked_meta = locked_target.source_metadata if isinstance(locked_target.source_metadata, dict) else {}
            if (
                locked_target.source_type == "output_chain"
                and locked_target.source_clip_version_id == locked_version.pk
                and locked_meta.get("frame_selector") == "final"
            ):
                remove_asset(derived)
                return locked_target

            if locked_clip.selected_version_id != locked_version.pk:
                raise SequenceError("Den valda source-versionen ändrades under Output Chain-promotion.")
            if locked_version.generation.status != "completed":
                raise SequenceError("Source-generationen är inte längre färdig.")
            if locked_target.locked:
                raise SequenceError("Nästa anchor låstes under Output Chain-promotion.")
            if locked_target.asset_id != target.asset_id:
                raise SequenceError("Nästa anchor ändrades under Output Chain-promotion.")
            if locked_target.pk != locked_clip.end_anchor_id:
                raise SequenceError("Clipets slut-anchor ändrades under Output Chain-promotion.")
            if not locked_target.starting_clips.filter(project_id=locked_clip.project_id).exists():
                raise SequenceError("Nästa clip saknas för Output Chain.")
            if locked_target.starting_clips.filter(
                project_id=locked_clip.project_id, selected_version__isnull=False
            ).exists():
                raise SequenceError("Ett efterföljande clip fick en vald version under Output Chain-promotion.")

            locked_target.asset = derived
            locked_target.source_type = "output_chain"
            locked_target.source_clip_version = locked_version
            locked_target.source_metadata = provenance
            locked_target.save(
                update_fields=[
                    "asset",
                    "source_type",
                    "source_clip_version",
                    "source_metadata",
                    "updated_at",
                ]
            )
            locked_target.starting_clips.filter(
                project_id=locked_clip.project_id,
                selected_version__isnull=True,
            ).update(status="review")
        return SequenceAnchor.objects.select_related("asset", "source_clip_version").get(pk=target.pk)
    except Exception:
        try:
            if MediaAsset.objects.filter(pk=derived.pk).exists():
                remove_asset(derived)
        except Exception:
            pass
        raise

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
    "prepare_anchor_chain_version",
    "regenerate_anchor_chain_clip",
    "preview_anchor_chain_version",
    "promote_output_chain_final_frame",
]
