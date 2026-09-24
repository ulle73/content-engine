from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .models import SequenceBridge, SequenceClip, SequenceProject
from .ownership import company_required
from .sequence import SequenceError, create_sequence_project


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
    project = get_object_or_404(
        SequenceProject.objects.select_related("company", "author"),
        pk=project_id,
        company=request.workspace,
    )
    anchors = list(
        project.anchors.select_related("asset", "source_clip_version")
        .order_by("position", "created_at")
    )
    clips = list(
        project.clips.select_related(
            "start_anchor",
            "end_anchor",
            "selected_version__generation",
        )
        .annotate(candidate_count=Count("versions", distinct=True))
        .order_by("position", "created_at")
    )
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
            "format_label": FORMAT_CHOICES.get(project.format, project.format or "Ej angivet"),
            "platform_label": PLATFORM_CHOICES.get(project.platform, project.platform or "Ej angivet"),
        },
    )
