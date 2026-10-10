"""Cloud edit jobs: queue a cut spec, wake the GitHub Actions renderer, and turn its output into a Discord review.

Flow: create_job → dispatch (workflow_dispatch on .github/workflows/edit-render.yml) → the worker claims the job over
/internal/edit/ (engine/edit/worker_api.py), downloads the assets, renders with HyperFrames, uploads the MP4 →
complete() stores it in the media bank, creates a Review with a manifest built from the cut spec and posts it to
Discord. A failed Discord post never fails the job: it is retried by recover() (every claim and the daily workflow).

Which file is reviewed: the master is always stored as output_asset (full quality, what gets published). When the
master is larger than PREVIEW_MAX_BYTES the worker also uploads a compressed preview; the Review then uses the preview
so it plays inline in Discord; the master stays reachable from the review via EditJob (review.edit_jobs).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import timedelta

import httpx
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from engine.media import store_asset
from engine.models import MediaAsset

from . import spec as cut_spec
from .models import EditJob

log = logging.getLogger(__name__)

LEASE_SECONDS = 300
MAX_ATTEMPTS = 3
ACTIVE = ("queued", "claimed", "rendering")
MASTER_MAX_BYTES = 80 * 1024 * 1024
PREVIEW_MAX_BYTES = int(9.5 * 1024 * 1024)
WORKFLOW = "edit-render.yml"
REDISPATCH_AFTER = timedelta(minutes=30)
FAIL_MESSAGES = {
    "asset_missing": "En mediefil kunde inte hämtas eller har ändrats.",
    "compose_failed": "Klippmallen kunde inte byggas av klippspecen.",
    "render_failed": "Videon kunde inte renderas.",
    "audio_failed": "Ljudmixen (musik/loudness) misslyckades.",
    "invalid_output": "Den renderade filen klarade inte kontrollen.",
    "upload_failed": "Den färdiga videon kunde inte laddas upp.",
    "worker_timeout": "Renderingen tog för lång tid.",
}


class EditError(ValueError):
    pass


def max_active() -> int:
    return int(os.environ.get("EDIT_MAX_ACTIVE_JOBS", "3"))


def max_per_day() -> int:
    return int(os.environ.get("EDIT_MAX_JOBS_PER_DAY", "20"))


def create_job(company, raw_spec, *, dispatch_now=True) -> EditJob:
    """Validate the cut spec against the company's media bank and queue it. Free (GitHub Actions), but rate limited."""
    spec, warnings = cut_spec.validate(company, raw_spec)
    active = EditJob.objects.filter(company=company, status__in=ACTIVE).count()
    if active >= max_active():
        raise EditError(f"{company.name} har redan {active} klippjobb i kö eller under rendering. "
                        "Vänta tills något är klart och försök igen.")
    today = EditJob.objects.filter(company=company, created_at__gte=timezone.now() - timedelta(hours=24)).count()
    if today >= max_per_day():
        raise EditError(f"Max {max_per_day()} klippjobb per dygn och bolag är nått. Försök igen senare.")
    job = EditJob.objects.create(company=company, recipe_id=spec["recipe_id"] or "", cut_spec=spec, warnings=warnings)
    if dispatch_now:
        dispatch(job)
    return job


def dispatch(job: EditJob, *, client=None) -> bool:
    """Ask GitHub Actions to run the renderer now. Never raises: without a token the job waits for the next run."""
    token = os.environ.get("GITHUB_DISPATCH_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "ulle73/content-engine")
    ref = os.environ.get("GITHUB_DISPATCH_REF", "main")
    if not token:
        job.dispatch_error = "GITHUB_DISPATCH_TOKEN saknas; jobbet körs vid nästa schemalagda körning."
        EditJob.objects.filter(pk=job.pk).update(dispatch_error=job.dispatch_error)
        return False
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "content-engine"}
    own = client is None
    client = client or httpx.Client(timeout=10)
    try:
        response = client.post(url, headers=headers, json={"ref": ref, "inputs": {"job_id": str(job.pk)}})
        ok = response.status_code in (200, 201, 204)
        error = "" if ok else f"GitHub svarade {response.status_code} på workflow_dispatch."
    except httpx.HTTPError as exc:
        ok, error = False, f"GitHub kunde inte nås: {type(exc).__name__}."
    finally:
        if own:
            client.close()
    if ok:
        EditJob.objects.filter(pk=job.pk).update(dispatched_at=timezone.now(), dispatch_error="")
    else:
        log.warning("Edit dispatch failed for %s: %s", job.pk, error)
        EditJob.objects.filter(pk=job.pk).update(dispatch_error=error[:300])
    job.refresh_from_db(fields=["dispatched_at", "dispatch_error"])
    return ok


