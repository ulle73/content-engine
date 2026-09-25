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
from .creative_director import analyze_complexity, eligible_models, parse_brief, route_model
from .creative_recipes import get_recipe
from .media import create_job, extract_video_frame_png, preview_job, remove_asset, store_derived_image
from .media_references import add_generation_reference, reference_asset, serialize_generation_references
from .models import (
    Company,
    ContentRun,
    MediaAsset,
    MediaGeneration,
    SequenceAnchor,
    SequenceAnchorGenerationTarget,
    SequenceAnchorRevision,
    SequenceBridge,
    SequenceBridgeVersion,
    SequenceClip,
    SequenceClipVersion,
    SequenceProject,
)


class SequenceError(ValueError):
    pass


def _preserve_anchor_asset(asset: MediaAsset) -> MediaAsset:
    current = MediaAsset.objects.select_for_update().get(pk=asset.pk)
    fields = []
    if current.expires_at is not None:
        current.expires_at = None
        fields.append("expires_at")
    if current.used_at is None:
        current.used_at = timezone.now()
        fields.append("used_at")
    if fields:
        current.save(update_fields=fields)
    return current


def _record_anchor_revision(anchor: SequenceAnchor, *, reason: str, created_by=None) -> SequenceAnchorRevision:
    latest = anchor.revisions.aggregate(value=Max("revision_number"))["value"] or 0
    return SequenceAnchorRevision.objects.create(
        anchor=anchor,
        revision_number=latest + 1,
        asset=anchor.asset,
        source_type=anchor.source_type,
        source_clip_version=anchor.source_clip_version,
        source_metadata=deepcopy(anchor.source_metadata or {}),
        reason=(reason or "changed")[:40],
        created_by=created_by,
    )


def _ensure_anchor_revision(anchor: SequenceAnchor) -> SequenceAnchorRevision:
    existing = anchor.revisions.order_by("revision_number").first()
    if existing:
        return existing
    return _record_anchor_revision(anchor, reason="baseline")


def _anchor_dependent_versions(anchor: SequenceAnchor):
    clip_ids = set(anchor.starting_clips.values_list("pk", flat=True)) | set(
        anchor.ending_clips.values_list("pk", flat=True)
    )
    bridge_ids = set(anchor.starting_bridges.values_list("pk", flat=True)) | set(
        anchor.ending_bridges.values_list("pk", flat=True)
    )
    clip_versions = SequenceClipVersion.objects.filter(clip_id__in=clip_ids).exclude(status="stale")
    bridge_versions = SequenceBridgeVersion.objects.filter(bridge_id__in=bridge_ids).exclude(status="stale")
    return clip_versions, bridge_versions


def anchor_change_impact(anchor: SequenceAnchor) -> dict:
    clip_versions, bridge_versions = _anchor_dependent_versions(anchor)
    selected_clip_ids = set(
        SequenceClip.objects.filter(
            selected_version_id__in=clip_versions.values_list("pk", flat=True)
        ).values_list("pk", flat=True)
    )
    selected_bridge_ids = set(
        SequenceBridge.objects.filter(
            selected_version_id__in=bridge_versions.values_list("pk", flat=True)
        ).values_list("pk", flat=True)
    )
    return {
        "clip_versions": clip_versions.count(),
        "bridge_versions": bridge_versions.count(),
        "total_versions": clip_versions.count() + bridge_versions.count(),
        "selected_segments": len(selected_clip_ids) + len(selected_bridge_ids),
    }


def _mark_anchor_dependents_stale(anchor: SequenceAnchor) -> dict:
    clip_versions, bridge_versions = _anchor_dependent_versions(anchor)
    clip_version_ids = list(clip_versions.values_list("pk", flat=True))
    bridge_version_ids = list(bridge_versions.values_list("pk", flat=True))

    selected_clips = list(
        SequenceClip.objects.select_for_update().filter(selected_version_id__in=clip_version_ids)
    )
    selected_bridges = list(
        SequenceBridge.objects.select_for_update().filter(selected_version_id__in=bridge_version_ids)
    )
    if clip_version_ids:
        SequenceClipVersion.objects.filter(pk__in=clip_version_ids).update(status="stale")
    if bridge_version_ids:
        SequenceBridgeVersion.objects.filter(pk__in=bridge_version_ids).update(status="stale")
    if selected_clips:
        SequenceClip.objects.filter(pk__in=[item.pk for item in selected_clips]).update(
            selected_version=None, status="review", updated_at=timezone.now()
        )
    if selected_bridges:
        SequenceBridge.objects.filter(pk__in=[item.pk for item in selected_bridges]).update(
            selected_version=None, status="review", updated_at=timezone.now()
        )
    return {
        "clip_versions": len(clip_version_ids),
        "bridge_versions": len(bridge_version_ids),
        "selected_segments": len(selected_clips) + len(selected_bridges),
    }


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
    created_by=None,
) -> SequenceAnchor:
    if position < 0:
        raise SequenceError("Anchor-positionen kan inte vara negativ.")
    _validate_anchor_asset(project, asset)
    if source_clip_version and source_clip_version.clip.project_id != project.pk:
        raise SequenceError("Anchor-källan måste tillhöra samma sequence-projekt.")
    try:
        with transaction.atomic():
            persistent_asset = _preserve_anchor_asset(asset)
            anchor = SequenceAnchor.objects.create(
                project=project,
                position=position,
                asset=persistent_asset,
                label=label,
                role=role,
                locked=locked,
                source_type=source_type,
                source_clip_version=source_clip_version,
                source_metadata=deepcopy(source_metadata or {}),
                notes=notes,
            )
            _record_anchor_revision(anchor, reason="created", created_by=created_by)
            return anchor
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



