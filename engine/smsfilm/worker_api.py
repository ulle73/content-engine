"""Private protocol for the SMS film worker (GitHub Actions). Bearer EDIT_WORKER_TOKEN, no CSRF.

    POST claim/                      {"worker_id", "job_id"?}            → {"job": null | payload}
    POST heartbeat/                  {"job_id", "lease", "progress", "stage"}
    GET  assets/<job>/<asset>/       header X-Edit-Lease                 → image bytes (only the job's own images)
    GET  apple-pack/<job>/           header X-Edit-Lease                 → private Apple tar.gz (never public)
    POST output/<job>/               header X-Edit-Lease, multipart: file (MP4), warnings (JSON list), meta (JSON)
    POST failed/                     {"job_id", "lease", "code", "detail", "retryable"}
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.core.exceptions import RequestDataTooBig, ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import path

from engine.edit.worker_api import body, worker_endpoint as _edit_endpoint
from engine.media_storage import MediaError, open_asset, open_key

from . import service

log = logging.getLogger(__name__)


def worker_endpoint(method="POST"):
    """The edit worker's auth check, plus this module's own error type."""

    def decorate(func):
        def inner(request, *args, **kwargs):
            try:
                return func(request, *args, **kwargs)
            except service.SmsFilmError as exc:
                return JsonResponse({"error": str(exc)}, status=409)
            except (ValueError, ValidationError, MediaError, RequestDataTooBig) as exc:
                log.warning("SMS film worker request rejected: %s", type(exc).__name__)
                return JsonResponse({"error": "Filmjobbets lease, indata eller utdata kunde inte valideras."}, status=409)

        inner.__name__ = func.__name__
        return _edit_endpoint(method)(inner)

    return decorate


def _stream(opener, mime, size=None):
    def content():
        with opener() as stream:
            while chunk := stream.read(256 * 1024):
                yield chunk

    response = StreamingHttpResponse(content(), content_type=mime)
    if size:
        response["Content-Length"] = size
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@worker_endpoint()
def claim(request):
    data = body(request)
    try:
        service.recover(redispatch=False)
    except Exception:  # noqa: BLE001 - recovery is best effort; claiming must still work
        log.exception("SMS film recovery during claim failed")
    job = service.claim(data.get("job_id") or None)
    if job is None:
        return JsonResponse({"job": None})
    try:
        payload = service.worker_payload(job, settings.APP_URL)
    except service.SmsFilmError as exc:
        service.fail(job.pk, job.lease_token, "asset_missing", detail=str(exc))
        return JsonResponse({"job": None, "skipped": str(job.pk)})
    return JsonResponse({"job": payload})


@worker_endpoint()
def heartbeat(request):
    data = body(request)
    job = service.heartbeat(data.get("job_id"), data.get("lease"), progress=data.get("progress", 0),
                            stage=str(data.get("stage") or ""))
    return JsonResponse({"accepted": True, "status": job.status})


@worker_endpoint()
def failed(request):
    data = body(request)
    job = service.fail(data.get("job_id"), data.get("lease"), str(data.get("code") or "render_failed"),
                       detail=str(data.get("detail") or ""), retryable=data.get("retryable") is True)
    return JsonResponse({"accepted": True, "status": job.status})


@worker_endpoint("GET")
def asset_bytes(request, job_id, asset_id):
    job = service.leased(job_id, request.headers.get("X-Edit-Lease"))
    asset = None
    if str(asset_id) in {str(i) for i in job.image_asset_ids}:
        asset = job.company.media_assets.filter(pk=asset_id, kind="image").first()
    elif str(asset_id) == service.outro_asset_id(job):
        asset = job.company.media_assets.filter(pk=asset_id, kind="video").first()
    if not asset:
        return JsonResponse({"error": "Bilden hör inte till filmjobbet."}, status=404)
    return _stream(lambda: open_asset(asset), asset.mime_type, asset.byte_size)


@worker_endpoint("GET")
def apple_pack(request, job_id):
    job = service.leased(job_id, request.headers.get("X-Edit-Lease"))
    if job.kind != "sms":
        return JsonResponse({"error": "Slutmallar använder inga Apple-filer."}, status=404)
    return _stream(lambda: open_key(service.APPLE_PACK_KEY), "application/gzip")


@worker_endpoint()
def output(request, job_id):
    video = request.FILES.get("file")
    if not video or not 0 < video.size <= service.OUTPUT_MAX_BYTES:
        raise service.SmsFilmError("Videon saknas eller är större än 120 MB.")
    raw_meta = request.POST.get("meta") or "{}"
    raw_warnings = request.POST.get("warnings") or "[]"
    if len(raw_meta) > 8192 or len(raw_warnings) > 32768:
        raise ValueError("Oversized field")
    meta = json.loads(raw_meta)
    job = service.complete(job_id, request.headers.get("X-Edit-Lease"), video.read(),
                           duration_s=meta.get("duration_s") if isinstance(meta, dict) else None,
                           warnings=json.loads(raw_warnings))
    return JsonResponse({"accepted": True, "job": service.serialize(job)})


urlpatterns = [
    path("claim/", claim),
    path("heartbeat/", heartbeat),
    path("failed/", failed),
    path("assets/<uuid:job_id>/<uuid:asset_id>/", asset_bytes),
    path("apple-pack/<uuid:job_id>/", apple_pack),
    path("output/<uuid:job_id>/", output),
]
