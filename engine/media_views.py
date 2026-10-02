import json
import re
import uuid
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .creative_core import ReferenceRole
from .creative_registry import verified_models
from .forms import snapshot_company_context
from .media import (
    ACTIVE,
    PENDING,
    advance_job,
    asset_removal_blocker,
    cancel_job,
    cleanup_expired,
    create_job,
    default_brief,
    preview_job,
    publishable_assets,
    refresh_terminal_provider_status,
    remove_asset,
    select_asset,
    start_reviewed_job,
    store_asset,
)
from .media_providers import higgsfield_configured
from .media_references import reference_asset, serialize_generation_references
from .media_storage import MediaError, download_url, local_path
from .media_usage import registered_usage, storage_usage
from .models import (
    ContentRun,
    MediaAsset,
    MediaGeneration,
    SequenceAnchorGenerationTarget,
    SequenceBridgeVersion,
    SequenceClipVersion,
)
from .ownership import company_required
from .sequence import anchor_change_impact, sync_sequence_generation


def run_for(request, run_id):
    return get_object_or_404(ContentRun.objects.select_related("workspace", "media_asset"), pk=run_id, workspace=request.workspace)


@login_required
@company_required
def library(request, workspace_id):
    now = timezone.now()
    assets = request.workspace.media_assets.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).select_related(
        "generation", "generation__run"
    ).exclude(motion_outputs__mode="preview").exclude(motion_storyboards__isnull=False)
    filter_value = request.GET.get("filter", "all")
    if filter_value in {"image", "video", "audio"}:
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
        .exclude(motion_render__mode="preview")
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
            "unfinished_jobs": MediaGeneration.objects.filter(run__workspace=request.workspace, status__in=ACTIVE).exclude(provider="remotion").order_by("-created_at")[:12],
            "filter_value": filter_value,
            "now": now,
            "studio_token": uuid.uuid4(),
            "storage_usage": registered_usage(request.workspace),
        },
    )


@login_required
@company_required
@require_GET
def library_storage(request, workspace_id):
    response = JsonResponse(storage_usage(request.workspace, refresh=request.GET.get("refresh") == "1"))
    response["Cache-Control"] = "private, no-store"
    return response


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
@require_http_methods(["GET", "POST"])
def library_delete(request, workspace_id, asset_id):
    asset = get_object_or_404(MediaAsset, pk=asset_id, company=request.workspace)
    filter_value = request.POST.get("filter", request.GET.get("filter", "all"))
    if filter_value not in {"all", "image", "video", "audio", "uploaded", "generated", "logo"}:
        filter_value = "all"
    library_url = reverse("engine:media_library", kwargs={"workspace_id": workspace_id})
    if filter_value != "all":
        library_url += "?" + urlencode({"filter": filter_value})
    error = ""
    status = 200
    if request.method == "POST":
        if request.POST.get("confirm_delete") != "1":
            error = "Bekräfta att du vill radera filen permanent."
            status = 400
        else:
            try:
                remove_asset(asset)
            except MediaError as exc:
                error = str(exc)
                status = 409
            else:
                messages.success(request, "Media har raderats från databasen och fillagringen.")
                return redirect(library_url)
    return render(request, "engine/media_delete.html", {
        "workspace": request.workspace, "asset": asset,
        "blocker": asset_removal_blocker(asset), "error": error,
        "filter_value": filter_value, "library_url": library_url,
    }, status=status)


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
    source_query = ""
    if request.POST.get("source_asset"):
        from .forms import MediaCreationForm
        try:
            source_id = uuid.UUID(request.POST["source_asset"])
        except ValueError:
            raise Http404("Bilden finns inte.") from None
        available = MediaCreationForm(company=company).fields["source_asset"].queryset
        asset = get_object_or_404(available, pk=source_id)
        source_query = "&source=" + str(asset.pk)
    brief = ""
    snapshot = {**snapshot_company_context(company), "media_only": True}
    channel = "organic"
    market_signal_id = ""
    if request.POST.get("market_id"):
        from .learning import attach_generation_evidence
        from .market import classify as classify_market
        from .models import MarketItem
        item = get_object_or_404(MarketItem, pk=request.POST["market_id"], company=company)
        try:
            result = classify_market(item, company)
            channel = item.channel
            market_signal_id = f"market:{item.pk}"
            attach_generation_evidence(snapshot, company, channel, item.pk)
        except ValueError as exc:
            return HttpResponse(str(exc), status=400)
        brief = result.get("adaptation", "")
    run, _ = ContentRun.objects.get_or_create(pk=token, defaults={
        "workspace": company, "author": request.user, "model": "creative-studio", "channel": channel,
        "context": snapshot,
        "ideas": [{"title": "Bild eller video", "photo_brief": brief, "angle": brief, "signal_id": market_signal_id}], "selected": 0,
        "draft": {"photo_brief": brief, "instagram": "", "facebook": ""},
    })
    if run.workspace_id != company.pk:
        return HttpResponse(status=404)
    kind = request.POST.get("kind", "image")
    kind = kind if kind in {"image", "video"} else "image"
    return redirect(reverse("engine:media", kwargs={"workspace_id": company.pk, "run_id": run.pk}) + "?kind=" + kind + source_query + "#generate")


