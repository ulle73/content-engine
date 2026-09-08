import os
import re
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .media import ACTIVE, advance_job, cleanup_expired, create_job, default_brief, remove_asset, select_asset, store_asset
from .media_storage import MediaError, download_url, local_path
from .models import ContentRun, MediaAsset, MediaGeneration
from .ownership import company_required


def run_for(request, run_id):
    return get_object_or_404(ContentRun.objects.select_related("workspace", "media_asset"), pk=run_id, workspace=request.workspace)


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
    assets = request.workspace.media_assets.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
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
        "higgs_ready": bool(os.environ.get("HIGGSFIELD_API_KEY") and os.environ.get("HIGGSFIELD_API_SECRET")),
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
                         shape=request.POST.get("shape", "portrait"), source=source)
        messages.success(request, "Genereringen är sparad. Du kan lämna sidan och återkomma till samma jobb.")
        return redirect("engine:media_job", workspace_id=workspace_id, run_id=run.pk, job_id=job.pk)
    except (MediaError, ValueError) as exc:
        messages.error(request, str(exc) if isinstance(exc, MediaError) else "Formuläret kunde inte läsas. Försök igen.")
    return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@login_required
@company_required
def job_page(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    return render(request, "engine/media_job.html", {"workspace": request.workspace, "run": run, "job": job,
                  "pending": job.status in ("queued", "starting", "running"), "now": timezone.now()})


@login_required
@company_required
@require_POST
def job_status(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration.objects.select_related("run__workspace", "source_asset"), pk=job_id, run=run)
    try:
        job = advance_job(job)
        return JsonResponse({"status": job.status, "pending": job.status in ("queued", "starting", "running"), "error": job.error})
    except (MediaError, KeyError, ValueError):
        return JsonResponse({"error": "Status kunde inte hämtas. Försök igen; befintligt jobb återanvänds."}, status=502)


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
