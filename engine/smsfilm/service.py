"""SMS film jobs: queue a conversation, wake the GitHub Actions renderer, store the MP4 it sends back.

Flow: views.create → dispatch (workflow_dispatch on .github/workflows/sms-film-render.yml) → the worker
(library/templates/imessage-samtal/dashboard-worker.mjs) claims the job over /internal/sms-film/, downloads the
uploaded images and the private Apple pack, runs build.mjs + HyperFrames, and uploads the MP4 → complete().

The worker shares EDIT_WORKER_TOKEN and GITHUB_DISPATCH_TOKEN with the cloud edit renderer.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import timedelta

import httpx
from django.db import connection, transaction
from django.utils import timezone

from engine.media import store_asset
from engine.models import MediaAsset

from . import mallar, publicera
from .models import SmsFilmJob, SmsFilmOutput
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
               kind="sms", mall_id="", varden=None, formats=None):
    active = SmsFilmJob.objects.filter(company=company, status__in=ACTIVE).count()
    if active >= max_active():
        raise SmsFilmError(f"{active} filmer renderas redan. Vänta tills någon är klar och försök igen.")
    today = SmsFilmJob.objects.filter(company=company, created_at__gte=timezone.now() - timedelta(hours=24)).count()
    if today >= max_per_day():
        raise SmsFilmError(f"Max {max_per_day()} SMS-filmer per dygn är nått. Försök igen i morgon.")
    job = SmsFilmJob.objects.create(company=company, created_by=user, title=title[:200], form=form,
                                    conversation=conversation, image_asset_ids=image_asset_ids, duration_s=duration_s,
                                    kind=kind, mall_id=mall_id, varden=varden or {}, formats=formats or [])
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
    if job.mall_id:
        return _mall_payload(job, base, limits)
    assets = []
    for asset in MediaAsset.objects.filter(pk__in=job.image_asset_ids, company=job.company, kind="image"):
        ext = asset.storage_key.rsplit(".", 1)[-1].lower()
        assets.append({"id": str(asset.pk), "path": f"assets/upload/{asset.pk}.{ext}", "sha256": asset.sha256,
                       "byte_size": asset.byte_size, "url": f"{base}/internal/sms-film/assets/{job.pk}/{asset.pk}/"})
    if len(assets) != len(set(job.image_asset_ids)):
        raise SmsFilmError("En bild i filmen finns inte längre i mediabanken.")
    payload = {
        "job_id": str(job.pk), "lease": str(job.lease_token), "attempt": job.attempts, "kind": "sms",
        "conversation": job.conversation, "assets": assets,
        "apple_pack_url": f"{base}/internal/sms-film/apple-pack/{job.pk}/",
        "limits": limits,
    }
    outro_id = outro_asset_id(job)
    if outro_id:
        video = MediaAsset.objects.filter(pk=outro_id, company=job.company, kind="video").first()
        if video is None:
            raise SmsFilmError("Slutmallen i filmen finns inte längre i mediabanken.")
        payload["outro_asset"] = {"id": str(video.pk), "path": job.conversation["outro"]["src"], "sha256": video.sha256,
                                  "byte_size": video.byte_size,
                                  "url": f"{base}/internal/sms-film/assets/{job.pk}/{video.pk}/"}
    return payload


def _mall_payload(job: SmsFilmJob, base: str, limits: dict) -> dict:
    """A dashboard template job (mall/v1): the values, the formats and the files the worker must send back."""
    mall = mallar.hamta(job.mall_id)
    bilder = []
    for asset in MediaAsset.objects.filter(pk__in=job.image_asset_ids, company=job.company, kind="image"):
        ext = asset.storage_key.rsplit(".", 1)[-1].lower()
        bilder.append({"id": str(asset.pk), "fil": f"{asset.pk}.{ext}", "sha256": asset.sha256, "byte_size": asset.byte_size,
                       "url": f"{base}/internal/sms-film/assets/{job.pk}/{asset.pk}/"})
    if len(bilder) != len(set(job.image_asset_ids)):
        raise SmsFilmError("En bild i mallen finns inte längre i mediabanken.")
    payload = {"job_id": str(job.pk), "lease": str(job.lease_token), "attempt": job.attempts, "kind": job.kind,
               "mall": {"id": job.mall_id, "typ": mall["typ"], "varden": job.varden, "formats": job.formats,
                        "bilder": {r["nyckel"]: job.varden.get(r["nyckel"]) for r in mall["reglage"] if r["typ"] == "bild"
                                   and job.varden.get(r["nyckel"])},
                        "utdata": mallar.utdata(mall, job.formats)},
               "assets": bilder, "limits": limits}
    if job.kind == "slutmall":
        # A worker from before the multi-file protocol only knows this shape; it renders the first format.
        v = job.varden
        payload["slutmall"] = {"mall": v.get("mall"), "rad1": v.get("text1", ""), "rad2": v.get("text2", ""),
                               "effekt": v.get("effekt") or "small",
                               "stil": {k: x for k, x in v.items() if k not in ("mall", "text1", "text2", "effekt")},
                               "format": (job.formats or ["9x16"])[0]}
    return payload


def outro_asset_id(job: SmsFilmJob) -> str | None:
    """The slutmall video an SMS film ends with, if one was chosen under "Slut"."""
    outro = (job.conversation or {}).get("outro")
    if job.kind == "sms" and isinstance(outro, dict) and outro.get("asset"):
        return str(outro["asset"])
    return None


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
    slutmall = job.kind in ("slutmall", "mall")
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
        if job.mall_id:
            # a worker from before the multi-file protocol sends one file: the first format
            fmt = (job.formats or ["9x16"])[0]
            w, h = _storlek(fmt)
            SmsFilmOutput.objects.update_or_create(job=job, typ="video", format=fmt, variant="", defaults={
                "asset": asset, "bredd": w, "hojd": h, "langd": job.duration_s})
    return job


def _storlek(fmt):
    return {"9x16": (1080, 1920), "4x5": (1080, 1350), "1x1": (1080, 1080), "16x9": (1920, 1080)}.get(fmt, (0, 0))


def add_output(job_id, token, data: bytes, *, typ, format, variant="", langd=None) -> SmsFilmOutput:
    """Multi-file protocol: one call per file. Calling again for the same file replaces it, so a retry is safe."""
    job = leased(job_id, token)
    if not job.mall_id:
        raise SmsFilmError("Bara mallar skickar flera filer.")
    vantade = {(u["typ"], u["format"], u["variant"]) for u in mallar.utdata(mallar.hamta(job.mall_id), job.formats)}
    variant = str(variant or "")
    if (typ, format, variant) not in vantade:
        raise SmsFilmError(f"Filen {typ} {format} {variant} hör inte till jobbet.")
    if not data or len(data) > OUTPUT_MAX_BYTES:
        raise SmsFilmError("Filen ska vara mellan 1 byte och 120 MB.")
    title = job.title or "Mall"
    asset = store_asset(job.company, data, alt_text=title[:500])
    if asset.kind != typ_kind(typ):
        raise SmsFilmError(f"Renderaren skickade inte en {'video' if typ == 'video' else 'bild'}.")
    MediaAsset.objects.filter(pk=asset.pk).update(origin="generated", provider="playwright",
                                                  brief=f"Mall {job.mall_id} {format}: {title}"[:2000])
    w, h = _storlek(format)
    with transaction.atomic():
        job = leased(job_id, token, lock=True)
        out, _ = SmsFilmOutput.objects.update_or_create(job=job, typ=typ, format=format, variant=variant, defaults={
            "asset": asset, "bredd": w, "hojd": h,
            "langd": float(langd) if isinstance(langd, (int, float)) and not isinstance(langd, bool) else None})
    return out


def typ_kind(typ):
    return "video" if typ == "video" else "image"


def finish(job_id, token, *, duration_s=None, warnings=None, render_commit="") -> SmsFilmJob:
    """Multi-file protocol: the last call. Every expected file must have arrived; the 9:16 file becomes output_asset."""
    with transaction.atomic():
        job = leased(job_id, token, lock=True)
        vantade = mallar.utdata(mallar.hamta(job.mall_id), job.formats)
        filer = {(o.typ, o.format, o.variant): o for o in job.outputs.all()}
        saknas = [f"{u['typ']} {u['format']}" for u in vantade if (u["typ"], u["format"], u["variant"]) not in filer]
        if saknas:
            raise SmsFilmError(f"Filer saknas: {', '.join(saknas)}.")
        forsta = filer[(vantade[0]["typ"], vantade[0]["format"], vantade[0]["variant"])]
        job.output_asset = forsta.asset
        job.status = "done"
        job.progress = 1
        job.stage = ""
        job.finished_at = timezone.now()
        job.lease_token = None
        job.lease_expires_at = None
        if isinstance(duration_s, (int, float)) and not isinstance(duration_s, bool) and 0 < duration_s < 3600:
            job.duration_s = float(duration_s)
        if re.fullmatch(r"[0-9a-f]{7,40}", str(render_commit or "")):
            job.render_commit = str(render_commit)
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
    return SmsFilmJob.objects.filter(company=company).select_related("output_asset", "created_by").prefetch_related("outputs__publiceringar")[:limit]


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
        "format": (job.formats or ["9x16"])[0],
        "mall_id": job.mall_id,
        "outputs": [{"id": str(o.pk), "typ": o.typ, "format": o.format, "variant": o.variant, "asset_id": str(o.asset_id),
                     "publiceringar": [publicera.serialize(p) for p in o.publiceringar.all()]}
                    for o in sorted(job.outputs.all(), key=lambda o: (o.format != "9x16", o.format, o.variant))] if job.mall_id else [],
        "created_at": job.created_at.isoformat(),
    }


def finished_slutmallar(company, limit=30):
    """Rendered slutmallar that an SMS film can end with, newest first."""
    jobs = SmsFilmJob.objects.filter(company=company, kind="slutmall", status="done", output_asset__isnull=False)
    return [serialize(job) for job in jobs.order_by("-created_at")[:limit]]