# ---------------------------------------------------------------- worker side


def _lock(qs):
    return qs.select_for_update(skip_locked=True, of=("self",)) if connection.vendor == "postgresql" else qs.select_for_update()


@transaction.atomic
def claim(preferred_id=None) -> EditJob | None:
    now = timezone.now()
    qs = _lock(EditJob.objects.filter(status="queued").order_by("created_at"))
    job = None
    if preferred_id:
        try:
            job = qs.filter(pk=uuid.UUID(str(preferred_id))).first()
        except ValueError:
            job = None
    job = job or qs.first()
    if not job:
        return None
    job.status = "claimed"
    job.lease_token = uuid.uuid4()
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    job.claimed_at = job.heartbeat_at = now
    job.attempts += 1
    job.progress = 0
    job.error = ""
    job.save()
    return job


def leased(job_id, token, *, lock=False) -> EditJob:
    try:
        token = uuid.UUID(str(token))
        qs = EditJob.objects.select_for_update(of=("self",)) if lock else EditJob.objects
        job = qs.select_related("company").get(pk=uuid.UUID(str(job_id)))
    except (ValueError, EditJob.DoesNotExist):
        raise EditError("Okänt klippjobb eller ogiltig lease.") from None
    if (job.lease_token != token or job.status not in {"claimed", "rendering"} or not job.lease_expires_at
            or job.lease_expires_at <= timezone.now()):
        raise EditError("Klippjobbets lease har gått ut eller jobbet är avbrutet.")
    return job


def worker_payload(job: EditJob, base_url: str) -> dict:
    """Everything the renderer needs: the spec, brand tokens and authorized download locations for each file."""
    from engine.media_storage import MediaError, download_url
    from engine.motion import brand as brand_kit

    company = job.company
    tokens = brand_kit.tokens_for(company)
    logo = company.official_logo if company.official_logo_id and company.official_logo.company_id == company.pk else None
    ids = cut_spec.asset_ids(job.cut_spec) + ([str(logo.pk)] if logo else [])
    assets = []
    for asset in MediaAsset.objects.filter(pk__in=ids, company=company):
        direct = None
        if asset.storage_backend == "r2":
            try:
                direct = download_url(asset)
            except MediaError:
                direct = None
        assets.append({
            "id": str(asset.pk), "kind": asset.kind, "mime_type": asset.mime_type, "sha256": asset.sha256,
            "byte_size": asset.byte_size, "width": asset.width, "height": asset.height,
            "duration_seconds": asset.duration_seconds,
            "url": f"{base_url.rstrip('/')}/internal/edit/assets/{job.pk}/{asset.pk}/",
            "download_url": direct,
        })
    if len(assets) != len(set(ids)):
        raise EditError("En mediefil i klippspecen finns inte längre i mediabanken.")
    return {
        "job_id": str(job.pk), "lease": str(job.lease_token), "attempt": job.attempts,
        "spec": job.cut_spec,
        "brand": {**tokens, "name": company.name, "logo_asset_id": str(logo.pk) if logo else None,
                  "landing_url": brand_kit.landing_url(company)},
        "assets": assets,
        "limits": {"master_max_bytes": MASTER_MAX_BYTES, "preview_max_bytes": PREVIEW_MAX_BYTES,
                   "heartbeat_s": 30, "lease_s": LEASE_SECONDS},
    }


@transaction.atomic
def heartbeat(job_id, token, *, progress=0, stage="") -> EditJob:
    if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not 0 <= progress <= 1:
        raise EditError("Ogiltig progress.")
    job = leased(job_id, token, lock=True)
    now = timezone.now()
    job.progress = max(job.progress, float(progress))
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    if stage == "rendering":
        job.status = "rendering"
    job.save(update_fields=["progress", "heartbeat_at", "lease_expires_at", "status", "updated_at"])
    return job


def _clean_warnings(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(w)[:300] for w in raw if isinstance(w, str) and w.strip()][:40]


@transaction.atomic
def fail(job_id, token, code, *, detail="", retryable=False) -> EditJob:
    job = leased(job_id, token, lock=True)
    code = code if code in FAIL_MESSAGES else "render_failed"
    message = FAIL_MESSAGES[code] + (f" ({str(detail).strip()[:300]})" if str(detail or "").strip() else "")
    job.status = "queued" if retryable and job.attempts < MAX_ATTEMPTS else "failed"
    job.error = message
    job.lease_token = None
    job.lease_expires_at = None
    job.finished_at = None if job.status == "queued" else timezone.now()
    job.save()
    return job


