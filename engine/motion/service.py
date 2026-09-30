"""Same goal-oriented operations for browser and MCP, using the existing action ledger."""

from __future__ import annotations
import hashlib
import json
import uuid
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from engine.models import Company, ContentRun, MediaAsset, MediaGeneration
from engine.operator_common import begin_action, finish_action
from .models import MotionProject, MotionRevision, MotionAssetReference, MotionRender
from .schema import asset_ids, spec_hash, validate_spec
from .brand import snapshot

ACTIVE = ("queued", "running", "saving")


def _owner(company, user):
    if company.owner_id != user.pk:
        raise ValueError("F\u00f6retaget tillh\u00f6r inte anv\u00e4ndaren.")


def get_project(company, project_id, *, lock=False):
    try:
        qs = MotionProject.objects.select_for_update(of=("self",)) if lock else MotionProject.objects
        project = qs.select_related("run", "company", "approved_preview").filter(company=company, pk=project_id).first()
    except (ValidationError, ValueError):
        project = None
    if not project:
        raise ValueError("Motion-projektet finns inte i detta f\u00f6retag.")
    return project


def get_render(company, render_id, *, lock=False):
    try:
        qs = MotionRender.objects.select_for_update(of=("self",)) if lock else MotionRender.objects
        job = (
            qs.select_related("generation", "revision__project__company", "output_asset")
            .filter(pk=render_id, revision__project__company=company)
            .first()
        )
    except (ValueError, ValidationError):
        job = None
    if not job:
        raise ValueError("Renderjobbet finns inte i detta f\u00f6retag.")
    return job


