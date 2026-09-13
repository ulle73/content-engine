"""Provider cost accounting for the Content Engine UI.

Apify and Higgsfield already return dollar amounts. OpenAI returns token usage,
so those calls are priced from the published API rate card. Historical OpenAI
text calls made before usage tracking was added cannot be reconstructed exactly.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from django.utils import timezone

from .models import AnalysisMemo, ContentEvent, MediaGeneration, ScrapeRequest

MILLION = Decimal("1000000")

# Published OpenAI API prices per 1M tokens, verified 2026-09-13.
TEXT_RATES = {
    "gpt-5.6-luna": {"input": Decimal("0.20"), "cached": Decimal("0.02"), "output": Decimal("1.20")},
    "gpt-5.6-terra": {"input": Decimal("2.00"), "cached": Decimal("0.20"), "output": Decimal("12.00")},
    "gpt-5.6-sol": {"input": Decimal("4.00"), "cached": Decimal("0.40"), "output": Decimal("20.00")},
    "gpt-5.6": {"input": Decimal("4.00"), "cached": Decimal("0.40"), "output": Decimal("20.00")},
}
IMAGE_RATES = {
    "text_input": Decimal("5.00"),
    "text_cached": Decimal("1.25"),
    "image_input": Decimal("8.00"),
    "image_cached": Decimal("2.00"),
    "image_output": Decimal("30.00"),
}


def _decimal(value, default=Decimal("0")):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else default
    except (InvalidOperation, TypeError, ValueError):
        return default


def _int(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _model_rate(model):
    model = str(model or "")
    if model in TEXT_RATES:
        return TEXT_RATES[model]
    for prefix, rates in TEXT_RATES.items():
        if model.startswith(prefix + "-"):
            return rates
    return None


def openai_text_cost(meta):
    """Price a Responses API usage object. Returns None for unknown models."""
    if not isinstance(meta, dict):
        return None
    rates = _model_rate(meta.get("model"))
    usage = meta.get("usage") or {}
    if not rates or not isinstance(usage, dict):
        return None
    input_tokens = _int(usage.get("input_tokens") or usage.get("prompt_tokens"))
    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    cached = min(input_tokens, _int(details.get("cached_tokens")) if isinstance(details, dict) else 0)
    output_tokens = _int(usage.get("output_tokens") or usage.get("completion_tokens"))
    multiplier_in = Decimal("2") if input_tokens > 272000 and str(meta.get("model", "")).startswith("gpt-5.6") else Decimal("1")
    multiplier_out = Decimal("1.5") if input_tokens > 272000 and str(meta.get("model", "")).startswith("gpt-5.6") else Decimal("1")
    cost = (
        Decimal(input_tokens - cached) * rates["input"] * multiplier_in
        + Decimal(cached) * rates["cached"] * multiplier_in
        + Decimal(output_tokens) * rates["output"] * multiplier_out
    ) / MILLION
    return cost.quantize(Decimal("0.00000001"))


def openai_usage_meta(response, operation):
    usage = getattr(response, "usage", None)
    return {
        "provider": "openai",
        "service": "text",
        "operation": str(operation or "text")[:80],
        "model": str(getattr(response, "model", "") or ""),
        "response_id": str(getattr(response, "id", "") or ""),
        "usage": usage.model_dump() if usage and hasattr(usage, "model_dump") else {},
        "pricing_verified": "2026-09-13",
    }


def openai_image_cost(job):
    """Price stored Image API usage. Returns (cost, partial)."""
    if not str(job.parameters.get("model", "")).startswith("gpt-image-2"):
        return None, False
    usage = job.usage or {}
    if not isinstance(usage, dict):
        return None, False
    output = _int(usage.get("output_tokens"))
    total_input = _int(usage.get("input_tokens"))
    details = usage.get("input_tokens_details") or {}
    text_tokens = _int(details.get("text_tokens")) if isinstance(details, dict) else 0
    image_tokens = _int(details.get("image_tokens")) if isinstance(details, dict) else 0
    cached = _int(details.get("cached_tokens")) if isinstance(details, dict) else 0
    partial = False

    if not text_tokens and not image_tokens and total_input:
        if not job.source_asset_id:
            text_tokens = total_input
        else:
            # Edits may mix text and image input. Without the provider breakdown
            # only output can be priced without inventing an allocation.
            partial = True
    input_cost = Decimal("0")
    if text_tokens or image_tokens:
        # The Image API normally reports the split. If it reports only a combined
        # cached count, apply it to text first and then image, conservatively.
        cached_text = min(text_tokens, cached)
        cached_image = min(image_tokens, max(0, cached - cached_text))
        input_cost = (
            Decimal(text_tokens - cached_text) * IMAGE_RATES["text_input"]
            + Decimal(cached_text) * IMAGE_RATES["text_cached"]
            + Decimal(image_tokens - cached_image) * IMAGE_RATES["image_input"]
            + Decimal(cached_image) * IMAGE_RATES["image_cached"]
        ) / MILLION
    if not output and not total_input and not text_tokens and not image_tokens:
        return None, False
    cost = input_cost + Decimal(output) * IMAGE_RATES["image_output"] / MILLION
    return cost.quantize(Decimal("0.00000001")), partial


def _usage_from_memo(memo):
    result = memo.result or {}
    return result.get("_provider_usage") if isinstance(result, dict) else None


def _event_row(at, provider, service, description, cost, basis, model="", status=""):
    return {
        "at": at,
        "provider": provider,
        "service": service,
        "description": description,
        "cost_usd": cost,
        "basis": basis,
        "model": model,
        "status": status,
    }


def cost_summary(company):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = []
    unknown = 0

    scrape = ScrapeRequest.objects.filter(state__company=company).select_related("state")
    apify_total = scrape.aggregate(value=Sum("cost_usd"))["value"] or Decimal("0")
    apify_month = scrape.filter(created_at__gte=month_start).aggregate(value=Sum("cost_usd"))["value"] or Decimal("0")
    for item in scrape.exclude(cost_usd=None).order_by("-created_at")[:50]:
        rows.append(_event_row(item.created_at, "Apify", "Scraping", f"{item.state.source} · {item.mode}", item.cost_usd, "Leverantör rapporterad", item.actor, item.status))

    text_total = Decimal("0")
    text_month = Decimal("0")
    text_calls = 0
    first_text_tracking = None

    for event in ContentEvent.objects.filter(run__workspace=company, action="provider_usage").select_related("run"):
        meta = event.data or {}
        if meta.get("provider") != "openai" or meta.get("service") != "text":
            continue
        cost = openai_text_cost(meta)
        text_calls += 1
        first_text_tracking = min(first_text_tracking or event.created_at, event.created_at)
        if cost is None:
            unknown += 1
            continue
        text_total += cost
        if event.created_at >= month_start:
            text_month += cost
        rows.append(_event_row(event.created_at, "OpenAI", "Text", meta.get("operation", "Text"), cost, "Beräknad från tokens", meta.get("model", ""), "completed"))

    for memo in AnalysisMemo.objects.filter(company=company):
        meta = _usage_from_memo(memo)
        if not meta:
            continue
        cost = openai_text_cost(meta)
        text_calls += 1
        first_text_tracking = min(first_text_tracking or memo.created_at, memo.created_at)
        if cost is None:
            unknown += 1
            continue
        text_total += cost
        if memo.created_at >= month_start:
            text_month += cost
        rows.append(_event_row(memo.created_at, "OpenAI", "AI-analys", meta.get("operation", "Analys"), cost, "Beräknad från tokens", meta.get("model", memo.model), memo.status))

    image_total = Decimal("0")
    image_month = Decimal("0")
    image_partial = 0
    higgs_total = Decimal("0")
    higgs_month = Decimal("0")
    higgs_unknown = 0
    jobs = MediaGeneration.objects.filter(run__workspace=company).select_related("run", "source_asset")
    for job in jobs:
        if job.provider == "openai" and job.status == "completed":
            cost, partial = openai_image_cost(job)
            if cost is None:
                unknown += 1
                continue
            image_total += cost
            if job.created_at >= month_start:
                image_month += cost
            image_partial += int(partial)
            rows.append(_event_row(job.created_at, "OpenAI", "Bild", job.brief[:100], cost, "Beräknad från tokens" + (" · delvis" if partial else ""), job.parameters.get("model", ""), job.status))
        elif job.provider == "higgsfield":
            estimate = (job.usage or {}).get("estimate", {}) if isinstance(job.usage, dict) else {}
            cost = _decimal(estimate.get("usd"), default=Decimal("-1")) if isinstance(estimate, dict) else Decimal("-1")
            if job.status in {"running", "completed"} and cost >= 0:
                higgs_total += cost
                if job.created_at >= month_start:
                    higgs_month += cost
                rows.append(_event_row(job.created_at, "Higgsfield", "Video", job.brief[:100], cost, "Accepterat prisestimat", (job.usage or {}).get("model", ""), job.status))
            elif job.status == "unknown" and cost >= 0:
                higgs_unknown += 1

    known_total = apify_total + text_total + image_total + higgs_total
    known_month = apify_month + text_month + image_month + higgs_month
    rows.sort(key=lambda row: row["at"] or datetime.min.replace(tzinfo=timezone.get_current_timezone()), reverse=True)

    return {
        "total_usd": known_total,
        "month_usd": known_month,
        "apify_usd": apify_total,
        "apify_month_usd": apify_month,
        "openai_text_usd": text_total,
        "openai_text_month_usd": text_month,
        "openai_image_usd": image_total,
        "openai_image_month_usd": image_month,
        "higgsfield_usd": higgs_total,
        "higgsfield_month_usd": higgs_month,
        "text_calls": text_calls,
        "text_tracking_started_at": first_text_tracking,
        "unknown_cost_count": unknown,
        "image_partial_count": image_partial,
        "higgsfield_unknown_count": higgs_unknown,
        "recent": rows[:50],
    }