def complete(job_id, token, master: bytes, preview: bytes | None = None, *, warnings=None, meta=None) -> EditJob:
    """Store the rendered video, create the review and post it to Discord (a Discord failure is retried later)."""
    job = leased(job_id, token)
    if not master or len(master) > MASTER_MAX_BYTES:
        raise EditError("Mastern ska vara mellan 1 byte och 80 MB.")
    if preview is not None and not 0 < len(preview) <= PREVIEW_MAX_BYTES:
        raise EditError("Förhandsvisningen får vara högst 9,5 MB.")
    company, spec = job.company, job.cut_spec
    master_asset = _store(company, master, spec)
    preview_asset = _store(company, preview, spec, suffix=" (förhandsvisning)") if preview else None
    with transaction.atomic():
        job = leased(job_id, token, lock=True)
        from engine.review import service as review_service

        review_asset = preview_asset or master_asset
        review = review_service.create(company, review_asset, title=spec["title"], caption=spec.get("caption", ""),
                                       manifest=build_manifest(spec))
        job.output_asset = master_asset
        job.preview_asset = preview_asset
        job.review = review
        job.status = "done"
        job.progress = 1
        job.finished_at = timezone.now()
        job.lease_token = None
        job.lease_expires_at = None
        job.warnings = list(dict.fromkeys([*job.warnings, *_clean_warnings(warnings)]))
        if isinstance(meta, dict):
            job.cut_spec = {**spec, "render": {k: meta[k] for k in ("duration_s", "loudness_lufs", "master_bytes",
                                                                    "preview_bytes", "hyperframes") if k in meta}}
        job.save()
    _critique(job, preview or master)
    post_review(job)
    return job


def _critique(job: EditJob, video: bytes | None) -> None:
    """Fail-open AI critique before the Discord card is posted; never blocks delivery."""
    from . import critic

    try:
        job.ai_critique = critic.run(job, video)
        EditJob.objects.filter(pk=job.pk).update(ai_critique=job.ai_critique)
    except Exception:  # noqa: BLE001 - storing the critique must not fail the delivery either
        log.exception("Storing the AI critique for edit job %s failed", job.pk)


def _store(company, data, spec, suffix=""):
    asset = store_asset(company, data, alt_text=(spec["title"] + suffix)[:500])
    if asset.kind != "video":
        raise EditError("Renderaren skickade inte en video.")
    MediaAsset.objects.filter(pk=asset.pk).update(origin="generated", provider="hyperframes",
                                                  brief=f"Klippt i molnet: {spec['title']}"[:2000])
    asset.refresh_from_db()
    return asset


def post_review(job: EditJob) -> bool:
    from engine.review import discord
    from engine.review.service import ReviewError

    review = job.review
    if not review or review.discord_message_id:
        return True
    try:
        discord.send(review)
    except ReviewError as exc:
        log.warning("Discord post for edit job %s failed: %s", job.pk, exc)
        EditJob.objects.filter(pk=job.pk).update(discord_error=str(exc)[:300])
        job.discord_error = str(exc)[:300]
        return False
    EditJob.objects.filter(pk=job.pk).update(discord_error="")
    job.discord_error = ""
    return True


def recover(*, send_discord=True, redispatch=True) -> dict:
    """Requeue jobs whose worker vanished, retry Discord posts and wake the renderer for jobs nobody picked up."""
    now = timezone.now()
    stats = {"requeued": 0, "failed": 0, "discord": 0, "dispatched": 0}
    stale = EditJob.objects.filter(status__in=["claimed", "rendering"], lease_expires_at__lt=now)
    for job in stale:
        if job.attempts >= MAX_ATTEMPTS:
            EditJob.objects.filter(pk=job.pk).update(
                status="failed", finished_at=now, lease_token=None, lease_expires_at=None,
                error="Renderaren tappade kontakten tre gånger. Se loggen för workflowet Edit Render på GitHub.")
            stats["failed"] += 1
        else:
            EditJob.objects.filter(pk=job.pk).update(
                status="queued", lease_token=None, lease_expires_at=None,
                error="Renderaren tappade kontakten; jobbet försöks igen.")
            stats["requeued"] += 1
    if send_discord:
        pending = (EditJob.objects.filter(status="done", review__isnull=False, review__discord_message_id="",
                                          review__status="pending", finished_at__gte=now - timedelta(days=7))
                   .select_related("review__company", "review__asset")[:10])
        for job in pending:
            stats["discord"] += int(post_review(job))
    if redispatch:
        waiting = (EditJob.objects.filter(status="queued")
                   .filter(Q(dispatched_at__isnull=True) | Q(dispatched_at__lt=now - REDISPATCH_AFTER))
                   .order_by("created_at").first())
        if waiting and dispatch(waiting):
            # One run processes several queued jobs, so one dispatch is enough.
            stats["dispatched"] += 1
    return stats