@login_required
@company_required
def picker(request, workspace_id, run_id):
    return _render_picker(request, run_for(request, run_id))


def _render_picker(request, run, form=None, *, status=200):
    """Keep bound input on errors; changing references never requires a new run."""
    from .forms import MediaCreationForm
    kind = request.GET.get("kind", "image")
    if kind not in {"image", "video"}:
        kind = "image"
    source = end_source = None
    retry = None
    if request.GET.get("retry"):
        try:
            retry_id = uuid.UUID(request.GET["retry"])
        except ValueError:
            raise Http404("Genereringen finns inte.") from None
        retry = get_object_or_404(MediaGeneration, pk=retry_id, run=run)
    initial = {"token": uuid.uuid4(), "kind": kind, "shape": "portrait", "priority": "balanced", "count": 1,
               "include_logo": bool(request.workspace.official_logo_id) and kind == "image"}
    if retry:
        kind, source = retry.kind, retry.source_asset
        end_source = reference_asset(retry, ReferenceRole.end_image)
        parameters = retry.parameters or {}
        creative = parameters.get("creative", {})
        saved = parameters.get("creator", {})
        initial.update(saved.get("controls", {}))
        initial.update(kind=kind, brief=retry.brief, count=parameters.get("count", 1),
                       shape=saved.get("shape") or {"1:1": "square", "16:9": "landscape", "1024x1024": "square", "1536x1024": "landscape"}.get(
                           creative.get("brief", {}).get("aspect_ratio") or parameters.get("aspect_ratio") or parameters.get("size"), "portrait"),
                       priority=creative.get("brief", {}).get("quality_preference", "balanced"),
                       recipe_id=saved.get("recipe_id") or creative.get("recipe", {}).get("recipe_id", ""), model_override=parameters.get("model_override", ""),
                       include_logo=bool(retry.logo_asset_id))
    for query, role in (("source", "start"), ("end_source", "end")):
        if request.GET.get(query):
            try:
                asset_id = uuid.UUID(request.GET[query])
            except ValueError:
                raise Http404("Bilden finns inte.") from None
            asset = get_object_or_404(MediaAsset, pk=asset_id, company=request.workspace, kind="image")
            if role == "start":
                source = asset
            else:
                end_source = asset
    if kind != "video":
        end_source = None
    initial.update(source_asset=source, end_asset=end_source)
    initial.setdefault("brief", default_brief(run, kind) or (source.brief if source else ""))
    if form is None:
        form = MediaCreationForm(company=request.workspace, initial=initial)
    else:
        kind = form.data.get("kind", "image")
        kind = kind if kind in {"image", "video"} else "image"
        source = form.cleaned_data.get("source_asset")
        end_source = form.cleaned_data.get("end_asset")
    assets = publishable_assets(request.workspace.media_assets.filter(purpose="content").filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())))
    filter_value = request.GET.get("filter", "all")
    if filter_value in {"image", "video", "audio"}:
        assets = assets.filter(kind=filter_value)
    elif filter_value in {"uploaded", "generated"}:
        assets = assets.filter(origin=filter_value)
    assets = assets.order_by(Case(When(origin="uploaded", then=Value(0)), default=Value(1), output_field=IntegerField()), "-created_at")[:60]
    mode = ("image-to-video" if source else "text-to-video") if kind == "video" else ("image-to-image" if source else "text-to-image")
    models = verified_models(kind, mode)
    if end_source:
        models = [m for m in models if m.supports_reference_role(mode, ReferenceRole.end_image)]
    return render(request, "engine/media.html", {
        "workspace": request.workspace, "run": run, "kind": kind, "assets": assets,
        "jobs": list(run.media_jobs.exclude(provider="remotion").order_by("-created_at").prefetch_related("assets")[:10]),
        "source": source, "end_source": end_source, "can_edit": run.delivery_status == "draft",
        "asset_url_pattern": reverse("engine:asset_file", kwargs={"workspace_id": request.workspace.pk, "asset_id": uuid.UUID(int=0)}),
        "creator_form": form, "creator_catalog": form.catalog, "creating": run.delivery_status == "draft",
        "restore_creator": not form.is_bound and not retry, "higgs_ready": higgsfield_configured(),
        "filter_value": filter_value, "now": timezone.now(), "active_statuses": ACTIVE,
        "override_models": models, "model_override": initial.get("model_override", ""),
    }, status=status)