def _revision(project, spec, number, brand=None):
    spec = validate_spec(spec)
    brand = brand or snapshot(project.company, spec["brand_id"])
    needed = asset_ids(spec)
    if brand.get("logo_asset_id"):
        needed.add(brand["logo_asset_id"])
    assets = list(MediaAsset.objects.select_for_update().filter(company=project.company, pk__in=needed))
    if len(assets) != len(needed):
        raise ValueError("Alla mediefiler m\u00e5ste finnas i projektets f\u00f6retag.")
    by_id = {str(a.id): a for a in assets}
    for asset in assets:
        if asset.expires_at and asset.expires_at <= timezone.now():
            raise ValueError("En mediefil har g\u00e5tt ut. V\u00e4lj en tillg\u00e4nglig fil.")
    for scene in spec["scenes"]:
        for key in ("asset_id", "secondary_asset_id"):
            aid = scene["props"].get(key)
            if aid and by_id[aid].kind not in {"image", "video"}:
                raise ValueError("Scenmedia m\u00e5ste vara bild eller video.")
    audio_id = spec["audio"].get("music_asset_id")
    if audio_id and by_id[audio_id].kind not in {"audio", "video"}:
        raise ValueError("Musik m\u00e5ste vara ljud eller en video med ljudsp\u00e5r.")
    end_id = spec.get("end_card_asset_id")
    if end_id and by_id[end_id].kind != "video":
        raise ValueError("Slutvideon m\u00e5ste vara en video.")
    digest = hashlib.sha256(
        json.dumps(
            {"spec_hash": spec_hash(spec), "brand": brand, "assets": {str(a.id): a.sha256 for a in assets}},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    revision = MotionRevision.objects.create(project=project, number=number, spec=spec, spec_hash=digest, brand=brand)
    MotionAssetReference.objects.bulk_create(
        [MotionAssetReference(revision=revision, asset=a, sha256=a.sha256) for a in assets]
    )
    # Retain inputs while an immutable revision references them. Deletion is protected by FK and remove_asset.
    MediaAsset.objects.filter(pk__in=needed).update(expires_at=None)
    return revision


@transaction.atomic
def create_project(company, user, *, title, spec, key):
    _owner(company, user)
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise ValueError("Ange ett projektnamn p\u00e5 1\u2013160 tecken.")
    spec = validate_spec(spec)
    Company.objects.select_for_update().get(pk=company.pk)
    action, new = begin_action(company, user, action="motion_create", key=key, payload={"title": title, "spec": spec})
    if not new:
        return get_project(company, action.result["project_id"])
    run = ContentRun.objects.create(
        workspace=company,
        author=user,
        model="motion-engine-v1",
        context={"motion": True},
        ideas=[],
        draft={"instagram": "", "facebook": "", "photo_brief": title},
    )
    project = MotionProject.objects.create(company=company, run=run, title=title.strip())
    _revision(project, spec, 1)
    finish_action(action, result={"project_id": str(project.id)})
    return project


@transaction.atomic
def update_project(company, user, project_id, *, spec, expected_revision, key):
    _owner(company, user)
    spec = validate_spec(spec)
    Company.objects.select_for_update().get(pk=company.pk)
    action, new = begin_action(
        company,
        user,
        action="motion_update",
        key=key,
        payload={"project_id": str(project_id), "spec": spec, "expected_revision": expected_revision},
    )
    if not new:
        return get_project(company, action.result["project_id"])
    project = get_project(company, project_id, lock=True)
    if type(expected_revision) is not int or project.current_revision != expected_revision:
        raise ValueError("Projektet har \u00e4ndrats. H\u00e4mta senaste version innan du sparar.")
    _revision(project, spec, expected_revision + 1)
    project.current_revision += 1
    project.approved_preview = None
    project.save(update_fields=["current_revision", "approved_preview", "updated_at"])
    finish_action(action, result={"project_id": str(project.id), "revision": project.current_revision})
    return project


@transaction.atomic
def queue_render(company, user, project_id, *, mode, expected_revision, key):
    _owner(company, user)
    if mode not in {"preview", "final"}:
        raise ValueError("V\u00e4lj preview eller final.")
    Company.objects.select_for_update().get(pk=company.pk)
    action, new = begin_action(
        company,
        user,
        action="motion_render",
        key=key,
        payload={"project_id": str(project_id), "mode": mode, "expected_revision": expected_revision},
    )
    if not new:
        return get_render(company, action.result["render_id"])
    project = get_project(company, project_id, lock=True)
    if type(expected_revision) is not int or project.current_revision != expected_revision:
        raise ValueError("Projektet har \u00e4ndrats. H\u00e4mta senaste version.")
    revision = project.revisions.get(number=expected_revision)
    if mode == "final":
        approved = project.approved_preview
        if not approved or approved.revision_id != revision.id or approved.generation.status != "completed":
            raise ValueError("Granska och godk\u00e4nn en f\u00f6rhandsvisning av denna version f\u00f6rst.")
    existing = (
        revision.renders.filter(mode=mode, generation__status__in=(*ACTIVE, "completed"))
        .order_by("-created_at")
        .first()
    )
    if existing:
        job = existing
    else:
        # Bound a company's outstanding queue rather than accepting unbounded work.
        if MotionRender.objects.filter(revision__project__company=company, generation__status__in=ACTIVE).count() >= 6:
            raise ValueError(
                "H\u00f6gst sex samtidiga jobb per f\u00f6retag. Avsluta eller avbryt ett jobb f\u00f6rst."
            )
        generation = MediaGeneration.objects.create(
            run=project.run,
            kind="video",
            provider="remotion",
            status="queued",
            brief=project.title,
            prompt="",
            parameters={"motion_revision_id": str(revision.id), "spec_hash": revision.spec_hash, "mode": mode},
        )
        job = MotionRender.objects.create(revision=revision, generation=generation, mode=mode)
    finish_action(action, result={"render_id": str(job.id)})
    from .jobs import wake_worker

    transaction.on_commit(wake_worker)
    return job


@transaction.atomic
def approve_preview(company, user, project_id, *, render_id, expected_revision):
    _owner(company, user)
    project = get_project(company, project_id, lock=True)
    job = get_render(company, render_id)
    if (
        project.current_revision != expected_revision
        or job.revision.project_id != project.id
        or job.revision.number != expected_revision
        or job.mode != "preview"
        or job.generation.status != "completed"
        or not job.output_asset_id
        or job.storyboard.count() != len(job.revision.spec["scenes"])
    ):
        raise ValueError("En komplett f\u00f6rhandsvisning av aktuell version kr\u00e4vs.")
    project.approved_preview = job
    project.save(update_fields=["approved_preview", "updated_at"])
    return project


@transaction.atomic
def cancel_render(company, render_id):
    job = get_render(company, render_id, lock=True)
    if job.generation.status in ACTIVE:
        MediaGeneration.objects.filter(pk=job.generation_id).update(
            status="canceled", error="Renderingen avbr\u00f6ts.", updated_at=timezone.now()
        )
        job.lease_token = None
        job.lease_expires_at = None
        job.save(update_fields=["lease_token", "lease_expires_at", "updated_at"])
    return job
