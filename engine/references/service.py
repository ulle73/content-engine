"""Reference videos: fetch → store → measure → break down → our version. Used by MCP, the CLI and the daily job.

Every step is saved on the ReferenceVideo, so a slow call that a chat client gives up on can be read back with
get_reference, and a second breakdown with another model is kept next to the first for comparison.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from engine import media_storage
from engine.models import CompetitorAd, CompetitorPost

from . import adapt, breakdown, fetch, measure
from .models import ReferenceVideo

INSTAGRAM_POST = re.compile(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


class _Stored:
    """Duck-typed stand-in for media_storage.open_asset (it only needs a backend and a key)."""

    def __init__(self, backend: str, key: str):
        self.storage_backend, self.storage_key, self.generation_base_key = backend, key, ""


def _key(ref: ReferenceVideo, name: str) -> str:
    return f"references/{ref.company_id}/{ref.pk}/{name}"


def _add_cost(ref: ReferenceVideo, cost) -> None:
    if cost is not None:
        ref.cost_usd = (ref.cost_usd or Decimal(0)) + Decimal(str(cost))


def _link_source(company, url: str) -> dict:
    ad_id = fetch.ad_library_id(url)
    if ad_id:
        ad = CompetitorAd.objects.filter(account__company=company, external_id=ad_id).select_related("account").first()
        return {"source_kind": "meta_ad", "competitor_ad": ad, "author": ad.account.name if ad else "",
                "title": ((ad.creative.get("headline") or ad.creative.get("text") or "") if ad else "")[:300]}
    match = INSTAGRAM_POST.search(url)
    if match:
        post = CompetitorPost.objects.filter(competitor__company=company, shortcode=match.group(1)) \
            .select_related("competitor").first()
        return {"source_kind": "instagram", "competitor_post": post,
                "author": post.competitor.username if post else "", "title": (post.caption if post else "")[:300]}
    return {"source_kind": "url"}


def store(company, url: str) -> ReferenceVideo:
    """Fetch the video and keep our own copy. The same file for the same company is stored once."""
    linked = _link_source(company, url)
    got = fetch.fetch(url)
    sha = hashlib.sha256(got.data).hexdigest()
    existing = ReferenceVideo.objects.filter(company=company, sha256=sha).first()
    if existing:
        return existing
    backend = media_storage.check_storage(settings.MEDIA_STORAGE)
    with transaction.atomic():
        ref = ReferenceVideo(company=company, source_url=got.source_url, storage_backend=backend, sha256=sha,
                             byte_size=len(got.data), author=(linked.pop("author", "") or got.author)[:200],
                             title=(linked.pop("title", "") or got.title)[:300], **linked)
        ref.storage_key = _key(ref, "video.mp4")
        media_storage.put(ref.storage_key, got.data, got.mime, backend)
        ref.save()
    return ref


def _read(ref: ReferenceVideo, key: str) -> bytes:
    with media_storage.open_asset(_Stored(ref.storage_backend, key)) as file:
        return file.read()


def measure_reference(ref: ReferenceVideo) -> ReferenceVideo:
    result = measure.measure(_read(ref, ref.storage_key), title=f"{ref.author} – {ref.title}".strip(" –")[:110])
    ref.proxy_key, ref.sheet_key = _key(ref, "proxy.mp4"), _key(ref, "sheet.jpg")
    media_storage.put(ref.proxy_key, result.pop("proxy"), "video/mp4", ref.storage_backend)
    sheet = result.pop("sheet")
    if sheet:
        media_storage.put(ref.sheet_key, sheet, "image/jpeg", ref.storage_backend)
    else:
        ref.sheet_key = ""
    probe = result["probe"]
    ref.measurements = result
    ref.duration_s, ref.width, ref.height = probe["duration_s"], probe["width"], probe["height"]
    ref.status, ref.error = "measured", ""
    ref.save()
    return ref


def _context(ref: ReferenceVideo) -> dict:
    out = {"url": ref.source_url, "kind": ref.source_kind}
    if ref.competitor_ad:
        ad = ref.competitor_ad
        end = ad.end_date or ad.last_seen_at.date()
        out.update({"ad_text": (ad.creative.get("text") or "")[:1500], "headline": ad.creative.get("headline"),
                    "days_running": (end - ad.start_date).days if ad.start_date else None,
                    "active": ad.is_active})
    return out


def analyze(ref: ReferenceVideo, *, model: str = "", make_current: bool | None = None) -> ReferenceVideo:
    """Break the reference down with `model` (default: REFERENCE_VIDEO_MODEL / the video tier). Keeps every run."""
    if not ref.proxy_key:
        measure_reference(ref)
    result, meta = breakdown.run(_read(ref, ref.proxy_key), ref.measurements, model=model, title=ref.title,
                                 author=ref.author, context=_context(ref))
    entry = {"model": meta.get("model") or model, "requested_model": meta.get("requested_model"),
             "cost_usd": meta.get("cost_usd"), "usage": meta.get("usage"),
             "created_at": timezone.now().isoformat(), "breakdown": result}
    ref.analyses = [*ref.analyses, entry]
    if make_current or (make_current is None and not ref.breakdown):
        ref.breakdown = {**result, "model": entry["model"]}
    _add_cost(ref, meta.get("cost_usd"))
    ref.status, ref.error = "analyzed", ""
    ref.save()
    return ref


def process(company, url: str, *, model: str = "") -> ReferenceVideo:
    """URL → stored, measured and broken down (skips steps already done for the same file)."""
    ref = store(company, url)
    try:
        if not ref.proxy_key:
            measure_reference(ref)
        if not ref.breakdown:
            analyze(ref, model=model)
    except Exception as exc:
        ref.status, ref.error = "failed", str(exc)[:500]
        ref.save(update_fields=["status", "error", "updated_at"])
        raise
    return ref


def plan_our_version(ref: ReferenceVideo, *, angle: str = "", notes: str = "", model: str = "") -> dict:
    reference = {"title": ref.title, "author": ref.author, "url": ref.source_url,
                 "measurements": ref.measurements.get("summary"), "breakdown": ref.breakdown}
    sheet = _read(ref, ref.sheet_key) if ref.sheet_key else None
    entry = adapt.run(ref.company, reference, sheet=sheet, angle=angle, notes=notes, model=model)
    ref.adaptations = [*ref.adaptations, entry]
    _add_cost(ref, entry.get("cost_usd"))
    ref.save(update_fields=["adaptations", "cost_usd", "updated_at"])
    return entry


def reach(ad: CompetitorAd) -> int | None:
    latest = ad.observations.order_by("-observed_at").values_list("data", flat=True).first() or {}
    return (latest.get("metrics") or {}).get("eu_total_reach")


def candidates(company, *, limit: int = 15, known: dict | None = None) -> list[dict]:
    """Monitored ads worth studying: long-running (= it works) and wide reach first. Says if already broken down."""
    done = known if known is not None else dict(
        ReferenceVideo.objects.filter(company=company, competitor_ad__isnull=False)
        .values_list("competitor_ad_id", "id"))
    rows = []
    today = timezone.localdate()
    for ad in CompetitorAd.objects.filter(account__company=company, account__active=True).select_related("account"):
        end = ad.end_date or (today if ad.is_active else ad.last_seen_at.date())
        days = (end - ad.start_date).days if ad.start_date else 0
        rows.append({"ad_id": ad.external_id, "advertiser": ad.account.name, "days_running": days,
                     "active": ad.is_active, "start_date": str(ad.start_date or ""), "eu_reach": reach(ad),
                     "headline": (ad.creative.get("headline") or "")[:120],
                     "text": (ad.creative.get("text") or "")[:200].replace("\n", " "),
                     "url": fetch.ad_library_url(ad.external_id),
                     "reference_id": str(done[ad.pk]) if ad.pk in done else None})
    rows.sort(key=lambda r: (r["days_running"] * (2 if r["active"] else 1), r["eu_reach"] or 0), reverse=True)
    # Breadth first: every advertiser's best ad before anyone's second, so one prolific advertiser can't fill the list.
    seen, first, rest = set(), [], []
    for row in rows:
        (rest if row["advertiser"] in seen else first).append(row)
        seen.add(row["advertiser"])
    return (first + rest)[:limit]


def serialize(ref: ReferenceVideo, *, full: bool = False) -> dict:
    data = {
        "reference_id": str(ref.pk), "status": ref.status, "error": ref.error, "source_url": ref.source_url,
        "source_kind": ref.source_kind, "author": ref.author, "title": ref.title, "duration_s": ref.duration_s,
        "size": f"{ref.width}x{ref.height}" if ref.width else "", "cost_usd": str(ref.cost_usd),
        "measured": ref.measurements.get("summary"), "has_sheet": bool(ref.sheet_key),
        "breakdown_models": [a.get("model") for a in ref.analyses],
        "adaptations": [{"adaptation_id": a["id"], "angle": a.get("angle"), "title": a["plan"].get("title"),
                         "created_at": a.get("created_at")} for a in ref.adaptations],
    }
    if ref.breakdown:
        b = ref.breakdown
        data["breakdown"] = b if full else {k: b.get(k) for k in (
            "summary", "format", "hook", "structure", "why_it_works", "mechanics", "quality_score", "quality_note")}
    if full:
        data["measurements"] = {k: ref.measurements.get(k) for k in ("cuts", "scenes", "audio")}
    return data