def _creation_error(exc):
    text = str(exc)
    if "model override" in text.casefold():
        return "Den valda modellen st\u00f6der inte alla val. V\u00e4lj Auto eller justera l\u00e4ngd, bilder, ljud och uppl\u00f6sning."
    if "No verified model" in text:
        return "Ingen verifierad modell st\u00f6der kombinationen. Prova Auto f\u00f6r modell och uppl\u00f6sning, eller f\u00e4rre krav."
    if "Creative recipe" in text:
        return "Mallen passar inte dina valda bilder. V\u00e4lj en annan mall eller l\u00e4gg till de bilder som beh\u00f6vs."
    if "Compiled video prompt" in text:
        return "Id\u00e9n och valen blir f\u00f6r omfattande f\u00f6r ett klipp. Beskriv en huvudhandling eller v\u00e4lj Film av flera delar."
    return text


@login_required
@company_required
@require_POST
def creation_preview(request, workspace_id, run_id):
    """Pure local planning: no generation row, uploads, pricing or provider call."""
    from .creative_director import build_plan
    from .creative_registry import get_model
    from .forms import MediaCreationForm
    from .model_catalog import model_label
    from .prompt_library import retrieve_inspiration
    run = run_for(request, run_id)
    if run.delivery_status != "draft":
        return JsonResponse({"error": "Utkastet \u00e4r inte l\u00e4ngre redigerbart."}, status=409)
    form = MediaCreationForm(request.POST, company=request.workspace)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=422)
    options = form.job_options()
    options.pop("include_logo")
    brief = options.pop("brief")
    try:
        inspirations = retrieve_inspiration(request.workspace.owner, request.workspace.pk, brief, limit=3)
        plan = build_plan(run, brief, inspirations=inspirations, **options)
    except (ValueError, MediaError) as exc:
        return JsonResponse({"error": _creation_error(exc)}, status=422)
    model = get_model(plan.selection.provider, plan.selection.model_id)
    contract = model.request_contract(plan.brief.mode)
    return JsonResponse({"model": model_label(model.model_id), "model_id": model.model_id,
                         "mode": plan.brief.mode, "duration": plan.parameters.get("duration"),
                         "aspect_ratio": plan.brief.aspect_ratio, "aspect_behavior": contract.aspect_ratio_behavior,
                         "prompt": plan.prompt, "recipe": plan.recipe.recipe_id,
                         "warnings": [issue.message for issue in plan.preflight],
                         "paid_generation_started": False})


