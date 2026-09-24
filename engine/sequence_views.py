import uuid
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .media import MediaError, cancel_job, cleanup_expired, describe_file, store_asset
from .models import MediaAsset, SequenceAnchorGenerationTarget, SequenceAnchorRevision, SequenceClipVersion, SequenceProject
from .ownership import company_required
from .openrouter import OpenRouterError
from .sequence import (
    SequenceError,
    add_anchor,
    anchor_change_impact,
    apply_generated_anchor_asset,
    available_clip_model_overrides,
    change_anchor_asset,
    create_sequence_project,
    next_anchor_position,
    prepare_anchor_chain_version,
    prepare_anchor_image_generation,
    preview_anchor_chain_version,
    restore_anchor_revision,
    select_clip_version,
    set_anchor_locked,
    set_clip_model_override,
    sync_sequence_generation,
)
from .sequence_planner import SequencePlanError, generate_sequence_plan, update_sequence_plan


FORMAT_CHOICES = {
    "scroll_story": "Scroll story",
    "reel": "Reel / social video",
    "product_film": "Produktfilm",
    "brand_film": "Brand film",
    "other": "Annat",
}

PLATFORM_CHOICES = {
    "web": "Webb",
    "instagram": "Instagram",
    "meta_ads": "Meta Ads",
    "other": "Annat",
}


def _project_for_request(request, project_id):
    return get_object_or_404(
        SequenceProject.objects.select_related("company", "author"),
        pk=project_id,
        company=request.workspace,
    )


def _anchor_for_project(project, anchor_id):
    return get_object_or_404(
        project.anchors.select_related("asset", "source_clip_version"),
        pk=anchor_id,
    )


def _clip_for_project(project, clip_id):
    return get_object_or_404(
        project.clips.select_related(
            "project__company",
            "start_anchor__asset",
            "end_anchor__asset",
            "selected_version__generation",
        ),
        pk=clip_id,
    )


def _confirm_stale(request) -> bool:
    return request.POST.get("confirm_stale") == "1"


def _selected_image(request):
    asset = get_object_or_404(
        MediaAsset,
        pk=request.POST.get("asset_id"),
        company=request.workspace,
        kind="image",
        purpose="content",
    )
    if asset.expires_at and asset.expires_at <= timezone.now():
        raise SequenceError("Bilden har gått ut. Välj ett annat media.")
    return asset


def _uploaded_image(request):
    file = request.FILES.get("file")
    if not file or file.size > 8 * 1024 * 1024:
        raise SequenceError("Välj JPEG, PNG eller WebP, högst 8 MB.")
    data = file.read()
    try:
        metadata = describe_file(data)
    except MediaError as exc:
        raise SequenceError(str(exc)) from exc
    if metadata.get("kind") != "image":
        raise SequenceError("Sequence-anchors måste vara bilder.")
    cleanup_expired(request.workspace)
    return store_asset(
        request.workspace,
        data,
        alt_text=(request.POST.get("alt_text") or request.POST.get("label") or "Sequence anchor")[:500],
    )


def _workspace_redirect(request, project):
    return redirect("engine:sequence_workspace", workspace_id=request.workspace.pk, project_id=project.pk)


def _project_queryset(workspace):
    return (
        SequenceProject.objects.filter(company=workspace)
        .annotate(
            anchor_count=Count("anchors", distinct=True),
            clip_count=Count("clips", distinct=True),
            bridge_count=Count("bridges", distinct=True),
        )
        .order_by("-updated_at", "-created_at")
    )