def change_anchor_asset(
    anchor: SequenceAnchor,
    asset: MediaAsset,
    *,
    source_type: str = "existing",
    source_clip_version: SequenceClipVersion | None = None,
    source_metadata: dict | None = None,
    reason: str = "replaced",
    created_by=None,
    confirm_stale: bool = False,
) -> SequenceAnchor:
    """F2-safe anchor replacement with revision history and explicit stale invalidation."""
    with transaction.atomic():
        current = (
            SequenceAnchor.objects.select_for_update()
            .select_related("project", "asset")
            .get(pk=anchor.pk)
        )
        if current.locked:
            raise SequenceError("Ankaret är låst. Lås upp det explicit innan du byter bild.")
        _validate_anchor_asset(current.project, asset)
        if source_clip_version and source_clip_version.clip.project_id != current.project_id:
            raise SequenceError("Anchor-källan måste tillhöra samma sequence-projekt.")
        if current.asset_id == asset.pk:
            return current

        impact = anchor_change_impact(current)
        if impact["total_versions"] and not confirm_stale:
            raise SequenceError(
                f"Bytet gör {impact['total_versions']} befintliga clip/bridge-versioner inaktuella. "
                "Bekräfta ändringen för att behålla dem som historik och markera dem stale."
            )

        _ensure_anchor_revision(current)
        stale = _mark_anchor_dependents_stale(current) if impact["total_versions"] else {
            "clip_versions": 0, "bridge_versions": 0, "selected_segments": 0
        }
        persistent_asset = _preserve_anchor_asset(asset)
        metadata = deepcopy(source_metadata or {})
        if stale["clip_versions"] or stale["bridge_versions"]:
            metadata["staled_versions"] = {
                "clip_versions": stale["clip_versions"],
                "bridge_versions": stale["bridge_versions"],
                "selected_segments": stale["selected_segments"],
            }
        current.asset = persistent_asset
        current.source_type = source_type
        current.source_clip_version = source_clip_version
        current.source_metadata = metadata
        current.save(
            update_fields=[
                "asset", "source_type", "source_clip_version", "source_metadata", "updated_at"
            ]
        )
        _record_anchor_revision(current, reason=reason, created_by=created_by)
    return SequenceAnchor.objects.select_related("asset").get(pk=anchor.pk)


def restore_anchor_revision(
    anchor: SequenceAnchor,
    revision: SequenceAnchorRevision,
    *,
    created_by=None,
    confirm_stale: bool = False,
) -> SequenceAnchor:
    if revision.anchor_id != anchor.pk:
        raise SequenceError("Anchor-versionen tillhör ett annat anchor.")
    metadata = deepcopy(revision.source_metadata or {})
    metadata["restored_from_revision_id"] = str(revision.pk)
    metadata["restored_from_revision_number"] = revision.revision_number
    return change_anchor_asset(
        anchor,
        revision.asset,
        source_type=revision.source_type,
        source_clip_version=revision.source_clip_version,
        source_metadata=metadata,
        reason="restored",
        created_by=created_by,
        confirm_stale=confirm_stale,
    )


def next_anchor_position(project: SequenceProject) -> int:
    value = project.anchors.aggregate(value=Max("position"))["value"]
    return 0 if value is None else value + 1


def _planned_anchor_spec(project: SequenceProject, position: int) -> dict:
    plan = project.plan if isinstance(project.plan, dict) else {}
    if plan.get("planner_id") != "sequence_planner" or not isinstance(plan.get("anchors"), list):
        raise SequenceError("Projektet har ingen Sequence Planner-plan att materialisera.")
    try:
        position = int(position)
    except (TypeError, ValueError) as exc:
        raise SequenceError("Planerad anchor-position är ogiltig.") from exc
    spec = next(
        (
            item for item in plan["anchors"]
            if isinstance(item, dict) and int(item.get("position", -1)) == position
        ),
        None,
    )
    if spec is None:
        raise SequenceError(f"K{position} finns inte i den aktuella Sequence-planen.")
    return deepcopy(spec)


def sequence_plan_anchor_readiness(project: SequenceProject) -> dict:
    plan = project.plan if isinstance(project.plan, dict) else {}
    planned = []
    if plan.get("planner_id") == "sequence_planner" and isinstance(plan.get("anchors"), list):
        for item in plan["anchors"]:
            if isinstance(item, dict):
                try:
                    planned.append(int(item["position"]))
                except (KeyError, TypeError, ValueError):
                    continue
    planned = sorted(set(position for position in planned if position >= 0))
    if not planned:
        return {
            "planned": False,
            "ready": True,
            "required_positions": [],
            "materialized_positions": [],
            "missing_positions": [],
        }
    materialized = sorted(
        set(project.anchors.filter(position__in=planned).values_list("position", flat=True))
    )
    missing = [position for position in planned if position not in materialized]
    return {
        "planned": True,
        "ready": not missing,
        "required_positions": planned,
        "materialized_positions": materialized,
        "missing_positions": missing,
    }


