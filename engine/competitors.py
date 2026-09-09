"""Import only explicit competitor accounts, retaining post identity and real observations."""

import math
import re
from datetime import datetime, timedelta
from datetime import timezone as utc
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from . import apify
from .models import Competitor, CompetitorImport, CompetitorPost, CompetitorSnapshot

OPEN_STATUSES = ("starting", "running", "unknown")


def instagram_username(value):
    value = value.strip()
    if "://" in value:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname not in {"instagram.com", "www.instagram.com"}:
            raise ValueError("Ange en Instagram-profil med https://www.instagram.com/ eller ett användarnamn.")
        value = parsed.path.strip("/")
    value = value.lstrip("@").lower()
    if not re.fullmatch(r"[a-z0-9_][a-z0-9_.]{0,29}", value) or value in {
        "p",
        "reel",
        "reels",
        "stories",
        "explore",
        "accounts",
    }:
        raise ValueError("Ange profilens användarnamn, inte länken till en enskild post.")
    return value


def number(value, *, integer=True):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return (int(result) if integer else result) if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def normalize(row, actor, username):
    primary = actor == apify.PRIMARY_ACTOR
    handle = row.get("usuario", "") if primary else row.get("ownerUsername", "")
    input_handle = urlparse(row.get("inputUrl", "")).path.strip("/").lower()
    if handle.lstrip("@").lower() != username and input_handle != username:
        raise ValueError("Posten tillhör inte det valda kontot.")
    code = row.get("codigo" if primary else "shortCode")
    url = row.get("link_post" if primary else "url", "")
    parsed = urlparse(url)
    if parsed.hostname not in {"www.instagram.com", "instagram.com"}:
        raise ValueError("Ogiltig Instagram-länk.")
    match = re.fullmatch(r"/(p|reel|reels)/([A-Za-z0-9_-]+)/?", parsed.path)
    if not match or (code and code != match[2]):
        raise ValueError("Postens identitet saknas eller motsäger länken.")
    code = match[2]
    kind = row.get("media_type" if primary else "type")
    format_name = {1: "image", 2: "reel", 8: "carousel", "Image": "image", "Video": "reel", "Sidecar": "carousel"}.get(
        kind
    )
    if not format_name:
        raise ValueError("Okänt Instagram-format.")
    timestamp = row.get("data_criacao_iso" if primary else "timestamp")
    if not timestamp:
        raise ValueError("Publiceringsdatum saknas.")
    published = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if published.tzinfo is None:
        published = published.replace(tzinfo=utc.utc)
    if published > timezone.now() + timedelta(minutes=15):
        raise ValueError("Publiceringsdatum ligger i framtiden.")
    caption = row.get("caption")
    if isinstance(caption, dict):
        caption = caption.get("text", "")
    children = row.get("itens_carrossel" if primary else "childPosts")
    view_key = (
        "visualizacoes"
        if primary
        else ("videoPlayCount" if row.get("videoPlayCount") is not None else "videoViewCount")
    )
    return {
        "shortcode": code,
        "instagram_id": str(row.get("id") or ""),
        "url": f"https://www.instagram.com/{match[1]}/{code}/",
        "published_at": published,
        "caption": caption if isinstance(caption, str) else "",
        "format": format_name,
        "duration_seconds": number(row.get("duracao" if primary else "videoDuration"), integer=False)
        if format_name == "reel"
        else None,
        "slide_count": len(children) if format_name == "carousel" and isinstance(children, list) and children else None,
        "metrics": {
            "likes": number(row.get("curtidas" if primary else "likesCount")),
            "comments": number(row.get("comentarios" if primary else "commentsCount")),
            "views": number(row.get(view_key)) if format_name == "reel" else None,
            "view_metric": view_key if format_name == "reel" else "",
        },
    }


def start_import(competitor, *, actor=apify.PRIMARY_ACTOR, fallback_of=None):
    from .sync import dispatch, organic_plan, state_for
    with transaction.atomic():
        current = Competitor.objects.select_for_update().get(pk=competitor.pk)
        existing = current.imports.filter(status__in=OPEN_STATUSES).first()
        if existing:
            return existing
        if not current.active:
            raise apify.ApifyError("Kontot är inaktiverat.")
        if fallback_of:
            previous = current.imports.filter(fallback_of=fallback_of).first()
        else:
            previous = current.imports.filter(started_at__gte=timezone.now()-timedelta(hours=23)).order_by("-started_at").first()
        if previous:
            return previous
        state = state_for(current.company, "instagram", current.username)
        mode, limit = organic_plan(current, state)
        if fallback_of:
            mode, limit = fallback_of.sync_mode, fallback_of.requested_limit
        run = CompetitorImport.objects.create(
            competitor=current, actor=actor, fallback_of=fallback_of, requested_limit=limit, sync_mode=mode
        )
    try:
        request = dispatch(state, actor, mode, apify.instagram_input(current.username, actor, limit),
            max_cost="0.05" if actor == apify.PRIMARY_ACTOR else "0.25",
            sender=lambda: apify.start_actor(current.username, actor, limit))
    except apify.ApifyError as exc:
        # A POST timeout can mean the paid run did start; never automatically duplicate it.
        run.status = "unknown" if exc.uncertain else "failed"
        run.scrape_request = state.requests.filter(actor=actor, mode=mode).order_by("-created_at").first()
        run.error = (
            "Starten kunde inte bekräftas. Kontrollera Apify och koppla körnings-id innan ett nytt försök."
            if exc.uncertain
            else str(exc)
        )
        run.save(update_fields=["status", "error", "scrape_request"])
        raise
    # A cross-entrypoint reservation is authoritative even after a process interruption.
    run.scrape_request = request
    run.actor_run_id = request.actor_run_id
    run.dataset_id = request.dataset_id
    run.status = request.status if request.status in OPEN_STATUSES else "failed"
    run.save(update_fields=["scrape_request", "actor_run_id", "dataset_id", "status"])
    return run


