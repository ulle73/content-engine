"""Durable, leased jobs. No Remotion work executes inside a web request."""

from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from engine.models import MediaGeneration

from .models import MotionRender, MotionWorkerSession

log = logging.getLogger(__name__)
LEASE_SECONDS = 180
MAX_ATTEMPTS = 3


def worker_available():
    if len(os.environ.get("MOTION_WORKER_TOKEN", "")) < 32:
        return False
    if os.environ.get("MOTION_WORKER_MODE") == "pull":
        return MotionWorkerSession.objects.filter(expires_at__gt=timezone.now()).exists()
    return bool(os.environ.get("MOTION_WORKER_URL"))


def touch_worker(worker_id):
    if not worker_id:
        return
    worker_id = uuid.UUID(str(worker_id))
    now = timezone.now()
    MotionWorkerSession.objects.filter(expires_at__lte=now).delete()
    MotionWorkerSession.objects.update_or_create(
        id=worker_id, defaults={"expires_at": now + timedelta(seconds=90)}
    )


def wake_worker():
    """Best-effort bounded wake signal; durable queue remains the source of truth."""
    url = os.environ.get("MOTION_WORKER_URL", "").rstrip("/")
    token = os.environ.get("MOTION_WORKER_TOKEN", "")
    if os.environ.get("MOTION_WORKER_MODE") == "pull" or not url or not token:
        return

    def wake():
        import httpx

        try:
            httpx.post(url + "/wake", headers={"Authorization": "Bearer " + token}, timeout=10, follow_redirects=False)
        except httpx.HTTPError:
            log.info("Motion worker wake deferred; queued job remains durable.")

    threading.Thread(target=wake, daemon=True, name="motion-wake").start()


@transaction.atomic
def claim_job():
    now = timezone.now()
    # Lock the job, not a nullable joined relation. PostgreSQL skip_locked permits several workers.
    qs = MotionRender.objects.filter(
        Q(generation__status="queued") | Q(generation__status__in=["running", "saving"], lease_expires_at__lt=now)
    )
    qs = qs.order_by("created_at")
    qs = (
        qs.select_for_update(skip_locked=True, of=("self",))
        if connection.vendor == "postgresql"
        else qs.select_for_update()
    )
    for job in qs[:20]:
        if job.attempts >= MAX_ATTEMPTS:
            MediaGeneration.objects.filter(pk=job.generation_id).update(
                status="failed",
                error="Renderarbetaren tappade kontakten tre g\u00e5nger. Kontrollera driftloggen och starta ett nytt jobb.",
                updated_at=now,
            )
            job.lease_token = None
            job.lease_expires_at = None
            job.save(update_fields=["lease_token", "lease_expires_at", "updated_at"])
            continue
        job.lease_token = uuid.uuid4()
        job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        job.attempts += 1
        job.progress = 0
        job.save(update_fields=["lease_token", "lease_expires_at", "attempts", "progress", "updated_at"])
        MediaGeneration.objects.filter(pk=job.generation_id).update(status="running", error="", updated_at=now)
        return MotionRender.objects.select_related("generation", "revision__project__company").get(pk=job.pk)
    return None


def leased_job(job_id, token, *, lock=False):
    try:
        token = uuid.UUID(str(token))
        qs = MotionRender.objects.select_for_update(of=("self",)) if lock else MotionRender.objects
        job = qs.select_related("generation", "revision__project__company").get(pk=job_id)
    except (ValueError, MotionRender.DoesNotExist):
        raise ValueError("Ogiltigt renderjobb eller lease.") from None
    if (
        job.lease_token != token
        or not job.lease_expires_at
        or job.lease_expires_at <= timezone.now()
        or job.generation.status not in {"running", "saving"}
    ):
        raise ValueError("Renderjobbet har avbrutits eller dess lease har g\u00e5tt ut.")
    return job


@transaction.atomic
def heartbeat(job_id, token, progress=0):
    if not isinstance(progress, (int, float)) or not 0 <= progress <= 1:
        raise ValueError("Ogiltig progress.")
    job = leased_job(job_id, token, lock=True)
    job.progress = max(job.progress, float(progress))
    job.lease_expires_at = timezone.now() + timedelta(seconds=LEASE_SECONDS)
    job.save(update_fields=["progress", "lease_expires_at", "updated_at"])
    return job


@transaction.atomic
def fail_job(job_id, token, code, *, retryable=False):
    job = leased_job(job_id, token, lock=True)
    # Never persist provider response bodies, local paths, headers, or arbitrary exception messages.
    messages = {
        "asset_missing": "En mediefil saknas eller har \u00e4ndrats.",
        "render_failed": "Videon kunde inte renderas. Kontrollera driftloggen.",
        "invalid_output": "Videofilen klarade inte kvalitetskontrollen.",
        "worker_timeout": "Renderingen tog f\u00f6r l\u00e5ng tid.",
        "license_required": "Remotion-licensen m\u00e5ste konfigureras innan produktion.",
    }
    code = code if code in messages else "render_failed"
    status = "queued" if retryable and job.attempts < MAX_ATTEMPTS else "failed"
    MediaGeneration.objects.filter(pk=job.generation_id).update(
        status=status, error=messages[code], updated_at=timezone.now()
    )
    job.lease_token = None
    job.lease_expires_at = None
    job.diagnostics = {"code": code}
    job.save(update_fields=["lease_token", "lease_expires_at", "diagnostics", "updated_at"])
    return job
