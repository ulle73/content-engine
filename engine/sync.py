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


FINISHED_RUN = ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED")


def daily_limit():
    return min(Decimal(os.environ.get("SCRAPER_DAILY_BUDGET_USD", "0.50")), Decimal("10"))


def spent_today(company_id, settled=None):
    """Reported cost, else the reserved cap. `settled` holds real costs of finished but uncollected runs."""
    settled = settled or {}
    return sum(
        (settled.get(r.pk, r.cost_usd if r.cost_usd is not None else r.max_cost_usd)
         for r in ScrapeRequest.objects.filter(state__company_id=company_id, created_at__date=timezone.localdate())),
        Decimal("0"),
    )


def settled_costs(company_id):
    """Real cost of today's Apify runs that already finished but are not collected yet.

    An Instagram run is done in seconds, yet its 0.02 USD cap stays reserved until a later pass collects it,
    so nine of them used to block the day's ad checks. Read-only: collection still records the cost.
    """
    settled, members = {}, {}
    for request in (ScrapeRequest.objects.filter(state__company_id=company_id, created_at__date=timezone.localdate(),
                                                 cost_usd=None).exclude(actor_run_id=None)
                    .exclude(actor_run_id__contains=":").order_by("pk")):  # "virlo:…" reports its own cost
        members.setdefault(request.actor_run_id, []).append(request.pk)
    for run_id, pks in members.items():
        try:
            remote = apify.get_run(run_id)
        except apify.ApifyError:
            continue
        cost = remote.get("usageTotalUsd")
        if remote.get("status") in FINISHED_RUN and isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
            # A batch run is shared by several accounts: its cost counts once.
            settled.update({pk: Decimal("0") for pk in pks})
            settled[pks[0]] = Decimal(str(cost))
    return settled


def dispatch(state, actor, mode, inputs, *, max_cost="0.10", sender=None, provider="apify", period=None):
    now = timezone.now()
    key = fingerprint([state.pk, actor, mode, period or timezone.localdate().isoformat()])
    limit = daily_limit()
    settled = {}
    if spent_today(state.company_id) + Decimal(max_cost) > limit:
        settled = settled_costs(state.company_id)  # outside the lock: one GET per uncollected run
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=state.company_id)
        state = ScraperState.objects.select_for_update().get(pk=state.pk)
        existing = state.requests.filter(status__in=OPEN).first() or state.requests.filter(key=key).first()
        if existing:
            return existing
        cap = Decimal(max_cost)
        # A ceiling per company and day, not the expected spend (typically a few cents); reserved caps count until
        # a run reports its real cost.
        spent = spent_today(state.company_id, settled)
        if cap <= 0 or spent + cap > limit:
            raise apify.BudgetExceeded(
                f"Dagens kostnadsgräns för företagets scrapers är nådd ({spent:.3f} av {limit:.2f} USD använt eller "
                f"reserverat, körningen behöver {cap:.3f}). Försök nästa dygn.")
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
        if not remote.get("id") or (provider == "apify" and not remote.get("defaultDatasetId")):
            raise apify.ApifyError("Startsvaret saknar körnings-id.", uncertain=True)
    except Exception as exc:
        if isinstance(exc, apify.ApifyError):
            uncertain = exc.uncertain
            safe_error = str(exc)[:500] or "Apify avvisade körningen utan feltext."
            status_code = exc.status_code
            error_type = exc.error_type
        else:
            uncertain = True
            provider_label = "Virlo" if provider == "virlo" else "Apify"
            safe_error = f"Providerstarten kunde inte bekräftas. Kontrollera {provider_label} före nytt försök."
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
    request.actor_run_id = remote["id"] if provider == "apify" else f"{provider}:{remote['id']}"
    request.dataset_id, request.status = remote.get("defaultDatasetId", ""), "running"
    if provider != "apify":
        request.cost_usd = remote.get("cost_usd")
        request.result = {"provider": provider, "remote_id": remote["id"]}
    request.save(update_fields=["actor_run_id", "dataset_id", "status", "cost_usd", "result"])
    return request


BATCH_TIMEOUT_BASE_S = 300
BATCH_TIMEOUT_PER_ACCOUNT_S = 90