def _plan_anchor_metadata(project: SequenceProject, spec: dict, *, mode: str, asset: MediaAsset | None = None) -> dict:
    return {
        "mode": mode,
        "plan_revision": project.plan_revision,
        "plan_anchor_position": int(spec["position"]),
        "plan_anchor_label": str(spec.get("label") or "")[:120],
        "plan_anchor_description": str(spec.get("description") or "")[:1200],
        "reference_requirements": list(spec.get("reference_requirements") or []),
        **({"asset_id": str(asset.pk)} if asset else {}),
    }


def materialize_planned_anchor_asset(
    project: SequenceProject,
    asset: MediaAsset,
    *,
    position: int,
    source_type: str,
    created_by=None,
    confirm_stale: bool = False,
) -> SequenceAnchor:
    spec = _planned_anchor_spec(project, position)
    _validate_anchor_asset(project, asset)
    metadata = _plan_anchor_metadata(project, spec, mode=f"planned_{source_type}", asset=asset)
    existing = project.anchors.filter(position=int(spec["position"])).first()
    if existing:
        if existing.asset_id == asset.pk:
            return existing
        return change_anchor_asset(
            existing,
            asset,
            source_type=source_type,
            source_metadata=metadata,
            reason=f"plan_{source_type}"[:40],
            created_by=created_by,
            confirm_stale=confirm_stale,
        )
    return add_anchor(
        project,
        asset,
        position=int(spec["position"]),
        label=str(spec.get("label") or "")[:120],
        role=str(spec.get("role") or "")[:40],
        source_type=source_type,
        source_metadata=metadata,
        created_by=created_by,
    )


def _planned_anchor_generation_brief(project: SequenceProject, spec: dict) -> str:
    requirements = set(spec.get("reference_requirements") or [])
    sections = [
        str(spec.get("description") or "").strip(),
        f"Create canonical sequence anchor K{int(spec['position'])}.",
        "Keep the composition strong enough to be reused as an exact visual anchor for connected video clips.",
    ]
    note = str(spec.get("reference_note") or "").strip()
    if note:
        sections.append("Reference intent: " + note)
    if "product" in requirements:
        sections.append(
            "Preserve the exact product identity, geometry, proportions, colors, labels, logos and visible text from the supplied product reference. Do not invent or alter product or brand details."
        )
    if "company" in requirements:
        sections.append(
            "Preserve exact company branding and logo identity from the supplied company reference or official logo. Do not invent or alter company marks or visible brand text."
        )
    result = " ".join(section for section in sections if section).strip()
    if not result or len(result) > 6000:
        raise SequenceError("Den planerade anchor-briefen är tom eller längre än 6000 tecken.")
    return result


def prepare_planned_anchor_generation(
    project: SequenceProject,
    *,
    position: int,
    reference_asset: MediaAsset | None = None,
    shape: str = "portrait",
    count: int = 2,
    priority: str = "balanced",
    token=None,
    created_by=None,
) -> SequenceAnchorGenerationTarget:
    project = SequenceProject.objects.select_related("company", "author", "company__official_logo").get(pk=project.pk)
    spec = _planned_anchor_spec(project, position)
    requirements = set(spec.get("reference_requirements") or [])
    if reference_asset:
        _validate_anchor_asset(project, reference_asset)
    if "product" in requirements and not reference_asset:
        raise SequenceError("Krävd produktreferens saknas. Välj en riktig produktbild från Media före AI-generation.")
    if "company" in requirements and not project.company.official_logo_id and not reference_asset:
        raise SequenceError("Krävd företagsreferens saknas. Ladda upp officiell logga eller välj en företagsbild från Media.")
    if {"company", "product"} <= requirements and not project.company.official_logo_id:
        raise SequenceError(
            "Den här anchorn kräver både företags- och produktreferens. Lägg in officiell logga så produktbilden kan användas som exakt AI-referens."
        )

    target_anchor = project.anchors.filter(position=int(spec["position"])).first()
    target = prepare_anchor_image_generation(
        project,
        brief=_planned_anchor_generation_brief(project, spec),
        target_anchor=target_anchor,
        target_label=str(spec.get("label") or "")[:120],
        target_role=str(spec.get("role") or "")[:40],
        target_position=int(spec["position"]),
        plan_revision=project.plan_revision,
        plan_anchor_snapshot=spec,
        source=reference_asset,
        include_logo="company" in requirements and bool(project.company.official_logo_id),
        shape=shape,
        count=count,
        priority=priority,
        token=token,
        created_by=created_by,
    )
    if reference_asset:
        if "product" in requirements:
            add_generation_reference(target.generation, reference_asset, ReferenceRole.product_reference)
        if "company" in requirements and not project.company.official_logo_id:
            add_generation_reference(target.generation, reference_asset, ReferenceRole.style_reference)
    return target


def _anchor_generation_run(
    project: SequenceProject,
    *,
    brief: str,
    mode: str,
    anchor=None,
    target_position: int | None = None,
    plan_revision: int | None = None,
) -> ContentRun:
    return ContentRun.objects.create(
        workspace=project.company,
        author=project.author or project.company.owner,
        context={
            "profile": project.company.profile,
            "voice": project.company.voice,
            "current": project.company.current,
            "sequence": {
                "mode": "anchor_generation",
                "project_id": str(project.pk),
                "target_mode": mode,
                "target_anchor_id": str(anchor.pk) if anchor else None,
                "target_position": target_position,
                "plan_revision": plan_revision,
            },
        },
        ideas=[{"title": (anchor.label if anchor else project.title) or "Sequence anchor", "photo_brief": brief}],
        selected=0,
        draft={"instagram": brief[:1800], "photo_brief": brief},
        model="sequence-anchor-generation",
    )


