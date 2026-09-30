"""Private worker protocol, authenticated independently of browser sessions/CSRF."""

from __future__ import annotations
import json
import os
from functools import wraps
from django.core.exceptions import RequestDataTooBig, ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import path
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from engine.media_storage import MediaError, open_asset
from engine.operator_common import serialize_asset
from . import jobs, outputs


def worker_endpoint(method="POST"):
    def decorate(func):
        @csrf_exempt
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            token = os.environ.get("MOTION_WORKER_TOKEN", "")
            supplied = request.headers.get("Authorization", "")
            if len(token) < 32 or not constant_time_compare(supplied, "Bearer " + token):
                return JsonResponse({"error": "Worker authentication required."}, status=401)
            if request.method != method:
                return JsonResponse({"error": "Method not allowed."}, status=405)
            try:
                return func(request, *args, **kwargs)
            except (ValueError, ValidationError, MediaError, RequestDataTooBig):
                # No untrusted body, exception, credential or storage key escapes this boundary.
                return JsonResponse({"error": "Job lease, input or output validation failed."}, status=409)

        return wrapped

    return decorate


def body(request):
    if int(request.META.get("CONTENT_LENGTH") or 0) > 8192:
        raise ValueError("Oversized worker message")
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError("Object required")
    return data


def uploaded(request, maximum):
    file = request.FILES.get("file")
    if not file or not 0 < file.size <= maximum:
        raise ValueError("Invalid upload")
    return file.read()


@worker_endpoint()
def claim(request):
    job = jobs.claim_job()
    if job is None:
        return JsonResponse({"job": None})
    try:
        payload = outputs.manifest(job)
    except ValueError:
        jobs.fail_job(job.id, job.lease_token, "asset_missing")
        return JsonResponse({"job": None})
    return JsonResponse({"job": payload})


@worker_endpoint()
def heartbeat(request):
    data = body(request)
    job = jobs.heartbeat(data.get("render_id"), data.get("lease"), data.get("progress", 0))
    return JsonResponse({"accepted": True, "progress": job.progress})


@worker_endpoint()
def failed(request):
    data = body(request)
    jobs.fail_job(
        data.get("render_id"),
        data.get("lease"),
        data.get("code", "render_failed"),
        retryable=data.get("retryable") is True,
    )
    return JsonResponse({"accepted": True})


@worker_endpoint("GET")
def asset_bytes(request, render_id, asset_id):
    job = jobs.leased_job(render_id, request.headers.get("X-Motion-Lease"))
    reference = job.revision.asset_references.select_related("asset").filter(asset_id=asset_id).first()
    if not reference or reference.asset.company_id != job.revision.project.company_id:
        return JsonResponse({"error": "Asset not referenced by this render."}, status=404)
    asset = reference.asset
    if reference.sha256 != asset.sha256:
        raise ValueError("Asset changed")

    def content():
        with open_asset(asset) as stream:
            while chunk := stream.read(64 * 1024):
                yield chunk

    response = StreamingHttpResponse(content(), content_type=asset.mime_type)
    response["Content-Length"] = asset.byte_size
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@worker_endpoint()
def keyframe(request, render_id):
    asset = outputs.save_keyframe(
        render_id,
        request.headers.get("X-Motion-Lease"),
        request.POST.get("scene_id", ""),
        int(request.POST.get("frame", "-1")),
        uploaded(request, 8 * 1024 * 1024),
    )
    return JsonResponse(serialize_asset(asset))


@worker_endpoint()
def output(request, render_id):
    asset = outputs.save_output(render_id, request.headers.get("X-Motion-Lease"), uploaded(request, 80 * 1024 * 1024))
    return JsonResponse(serialize_asset(asset))


urlpatterns = [
    path("claim/", claim),
    path("heartbeat/", heartbeat),
    path("failed/", failed),
    path("assets/<uuid:render_id>/<uuid:asset_id>/", asset_bytes),
    path("keyframe/<uuid:render_id>/", keyframe),
    path("output/<uuid:render_id>/", output),
]