@login_required
@company_required
@require_GET
def creation_references(request, workspace_id, run_id):
    from .forms import MediaCreationForm
    run_for(request, run_id)
    try:
        page = max(0, min(int(request.GET.get("page", "0")), 1000))
    except ValueError:
        return JsonResponse({"error": "Ogiltig sida."}, status=400)
    images = MediaCreationForm(company=request.workspace).fields["source_asset"].queryset
    query = request.GET.get("q", "").strip()[:200]
    if query:
        images = images.filter(Q(alt_text__icontains=query) | Q(brief__icontains=query))
    images = list(images.order_by("-created_at", "-pk")[page*60:page*60+61])
    return JsonResponse({"assets": [{"id": str(a.pk), "label": a.alt_text or "Bild " + str(a.pk)[:8],
                                    "url": reverse("engine:asset_file", kwargs={"workspace_id": workspace_id, "asset_id": a.pk})} for a in images[:60]],
                         "next_page": page+1 if len(images) > 60 else None})


@login_required
@company_required
@require_POST
def creation_handoff(request, workspace_id, run_id):
    from .operator_common import run_state
    run = run_for(request, run_id)
    target = request.POST.get("workflow") or request.POST.get("target")
    if target not in {"motion", "sequence"}:
        return HttpResponse("V\u00e4lj Text och siffror eller Film av flera delar.", status=400)
    brief = request.POST.get("brief", "").strip()
    if not brief or len(brief) > 6000:
        return HttpResponse("Beskriv vad du vill skapa (h\u00f6gst 6000 tecken).", status=400)
    from .forms import MediaCreationForm
    fields = MediaCreationForm(company=request.workspace).fields
    images = []
    try:
        for name in ("source_asset", "end_asset"):
            asset = fields[name].clean(request.POST.get(name, ""))
            if asset and asset not in images:
                images.append(asset)
    except ValidationError:
        return HttpResponse("En vald bild finns inte l\u00e4ngre i f\u00f6retagets bibliotek.", status=400)
    if target == "sequence" and any(asset.purpose != "content" for asset in images):
        return HttpResponse("V\u00e4lj en vanlig bild f\u00f6r en film av flera delar. En frist\u00e5ende logga kan anv\u00e4ndas i Text och siffror.", status=400)
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().get(pk=run.pk)
        if locked.delivery_status != "draft":
            return HttpResponse("Utkastet \u00e4r inte redigerbart.", status=409)
        if brief and brief != locked.draft.get("photo_brief"):
            locked.draft = {**locked.draft, "photo_brief": brief}
            locked.save(update_fields=["draft"])
            state = run_state(locked, lock=True)
            state.revision += 1
            state.save(update_fields=["revision", "updated_at"])
    params = [("run_id", str(run.pk)), ("aspect_ratio", {"portrait": "9:16", "square": "1:1", "landscape": "16:9"}.get(request.POST.get("shape"), "9:16"))]
    params.extend(("image_ids", str(asset.pk)) for asset in images)
    return redirect(reverse("engine:" + ("motion_list" if target == "motion" else "sequence_list"), kwargs={"workspace_id": workspace_id}) + "?" + urlencode(params))


@login_required
@company_required
@require_POST
def upload(request, workspace_id, run_id):
    run = run_for(request, run_id)
    json_upload = request.headers.get("X-Creator-Upload") == "1"
    try:
        if run.delivery_status != "draft":
            raise MediaError("Utkastet har redan överförts. Ändra media i Postiz.")
        file = request.FILES.get("file")
        if not file or file.size > 80 * 1024 * 1024:
            raise MediaError("Välj en bild (högst 8 MB) eller MP4-video (högst 80 MB).")
        cleanup_expired(request.workspace)
        data = file.read()
        if json_upload:
            from .media import describe_file
            if len(data) > 8 * 1024 * 1024 or describe_file(data)["kind"] != "image":
                raise MediaError("V\u00e4lj JPEG, PNG eller WebP, h\u00f6gst 8 MB.")
        asset = store_asset(request.workspace, data, alt_text=request.POST.get("alt_text", ""))
        if json_upload:
            return JsonResponse({"id": str(asset.pk), "label": asset.alt_text or "Ny bild",
                                 "url": reverse("engine:asset_file", kwargs={"workspace_id": workspace_id, "asset_id": asset.pk})}, status=201)
        if request.POST.get("use"):
            select_asset(run, asset)
            return redirect("engine:review", workspace_id=workspace_id, run_id=run.pk)
        messages.success(request, "Filen finns nu bland företagets uppladdade media.")
    except MediaError as exc:
        if json_upload:
            return JsonResponse({"error": str(exc)}, status=400)
        messages.error(request, str(exc))
    return redirect("engine:media", workspace_id=workspace_id, run_id=run.pk)


