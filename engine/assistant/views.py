"""Thin authenticated browser adapters; orchestration lives in the shared service."""
import hashlib
import json
import uuid

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pydantic import ValidationError

from engine.creative_controls import creation_catalog
from engine.media import describe_file, store_asset
from engine.media_storage import MediaError
from engine.models import AssistantConversation
from engine.ownership import company_required

from . import registry, service, templates


def _json(request):
    if len(request.body) > 80_000:
        raise ValueError("Meddelandet är för stort.")
    value = json.loads(request.body)
    if not isinstance(value, dict):
        raise ValueError("Skicka ett giltigt meddelande.")
    return value


def _error(exc):
    if isinstance(exc, ValidationError):
        return "Kontrollera meddelandet, bilagorna och inställningarna."
    if isinstance(exc, json.JSONDecodeError):
        return "Meddelandet kunde inte läsas. Ladda om sidan och försök igen."
    return str(exc)[:600]


@login_required
@company_required
def workspace(request, workspace_id, conversation_id=None):
    company = request.workspace
    conversation = None
    if conversation_id:
        try:
            conversation = service.owned(company, request.user, conversation_id)
        except ValueError:
            raise Http404 from None
    return render(request, "engine/assistant_workspace.html", {
        "workspace": company, "conversation": conversation,
        "conversations": company.conversations.all()[:30],
        "assistant_state": service.state(company, request.user, conversation.pk) if conversation else {"revision": 0, "turns": []},
        "assistant_catalog": {"workflows": registry.catalog(), "templates": templates.catalog(company),
                              "models": {kind: creation_catalog(kind)["models"] for kind in ("image", "video")}},
    })


@login_required
@company_required
@require_POST
def create(request, workspace_id):
    try:
        data = _json(request)
        key = uuid.UUID(str(data.get("key", "")))
        # Client-generated identity also makes network retries safe before a first turn.
        try:
            with transaction.atomic():
                conversation, _ = AssistantConversation.objects.get_or_create(pk=key, company=request.workspace,
                                                                             defaults={"author": request.user})
        except IntegrityError:
            conversation = AssistantConversation.objects.filter(pk=key, company=request.workspace).first()
            if not conversation:
                raise ValueError("Använd en ny samtalsnyckel.") from None
        return JsonResponse({"id": str(conversation.pk)})
    except (ValueError, ValidationError) as exc:
        return JsonResponse({"error": _error(exc)}, status=422)


@login_required
@company_required
@require_GET
def state(request, workspace_id, conversation_id):
    try:
        return JsonResponse(service.state(request.workspace, request.user, conversation_id))
    except ValueError:
        return JsonResponse({"error": "Samtalet finns inte."}, status=404)


@login_required
@company_required
@require_POST
def send(request, workspace_id, conversation_id):
    try:
        conversation = service.send_turn(request.workspace, request.user, conversation_id, _json(request))
        return JsonResponse(service.state(request.workspace, request.user, conversation.pk))
    except (ValueError, MediaError) as exc:
        return JsonResponse({"error": _error(exc)}, status=422)


@login_required
@company_required
@require_POST
def action(request, workspace_id, conversation_id):
    try:
        conversation = service.act(request.workspace, request.user, conversation_id, _json(request))
        return JsonResponse(service.state(request.workspace, request.user, conversation.pk))
    except (ValueError, MediaError) as exc:
        return JsonResponse({"error": _error(exc)}, status=422)


@login_required
@company_required
@require_GET
def assets(request, workspace_id):
    query = request.GET.get("q", "").strip()[:200]
    try:
        page = max(0, min(int(request.GET.get("page", "0")), 1000))
    except ValueError:
        return JsonResponse({"error": "Ogiltig sida."}, status=422)
    rows = service.available_assets(request.workspace)
    if query:
        rows = rows.filter(Q(alt_text__icontains=query) | Q(brief__icontains=query))
    rows = list(rows.order_by("-created_at", "-pk")[page * 24:page * 24 + 25])
    return JsonResponse({"assets": [service.file_info(request.workspace, asset) for asset in rows[:24]], "next_page": page + 1 if len(rows) > 24 else None})


@login_required
@company_required
@require_POST
def upload(request, workspace_id):
    try:
        file = request.FILES.get("file")
        if not file or file.size > 80 * 1024 * 1024:
            raise ValueError("Välj en bild, video eller ljudfil, högst 80 MB.")
        data = file.read()
        metadata = describe_file(data)
        if metadata["kind"] == "image" and len(data) > 8 * 1024 * 1024:
            raise ValueError("Bilder får vara högst 8 MB.")
        sha = hashlib.sha256(data).hexdigest()
        asset = service.available_assets(request.workspace).filter(sha256=sha).order_by("created_at").first()
        asset = asset or store_asset(request.workspace, data, alt_text=request.POST.get("description") or file.name)
        return JsonResponse(service.file_info(request.workspace, asset))
    except (ValueError, MediaError) as exc:
        return JsonResponse({"error": _error(exc)}, status=422)


@login_required
@company_required
@require_POST
def save_template(request, workspace_id):
    try:
        templates.save(request.workspace, request.user, _json(request))
        return JsonResponse({"templates": templates.catalog(request.workspace)})
    except (ValueError, ValidationError) as exc:
        return JsonResponse({"error": _error(exc)}, status=422)


@login_required
@company_required
@require_POST
def refresh_job(request, workspace_id, conversation_id):
    """Polling advances an already explicitly started job, never a queued generation."""
    from engine.media import advance_job
    from engine.models import MediaGeneration
    try:
        conversation = service.owned(request.workspace, request.user, conversation_id)
        prepared = [plan.prepared for turn in conversation.turns.select_related("plan")
                    if (plan := getattr(turn, "plan", None)) and plan.prepared.get("kind") in {"media", "sequence"}]
        jobs = MediaGeneration.objects.filter(pk__in=[key for item in prepared for key in (item.get("job_ids") or [item["job_id"]])], run__workspace=request.workspace,
                                               status__in=["starting", "running", "saving"]).order_by("updated_at")[:5]
        for job in jobs:
            advance_job(job)
            from engine.sequence import sync_sequence_generation
            sync_sequence_generation(job)
        return JsonResponse(service.state(request.workspace, request.user, conversation.pk))
    except (ValueError, MediaError) as exc:
        return JsonResponse({"error": _error(exc)}, status=422)
