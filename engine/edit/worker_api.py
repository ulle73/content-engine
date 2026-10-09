"""Private protocol for the cloud edit worker (edit-renderer/ on GitHub Actions). Bearer EDIT_WORKER_TOKEN, no CSRF.

    POST claim/                      {"worker_id", "job_id"?}            → {"job": null | payload}
    POST heartbeat/                  {"job_id", "lease", "progress", "stage"}
    GET  assets/<job>/<asset>/       header X-Edit-Lease                 → file bytes
    POST output/<job>/               header X-Edit-Lease, multipart: file (master MP4), preview (optional MP4),
                                     warnings (JSON list), meta (JSON object)
    POST failed/                     {"job_id", "lease", "code", "detail", "retryable"}
"""

from __future__ import annotations

import json
import logging
import os
from functools import wraps

from django.conf import settings
from django.core.exceptions import RequestDataTooBig, ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import path
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt

from engine.media_storage import MediaError, open_asset

from . import service
from . import spec as cut_spec

log = logging.getLogger(__name__)


def worker_endpoint(method="POST"):
    def decorate(func):
        @csrf_exempt
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            token = os.environ.get("EDIT_WORKER_TOKEN", "")
            supplied = request.headers.get("Authorization", "")
            if len(token) < 32 or not constant_time_compare(supplied, "Bearer " + token):
                return JsonResponse({"error": "Worker authentication required."}, status=401)
            if request.method != method:
                return JsonResponse({"error": "Method not allowed."}, status=405)
            try:
                return func(request, *args, **kwargs)
            except service.EditError as exc:
                return JsonResponse({"error": str(exc)}, status=409)
            except (ValueError, ValidationError, MediaError, RequestDataTooBig) as exc:
                log.warning("Edit worker request rejected: %s", type(exc).__name__)
                return JsonResponse({"error": "Klippjobbets lease, indata eller utdata kunde inte valideras."}, status=409)

        return wrapped

    return decorate


def body(request) -> dict:
    if int(request.META.get("CONTENT_LENGTH") or 0) > 16384:
        raise ValueError("Oversized worker message")
    data = json.loads(request.body or b"{}")
    if not isinstance(data, dict):
        raise ValueError("Object required")
    return data


@worker_endpoint()
def claim(request):
    data = body(request)
    try:
        service.recover(send_discord=True, redispatch=False)
    except Exception:  # noqa: BLE001 - recovery is best effort; claiming must still work
        log.exception("Edit recovery during claim failed")
    job = service.claim(data.get("job_id") or None)
    if job is None:
        return JsonResponse({"job": None})
    try:
        payload = service.worker_payload(job, settings.APP_URL)
    except service.EditError as exc:
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
    allowed = set(cut_spec.asset_ids(job.cut_spec))
    if job.company.official_logo_id:
        allowed.add(str(job.company.official_logo_id))
    asset = job.company.media_assets.filter(pk=asset_id).first() if str(asset_id) in allowed else None
    if not asset:
        return JsonResponse({"error": "Filen hör inte till klippjobbet."}, status=404)

    def content():
        with open_asset(asset) as stream:
            while chunk := stream.read(256 * 1024):
                yield chunk

    response = StreamingHttpResponse(content(), content_type=asset.mime_type)
    response["Content-Length"] = asset.byte_size
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _json_field(request, name, default):
    raw = request.POST.get(name)
    if not raw:
        return default
    if len(raw) > 32768:
        raise ValueError("Oversized field")
    return json.loads(raw)


@worker_endpoint()
def output(request, job_id):
    master = request.FILES.get("file")
    if not master or not 0 < master.size <= service.MASTER_MAX_BYTES:
        raise service.EditError("Mastern saknas eller är större än 80 MB.")
    preview = request.FILES.get("preview")
    if preview is not None and not 0 < preview.size <= service.PREVIEW_MAX_BYTES:
        raise service.EditError("Förhandsvisningen får vara högst 9,5 MB.")
    job = service.complete(job_id, request.headers.get("X-Edit-Lease"), master.read(),
                           preview.read() if preview else None,
                           warnings=_json_field(request, "warnings", []), meta=_json_field(request, "meta", {}))
    return JsonResponse({"accepted": True, "job": service.serialize(job)})


urlpatterns = [
    path("claim/", claim),
    path("heartbeat/", heartbeat),
    path("failed/", failed),
    path("assets/<uuid:job_id>/<uuid:asset_id>/", asset_bytes),
    path("output/<uuid:job_id>/", output),
]