@login_required
@company_required
@require_POST
def generate_media(request, workspace_id, run_id):
    from .forms import MediaCreationForm
    run = run_for(request, run_id)
    form = MediaCreationForm(request.POST, company=request.workspace)
    if form.is_valid():
        try:
            cleanup_expired(request.workspace)
            job = create_job(run, token=form.cleaned_data["token"], **form.job_options())
            if job.pk != form.cleaned_data["token"]:
                form.add_error(None, "Du har redan ett p\u00e5g\u00e5ende eller v\u00e4ntande jobb. Avbryt det innan du skapar en ny variant. Din id\u00e9 finns kvar h\u00e4r.")
                return _render_picker(request, run, form, status=409)
            try:
                preview_job(job)
            except MediaError as exc:
                messages.error(request, str(exc))
            return redirect("engine:media_job", workspace_id=workspace_id, run_id=run.pk, job_id=job.pk)
        except (MediaError, ValueError) as exc:
            form.add_error(None, _creation_error(exc))
    return _render_picker(request, run, form, status=422)


@login_required
@company_required
def job_page(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    creative = job.parameters.get("creative", {}) if isinstance(job.parameters, dict) else {}
    safe_parameters = {key: value for key, value in (job.parameters or {}).items() if key in {"model", "provider_model", "model_override", "count", "size", "quality", "duration", "aspect_ratio", "resolution", "generate_audio", "output_format"}}
    status_index = {"queued": 2, "starting": 2, "running": 3, "saving": 4, "completed": 5}.get(job.status, -1)
    anchor_target = (
        SequenceAnchorGenerationTarget.objects.select_related("project", "target_anchor", "applied_anchor")
        .filter(generation=job, project__company=request.workspace)
        .first()
    )
    anchor_impact = (
        anchor_change_impact(anchor_target.target_anchor)
        if anchor_target and anchor_target.target_anchor_id
        else {"total_versions": 0, "selected_segments": 0}
    )
    sequence_clip_version = (
        SequenceClipVersion.objects.select_related("clip__project")
        .filter(generation=job, clip__project__company=request.workspace)
        .first()
    )
    sequence_bridge_version = (
        SequenceBridgeVersion.objects.select_related("bridge__project")
        .filter(generation=job, bridge__project__company=request.workspace)
        .first()
    )
    return render(request, "engine/media_job.html", {
        "workspace": request.workspace, "run": run, "job": job, "pending": job.status in PENDING, "now": timezone.now(),
        "creative": creative, "safe_parameters": safe_parameters, "status_index": status_index,
        "start_reference": reference_asset(job, ReferenceRole.start_image),
        "end_reference": reference_asset(job, ReferenceRole.end_image),
        "generation_references": serialize_generation_references(job),
        "structured_brief_json": json.dumps(creative.get("brief", {}), ensure_ascii=False, indent=2),
        "parameters_json": json.dumps(safe_parameters, ensure_ascii=False, indent=2),
        "queued": job.status == "queued",
        "sequence_anchor_target": anchor_target,
        "sequence_anchor_impact": anchor_impact,
        "sequence_clip_version": sequence_clip_version,
        "sequence_bridge_version": sequence_bridge_version,
    })


@login_required
@company_required
@require_POST
def job_start(request, workspace_id, run_id, job_id):
    run = run_for(request, run_id)
    job = get_object_or_404(MediaGeneration, pk=job_id, run=run)
    try:
        if request.POST.get("action") == "preview":
            job = preview_job(job)
        else:
            job = start_reviewed_job(job)
        sync_sequence_generation(job)
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
        sync_sequence_generation(job)
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
        sync_sequence_generation(job)
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
        sync_sequence_generation(job)
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