@login_required
@company_required
def sequence_list(request, workspace_id):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        brief = request.POST.get("brief", "").strip()
        format_value = request.POST.get("format", "").strip()
        platform = request.POST.get("platform", "").strip()

        try:
            if format_value not in FORMAT_CHOICES:
                raise SequenceError("Välj ett giltigt format.")
            if platform not in PLATFORM_CHOICES:
                raise SequenceError("Välj en giltig kanal.")
            if len(brief) > 6000:
                raise SequenceError("Projektbriefen får vara högst 6000 tecken.")
            project = create_sequence_project(
                request.workspace,
                author=request.user,
                title=title,
                brief=brief,
                format=format_value,
                platform=platform,
            )
            messages.success(request, "Sequence-projektet är skapat.")
            return redirect(
                "engine:sequence_workspace",
                workspace_id=request.workspace.pk,
                project_id=project.pk,
            )
        except SequenceError as exc:
            messages.error(request, str(exc))

    projects = list(_project_queryset(request.workspace))
    for project in projects:
        project.format_label = FORMAT_CHOICES.get(project.format, project.format or "Ej angivet")
        project.platform_label = PLATFORM_CHOICES.get(project.platform, project.platform or "Ej angivet")
    return render(
        request,
        "engine/sequence_list.html",
        {
            "workspace": request.workspace,
            "projects": projects,
            "format_choices": FORMAT_CHOICES,
            "platform_choices": PLATFORM_CHOICES,
            "form_values": {
                "title": request.POST.get("title", "") if request.method == "POST" else "",
                "brief": request.POST.get("brief", "") if request.method == "POST" else "",
                "format": request.POST.get("format", "scroll_story") if request.method == "POST" else "scroll_story",
                "platform": request.POST.get("platform", "web") if request.method == "POST" else "web",
            },
        },
    )


@login_required
@company_required
def sequence_workspace(request, workspace_id, project_id):
    project = _project_for_request(request, project_id)
    anchors = list(
        project.anchors.select_related("asset", "source_clip_version")
        .prefetch_related("revisions__asset", "revisions__source_clip_version")
        .order_by("position", "created_at")
    )
    for anchor in anchors:
        anchor.revision_list = list(anchor.revisions.order_by("-revision_number")[:8])
        anchor.change_impact = anchor_change_impact(anchor)
        anchor.latest_generation_targets = list(
            anchor.generation_targets.select_related("generation").order_by("-created_at")[:3]
        )
        anchor.generation_token = uuid.uuid4()
    clips = list(
        project.clips.select_related(
            "start_anchor__asset",
            "end_anchor__asset",
            "selected_version__generation",
        )
        .annotate(candidate_count=Count("versions", distinct=True))
        .order_by("position", "created_at")
    )
    for clip in clips:
        clip.version_list = list(
            clip.versions.select_related("generation")
            .prefetch_related("generation__assets")
            .order_by("-version_number", "-created_at")
        )
        for version in clip.version_list:
            version.asset_list = list(version.generation.assets.filter(kind="video").order_by("created_at", "pk"))
        try:
            clip.model_options = available_clip_model_overrides(clip)
        except (SequenceError, ValueError):
            clip.model_options = []
        clip.generation_token = uuid.uuid4()
        clip.default_brief = (clip.notes or project.brief or clip.label or project.title)[:6000]
    bridges = list(
        project.bridges.select_related(
            "left_clip",
            "right_clip",
            "start_anchor",
            "end_anchor",
            "selected_version__generation",
        )
        .annotate(candidate_count=Count("versions", distinct=True))
        .order_by("created_at")
    )

    clips_by_start = defaultdict(list)
    for clip in clips:
        clips_by_start[clip.start_anchor_id].append(clip)
    bridges_by_start = defaultdict(list)
    for bridge in bridges:
        bridges_by_start[bridge.start_anchor_id].append(bridge)

    timeline = []
    for anchor in anchors:
        timeline.append({"type": "anchor", "anchor": anchor})
        for clip in clips_by_start.get(anchor.pk, []):
            timeline.append({"type": "clip", "clip": clip})
        for bridge in bridges_by_start.get(anchor.pk, []):
            timeline.append({"type": "bridge", "bridge": bridge})

    candidate_count = sum(clip.candidate_count for clip in clips) + sum(
        bridge.candidate_count for bridge in bridges
    )
    return render(
        request,
        "engine/sequence_workspace.html",
        {
            "workspace": request.workspace,
            "project": project,
            "anchors": anchors,
            "clips": clips,
            "bridges": bridges,
            "timeline": timeline,
            "candidate_count": candidate_count,
            "segment_count": len(clips) + len(bridges),
            "format_label": FORMAT_CHOICES.get(project.format, project.format or "Ej angivet"),
            "platform_label": PLATFORM_CHOICES.get(project.platform, project.platform or "Ej angivet"),
            "available_images": request.workspace.media_assets.filter(
                kind="image", purpose="content"
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).order_by("-created_at")[:24],
            "pending_new_anchor_targets": project.anchor_generation_targets.filter(
                mode="create", applied_anchor__isnull=True
            ).select_related("generation").order_by("-created_at")[:6],
            "anchor_generation_token": uuid.uuid4(),
            "sequence_plan": project.plan if isinstance(project.plan, dict) else {},
        },
    )