# ---------------------------------------------------------------- manifest and serialization


def build_manifest(spec: dict) -> dict:
    """Review manifest (engine/review/manifest.py) from a cut spec: every scene with its exact library items."""
    global_items = [{"id": "edit-renderer.cut-template", "type": "template", "label": "Klippmall (HyperFrames)"}]
    if spec.get("recipe_id"):
        global_items.append({"id": spec["recipe_id"], "type": "template", "label": f"Recept {spec['recipe_id']}"})
    if spec.get("music_asset_id"):
        global_items.append({"id": spec["music_asset_id"], "type": "music", "label": "Musik"})
    scenes, clock = [], 0.0
    for scene in spec["scenes"]:
        items = []
        if scene.get("transition_in"):
            items.append({"id": scene["transition_in"], "type": "transition",
                          "label": cut_spec.label("transitions", scene["transition_in"])})
        if scene.get("text_style"):
            items.append({"id": scene["text_style"], "type": "text", "label": cut_spec.label("text", scene["text_style"])})
        for effect in scene.get("effects") or []:
            native = cut_spec.resolve("effects", effect) or ""
            items.append({"id": effect, "type": "grade" if native.startswith("grade-") else "effect",
                          "label": cut_spec.label("effects", effect)})
        items.append({"id": scene["asset_id"], "type": "asset",
                      "label": f"{'Videoklipp' if scene.get('asset_kind') == 'video' else 'Bild'} {scene['id']}",
                      "params": {"trim_start_s": scene.get("trim_start_s", 0), "fit": scene.get("fit", "cover")}})
        end = clock + float(scene["duration_s"])
        scenes.append({"id": scene["id"], "start": clock, "end": end, "purpose": scene.get("purpose", ""),
                       "text": scene.get("text", ""), "items": items})
        clock = end
    if spec.get("cta"):
        end = clock + float(spec["cta"]["duration_s"])
        scenes.append({"id": "cta", "start": clock, "end": end, "purpose": "cta", "text": spec["cta"]["text"],
                       "items": [{"id": "edit-renderer.end-card", "type": "scene", "label": "Slutkort med CTA och logga",
                                  "params": {"url": spec["cta"].get("url", "")}}]})
        clock = end
    if spec.get("outro"):
        end = clock + float(spec["outro"]["duration_s"])
        scenes.append({"id": "outro", "start": clock, "end": end, "purpose": "cta", "text": "",
                       "items": [{"id": spec["outro"]["id"], "type": "scene", "label": spec["outro"]["label"]}]})
        clock = end
    return {"duration_s": clock, "global": global_items, "scenes": scenes}


def get_job(company, job_id) -> EditJob:
    try:
        return EditJob.objects.select_related("review", "company").get(pk=uuid.UUID(str(job_id)), company=company)
    except (ValueError, EditJob.DoesNotExist):
        raise EditError("Klippjobbet finns inte för bolaget.") from None


NEXT_STEP = {
    "queued": "Väntar på renderaren (GitHub Actions). Kolla igen om någon minut med get_cut_job.",
    "claimed": "Renderaren har hämtat jobbet och laddar ner materialet.",
    "rendering": "Videon renderas. Det tar oftast 3–10 minuter.",
    "done": "Klar och skickad för granskning i Discord.",
    "failed": "Rendering misslyckades. Rätta klippspecen och skicka ett nytt jobb med render_cut.",
}


def serialize(job: EditJob) -> dict:
    from engine.review.service import video_link

    review = job.review
    step = NEXT_STEP[job.status]
    if job.status == "done" and review and not review.discord_message_id:
        step = "Klar. Discord-posten misslyckades och görs om automatiskt: " + (job.discord_error or "okänt fel")
    return {
        "job_id": str(job.pk), "status": job.status, "status_label": job.get_status_display(), "next_step": step,
        "title": job.cut_spec.get("title", ""), "recipe_id": job.recipe_id or None,
        "duration_s": job.cut_spec.get("duration_s"), "format": job.cut_spec.get("format"),
        "attempts": job.attempts, "progress": round(job.progress, 2), "error": job.error, "warnings": job.warnings,
        "output_asset_id": str(job.output_asset_id) if job.output_asset_id else None,
        "preview_asset_id": str(job.preview_asset_id) if job.preview_asset_id else None,
        "review_id": str(review.pk) if review else None,
        "video_link": video_link(review) if review else None,
        "discord_posted": bool(review and review.discord_message_id),
        "ai_critique": job.ai_critique or None,
        "dispatched": bool(job.dispatched_at), "dispatch_error": job.dispatch_error or None,
        "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat(),
    }
