import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import market, virlo
from .apify import ApifyError
from .models import MarketItem, ScrapeRequest
from .ownership import company_required

STATUS_LABELS = {"starting": "Startar", "running": "Pågår", "unknown": "Behöver kontrolleras",
                 "succeeded": "Klar", "failed": "Misslyckades", "partial": "Delvis klar"}


@login_required
@company_required
def intelligence(request, workspace_id):
    company = request.workspace
    channel = "paid" if request.GET.get("channel") == "paid" else "organic"
    items = market.candidates(company, channel)
    items = [item for item in items if not item.classification or item.classification.get("profile_relevance", 0) >= 2]
    for item in items:
        item.analysis_current = item.classification_hash == market.classification_key(item, company)
        item.linked_sources = market.linked_sources(item)
        item.studio_token = uuid.uuid4()
    runs = ScrapeRequest.objects.filter(state__company=company, state__source=market.SOURCE).order_by("-created_at")
    recent_runs = list(runs[:8])
    for run in recent_runs:
        run.status_label = STATUS_LABELS.get(run.status, "Behöver kontrolleras")
    return render(request, "engine/market.html", {"workspace": company, "channel": channel,
        "items": items[:20], "patterns": market.patterns([i for i in items if i.analysis_current]),
        "runs": recent_runs, "latest": recent_runs[0] if recent_runs else None, "configured": virlo.configured(),
        "dismissed": company.market_items.filter(channel=channel, preference=-1).order_by("-feedback_at")[:20],
        "cost": runs.aggregate(total=Sum("cost_usd"))["total"], "unknown_cost": runs.filter(cost_usd=None).exists()})


@login_required
@company_required
@require_POST
def action(request, workspace_id):
    company = request.workspace
    try:
        if request.POST.get("action") == "toggle":
            company.market_intelligence_enabled = not company.market_intelligence_enabled
            company.save(update_fields=["market_intelligence_enabled"])
        else:
            run = market.collect(market.start(company))
            if run.status == "succeeded":
                market.analyze_top(company)
                messages.success(request, "Marknadsinspirationen är uppdaterad.")
            else:
                messages.info(request, f"Research: {STATUS_LABELS.get(run.status, 'Behöver kontrolleras')}. Ingen ny betald körning startas vid statuskontroll.")
    except (ValueError, ApifyError) as exc:
        messages.error(request, str(exc))
    return redirect("engine:market_intelligence", workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def feedback(request, workspace_id, item_id):
    item = get_object_or_404(MarketItem, pk=item_id, company=request.workspace)
    choice = request.POST.get("preference")
    if choice not in {"-1", "0", "1"}:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("Ogiltig relevansfeedback.")
    item.preference, item.feedback_at = int(choice), timezone.now()
    item.save(update_fields=["preference", "feedback_at"])
    messages.success(request, "Relevansfeedback sparad för företaget.")
    from django.urls import reverse
    return redirect(reverse("engine:market_intelligence", kwargs={"workspace_id": workspace_id}) + "?channel=" + item.channel)
