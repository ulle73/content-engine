"""Ad Studio workbench: the place to click, see and approve what the chat agreed."""

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from engine.motion.catalog import catalog
from engine.ownership import company_required

from . import service
from .models import AssetTags

OBJECTIVES = [("awareness", "Kännedom"), ("consideration", "Övervägande"), ("conversion", "Köp"),
              ("retargeting", "Återaktivering")]
SCENE_LABELS = {"hook": "Hook", "problem": "Problem", "solution": "Lösning", "how": "Så funkar det",
                "proof": "Bevis", "offer": "Erbjudande", "cta": "Slutkort"}


def _draft_or_404(company, draft_id):
    try:
        return service.get_draft(company, draft_id)
    except ValueError:
        raise Http404("Annonsen finns inte.") from None


def _back(workspace_id, draft_id, anchor=""):
    response = redirect("engine:ad_workspace", workspace_id=workspace_id, draft_id=draft_id)
    if anchor:
        response["Location"] += "#" + anchor
    return response


def _revision(request):
    try:
        return int(request.POST.get("revision", ""))
    except ValueError:
        raise Http404("Saknar revision.") from None


@login_required
@company_required
def ad_list(request, workspace_id):
    company = request.workspace
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if not message:
            messages.error(request, "Skriv budskapet först.")
            return redirect("engine:ad_list", workspace_id=workspace_id)
        draft = service.start_draft(company, request.user, message=message)
        return redirect("engine:ad_workspace", workspace_id=workspace_id, draft_id=draft.pk)
    return render(request, "engine/ad_studio_list.html", {
        "workspace": company, "drafts": service.list_drafts(company),
    })


@login_required
@company_required
def ad_workspace(request, workspace_id, draft_id):
    company = request.workspace
    draft = _draft_or_404(company, draft_id)
    data = service.serialize(draft)
    brief = data["brief"]
    assets = service._assets_by_id(company, [s.get("asset_id") for s in brief["scenes"]])
    scenes = []
    elapsed = 0.0
    for scene in brief["scenes"]:
        asset = assets.get(scene.get("asset_id") or "")
        scenes.append({**scene, "label": SCENE_LABELS.get(scene["purpose"], scene["purpose"]),
                       "start": elapsed, "asset": asset})
        elapsed += scene["duration_s"]
    templates = [t for t in catalog(kind="template") if t["id"] in service.AD_TEMPLATES]
    return render(request, "engine/ad_studio_workspace.html", {
        "workspace": company, "draft": draft, "data": data, "brief": brief, "scenes": scenes,
        "objectives": OBJECTIVES, "templates": templates, "editable": draft.status == "draft",
    })


@login_required
@company_required
@require_POST
def ad_update(request, workspace_id, draft_id):
    company = request.workspace
    draft = _draft_or_404(company, draft_id)
    revision = _revision(request)
    post = request.POST
    try:
        template_id = post.get("template_id", "").strip()
        current_template = (draft.brief.get("engine") or {}).get("remotion_template_id")
        if template_id and template_id != current_template:
            draft = service.apply_template(company, draft.pk, template_id=template_id, expected_revision=revision)
            revision = draft.revision
        brief = draft.brief
        scenes = [dict(s) for s in brief.get("scenes", [])]
        for scene in scenes:
            key = f"scene_{scene['id']}_text"
            if key in post:
                scene["on_screen_text"] = post[key].strip()
        changes = {
            "message": post.get("message", brief.get("message", "")).strip(),
            "audience": post.get("audience", brief.get("audience", "")).strip(),
            "objective": post.get("objective") or brief.get("objective"),
            "copy": {**brief.get("copy", {}), "headline": post.get("headline", "").strip(),
                     "primary_text": post.get("primary_text", "").strip()},
            "scenes": scenes,
        }
        if post.get("facts_present"):
            checked = set(post.getlist("fact_verified"))
            facts = []
            for i, fact in enumerate(brief.get("facts", [])):
                verified = str(i) in checked
                if fact.get("fact_id"):  # the bank decides; a human checking it here verifies it in the bank
                    if verified != bool(fact.get("verified")):
                        service.set_fact(company, fact["fact_id"], status="verified" if verified else "unverified")
                facts.append({**fact, "verified": verified})
            changes["facts"] = facts
        title, hook = post.get("angle_title", "").strip(), post.get("angle_hook", "").strip()
        if title and hook:
            changes["angle"] = {**(brief.get("angle") or {}), "title": title, "hook": hook}
        service.update_draft(company, draft.pk, changes=changes, expected_revision=revision)
        messages.success(request, "Sparat.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return _back(workspace_id, draft_id)


@login_required
@company_required
def ad_pick(request, workspace_id, draft_id, scene_id):
    company = request.workspace
    draft = _draft_or_404(company, draft_id)
    scene = next((s for s in draft.brief.get("scenes", []) if s["id"] == scene_id), None)
    if scene is None:
        raise Http404("Scenen finns inte.")
    if request.method == "POST":
        revision = _revision(request)
        try:
            upload = request.FILES.get("file")
            if upload:
                from engine.media import store_asset
                from engine.media_storage import MediaError

                description = request.POST.get("description", "").strip() or upload.name
                try:
                    asset = store_asset(company, upload.read(), alt_text=description[:500])
                except MediaError as exc:
                    raise ValueError(str(exc)) from exc
                role = (service.SCENE_ROLES.get(scene["purpose"]) or ["footage"])[0]
                if scene_id in {"portal", "purchase", "app", "website", "receipt"}:
                    role = "screen"
                service.tag_asset(company, asset.pk, description=description, tags=[], roles=[role],
                                  source="uppladdad i studion", verified=True)
                asset_id = str(asset.pk)
            else:
                asset_id = request.POST.get("asset_id", "")
                uuid.UUID(asset_id)
            service.set_scene_asset(company, draft.pk, scene_id=scene_id, asset_id=asset_id, expected_revision=revision)
            messages.success(request, "Bilden är vald.")
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc) or "Välj en bild.")
            return redirect(request.path)
        return _back(workspace_id, draft_id, f"scene-{scene_id}")
    query = request.GET.get("q", "").strip()
    found = service.search_assets(company, query=query, limit=30)
    suggested = []
    if not query:
        try:
            suggestion = next(s for s in service.suggest_scene_assets(company, draft.pk)["scenes"]
                              if s["scene_id"] == scene_id)
            suggested = [c["id"] for c in suggestion["candidates"]]
        except (ValueError, StopIteration):
            suggested = []
    results = found["results"]
    results.sort(key=lambda r: (r["id"] not in suggested, 0))
    return render(request, "engine/ad_studio_pick.html", {
        "workspace": company, "draft": draft, "scene": scene,
        "label": SCENE_LABELS.get(scene["purpose"], scene["purpose"]), "results": results,
        "suggested": set(suggested), "query": query, "untagged": found["untagged_count"],
    })