@login_required
@company_required
@require_POST
def sequence_plan_generate(request, workspace_id, project_id):
    project = _project_for_request(request, project_id)
    try:
        project = generate_sequence_plan(
            project,
            brief=request.POST.get("brief"),
            goal=request.POST.get("goal"),
        )
        messages.success(
            request,
            f"Sequence-plan V{project.plan_revision} är skapad som Draft. Ingen mediegenerering har startats.",
        )
    except (SequencePlanError, OpenRouterError, ValueError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_plan_save(request, workspace_id, project_id):
    project = _project_for_request(request, project_id)
    try:
        plan = project.plan if isinstance(project.plan, dict) else {}
        anchors = []
        for anchor in plan.get("anchors", []):
            position = int(anchor["position"])
            anchors.append(
                {
                    "position": position,
                    "label": request.POST.get(f"anchor_{position}_label", anchor.get("label", "")),
                    "description": request.POST.get(
                        f"anchor_{position}_description", anchor.get("description", "")
                    ),
                    "role": request.POST.get(f"anchor_{position}_role", anchor.get("role", "")),
                }
            )
        scenes = []
        for scene in plan.get("scenes", []):
            position = int(scene["position"])
            scenes.append(
                {
                    "position": position,
                    "title": request.POST.get(f"scene_{position}_title", scene.get("title", "")),
                    "purpose": request.POST.get(f"scene_{position}_purpose", scene.get("purpose", "")),
                    "narrative": request.POST.get(f"scene_{position}_narrative", scene.get("narrative", "")),
                    "duration_seconds": request.POST.get(
                        f"scene_{position}_duration", scene.get("duration_seconds", 5)
                    ),
                    "transition_intent": request.POST.get(
                        f"scene_{position}_transition", scene.get("transition_intent", "")
                    ),
                }
            )
        progression = [
            line.strip()
            for line in request.POST.get("narrative_progression", "").splitlines()
            if line.strip()
        ]
        project = update_sequence_plan(
            project,
            {
                "status": request.POST.get("status", "draft"),
                "summary": request.POST.get("summary", ""),
                "narrative_progression": progression,
                "anchors": anchors,
                "scenes": scenes,
            },
        )
        messages.success(request, f"Sequence-plan V{project.plan_revision} är sparad.")
    except (SequencePlanError, TypeError, ValueError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_add_existing(request, workspace_id, project_id):
    project = _project_for_request(request, project_id)
    try:
        asset = _selected_image(request)
        anchor = add_anchor(
            project,
            asset,
            position=next_anchor_position(project),
            label=(request.POST.get("label") or "").strip()[:120],
            role=(request.POST.get("role") or "").strip()[:40],
            source_type="existing",
            source_metadata={"mode": "media_library", "asset_id": str(asset.pk)},
            created_by=request.user,
        )
        messages.success(request, f"K{anchor.position} är tillagd från Media.")
    except (SequenceError, MediaError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_add_upload(request, workspace_id, project_id):
    project = _project_for_request(request, project_id)
    try:
        asset = _uploaded_image(request)
        anchor = add_anchor(
            project,
            asset,
            position=next_anchor_position(project),
            label=(request.POST.get("label") or "").strip()[:120],
            role=(request.POST.get("role") or "").strip()[:40],
            source_type="uploaded",
            source_metadata={"mode": "upload", "asset_id": str(asset.pk)},
            created_by=request.user,
        )
        messages.success(request, f"K{anchor.position} är uppladdad och tillagd.")
    except (SequenceError, MediaError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_lock(request, workspace_id, project_id, anchor_id):
    project = _project_for_request(request, project_id)
    anchor = _anchor_for_project(project, anchor_id)
    try:
        locked = request.POST.get("locked") == "1"
        set_anchor_locked(anchor, locked)
        messages.success(request, "Ankaret är låst." if locked else "Ankaret är upplåst.")
    except SequenceError as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_replace_existing(request, workspace_id, project_id, anchor_id):
    project = _project_for_request(request, project_id)
    anchor = _anchor_for_project(project, anchor_id)
    try:
        asset = _selected_image(request)
        change_anchor_asset(
            anchor,
            asset,
            source_type="existing",
            source_metadata={"mode": "media_library", "asset_id": str(asset.pk)},
            reason="media_library",
            created_by=request.user,
            confirm_stale=_confirm_stale(request),
        )
        messages.success(request, f"K{anchor.position} är uppdaterad.")
    except (SequenceError, MediaError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_replace_upload(request, workspace_id, project_id, anchor_id):
    project = _project_for_request(request, project_id)
    anchor = _anchor_for_project(project, anchor_id)
    try:
        if anchor.locked:
            raise SequenceError("Ankaret är låst. Lås upp det innan du laddar upp en ersättare.")
        impact = anchor_change_impact(anchor)
        if impact["total_versions"] and not _confirm_stale(request):
            raise SequenceError(
                f"Bytet gör {impact['total_versions']} befintliga clip/bridge-versioner inaktuella. "
                "Bekräfta ändringen innan filen laddas upp."
            )
        asset = _uploaded_image(request)
        change_anchor_asset(
            anchor,
            asset,
            source_type="uploaded",
            source_metadata={"mode": "upload", "asset_id": str(asset.pk)},
            reason="upload",
            created_by=request.user,
            confirm_stale=_confirm_stale(request),
        )
        messages.success(request, f"K{anchor.position} är ersatt med den uppladdade bilden.")
    except (SequenceError, MediaError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_restore(request, workspace_id, project_id, anchor_id, revision_id):
    project = _project_for_request(request, project_id)
    anchor = _anchor_for_project(project, anchor_id)
    revision = get_object_or_404(SequenceAnchorRevision.objects.select_related("asset", "source_clip_version"), pk=revision_id, anchor=anchor)
    try:
        restore_anchor_revision(
            anchor,
            revision,
            created_by=request.user,
            confirm_stale=_confirm_stale(request),
        )
        messages.success(request, f"K{anchor.position} är återställd från revision {revision.revision_number}.")
    except SequenceError as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_generate(request, workspace_id, project_id, anchor_id=None):
    project = _project_for_request(request, project_id)
    anchor = _anchor_for_project(project, anchor_id) if anchor_id else None
    try:
        target = prepare_anchor_image_generation(
            project,
            brief=request.POST.get("brief", ""),
            target_anchor=anchor,
            target_label=(request.POST.get("label") or "").strip()[:120],
            target_role=(request.POST.get("role") or "").strip()[:40],
            shape=request.POST.get("shape", "portrait"),
            count=int(request.POST.get("count", "2")),
            priority=request.POST.get("priority", "balanced"),
            token=request.POST.get("token") or uuid.uuid4(),
            created_by=request.user,
        )
        messages.success(request, "AI-anchor är förberedd. Granska inställningarna innan betald start.")
        return redirect(
            "engine:media_job",
            workspace_id=request.workspace.pk,
            run_id=target.generation.run_id,
            job_id=target.generation_id,
        )
    except (SequenceError, MediaError, ValueError) as exc:
        messages.error(request, str(exc) if not isinstance(exc, ValueError) else "AI-formuläret kunde inte läsas.")
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_anchor_apply_generated(request, workspace_id, project_id, target_id, asset_id):
    project = _project_for_request(request, project_id)
    target = get_object_or_404(
        SequenceAnchorGenerationTarget.objects.select_related("generation", "target_anchor"),
        pk=target_id,
        project=project,
    )
    asset = get_object_or_404(MediaAsset, pk=asset_id, company=request.workspace, kind="image")
    try:
        anchor = apply_generated_anchor_asset(
            target,
            asset,
            created_by=request.user,
            confirm_stale=_confirm_stale(request),
        )
        messages.success(request, f"AI-bilden används nu som K{anchor.position}.")
        return _workspace_redirect(request, project)
    except SequenceError as exc:
        messages.error(request, str(exc))
        return redirect(
            "engine:media_job",
            workspace_id=request.workspace.pk,
            run_id=target.generation.run_id,
            job_id=target.generation_id,
        )


@login_required
@company_required
@require_POST
def sequence_clip_prepare(request, workspace_id, project_id, clip_id):
    project = _project_for_request(request, project_id)
    clip = _clip_for_project(project, clip_id)
    brief = request.POST.get("brief", "")
    priority = request.POST.get("priority", "balanced")
    model_override = request.POST.get("model_override", "")
    try:
        clip = set_clip_model_override(
            clip,
            model_override,
            brief=brief,
            priority=priority,
        )
        version = prepare_anchor_chain_version(
            clip,
            brief=brief,
            priority=priority,
            token=request.POST.get("token") or uuid.uuid4(),
        )
    except (SequenceError, MediaError, ValueError) as exc:
        messages.error(request, str(exc))
        return _workspace_redirect(request, project)

    try:
        version = preview_anchor_chain_version(version)
        messages.success(
            request,
            f"Clip {clip.position + 1} · V{version.version_number} är förberedd för review. Ingen betald generation har startats.",
        )
    except (SequenceError, MediaError) as exc:
        messages.error(request, str(exc))

    return redirect(
        "engine:media_job",
        workspace_id=request.workspace.pk,
        run_id=version.generation.run_id,
        job_id=version.generation_id,
    )


@login_required
@company_required
@require_POST
def sequence_clip_select(request, workspace_id, project_id, clip_id, version_id):
    project = _project_for_request(request, project_id)
    clip = _clip_for_project(project, clip_id)
    version = get_object_or_404(
        SequenceClipVersion.objects.select_related("generation"),
        pk=version_id,
        clip=clip,
    )
    try:
        sync_sequence_generation(version.generation)
        version.refresh_from_db()
        select_clip_version(clip, version)
        messages.success(request, f"Clip {clip.position + 1} · V{version.version_number} är vald som vinnare.")
    except SequenceError as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)


@login_required
@company_required
@require_POST
def sequence_clip_cancel(request, workspace_id, project_id, clip_id, version_id):
    project = _project_for_request(request, project_id)
    clip = _clip_for_project(project, clip_id)
    version = get_object_or_404(
        SequenceClipVersion.objects.select_related("generation"),
        pk=version_id,
        clip=clip,
    )
    try:
        job = cancel_job(version.generation)
        sync_sequence_generation(job)
        messages.success(
            request,
            f"Clip {clip.position + 1} · V{version.version_number} avbröts säkert."
            if job.status == "canceled"
            else "Jobbet var redan avslutat.",
        )
    except (SequenceError, MediaError) as exc:
        messages.error(request, str(exc))
    return _workspace_redirect(request, project)
