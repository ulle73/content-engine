import json
import os
import re
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .media import ACTIVE, PENDING, advance_job, cancel_job, cleanup_expired, create_job, default_brief, remove_asset, select_asset, store_asset
from .media_storage import MediaError, download_url, local_path
from .models import ContentRun, MediaAsset, MediaGeneration
from .ownership import company_required
from .media import preview_job, refresh_terminal_provider_status, start_reviewed_job


def run_for(request, run_id):
    return get_object_or_404(ContentRun.objects.select_related("workspace", "media_asset"), pk=run_id, workspace=request.workspace)


@login_required
@company_required
def library(request, workspace_id):
    now = timezone.now()
    assets = request.workspace.media_assets.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).select_related(
        "generation", "generation__run"
    )
    filter_value = request.GET.get("filter", "all")
    if filter_value in {"image", "video"}:
        assets = assets.filter(kind=filter_value)
    elif filter_value in {"uploaded", "generated"}:
        assets = assets.filter(origin=filter_value)
    elif filter_value == "logo":
        assets = assets.filter(purpose="logo")
    elif filter_value != "all":
        filter_value = "all"

    assets = list(assets.order_by("-created_at")[:120])
    recent_jobs = list(
        MediaGeneration.objects.filter(run__workspace=request.workspace, status="completed")
        .select_related("run")
        .prefetch_related("assets")
        .order_by("-created_at")[:8]
    )
    return render(
        request,
        "engine/media_library.html",
        {
            "workspace": request.workspace,
            "assets": assets,
            "recent_jobs": recent_jobs,
            "unfinished_jobs": MediaGeneration.objects.filter(run__workspace=request.workspace, status__in=ACTIVE).order_by("-created_at")[:12],
            "filter_value": filter_value,
            "now": now,
            "studio_token": uuid.uuid4(),
        },
    )


