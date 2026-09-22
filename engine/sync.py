"""Shared paid-call boundary for every scraper and cached intelligence analysis.

Reservations precede external POSTs. Unknown starts are never retried automatically.
No provider credentials or unsafe raw errors belong in durable ledgers.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from . import apify
from .models import AnalysisMemo, Company, ScrapeRequest, ScraperState

OPEN = ("starting", "running", "unknown")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def state_for(company, source, key):
    return ScraperState.objects.get_or_create(company=company, source=source, external_key=str(key))[0]


def dispatch(state, actor, mode, inputs, *, max_cost="0.10", sender=None):
    now = timezone.now()
    key = fingerprint([state.pk, actor, mode, timezone.localdate().isoformat()])
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=state.company_id)
        state = ScraperState.objects.select_for_update().get(pk=state.pk)
        existing = state.requests.filter(status__in=OPEN).first() or state.requests.filter(key=key).first()
        if existing:
            return existing
        cap = Decimal(max_cost)
        daily_limit = min(Decimal(os.environ.get("SCRAPER_DAILY_BUDGET_USD", "1.00")), Decimal("10"))
        spent = sum(
            (r.cost_usd if r.cost_usd is not None else r.max_cost_usd)
            for r in ScrapeRequest.objects.filter(state__company_id=state.company_id, created_at__date=timezone.localdate())
        )
        if cap <= 0 or spent + cap > daily_limit:
            raise apify.ApifyError("Dagens kostnadsgräns för företagets scrapers är nådd. Försök nästa dygn.")
        request = ScrapeRequest.objects.create(
            state=state, key=key, actor=actor, mode=mode, inputs=inputs, max_cost_usd=cap
        )
        if mode == "backfill" and not state.backfill_attempted_at:
            state.backfill_attempted_at = now
            state.save(update_fields=["backfill_attempted_at"])
        if mode == "refresh":
            state.details = {**state.details, "last_refresh_attempt_at": now.isoformat()}
            state.save(update_fields=["details"])
    try:
        remote = (
            sender()
            if sender
            else apify.api(
                "POST",
                f"/acts/{actor.replace('/', '~')}/runs",
                json=inputs,
                params={"timeout": 300, "maxTotalChargeUsd": float(cap)},
            )["data"]
        )
        if not remote.get("id") or not remote.get("defaultDatasetId"):
            raise apify.ApifyError("Startsvaret saknar körnings-id.", uncertain=True)
    except Exception as exc:
        if isinstance(exc, apify.ApifyError):
            uncertain = exc.uncertain
            safe_error = str(exc)[:500] or "Apify avvisade körningen utan feltext."
            status_code = exc.status_code
            error_type = exc.error_type
        else:
            uncertain = True
            safe_error = "Providerstarten kunde inte bekräftas. Kontrollera Apify före nytt försök."
            status_code = getattr(exc, "status_code", None)
            error_type = None
        request.status = "unknown" if uncertain else "failed"
        request.result = {
            "error": safe_error,
            "http_status": status_code,
            "error_type": error_type,
        }
        if request.status == "failed":
            request.cost_usd = Decimal("0")  # Definitively rejected POST, no Actor run accepted.
        request.save(update_fields=["status", "result", "cost_usd"])
        raise apify.ApifyError(
            safe_error,
            uncertain=uncertain,
            status_code=status_code,
            error_type=error_type,
        ) from exc
    request.actor_run_id, request.dataset_id, request.status = remote["id"], remote["defaultDatasetId"], "running"
    request.save(update_fields=["actor_run_id", "dataset_id", "status"])
    return request


def finish(request, *, status, cost, result, observed_at):
    existing = ScrapeRequest.objects.get(pk=request.pk).result
    if existing.get("yield"):
        result = {**result, "yield": existing["yield"]}
    ScrapeRequest.objects.filter(pk=request.pk).update(
        status=status, cost_usd=cost, result=result, finished_at=observed_at
    )


def analysis(company, key, model, work, *, scrape_request_id=None):
    """Cross-entrypoint deduplication; uncertain paid analysis requires explicit review.

    Max 12 new classifications/company/day, including manual clicks. Cache hits are free.
    A private provider-usage object may be stored beside a classification, but it is
    always stripped before the classification is returned to callers.
    """
    key = fingerprint([key, model])
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=company.pk)
        memo = AnalysisMemo.objects.filter(company=company, key=key).first()
        if memo:
            if memo.status == "completed":
                cached = dict(memo.result or {})
                cached.pop("_provider_usage", None)
                return cached
            if memo.status == "rejected" and (memo.last_attempt_at or memo.created_at) <= timezone.now() - timedelta(hours=23):
                memo.status, memo.last_attempt_at = "started", timezone.now()
                memo.attempts += 1
                memo.save(update_fields=["status", "last_attempt_at", "attempts"])
            else:
                raise ValueError(
                    "Analysen har redan startats men kunde inte bekräftas. Kontrollera analysloggen före nytt betalt försök."
                )
        limit = min(50, max(0, int(os.environ.get("INTELLIGENCE_DAILY_ANALYSES", "12"))))
        from django.db.models import Q

        today = AnalysisMemo.objects.filter(company=company).filter(
            Q(last_attempt_at__date=timezone.localdate())
            | Q(last_attempt_at=None, created_at__date=timezone.localdate())
        )
        if today.exclude(pk=memo.pk if memo else None).count() >= limit:
            raise ValueError("Dagens gräns för nya AI-analyser är nådd. Sparade analyser går fortfarande att använda.")
        if not memo:
            memo = AnalysisMemo.objects.create(
                company=company,
                key=key,
                model=model,
                last_attempt_at=timezone.now(),
                scrape_request_id=scrape_request_id,
            )
    try:
        raw_result = work()
    except Exception as exc:
        if getattr(exc, "retryable", False):
            # Text classification has no external side effect. A provider/routing
            # failure must not lock the same analysis for 23 hours.
            AnalysisMemo.objects.filter(pk=memo.pk).delete()
        else:
            status = getattr(exc, "status_code", None)
            AnalysisMemo.objects.filter(pk=memo.pk).update(
                status="rejected" if isinstance(status, int) and 400 <= status < 500 else "unknown"
            )
        raise
    result = dict(raw_result) if isinstance(raw_result, dict) else raw_result
    stored = result
    if isinstance(result, dict):
        provider_usage = result.pop("_provider_usage", None)
        stored = {**result, "_provider_usage": provider_usage} if provider_usage else result
    AnalysisMemo.objects.filter(pk=memo.pk).update(status="completed", result=stored)
    return result


def refresh_due(state, now):
    dates = [d for d in (state.last_refresh_at, state.backfill_attempted_at) if d]
    if state.details.get("last_refresh_attempt_at"):
        dates.append(datetime.fromisoformat(state.details["last_refresh_attempt_at"]))
    return not dates or max(dates) <= now - timedelta(days=7)


def organic_plan(account, state):
    """Primary Actor has no cursor/date/direct-post input: use bounded recent-feed overlap.

    One bounded backfill attempt; daily 10 newest, weekly 30 for older metrics.
    Existing local history counts as initialized and never triggers a new backfill.
    """
    now = timezone.now()
    if not state.backfill_attempted_at and (account.last_success_at or account.posts.exists()):
        state.backfill_attempted_at = account.last_success_at or now
        state.watermark = account.posts.order_by("-published_at").values_list("published_at", flat=True).first()
        state.last_refresh_at = account.last_success_at
        state.save()
    if not state.backfill_attempted_at:
        return "backfill", 100
    if refresh_due(state, now):
        return "refresh", 30
    from .scraper_efficiency import discovery_limit

    return "discovery", discovery_limit(state)
