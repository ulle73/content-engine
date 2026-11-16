"""SMS film jobs: queue a conversation, wake the GitHub Actions renderer, store the MP4 it sends back.

Flow: views.create → dispatch (workflow_dispatch on .github/workflows/sms-film-render.yml) → the worker
(library/templates/imessage-samtal/dashboard-worker.mjs) claims the job over /internal/sms-film/, downloads the
uploaded images and the private Apple pack, runs build.mjs + HyperFrames, and uploads the MP4 → complete().

The worker shares EDIT_WORKER_TOKEN and GITHUB_DISPATCH_TOKEN with the cloud edit renderer.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import timedelta

import httpx
from django.db import connection, transaction
from django.utils import timezone

from engine.media import store_asset
from engine.models import MediaAsset

from .models import SmsFilmJob
from .spec import SmsFilmError

log = logging.getLogger(__name__)

LEASE_SECONDS = 300
MAX_ATTEMPTS = 3
ACTIVE = ("queued", "claimed", "rendering")
OUTPUT_MAX_BYTES = 120 * 1024 * 1024
WORKFLOW = "sms-film-render.yml"
APPLE_PACK_KEY = "private/apple/imessage-pack.tar.gz"
REDISPATCH_AFTER = timedelta(minutes=30)
FAIL_MESSAGES = {
    "asset_missing": "En bild eller Apple-paketet kunde inte hämtas.",
    "build_failed": "Konversationen kunde inte byggas till en film.",
    "render_failed": "Videon kunde inte renderas.",
    "invalid_output": "Den renderade filen klarade inte kontrollen.",
    "upload_failed": "Den färdiga videon kunde inte laddas upp.",
    "worker_timeout": "Renderingen tog för lång tid.",
}


def max_active() -> int:
    return int(os.environ.get("SMS_FILM_MAX_ACTIVE_JOBS", "3"))


def max_per_day() -> int:
    return int(os.environ.get("SMS_FILM_MAX_JOBS_PER_DAY", "30"))


def create_job(company, user, *, title, form, conversation, image_asset_ids, duration_s, dispatch_now=True,
               kind="sms"):
    active = SmsFilmJob.objects.filter(company=company, status__in=ACTIVE).count()
    if active >= max_active():
        raise SmsFilmError(f"{active} filmer renderas redan. Vänta tills någon är klar och försök igen.")
    today = SmsFilmJob.objects.filter(company=company, created_at__gte=timezone.now() - timedelta(hours=24)).count()
    if today >= max_per_day():
        raise SmsFilmError(f"Max {max_per_day()} SMS-filmer per dygn är nått. Försök igen i morgon.")
    job = SmsFilmJob.objects.create(company=company, created_by=user, title=title[:200], form=form,
                                    conversation=conversation, image_asset_ids=image_asset_ids, duration_s=duration_s,
                                    kind=kind)
    if dispatch_now:
        dispatch(job)
    return job


def dispatch(job: SmsFilmJob, *, client=None) -> bool:
    """Ask GitHub Actions to run the renderer now. Never raises: without a token the job waits for the next run."""
    token = os.environ.get("GITHUB_DISPATCH_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "ulle73/content-engine")
    ref = os.environ.get("GITHUB_DISPATCH_REF", "main")
    if not token:
        error = "GITHUB_DISPATCH_TOKEN saknas; filmen renderas vid nästa schemalagda körning."
        SmsFilmJob.objects.filter(pk=job.pk).update(dispatch_error=error)
        job.dispatch_error = error
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
        SmsFilmJob.objects.filter(pk=job.pk).update(dispatched_at=timezone.now(), dispatch_error="")
    else:
        log.warning("SMS film dispatch failed for %s: %s", job.pk, error)
        SmsFilmJob.objects.filter(pk=job.pk).update(dispatch_error=error[:300])
    job.refresh_from_db(fields=["dispatched_at", "dispatch_error"])
    return ok


# ---------------------------------------------------------------- worker side


def _lock(qs):
    return qs.select_for_update(skip_locked=True, of=("self",)) if connection.vendor == "postgresql" else qs.select_for_update()


@transaction.atomic
def claim(preferred_id=None) -> SmsFilmJob | None:
    now = timezone.now()
    qs = _lock(SmsFilmJob.objects.filter(status="queued").order_by("created_at"))
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
    job.stage = ""
    job.error = ""
    job.save()
    return job


def leased(job_id, token, *, lock=False) -> SmsFilmJob:
    try:
        token = uuid.UUID(str(token))
        qs = SmsFilmJob.objects.select_for_update(of=("self",)) if lock else SmsFilmJob.objects
        job = qs.select_related("company").get(pk=uuid.UUID(str(job_id)))
    except (ValueError, SmsFilmJob.DoesNotExist):
        raise SmsFilmError("Okänt filmjobb eller ogiltig lease.") from None
    if (job.lease_token != token or job.status not in {"claimed", "rendering"} or not job.lease_expires_at
            or job.lease_expires_at <= timezone.now()):
        raise SmsFilmError("Filmjobbets lease har gått ut eller jobbet är avbrutet.")
    return job


def worker_payload(job: SmsFilmJob, base_url: str) -> dict:
    base = base_url.rstrip("/")
    limits = {"output_max_bytes": OUTPUT_MAX_BYTES, "heartbeat_s": 30, "lease_s": LEASE_SECONDS}
    if job.kind == "slutmall":
        # end card: no conversation, no uploads and no Apple pack – the worker renders the template directly
        form = job.form or {}
        return {"job_id": str(job.pk), "lease": str(job.lease_token), "attempt": job.attempts, "kind": "slutmall",
                "slutmall": {"mall": form.get("mall"), "rad1": form.get("rad1", ""), "rad2": form.get("rad2", ""),
                             "effekt": form.get("effekt") or "small", "stil": form.get("stil") or {}},
                "assets": [], "limits": limits}
    assets = []
    for asset in MediaAsset.objects.filter(pk__in=job.image_asset_ids, company=job.company, kind="image"):
        ext = asset.storage_key.rsplit(".", 1)[-1].lower()
        assets.append({"id": str(asset.pk), "path": f"assets/upload/{asset.pk}.{ext}", "sha256": asset.sha256,
                       "byte_size": asset.byte_size, "url": f"{base}/internal/sms-film/assets/{job.pk}/{asset.pk}/"})
    if len(assets) != len(set(job.image_asset_ids)):
        raise SmsFilmError("En bild i filmen finns inte längre i mediabanken.")
    return {
        "job_id": str(job.pk), "lease": str(job.lease_token), "attempt": job.attempts, "kind": "sms",
        "conversation": job.conversation, "assets": assets,
        "apple_pack_url": f"{base}/internal/sms-film/apple-pack/{job.pk}/",
        "limits": limits,
    }


@transaction.atomic
def heartbeat(job_id, token, *, progress=0, stage="") -> SmsFilmJob:
    if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not 0 <= progress <= 1:
        raise SmsFilmError("Ogiltig progress.")
    job = leased(job_id, token, lock=True)
    now = timezone.now()
    job.progress = max(job.progress, float(progress))
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    job.stage = str(stage)[:40]
    if stage == "rendering":
        job.status = "rendering"
    job.save(update_fields=["progress", "heartbeat_at", "lease_expires_at", "status", "stage", "updated_at"])
    return job


@transaction.atomic
def fail(job_id, token, code, *, detail="", retryable=False) -> SmsFilmJob:
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


def _clean_warnings(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(w)[:300] for w in raw if isinstance(w, str) and w.strip()][:40]


def complete(job_id, token, video: bytes, *, duration_s=None, warnings=None) -> SmsFilmJob:
    job = leased(job_id, token)
    if not video or len(video) > OUTPUT_MAX_BYTES:
        raise SmsFilmError("Videon ska vara mellan 1 byte och 120 MB.")
    slutmall = job.kind == "slutmall"
    title = job.title or ("Slutmall" if slutmall else "SMS-film")
    asset = store_asset(job.company, video, alt_text=title[:500])
    if asset.kind != "video":
        raise SmsFilmError("Renderaren skickade inte en video.")
    MediaAsset.objects.filter(pk=asset.pk).update(origin="generated", provider="playwright" if slutmall else "hyperframes",
                                                  brief=f"{'Slutmall' if slutmall else 'SMS-film'}: {title}"[:2000])
    with transaction.atomic():
        job = leased(job_id, token, lock=True)
        job.output_asset = asset
        job.status = "done"
        job.progress = 1
        job.stage = ""
        job.finished_at = timezone.now()
        job.lease_token = None
        job.lease_expires_at = None
        if isinstance(duration_s, (int, float)) and not isinstance(duration_s, bool) and 0 < duration_s < 3600:
            job.duration_s = float(duration_s)
        job.warnings = list(dict.fromkeys([*job.warnings, *_clean_warnings(warnings)]))
        job.save()
    return job


def recover(*, redispatch=True) -> dict:
    """Requeue (or fail) jobs whose worker vanished, and re-wake GitHub for jobs that have waited too long."""
    now = timezone.now()
    requeued = failed = redispatched = 0
    for job in SmsFilmJob.objects.filter(status__in=["claimed", "rendering"], lease_expires_at__lt=now):
        if job.attempts >= MAX_ATTEMPTS:
            SmsFilmJob.objects.filter(pk=job.pk).update(status="failed", finished_at=now, lease_token=None,
                                                        lease_expires_at=None, error=FAIL_MESSAGES["worker_timeout"])
            failed += 1
        else:
            SmsFilmJob.objects.filter(pk=job.pk).update(status="queued", lease_token=None, lease_expires_at=None)
            requeued += 1
    if redispatch:
        for job in SmsFilmJob.objects.filter(status="queued", created_at__lt=now - REDISPATCH_AFTER).exclude(
                dispatched_at__gt=now - REDISPATCH_AFTER)[:5]:
            redispatched += dispatch(job)
    return {"requeued": requeued, "failed": failed, "redispatched": redispatched}


# ---------------------------------------------------------------- dashboard side


def jobs_for(company, limit=20):
    return SmsFilmJob.objects.filter(company=company).select_related("output_asset", "created_by")[:limit]


def get_job(company, job_id) -> SmsFilmJob:
    job = SmsFilmJob.objects.filter(company=company, pk=job_id).select_related("output_asset").first()
    if not job:
        raise SmsFilmError("Filmen finns inte.")
    return job


def serialize(job: SmsFilmJob) -> dict:
    return {
        "id": str(job.pk), "kind": job.kind, "title": job.title, "status": job.status, "status_label": job.get_status_display(),
        "progress": round(job.progress, 2), "stage": job.stage, "error": job.error, "warnings": job.warnings,
        "duration_s": job.duration_s, "dispatch_error": job.dispatch_error,
        "output_asset_id": str(job.output_asset_id) if job.output_asset_id else None,
        "created_at": job.created_at.isoformat(),
    }