@login_required
@company_required
@require_POST
def library_upload(request, workspace_id):
    try:
        file = request.FILES.get("file")
        if not file or file.size > 80 * 1024 * 1024:
            raise MediaError("Välj en bild (högst 8 MB) eller MP4-video (högst 80 MB).")
        cleanup_expired(request.workspace)
        store_asset(request.workspace, file.read(), alt_text=request.POST.get("alt_text", ""))
        messages.success(request, "Filen är sparad i Media och kan väljas i alla framtida utkast.")
    except MediaError as exc:
        messages.error(request, str(exc))
    return redirect("engine:media_library", workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def new_studio(request, workspace_id):
    """Open the existing studio with a local empty draft; no text or media API call."""
    try:
        token = uuid.UUID(request.POST.get("token", ""))
    except ValueError:
        return HttpResponse("Ogiltigt formulär. Öppna Media igen.", status=400)
    company = request.workspace
    run, _ = ContentRun.objects.get_or_create(pk=token, defaults={
        "workspace": company, "author": request.user, "model": "creative-studio",
        "context": {"media_only": True, "profile": company.profile, "voice": company.voice, "current": company.current},
        "ideas": [{"title": "Bild eller video", "photo_brief": ""}], "selected": 0,
        "draft": {"photo_brief": "", "instagram": "", "facebook": ""},
    })
    if run.workspace_id != company.pk:
        return HttpResponse(status=404)
    return redirect(reverse("engine:media", kwargs={"workspace_id": company.pk, "run_id": run.pk}) + "?kind=image#generate")


@login_required
@company_required
def picker(request, workspace_id, run_id):
    run = run_for(request, run_id)
    kind = request.GET.get("kind", "image")
    if kind not in {"image", "video"}:
        kind = "image"
    source = None
    retry = get_object_or_404(MediaGeneration, pk=request.GET["retry"], run=run) if request.GET.get("retry") else None
    if retry:
        kind, source = retry.kind, retry.source_asset
    if request.GET.get("source"):
        source = get_object_or_404(MediaAsset, pk=request.GET["source"], company=request.workspace, kind="image")
    assets = request.workspace.media_assets.filter(purpose="content").filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    filter_value = request.GET.get("filter", "all")
    if filter_value in {"image", "video"}:
        assets = assets.filter(kind=filter_value)
    elif filter_value in {"uploaded", "generated"}:
        assets = assets.filter(origin=filter_value)
    assets = assets.order_by(Case(When(origin="uploaded", then=Value(0)), default=Value(1), output_field=IntegerField()), "-created_at")[:60]
    jobs = list(run.media_jobs.order_by("-created_at").prefetch_related("assets")[:10])
    return render(request, "engine/media.html", {
        "workspace": request.workspace, "run": run, "kind": kind, "assets": assets, "jobs": jobs,
        "source": source, "brief": retry.brief if retry else source.brief if source and kind == "image" and source.brief else default_brief(run, kind),
        "token": uuid.uuid4(), "can_edit": run.delivery_status == "draft",
        "higgs_ready": bool(os.environ.get("HIGGSFIELD_API_KEY_GK") or os.environ.get("HIGGSFIELD_API_KEY")),
        "filter_value": filter_value, "now": timezone.now(), "active_statuses": ACTIVE,
    })


@login_required
@company_required
@require_POST
def upload(request, workspace_id, run_id):
    run = run_for(request, run_id)
    try:
        if run.delivery_status != "draft":
            raise MediaError("Utkastet har redan överförts. Ändra media i Postiz.")
        file = request.FILES.get("file")
        if not file or file.size > 80 * 1024 * 1024:
            raise MediaError("Välj en bild (högst 8 MB) eller MP4-video (högst 80 MB).")
        cleanup_expired(request.workspace)
        asset = store_asset(request.workspace, file.read(), alt_text=request.POST.get("alt_text", ""))
        if request.POST.get("use"):
            select_asset(run, asset)
            return redirect("engine:review", workspace_id=workspace_id, run_id=run.pk)
        messages.success(request, "Filen finns nu bland företagets uppladdade media.")
    except MediaError as exc:
        messages.error(request, str(exc))
    return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@login_required
@company_required
@require_POST
def generate_media(request, workspace_id, run_id):
    run = run_for(request, run_id)
    try:
        cleanup_expired(request.workspace)
        source = get_object_or_404(MediaAsset, pk=request.POST["source_asset"], company=request.workspace, kind="image") if request.POST.get("source_asset") else None
        job = create_job(run, token=uuid.UUID(request.POST.get("token", "")), kind=request.POST.get("kind"),
                         brief=request.POST.get("brief", ""), count=int(request.POST.get("count", "2")),
                         shape=request.POST.get("shape", "portrait"), source=source, include_logo=bool(request.POST.get("include_logo")),
                         priority=request.POST.get("priority", "balanced"))
        try:
            preview_job(job)
        except MediaError as exc:
            messages.error(request, str(exc))
        return redirect("engine:media_job", workspace_id=workspace_id, run_id=run.pk, job_id=job.pk)
    except (MediaError, ValueError) as exc:
        messages.error(request, str(exc) if isinstance(exc, MediaError) else "Formuläret kunde inte läsas. Försök igen.")
    return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@login_required
@company_required
def job_page(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    creative = job.parameters.get("creative", {}) if isinstance(job.parameters, dict) else {}
    safe_parameters = {key: value for key, value in (job.parameters or {}).items() if key in {"model", "provider_model", "count", "size", "quality", "duration", "aspect_ratio", "resolution", "generate_audio", "output_format"}}
    status_index = {"queued": 2, "starting": 2, "running": 3, "saving": 4, "completed": 5}.get(job.status, -1)
    return render(request, "engine/media_job.html", {
        "workspace": request.workspace, "run": run, "job": job, "pending": job.status in PENDING, "now": timezone.now(),
        "creative": creative, "safe_parameters": safe_parameters, "status_index": status_index,
        "structured_brief_json": json.dumps(creative.get("brief", {}), ensure_ascii=False, indent=2),
        "parameters_json": json.dumps(safe_parameters, ensure_ascii=False, indent=2),
        "queued": job.status == "queued",
    })


@login_required
@company_required
@require_POST
def job_start(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    try:
        if request.POST.get("action") == "preview":
            preview_job(job)
        else:
            start_reviewed_job(job)
    except MediaError as exc:
        messages.error(request, str(exc))
    return redirect("engine:media_job", workspace_id=workspace_id, run_id=run.pk, job_id=job.pk)


@login_required
@company_required
@require_POST
def job_status(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration.objects.select_related("run__workspace", "source_asset"), pk=job_id, run=run)
    try:
        if job.status != "queued":
            job = advance_job(job)
        return JsonResponse({"status": job.status, "pending": job.status in PENDING, "error": job.error})
    except (MediaError, KeyError, ValueError):
        return JsonResponse({"error": "Status kunde inte hämtas. Försök igen; befintligt jobb återanvänds."}, status=502)


@login_required
@company_required
@require_POST
def refresh_provider_status(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    try:
        job = refresh_terminal_provider_status(job)
        messages.success(request, "Higgsfields senaste felorsak har hämtats för samma request-id.")
    except MediaError as exc:
        messages.error(request, str(exc))
    return redirect("engine:media_job", workspace_id=workspace_id, run_id=run.pk, job_id=job.pk)


@login_required
@company_required
@require_POST
def cancel_generation(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    try:
        job = cancel_job(job)
        messages.success(request, "Genereringen är avbruten." if job.status == "canceled" else "Jobbet var redan avslutat.")
    except MediaError as exc:
        messages.error(request, str(exc))
    return redirect("engine:media_job", workspace_id=workspace_id, run_id=run.pk, job_id=job.pk)


@login_required
@company_required
@require_POST
def reset_job(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    if job.status == "unknown" and request.POST.get("checked_provider"):
        MediaGeneration.objects.filter(pk=job.pk, status="unknown").update(status="failed", error="Återställd efter användarens kontroll av leverantörskontot.")
        messages.success(request, "Du kan nu uttryckligen starta en ny generation.")
    return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@login_required
@company_required
@require_POST
def use_asset(request, workspace_id, run_id, asset_id):
    run = run_for(request, run_id)
    asset = get_object_or_404(MediaAsset, pk=asset_id, company=request.workspace)
    try:
        select_asset(run, asset)
        messages.success(request, "Media är sparat och valt för inlägget.")
        return redirect("engine:review", workspace_id=workspace_id, run_id=run.pk)
    except MediaError as exc:
        messages.error(request, str(exc))
        return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@login_required
@company_required
@require_POST
def delete_asset(request, workspace_id, run_id, asset_id):
    run = run_for(request, run_id)
    asset = get_object_or_404(MediaAsset, pk=asset_id, company=request.workspace)
    try:
        remove_asset(asset)
        messages.success(request, "Oanvänd media har tagits bort.")
    except MediaError as exc:
        messages.error(request, str(exc))
    return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@csrf_exempt
@require_POST
def higgsfield_webhook(request):
    """Untrusted completion hint; authoritative state is always re-fetched from Higgsfield."""
    if request.content_type != "application/json" or len(request.body) > 64 * 1024:
        return JsonResponse({"error": "invalid webhook envelope"}, status=400)
    try:
        body = json.loads(request.body)
        if not isinstance(body, dict) or not isinstance(body.get("status"), str) or not isinstance(body.get("request_id"), str):
            raise ValueError("invalid envelope")
        request_id = str(uuid.UUID(body["request_id"]))
        status = body["status"]
        if status not in {"completed", "failed", "nsfw"} or "error" not in body or "payload" not in body:
            raise ValueError("invalid status")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid webhook envelope"}, status=400)

    # Do not expose whether a provider id exists. Unknown but well-formed deliveries
    # are acknowledged; polling/recovery remains the fallback for races.
    job = MediaGeneration.objects.select_related("run__workspace", "source_asset", "logo_asset").filter(
        provider="higgsfield", provider_id=request_id
    ).first()
    if not job:
        return HttpResponse(status=204)

    # Persist only the safe envelope metadata. Payload URLs/errors are untrusted and
    # deliberately ignored; result retrieval happens through authenticated GET.
    with transaction.atomic():
        job = MediaGeneration.objects.select_for_update().get(pk=job.pk)
        usage = dict(job.usage or {})
        prior = usage.get("webhook", {})
        usage["webhook"] = {
            "last_status": status, "received_at": timezone.now().isoformat(),
            "deliveries": min(int(prior.get("deliveries", 0)) + 1, 1_000_000),
        }
        MediaGeneration.objects.filter(pk=job.pk).update(usage=usage)
    # Acknowledge within ten seconds. Recovery/polling does authenticated reconciliation.
    return HttpResponse(status=204)


@login_required
@company_required
def asset_file(request, workspace_id, asset_id):
    asset = get_object_or_404(MediaAsset, pk=asset_id, company=request.workspace)
    if asset.expires_at and asset.expires_at <= timezone.now():
        return HttpResponse("Förhandsvisningen har gått ut.", status=410)
    if asset.storage_backend == "r2":
        try:
            response = redirect(download_url(asset))
        except MediaError:
            return HttpResponse("Förhandsvisningen kunde inte öppnas. Kontrollera lagringen.", status=503)
    else:
        path = local_path(asset.storage_key)
        if not path.is_file():
            return HttpResponse("Filen saknas.", status=404)
        # MP4 previews need byte ranges for seeking; R2 supports these natively.
        range_header = request.headers.get("Range", "")
        match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            size = path.stat().st_size
            start, end = int(match[1]), min(int(match[2]) if match[2] else size - 1, size - 1)
            if start > end:
                return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
            with path.open("rb") as file:
                file.seek(start)
                response = HttpResponse(file.read(end - start + 1), status=206, content_type=asset.mime_type,
                                        headers={"Content-Range": f"bytes {start}-{end}/{size}"})
        else:
            response = FileResponse(path.open("rb"), content_type=asset.mime_type)
        response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