@login_required
@company_required
@require_GET
def ad_storyboard(request, workspace_id, draft_id):
    company = request.workspace
    _draft_or_404(company, draft_id)
    try:
        data = service.storyboard_image(company, draft_id)
    except ValueError as exc:
        return HttpResponse(str(exc), status=409, content_type="text/plain; charset=utf-8")
    response = HttpResponse(data, content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@company_required
@require_POST
def ad_action(request, workspace_id, draft_id):
    company = request.workspace
    draft = _draft_or_404(company, draft_id)
    action = request.POST.get("action")
    try:
        if action == "lock":
            service.lock_draft(company, draft.pk, expected_revision=_revision(request))
            messages.success(request, "Briefen är låst. Nu kan den produceras exakt som den är.")
        elif action == "reopen":
            service.reopen_draft(company, draft.pk)
            messages.success(request, "Briefen är öppen för ändringar igen.")
        elif action == "produce":
            if draft.motion_project_id:
                return redirect("engine:motion_workspace", workspace_id=workspace_id, project_id=draft.motion_project_id)
            result = service.produce(company, request.user, draft.pk, key=request.POST.get("key") or str(uuid.uuid4()))
            if result["status"] == "motion_project_created":
                messages.success(request, "Videoprojektet är skapat. Granska och rendera här.")
                return redirect("engine:motion_workspace", workspace_id=workspace_id,
                                project_id=result["motion_project_id"])
            messages.info(request, result.get("next", "Generera de AI-bilder som saknas först."))
        elif action == "archive":
            draft.status = "archived"
            draft.save(update_fields=["status", "updated_at"])
            return redirect("engine:ad_list", workspace_id=workspace_id)
        else:
            raise ValueError("Okänd åtgärd.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return _back(workspace_id, draft_id)


def tags_for(asset):
    try:
        return asset.ad_tags
    except AssetTags.DoesNotExist:
        return None


@login_required
@company_required
def ad_facts(request, workspace_id):
    company = request.workspace
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "add":
                service.propose_fact(company, claim=request.POST.get("claim", ""), source=request.POST.get("source", ""),
                                     note=request.POST.get("note", ""))
                messages.success(request, "Påståendet är tillagt som ej verifierat.")
            elif action in {"verified", "unverified", "blocked"}:
                service.set_fact(company, request.POST.get("fact_id"), status=action)
                messages.success(request, "Status uppdaterad.")
            elif action == "save":
                service.set_fact(company, request.POST.get("fact_id"), claim=request.POST.get("claim"),
                                 source=request.POST.get("source"), note=request.POST.get("note"))
                messages.success(request, "Sparat. Ändrad formulering måste verifieras igen.")
            elif action == "delete":
                company.ad_facts.filter(pk=request.POST.get("fact_id")).delete()
                messages.success(request, "Borttaget.")
            else:
                raise ValueError("Okänd åtgärd.")
        except (ValueError, ValidationError) as exc:
            messages.error(request, str(exc) if not isinstance(exc, ValidationError) else "Ogiltigt id.")
        return redirect("engine:ad_facts", workspace_id=workspace_id)
    return render(request, "engine/ad_studio_facts.html", {"workspace": company, "facts": service.list_facts(company)})