def prepare_anchor_image_generation(
    project: SequenceProject,
    *,
    brief: str,
    target_anchor: SequenceAnchor | None = None,
    target_label: str = "",
    target_role: str = "",
    target_position: int | None = None,
    plan_revision: int | None = None,
    plan_anchor_snapshot: dict | None = None,
    source: MediaAsset | None = None,
    include_logo: bool = False,
    shape: str = "portrait",
    count: int = 2,
    priority: str = "balanced",
    token=None,
    created_by=None,
) -> SequenceAnchorGenerationTarget:
    brief = (brief or "").strip()
    if not brief or len(brief) > 6000:
        raise SequenceError("Beskriv anchor-bilden med högst 6000 tecken.")
    if target_anchor and target_anchor.project_id != project.pk:
        raise SequenceError("Mål-ankaret måste tillhöra sequence-projektet.")
    if target_position is not None and target_position < 0:
        raise SequenceError("Målpositionen kan inte vara negativ.")
    if target_anchor and target_position is not None and target_anchor.position != target_position:
        raise SequenceError("Mål-ankaret ligger inte på den planerade positionen.")
    if source:
        _validate_anchor_asset(project, source)
    if shape not in {"portrait", "square", "landscape"}:
        raise SequenceError("Välj ett giltigt bildformat.")
    if count not in {1, 2, 3, 4}:
        raise SequenceError("Välj mellan 1 och 4 bildalternativ.")
    job_token = _normalize_generation_token(token)

    existing = SequenceAnchorGenerationTarget.objects.filter(generation_id=job_token).first()
    if existing:
        if existing.project_id != project.pk:
            raise SequenceError("Idempotency-token används redan i ett annat sequence-projekt.")
        return existing
    if MediaGeneration.objects.filter(pk=job_token).exists():
        raise SequenceError("Idempotency-token används redan av en annan mediageneration.")

    with transaction.atomic():
        run = _anchor_generation_run(
            project,
            brief=brief,
            mode="replace" if target_anchor else "create",
            anchor=target_anchor,
            target_position=target_position,
            plan_revision=plan_revision,
        )
        job = create_job(
            run,
            token=job_token,
            kind="image",
            brief=brief,
            count=count,
            shape=shape,
            source=source,
            end_source=None,
            include_logo=include_logo,
            priority=priority,
        )
        target = SequenceAnchorGenerationTarget.objects.create(
            project=project,
            generation=job,
            mode="replace" if target_anchor else "create",
            target_anchor=target_anchor,
            target_label=(target_anchor.label if target_anchor else target_label)[:120],
            target_role=(target_anchor.role if target_anchor else target_role)[:40],
            target_position=target_position,
            plan_revision=plan_revision,
            plan_anchor_snapshot=deepcopy(plan_anchor_snapshot or {}),
            created_by=created_by or project.author,
        )
        if target_position is not None:
            params = deepcopy(job.parameters or {})
            params["sequence"] = {
                "mode": "planned_anchor",
                "project_id": str(project.pk),
                "target_position": target_position,
                "plan_revision": plan_revision,
                "reference_requirements": list((plan_anchor_snapshot or {}).get("reference_requirements") or []),
            }
            MediaGeneration.objects.filter(pk=job.pk).update(parameters=params)
            job.parameters = params
        preview_job(job)
        return target


def apply_generated_anchor_asset(
    target: SequenceAnchorGenerationTarget,
    asset: MediaAsset,
    *,
    created_by=None,
    confirm_stale: bool = False,
) -> SequenceAnchor:
    with transaction.atomic():
        current = (
            SequenceAnchorGenerationTarget.objects.select_for_update()
            .select_related("project", "generation")
            .get(pk=target.pk)
        )
        if current.applied_anchor_id:
            return current.applied_anchor
        generation = MediaGeneration.objects.select_for_update().get(pk=current.generation_id)
        if generation.status != "completed":
            raise SequenceError("AI-jobbet måste vara klart innan en bild kan användas som anchor.")
        chosen = MediaAsset.objects.select_for_update().get(pk=asset.pk, company=current.project.company)
        if chosen.kind != "image" or chosen.purpose == "logo" or chosen.generation_id != generation.pk:
            raise SequenceError("Bilden måste vara ett färdigt alternativ från just detta AI-jobb.")

        if current.target_position is not None:
            project = SequenceProject.objects.select_for_update().get(pk=current.project_id)
            if project.plan_revision != current.plan_revision:
                raise SequenceError(
                    "Sequence-planen har ändrats sedan AI-anchorn förbereddes. Skapa ett nytt förslag från den aktuella planen."
                )
            spec = _planned_anchor_spec(project, current.target_position)
            if spec != (current.plan_anchor_snapshot or {}):
                raise SequenceError(
                    "Den planerade anchorn har ändrats sedan AI-förslaget skapades. Skapa ett nytt förslag."
                )

        metadata = {
            "mode": "ai_anchor",
            "generation_id": str(generation.pk),
            "provider": generation.provider,
            "asset_sha256": chosen.sha256,
        }
        if current.target_position is not None:
            metadata.update(
                _plan_anchor_metadata(project, current.plan_anchor_snapshot, mode="planned_ai", asset=chosen)
            )
        if current.mode == "replace":
            if not current.target_anchor_id:
                raise SequenceError("AI-jobbets mål-anchor finns inte längre.")
            anchor = change_anchor_asset(
                current.target_anchor,
                chosen,
                source_type="generated",
                source_metadata=metadata,
                reason="ai_generated",
                created_by=created_by,
                confirm_stale=confirm_stale,
            )
        else:
            project = SequenceProject.objects.select_for_update().get(pk=current.project_id)
            position = current.target_position if current.target_position is not None else next_anchor_position(project)
            if current.target_position is not None and project.anchors.filter(position=position).exists():
                raise SequenceError(
                    f"K{position} finns redan. Använd ersättningsflödet i stället för att applicera ett äldre create-förslag."
                )
            anchor = add_anchor(
                project,
                chosen,
                position=position,
                label=current.target_label,
                role=current.target_role,
                source_type="generated",
                source_metadata=metadata,
                created_by=created_by,
            )
        current.applied_anchor = anchor
        current.save(update_fields=["applied_anchor"])
        return anchor


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