def dispatch_batch(members, actor, inputs, *, period=None, sender=None):
    """One Apify run for several accounts of one company: fewer concurrent runs (the free plan allows 5) and one
    start instead of many. Every account keeps its own ScrapeRequest – ledger, yield, watermark and collection stay
    per account – and they all share the run id. `members` are (state, mode, account_inputs, max_cost); keys of
    `inputs` starting with "_" are ours and never sent.

    Returns {state.pk: request}; an account with an open or same-day request keeps that one and is not started."""
    if not members:
        return {}
    company_id = members[0][0].company_id
    if any(state.company_id != company_id for state, *_ in members):
        raise ValueError("En batch hör till ett företag.")
    now = timezone.now()
    day = period or timezone.localdate().isoformat()
    limit = daily_limit()
    wanted = sum((Decimal(cap) for *_, cap in members), Decimal("0"))
    settled = settled_costs(company_id) if spent_today(company_id) + wanted > limit else {}
    result, created, requests = {}, [], []
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=company_id)
        for state, mode, account_inputs, member_cap in members:
            state = ScraperState.objects.select_for_update().get(pk=state.pk)
            key = fingerprint([state.pk, actor, mode, day])
            existing = state.requests.filter(status__in=OPEN).first() or state.requests.filter(key=key).first()
            if existing:
                result[state.pk] = existing
                continue
            created.append((state, mode, account_inputs, Decimal(member_cap), key))
        if not created:
            return result
        cap = sum((member[3] for member in created), Decimal("0"))
        spent = spent_today(company_id, settled)
        if cap <= 0 or spent + cap > limit:
            raise apify.BudgetExceeded(
                f"Dagens kostnadsgräns för företagets scrapers är nådd ({spent:.3f} av {limit:.2f} USD använt eller "
                f"reserverat, batchen behöver {cap:.3f}). Försök nästa dygn.")
        batch = {"accounts": len(created), "max_items": inputs.get("_max_items")}
        for state, mode, account_inputs, member_cap, key in created:
            request = ScrapeRequest.objects.create(state=state, key=key, actor=actor, mode=mode,
                                                   inputs={**account_inputs, "batch": batch}, max_cost_usd=member_cap)
            if mode == "backfill" and not state.backfill_attempted_at:
                state.backfill_attempted_at = now
                state.save(update_fields=["backfill_attempted_at"])
            if mode == "refresh":
                state.details = {**state.details, "last_refresh_attempt_at": now.isoformat()}
                state.save(update_fields=["details"])
            requests.append(request)
            result[state.pk] = request
    body = {k: v for k, v in inputs.items() if not k.startswith("_")}
    # One account takes up to ~30 s (Instagram, 100 posts); the single-run 300 s would cut a batch short.
    # Time is not billed per se – maxTotalChargeUsd still caps the spend.
    timeout = min(BATCH_TIMEOUT_BASE_S + BATCH_TIMEOUT_PER_ACCOUNT_S * len(created), 3600)
    try:
        remote = sender() if sender else apify.api(
            "POST", f"/acts/{actor.replace('/', '~')}/runs", json=body,
            params={"timeout": timeout, "maxTotalChargeUsd": float(cap)})["data"]
        if not remote.get("id") or not remote.get("defaultDatasetId"):
            raise apify.ApifyError("Startsvaret saknar körnings-id.", uncertain=True)
    except Exception as exc:
        uncertain = exc.uncertain if isinstance(exc, apify.ApifyError) else True
        safe_error = (str(exc)[:500] if isinstance(exc, apify.ApifyError) else
                      "Providerstarten kunde inte bekräftas. Kontrollera Apify före nytt försök.")
        status = "unknown" if uncertain else "failed"
        for request in requests:
            request.status, request.result = status, {
                "error": safe_error, "http_status": getattr(exc, "status_code", None),
                "error_type": getattr(exc, "error_type", None)}
            if status == "failed":
                request.cost_usd = Decimal("0")  # Definitively rejected POST, no Actor run accepted.
            request.save(update_fields=["status", "result", "cost_usd"])
        raise apify.ApifyError(safe_error, uncertain=uncertain, status_code=getattr(exc, "status_code", None),
                               error_type=getattr(exc, "error_type", None)) from exc
    ScrapeRequest.objects.filter(pk__in=[r.pk for r in requests]).update(
        actor_run_id=remote["id"], dataset_id=remote["defaultDatasetId"], status="running")
    for request in requests:
        request.actor_run_id, request.dataset_id, request.status = remote["id"], remote["defaultDatasetId"], "running"
    return result


def batch_share(request, own_rows, all_rows, total_cost):
    """An account's part of a shared run's cost, by the rows it got (evenly when the run returned nothing)."""
    if total_cost is None:
        return None
    members = max(1, int((request.inputs.get("batch") or {}).get("accounts") or 1))
    share = Decimal(own_rows) / Decimal(all_rows) if all_rows else Decimal(1) / members
    return (Decimal(str(total_cost)) * share).quantize(Decimal("0.000001"))


def finish(request, *, status, cost, result, observed_at):
    existing = ScrapeRequest.objects.get(pk=request.pk).result
    if existing.get("yield"):
        result = {**result, "yield": existing["yield"]}
    ScrapeRequest.objects.filter(pk=request.pk).update(
        status=status, cost_usd=cost, result=result, finished_at=observed_at
    )


def analysis(company, key, model, work, *, scrape_request_id=None, retry_uncertain=True):
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
            last_attempt = memo.last_attempt_at or memo.created_at
            openrouter_stale = (
                retry_uncertain
                and
                str(model).startswith("openrouter:")
                and memo.status in {"started", "unknown"}
                and last_attempt <= timezone.now() - timedelta(seconds=30)
            )
            rejected_retry = memo.status == "rejected" and last_attempt <= timezone.now() - timedelta(hours=23)
            if openrouter_stale or rejected_retry:
                # OpenRouter classification is side-effect free and cheap/free-first.
                # A worker restart can interrupt us after the provider responded but
                # before the memo was committed, so recycle stale text memos quickly.
                memo.status, memo.last_attempt_at = "started", timezone.now()
                memo.attempts += 1
                memo.save(update_fields=["status", "last_attempt_at", "attempts"])
            else:
                raise ValueError(
                    "Analysen kör redan eller väntar på bekräftelse. Försök igen om en kort stund."
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
        if retry_uncertain and getattr(exc, "retryable", False):
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
