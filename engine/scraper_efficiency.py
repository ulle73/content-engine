"""Measured yield, not local deduplication, drives provider request frequency."""
from datetime import datetime, timedelta
from math import ceil
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import ScrapeRequest, ScraperState


def discovery_due(state, now=None):
    value = state.details.get("discovery_due_at")
    return not value or datetime.fromisoformat(value) <= (now or timezone.now())


def discovery_limit(state):
    return state.details.get("discovery_limit", 10 if state.source == "instagram" else 20)


def record_yield(request, *, returned, before, after, complete, capabilities):
    """before/after map stable external IDs to hashes of persisted useful data.

    Metrics/status changes count as changed; AI has its own narrower content hash.
    A replay cannot double-count costs, observations or adaptation decisions.
    """
    with transaction.atomic():
        locked = ScrapeRequest.objects.select_for_update().get(pk=request.pk)
        previous=locked.result.get("yield")
        groups={"new":[k for k in after if k not in before],"changed":[k for k in after if k in before and before[k]!=after[k]],
                "known":[k for k in after if k in before and before[k]==after[k]]}
        if previous:
            old=previous.get("object_ids")
            if not old:  # Earlier telemetry versions remain historical evidence.
                return previous
            seen=set().union(*(set(ids) for ids in old.values()))
            if set(after).issubset(seen):
                return previous
            groups={key:sorted(set(old[key]) | (set(ids)-seen)) for key,ids in groups.items()}
            returned=max(returned,previous["returned"])
        new,changed,known=(len(groups[k]) for k in ("new","changed","known"))
        useful = new+changed
        stats = {"version":1, "returned":returned, "new":new, "changed":changed, "known":known,
                 "previously_known":known+changed, "unusable_or_duplicate":max(0,returned-new-changed-known),"object_ids":groups,
                 "useful":useful, "cost_per_useful_usd":str(locked.cost_usd/Decimal(useful)) if useful and locked.cost_usd is not None else None,
                 "capabilities":capabilities, "complete":complete}
        locked.result = {**locked.result, "yield":stats}
        locked.save(update_fields=["result"])
        state = ScraperState.objects.select_for_update().get(pk=locked.state_id)
        # Failed/partial runs never look like quiet accounts and never reset historical state.
        if complete and locked.mode != "refresh" and not previous:
            idle = 0 if new else min(3, state.details.get("empty_discoveries",0)+1)
            days = (1,2,4,7)[idle]
            previous = state.details.get("last_new",0)
            busy = new >= 8 and previous >= 8
            minimum = 10 if state.source == "instagram" else 5
            limit = (20 if busy else 10) if state.source=="instagram" else max(minimum,min(20,max(len(after)+2,2*max(new,previous)+2)))
            unit_cost = float(locked.cost_usd)/returned if returned and locked.cost_usd is not None else 0
            # Expensive accounts use fewer checks, rather than shrinking below a known useful Ads result set.
            days = min(7,max(days,ceil(unit_cost*limit/.05)))
            now = locked.finished_at or timezone.now()
            state.details = {**state.details, "empty_discoveries":idle, "last_new":new,
                "discovery_interval_days":days, "discovery_limit":limit,"estimated_item_cost_usd":unit_cost,
                "discovery_due_at":(now+timedelta(days=days)-timedelta(hours=1)).isoformat()}
            state.save(update_fields=["details"])
        return stats


def report(company):
    requests = list(ScrapeRequest.objects.filter(state__company=company).select_related("state").annotate(
        analysis_count=Count("analysis_memos",filter=Q(analysis_memos__status="completed"))).order_by("-created_at")[:100])
    totals = {"returned":0,"new":0,"changed":0,"known":0,"measured_cost":Decimal(0),"all_reported_cost":Decimal(0),"ai":0}
    for request in requests:
        stats=request.result.get("yield")
        request.efficiency=stats
        request.ai_analyses=request.analysis_count
        totals["ai"] += request.ai_analyses
        totals["all_reported_cost"] += request.cost_usd or Decimal(0)
        if stats:
            for key in ("returned","new","changed","known"):
                totals[key] += stats[key]
            totals["measured_cost"] += request.cost_usd or Decimal(0)
    useful=totals["new"]+totals["changed"]
    totals["cost_per_useful"] = totals["measured_cost"]/useful if useful else None
    return {"requests":requests, "totals":totals}