def assert_sequence_project_video_ready(project: SequenceProject) -> dict:
    readiness = sequence_plan_anchor_readiness(project)
    if readiness["planned"] and not readiness["ready"]:
        missing = ", ".join(f"K{position}" for position in readiness["missing_positions"])
        raise SequenceError(
            "Alla anchors i den aktuella Sequence-planen måste finnas innan video kan förberedas eller startas. Saknas: "
            + missing
            + "."
        )
    return readiness


def assert_sequence_generation_video_ready(generation: MediaGeneration) -> None:
    if generation.kind != "video":
        return
    sequence_meta = (generation.parameters or {}).get("sequence")
    if not isinstance(sequence_meta, dict) or not sequence_meta.get("project_id"):
        return
    try:
        project = SequenceProject.objects.get(
            pk=sequence_meta["project_id"],
            company_id=generation.run.workspace_id,
        )
    except (SequenceProject.DoesNotExist, ValueError, TypeError) as exc:
        raise SequenceError("Sequence-projektet för videogenerationen finns inte längre.") from exc
    assert_sequence_project_video_ready(project)
    version = SequenceClipVersion.objects.filter(generation_id=generation.pk).first()
    if version:
        _assert_generation_matches_current_anchors(version)


def _clip_routing_brief(
    clip: SequenceClip,
    *,
    brief: str = "",
    priority: str = "balanced",
):
    request = _sequence_generation_brief(clip, brief)
    return parse_brief(
        request,
        kind="video",
        has_reference=True,
        reference_media=["source_asset", ReferenceRole.end_image.value],
        shape="portrait",
        priority=priority,
    )


def available_clip_model_overrides(
    clip: SequenceClip,
    *,
    brief: str = "",
    priority: str = "balanced",
) -> list:
    routing_brief = _clip_routing_brief(clip, brief=brief, priority=priority)
    recipe = get_recipe(clip.recipe_id)
    models = eligible_models(routing_brief, recipe=recipe)
    if routing_brief.duration_seconds:
        models = [
            model for model in models
            if model.request_contract(routing_brief.mode)
            and model.request_contract(routing_brief.mode).supports_duration(routing_brief.duration_seconds)
        ]
    return models


