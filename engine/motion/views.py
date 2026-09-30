import os
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from engine.models import ContentRun
from engine.ownership import company_required

from . import service
from .catalog import catalog
from .forms import MotionForm, revision_initial, template_editable
from .models import MotionProject
from .planner import recommend


def worker_available():
    return bool(os.environ.get("MOTION_WORKER_URL") and len(os.environ.get("MOTION_WORKER_TOKEN", "")) >= 32)


@login_required
@company_required
def project_list(request, workspace_id):
    company = request.workspace
    run_id = request.POST.get("run_id") if request.method == "POST" else request.GET.get("run_id")
    if run_id:
        try:
            uuid.UUID(str(run_id))
        except ValueError:
            raise Http404("Utkastet finns inte.") from None
    run = get_object_or_404(ContentRun, pk=run_id, workspace=company, delivery_status="draft") if run_id else None
    if run and MotionProject.objects.filter(run=run).exists():
        return redirect("engine:motion_workspace", workspace_id=workspace_id, project_id=run.motion_project.pk)
    initial = {}
    if run:
        initial = {"title": run.title, "headline": run.title, "body": run.draft.get("photo_brief", "")[:500]}
    suggested = recommend(initial.get("body", ""))["template_id"] if run else "kinetic-text"
    template_id = (
        request.POST.get("template_id") if request.method == "POST" else request.GET.get("template", suggested)
    )
    templates = [item for item in catalog(kind="template") if item["category"] != "sequence"]
    if template_id not in {item["id"] for item in templates}:
        template_id = "kinetic-text"
    form = MotionForm(company, template_id, request.POST if request.method == "POST" else None, initial=initial)
    key = request.POST.get("key", "") if request.method == "POST" else str(uuid.uuid4())
    if request.method == "POST" and form.is_valid():
        try:
            project = service.create_project(
                company, request.user, title=form.cleaned_data["title"], spec=form.compile(), key=key, run=run
            )
            return redirect("engine:motion_workspace", workspace_id=workspace_id, project_id=project.pk)
        except ValueError as exc:
            form.add_error(None, str(exc))
    return render(
        request,
        "engine/motion_list.html",
        {
            "workspace": company,
            "projects": company.motion_projects.select_related("run").order_by("-updated_at")[:40],
            "form": form,
            "templates": templates,
            "template_id": template_id,
            "run": run,
            "key": key,
        },
    )


def workspace_context(project):
    revision = project.revisions.get(number=project.current_revision)
    jobs = list(
        revision.renders.select_related("generation", "output_asset")
        .prefetch_related("storyboard__asset")
        .order_by("-created_at")
    )
    final = next((job for job in jobs if job.mode == "final" and job.generation.status == "completed"), None)
    ready_preview = next((job for job in jobs if job.mode == "preview" and job.generation.status == "completed" and job.output_asset_id), None)
    running = next((job for job in jobs if job.generation.status in service.ACTIVE), None)
    primary = final or running or ready_preview or (jobs[0] if jobs else None)
    source_error = ""
    if project.source_sequence_id:
        from engine.sequence_export import assert_film_current
        try:
            assert_film_current(project, revision)
        except ValueError as exc:
            source_error = str(exc)
    return {
        "project": project,
        "revision": revision,
        "renders": [primary] if primary else [],
        "render_history": [job for job in jobs if job != primary],
        "final": final,
        "ready_preview": ready_preview,
        "source_error": source_error,
        "active": any(job.generation.status in service.ACTIVE for job in jobs),
        "worker_available": worker_available(),
        "template_editable": template_editable(project, revision.spec),
    }


@login_required
@company_required
def workspace(request, workspace_id, project_id):
    project = get_object_or_404(
        MotionProject.objects.select_related("run", "approved_preview"), company=request.workspace, pk=project_id
    )
    context = workspace_context(project)
    spec = context["revision"].spec
    form = None if project.source_sequence_id else MotionForm(request.workspace, spec["template_id"], initial=revision_initial(project, spec))
    context.update(workspace=request.workspace, form=form, key=str(uuid.uuid4()))
    return render(request, "engine/motion_workspace.html", context)


@login_required
@company_required
@require_POST
def project_action(request, workspace_id, project_id):
    project = get_object_or_404(MotionProject, company=request.workspace, pk=project_id)
    form = None
    try:
        if not request.POST.get("revision", "").isdigit():
            raise ValueError("Öppna projektet igen för att hämta den sparade versionen.")
        expected = int(request.POST["revision"])
        action = request.POST.get("action")
        if action == "save":
            spec = project.revisions.get(number=project.current_revision).spec
            if not template_editable(project, spec):
                raise ValueError("Projektet har anpassade scener. Redigera specifikationen via MCP för att bevara dem.")
            form = MotionForm(request.workspace, spec["template_id"], request.POST)
            if not form.is_valid():
                raise ValueError("Kontrollera fälten och spara igen.")
            # The immutable specification is the shared edit boundary; project title remains stable.
            service.update_project(
                request.workspace,
                request.user,
                project.pk,
                spec=form.compile(),
                expected_revision=expected,
                key=request.POST.get("key", ""),
            )
            messages.success(request, "En ny version är sparad. Förhandsvisa den innan du skapar färdig video.")
        elif action in {"preview", "final"}:
            if not worker_available():
                raise ValueError("Renderarbetaren är inte ansluten. Kontakta driftansvarig.")
            service.queue_render(
                request.workspace,
                request.user,
                project.pk,
                mode=action,
                expected_revision=expected,
                key=request.POST.get("key", ""),
            )
        elif action == "approve":
            service.approve_preview(
                request.workspace,
                request.user,
                project.pk,
                render_id=request.POST.get("render_id"),
                expected_revision=expected,
            )
            messages.success(request, "Förhandsvisningen är godkänd. Du kan nu skapa färdig video.")
        elif action == "cancel":
            job = service.get_render(request.workspace, request.POST.get("render_id"))
            if job.revision.project_id != project.pk:
                raise ValueError("Renderjobbet tillhör ett annat projekt.")
            service.cancel_render(request.workspace, job.pk)
        else:
            raise ValueError("Välj en giltig åtgärd.")
    except ValueError as exc:
        if form is not None:
            form.add_error(None, str(exc))
            project.refresh_from_db()
            context = workspace_context(project)
            context.update(workspace=request.workspace, form=form, key=request.POST.get("key", ""))
            return render(request, "engine/motion_workspace.html", context, status=400)
        messages.error(request, str(exc) if str(exc) else "Öppna projektet igen och försök på nytt.")
    return redirect("engine:motion_workspace", workspace_id=workspace_id, project_id=project.pk)


@login_required
@company_required
def status(request, workspace_id, project_id):
    project = get_object_or_404(
        MotionProject.objects.select_related("run", "approved_preview"), company=request.workspace, pk=project_id
    )
    context = workspace_context(project)
    context.update(workspace=request.workspace, key=str(uuid.uuid4()))
    return render(request, "engine/motion_results.html", context)