def collect_import(run, *, allow_fallback=True):
    if run.status not in OPEN_STATUSES or not run.actor_run_id:
        if run.status not in OPEN_STATUSES and run.scrape_request_id:
            # A web process from the previous deployment may have completed the domain import.
            from .sync import OPEN, finish
            if run.scrape_request.status in OPEN:
                finish(run.scrape_request, status=run.status, cost=run.cost_usd,
                    result={"posts":run.item_count, "skipped":run.skipped_count},
                    observed_at=run.finished_at or timezone.now())
        return run
    remote = apify.get_run(run.actor_run_id)
    if remote["status"] in {"READY", "RUNNING", "TIMING-OUT", "ABORTING"}:
        return run
    succeeded = remote["status"] == "SUCCEEDED"
    incomplete = not succeeded
    report_error = False
    if succeeded and run.actor == apify.PRIMARY_ACTOR:
        report = apify.api("GET", f"/key-value-stores/{remote['defaultKeyValueStoreId']}/records/OUTPUT")
        entries = [u for u in report.get("users", []) if u.get("user", "").lower() == run.competitor.username]
        report_error = not report.get("ok") or not entries or any(u.get("erro") for u in entries)
    rows = apify.dataset_items(remote["defaultDatasetId"])
    # An error on the very last page is tolerable when nearly all requested data arrived.
    if report_error and len(rows) < run.requested_limit * 0.8:
        incomplete = True
    normalized, skipped = [], 0
    for row in rows:
        try:
            normalized.append(normalize(row, run.actor, run.competitor.username))
        except (ValueError, TypeError, KeyError, AttributeError):
            skipped += 1
    # A few malformed posts and absent optional metrics do not justify a second paid run.
    # Caption plus at least one public engagement metric is the minimum useful intelligence.
    useful = sum(
        bool(p["caption"].strip()) and any(p["metrics"][k] is not None for k in ("likes", "comments"))
        for p in normalized
    )
    if (not normalized and (rows or report_error or not succeeded)) or skipped > len(rows) * 0.2 or useful < len(normalized) * 0.7:
        incomplete = True
    quality_warning = report_error or bool(skipped) or useful < len(normalized)
    observed_at = datetime.fromisoformat(remote["finishedAt"].replace("Z", "+00:00"))
    with transaction.atomic():
        locked = CompetitorImport.objects.select_for_update().get(pk=run.pk)
        if locked.status not in OPEN_STATUSES:
            return locked
        normalized = list({item["shortcode"]: item for item in normalized}.values())
        if normalized:
            posts = CompetitorPost.objects.bulk_create(
                [
                    CompetitorPost(competitor=run.competitor, **{k: v for k, v in item.items() if k != "metrics"})
                    for item in normalized
                ],
                update_conflicts=True,
                unique_fields=["competitor", "shortcode"],
                update_fields=[
                    "instagram_id",
                    "url",
                    "published_at",
                    "caption",
                    "format",
                    "duration_seconds",
                    "slide_count",
                ],
            )
            CompetitorSnapshot.objects.bulk_create(
                [
                    CompetitorSnapshot(post=post, import_run=locked, observed_at=observed_at, **item["metrics"])
                    for post, item in zip(posts, normalized, strict=True)
                ],
                ignore_conflicts=True,
            )
        locked.status = (
            "partial" if normalized and (incomplete or quality_warning) else ("failed" if incomplete else "succeeded")
        )
        locked.finished_at = observed_at
        locked.cost_usd = remote.get("usageTotalUsd")
        locked.item_count = len(normalized)
        locked.skipped_count = skipped
        locked.error = (
            "Väsentligt ofullständig hämtning eller otillräckliga kritiska data. Resultaten har sparats."
            if incomplete
            else ("Användbar hämtning med enstaka dataluckor; ingen reservhämtning behövs." if quality_warning else "")
        )
        locked.save()
        updates = {"last_error": locked.error}
        if not incomplete:
            updates["last_success_at"] = observed_at
        Competitor.objects.filter(pk=run.competitor_id).update(**updates)
        if locked.scrape_request_id:
            from .sync import finish
            state = locked.scrape_request.state
            finish(locked.scrape_request, status=locked.status, cost=locked.cost_usd,
                   result={"posts":len(normalized), "skipped":skipped}, observed_at=observed_at)
            if not incomplete:
                newest = max((p["published_at"] for p in normalized), default=state.watermark)
                if newest and (not state.watermark or newest > state.watermark):
                    state.watermark = newest
                if locked.sync_mode in ("backfill", "refresh"):
                    state.last_refresh_at = observed_at
                state.coverage = "bounded_recent_feed"
                state.details = {**state.details, "limit":locked.requested_limit, "mode":locked.sync_mode,
                                 "cursor_supported":False, "cap_reached":len(rows) >= locked.requested_limit}
                state.save()
    if incomplete and allow_fallback and run.actor == apify.PRIMARY_ACTOR:
        start_import(run.competitor, actor=apify.FALLBACK_ACTOR, fallback_of=locked)
    return locked