def set_clip_model_override(
    clip: SequenceClip,
    model_override: str,
    *,
    brief: str = "",
    priority: str = "balanced",
) -> SequenceClip:
    override = (model_override or "").strip()
    if len(override) > 120:
        raise SequenceError("Model override får vara högst 120 tecken.")
    if override:
        routing_brief = _clip_routing_brief(clip, brief=brief, priority=priority)
        recipe = get_recipe(clip.recipe_id)
        try:
            route_model(
                routing_brief,
                analyze_complexity(routing_brief),
                recipe=recipe,
                model_override=override,
            )
        except ValueError as exc:
            raise SequenceError("Vald modell stöder inte clipets verifierade krav: " + str(exc)) from exc
    SequenceClip.objects.filter(pk=clip.pk).update(model_override=override, updated_at=timezone.now())
    return SequenceClip.objects.select_related("start_anchor__asset", "end_anchor__asset").get(pk=clip.pk)


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
    current_status = SequenceClipVersion.objects.only("status").get(pk=version.pk).status
    if current_status in {"stale", "rejected"}:
        status = current_status
    elif current_status == "selected" and generation.status == "completed":
        status = "selected"
    else:
        status = (
            "ready" if generation.status == "completed"
            else "failed" if generation.status in {"failed", "nsfw", "canceled", "unknown"}
            else current_status
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



def sync_sequence_generation(generation: MediaGeneration):
    """Synchronize sequence candidate snapshots after the shared media lifecycle changes."""
    clip_version = (
        SequenceClipVersion.objects.select_related("clip", "generation")
        .filter(generation_id=generation.pk)
        .first()
    )
    if clip_version:
        version = _sync_clip_version_provenance(clip_version)
        clip = SequenceClip.objects.get(pk=version.clip_id)
        if clip.selected_version_id == version.pk and version.status == "selected":
            desired = "selected"
        elif clip.selected_version_id:
            desired = clip.status
        elif generation.status in {"starting", "running", "saving"}:
            desired = "generating"
        else:
            desired = "review"
        if clip.status != desired:
            SequenceClip.objects.filter(pk=clip.pk).update(status=desired, updated_at=timezone.now())
        return version

    bridge_version = (
        SequenceBridgeVersion.objects.select_related("bridge", "generation")
        .filter(generation_id=generation.pk)
        .first()
    )
    if bridge_version:
        version = _sync_bridge_version_provenance(bridge_version)
        bridge = SequenceBridge.objects.get(pk=version.bridge_id)
        if bridge.selected_version_id == version.pk and version.status == "selected":
            desired = "selected"
        elif bridge.selected_version_id:
            desired = bridge.status
        else:
            desired = "review"
        if bridge.status != desired:
            SequenceBridge.objects.filter(pk=bridge.pk).update(status=desired, updated_at=timezone.now())
        return version
    return None


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
        _validate_anchor_asset(locked.project, locked.start_anchor.asset)
        _validate_anchor_asset(locked.project, locked.end_anchor.asset)
        assert_sequence_project_video_ready(locked.project)

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
                model_override=locked.model_override,
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
            "model_override": locked.model_override,
            "plan_revision": locked.project.plan_revision if isinstance(locked.project.plan, dict) and locked.project.plan else None,
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
            _record_anchor_revision(locked_target, reason="output_chain")
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



def create_transition_bridge(
    project: SequenceProject,
    left_clip: SequenceClip,
    right_clip: SequenceClip,
    *,
    label: str = "",
    duration_seconds_target: int | None = None,
    aspect_ratio: str = "",
    notes: str = "",
) -> SequenceBridge:
    """Create one logical non-destructive bridge between two existing clips."""
    if left_clip.project_id != project.pk or right_clip.project_id != project.pk:
        raise SequenceError("Båda clips måste tillhöra samma sequence-projekt.")
    if left_clip.pk == right_clip.pk or left_clip.position >= right_clip.position:
        raise SequenceError("Vänster clip måste ligga före höger clip.")

    left = SequenceClip.objects.select_related("end_anchor__asset").get(pk=left_clip.pk)
    right = SequenceClip.objects.select_related("start_anchor__asset").get(pk=right_clip.pk)
    start_anchor = left.end_anchor
    end_anchor = right.start_anchor

    if start_anchor.pk == end_anchor.pk:
        raise SequenceError("Clips delar redan samma canonical anchor och behöver ingen Transition Bridge.")
    if start_anchor.position >= end_anchor.position:
        raise SequenceError("Bridge-starten måste ligga före bridge-slutet.")

    _validate_anchor_asset(project, start_anchor.asset)
    _validate_anchor_asset(project, end_anchor.asset)

    recipe = get_recipe("scroll_transition_bridge")
    if not recipe or "video" not in recipe.kinds:
        raise SequenceError("Trusted scroll_transition_bridge recipe saknas.")

    with transaction.atomic():
        existing = (
            SequenceBridge.objects.select_for_update()
            .filter(project=project, left_clip=left, right_clip=right)
            .first()
        )
        if existing:
            if existing.start_anchor_id != start_anchor.pk or existing.end_anchor_id != end_anchor.pk:
                raise SequenceError("Befintlig bridge matchar inte längre clipens canonical anchors.")
            return existing
        try:
            return SequenceBridge.objects.create(
                project=project,
                left_clip=left,
                right_clip=right,
                start_anchor=start_anchor,
                end_anchor=end_anchor,
                recipe_id=recipe.recipe_id,
                recipe_version=recipe.version,
                label=label,
                duration_seconds_target=duration_seconds_target,
                aspect_ratio=aspect_ratio,
                notes=notes,
            )
        except (IntegrityError, ValidationError, ValueError) as exc:
            raise SequenceError("Transition Bridge kunde inte skapas.") from exc


def _bridge_generation_brief(bridge: SequenceBridge, override: str = "") -> str:
    text = (override or bridge.notes or bridge.label or bridge.project.brief or bridge.project.title).strip()
    if not text:
        text = "Connect the previous clip ending to the next clip opening with the simplest continuous transition."
    suffix = [
        "This generation exists only to bridge two established shots.",
        "Prioritize continuity over spectacle.",
        "Use the supplied START_IMAGE as the exact previous-shot ending and END_IMAGE as the exact next-shot opening.",
    ]
    if bridge.duration_seconds_target:
        suffix.append(f"Duration: {bridge.duration_seconds_target} seconds.")
    if bridge.aspect_ratio:
        suffix.append(f"Aspect ratio: {bridge.aspect_ratio}.")
    result = " ".join([text, *suffix]).strip()
    if len(result) > 6000:
        raise SequenceError("Bridge-briefen blir längre än 6000 tecken.")
    return result


def _bridge_run(bridge: SequenceBridge, *, brief: str) -> ContentRun:
    project = bridge.project
    return ContentRun.objects.create(
        workspace=project.company,
        author=project.author or project.company.owner,
        context={
            "profile": project.company.profile,
            "voice": project.company.voice,
            "current": project.company.current,
            "sequence": {
                "mode": "transition_bridge",
                "project_id": str(project.pk),
                "bridge_id": str(bridge.pk),
                "left_clip_id": str(bridge.left_clip_id),
                "right_clip_id": str(bridge.right_clip_id),
                "start_anchor_id": str(bridge.start_anchor_id),
                "end_anchor_id": str(bridge.end_anchor_id),
            },
        },
        ideas=[{
            "title": bridge.label or f"Bridge {bridge.left_clip.position}→{bridge.right_clip.position}",
            "angle": brief,
        }],
        selected=0,
        draft={"instagram": brief[:1800], "sequence": brief},
        model="sequence-transition-bridge",
    )


def attach_generation_to_bridge(
    bridge: SequenceBridge,
    generation: MediaGeneration,
    *,
    review_notes: str = "",
) -> SequenceBridgeVersion:
    if generation.run.workspace_id != bridge.project.company_id:
        raise SequenceError("Generationens företag matchar inte bridge-projektet.")
    if generation.kind != "video":
        raise SequenceError("Transition Bridge kan bara kopplas till videogenerationer.")
    if hasattr(generation, "sequence_clip_version") or hasattr(generation, "sequence_bridge_version"):
        raise SequenceError("Generationens provenance är redan kopplad till Sequence Engine.")

    creative = (generation.parameters or {}).get("creative") or {}
    recipe = creative.get("recipe") if isinstance(creative, dict) else {}
    recipe = recipe if isinstance(recipe, dict) else {}
    if (recipe.get("recipe_id") or bridge.recipe_id) != "scroll_transition_bridge":
        raise SequenceError("Transition Bridge-generationen måste använda scroll_transition_bridge.")

    with transaction.atomic():
        locked = SequenceBridge.objects.select_for_update().select_related("project").get(pk=bridge.pk)
        latest = locked.versions.aggregate(value=Max("version_number"))["value"] or 0
        status = (
            "ready" if generation.status == "completed"
            else "failed" if generation.status in {"failed", "nsfw", "canceled", "unknown"}
            else "queued"
        )
        return SequenceBridgeVersion.objects.create(
            bridge=locked,
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


def _assert_bridge_generation_matches_current_anchors(version: SequenceBridgeVersion) -> None:
    bridge = (
        SequenceBridge.objects.select_related(
            "left_clip", "right_clip", "start_anchor__asset", "end_anchor__asset"
        )
        .get(pk=version.bridge_id)
    )
    if bridge.start_anchor_id != bridge.left_clip.end_anchor_id:
        raise SequenceError("Bridge-starten matchar inte längre vänster clips end anchor.")
    if bridge.end_anchor_id != bridge.right_clip.start_anchor_id:
        raise SequenceError("Bridge-slutet matchar inte längre höger clips start anchor.")

    generation = MediaGeneration.objects.get(pk=version.generation_id)
    start = reference_asset(generation, ReferenceRole.start_image)
    end = reference_asset(generation, ReferenceRole.end_image)
    if not start or not end:
        raise SequenceError("Bridge-generationen saknar START_IMAGE eller END_IMAGE.")
    if start.pk != bridge.start_anchor.asset_id or end.pk != bridge.end_anchor.asset_id:
        raise SequenceError(
            "Bridge-anchors har ändrats sedan versionen skapades. Förbered en ny bridge-version."
        )


def _sync_bridge_version_provenance(version: SequenceBridgeVersion) -> SequenceBridgeVersion:
    generation = MediaGeneration.objects.get(pk=version.generation_id)
    current_status = SequenceBridgeVersion.objects.only("status").get(pk=version.pk).status
    if current_status in {"stale", "rejected"}:
        status = current_status
    elif current_status == "selected" and generation.status == "completed":
        status = "selected"
    else:
        status = (
            "ready" if generation.status == "completed"
            else "failed" if generation.status in {"failed", "nsfw", "canceled", "unknown"}
            else current_status
        )
    SequenceBridgeVersion.objects.filter(pk=version.pk).update(
        status=status,
        model_id=(generation.parameters or {}).get("model", ""),
        provider_model=(generation.parameters or {}).get("provider_model", ""),
        prompt_snapshot=generation.prompt,
        reference_snapshot=serialize_generation_references(generation),
        usage_snapshot=deepcopy(generation.usage or {}),
        cost_snapshot=_cost_snapshot(generation),
    )
    return SequenceBridgeVersion.objects.select_related("generation", "bridge").get(pk=version.pk)


def prepare_transition_bridge_version(
    bridge: SequenceBridge,
    *,
    brief: str = "",
    priority: str = "balanced",
    token=None,
) -> SequenceBridgeVersion:
    """Prepare a bridge candidate without contacting the provider."""
    job_token = _normalize_generation_token(token)
    existing = (
        SequenceBridgeVersion.objects.filter(generation_id=job_token)
        .select_related("bridge")
        .first()
    )
    if existing:
        if existing.bridge_id != bridge.pk:
            raise SequenceError("Idempotency-token används redan av en annan Transition Bridge.")
        return existing
    if MediaGeneration.objects.filter(pk=job_token).exists():
        raise SequenceError("Idempotency-token används redan av en annan mediageneration.")

    with transaction.atomic():
        locked = (
            SequenceBridge.objects.select_for_update()
            .select_related(
                "project__company",
                "left_clip",
                "right_clip",
                "start_anchor__asset",
                "end_anchor__asset",
            )
            .get(pk=bridge.pk)
        )
        if locked.recipe_id != "scroll_transition_bridge":
            raise SequenceError("Transition Bridge måste använda scroll_transition_bridge.")
        if locked.start_anchor_id != locked.left_clip.end_anchor_id:
            raise SequenceError("Bridge-starten matchar inte vänster clips canonical end anchor.")
        if locked.end_anchor_id != locked.right_clip.start_anchor_id:
            raise SequenceError("Bridge-slutet matchar inte höger clips canonical start anchor.")
        _validate_anchor_asset(locked.project, locked.start_anchor.asset)
        _validate_anchor_asset(locked.project, locked.end_anchor.asset)

        request = _bridge_generation_brief(locked, brief)
        run = _bridge_run(locked, brief=request)
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
            recipe_id="scroll_transition_bridge",
        )

        sequence_meta = {
            "mode": "transition_bridge",
            "project_id": str(locked.project_id),
            "bridge_id": str(locked.pk),
            "left_clip_id": str(locked.left_clip_id),
            "right_clip_id": str(locked.right_clip_id),
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

        version = attach_generation_to_bridge(locked, generation)
        params["sequence"]["version_id"] = str(version.pk)
        params["sequence"]["version_number"] = version.version_number
        MediaGeneration.objects.filter(pk=generation.pk).update(parameters=params)

        if not locked.selected_version_id and locked.status != "review":
            SequenceBridge.objects.filter(pk=locked.pk).update(status="review")
        return SequenceBridgeVersion.objects.select_related("generation", "bridge").get(pk=version.pk)


def regenerate_transition_bridge(
    bridge: SequenceBridge,
    *,
    brief: str = "",
    priority: str = "balanced",
    token=None,
) -> SequenceBridgeVersion:
    return prepare_transition_bridge_version(
        bridge,
        brief=brief,
        priority=priority,
        token=token,
    )


def preview_transition_bridge_version(version: SequenceBridgeVersion) -> SequenceBridgeVersion:
    """Run the existing non-billable estimate path for an exact bridge candidate."""
    _assert_bridge_generation_matches_current_anchors(version)
    preview_job(MediaGeneration.objects.get(pk=version.generation_id))
    version = _sync_bridge_version_provenance(version)
    bridge = SequenceBridge.objects.get(pk=version.bridge_id)
    if not bridge.selected_version_id and bridge.status != "review":
        SequenceBridge.objects.filter(pk=bridge.pk).update(status="review")
    return version


def select_transition_bridge_version(
    bridge: SequenceBridge,
    version: SequenceBridgeVersion,
) -> SequenceBridge:
    with transaction.atomic():
        locked = SequenceBridge.objects.select_for_update().get(pk=bridge.pk)
        selected = (
            SequenceBridgeVersion.objects.select_for_update()
            .select_related("generation")
            .get(pk=version.pk)
        )
        if selected.bridge_id != locked.pk:
            raise SequenceError("Bridge-versionen tillhör en annan Transition Bridge.")
        if selected.generation.status != "completed" or selected.status in {"failed", "rejected", "stale"}:
            raise SequenceError("Endast en färdig bridge-kandidat kan väljas.")
        previous_id = locked.selected_version_id
        if previous_id and previous_id != selected.pk:
            SequenceBridgeVersion.objects.filter(pk=previous_id, status="selected").update(status="ready")
        SequenceBridgeVersion.objects.filter(pk=selected.pk).update(status="selected")
        locked.selected_version = selected
        locked.status = "selected"
        locked.save(update_fields=["selected_version", "status", "updated_at"])
    return SequenceBridge.objects.select_related("selected_version").get(pk=bridge.pk)


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
    if hasattr(generation, "sequence_clip_version") or hasattr(generation, "sequence_bridge_version"):
        raise SequenceError("Generationens provenance är redan kopplad till Sequence Engine.")

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
        if selected.generation.status != "completed" or selected.status in {"failed", "rejected", "stale"}:
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
    bridges = list(
        project.bridges.select_related(
            "left_clip", "right_clip", "start_anchor", "end_anchor", "selected_version"
        ).order_by("created_at")
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
        "bridges": [
            {
                "id": str(bridge.pk),
                "left_clip_id": str(bridge.left_clip_id),
                "right_clip_id": str(bridge.right_clip_id),
                "start_anchor_id": str(bridge.start_anchor_id),
                "end_anchor_id": str(bridge.end_anchor_id),
                "recipe_id": bridge.recipe_id,
                "recipe_version": bridge.recipe_version,
                "selected_version_id": str(bridge.selected_version_id) if bridge.selected_version_id else None,
            }
            for bridge in bridges
        ],
    }


__all__ = [
    "SequenceError",
    "create_sequence_project",
    "add_anchor",
    "set_anchor_locked",
    "replace_anchor_asset",
    "change_anchor_asset",
    "restore_anchor_revision",
    "anchor_change_impact",
    "next_anchor_position",
    "prepare_anchor_image_generation",
    "prepare_planned_anchor_generation",
    "materialize_planned_anchor_asset",
    "sequence_plan_anchor_readiness",
    "assert_sequence_project_video_ready",
    "assert_sequence_generation_video_ready",
    "apply_generated_anchor_asset",
    "create_clip",
    "attach_generation_to_clip",
    "select_clip_version",
    "reject_clip_version",
    "sequence_snapshot",
    "available_clip_model_overrides",
    "set_clip_model_override",
    "sync_sequence_generation",
    "prepare_anchor_chain_version",
    "regenerate_anchor_chain_clip",
    "preview_anchor_chain_version",
    "promote_output_chain_final_frame",
    "create_transition_bridge",
    "attach_generation_to_bridge",
    "prepare_transition_bridge_version",
    "regenerate_transition_bridge",
    "preview_transition_bridge_version",
    "select_transition_bridge_version",
]
