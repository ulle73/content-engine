"""Register future performance/outcomes/shadow stages here; GitHub only starts run_daily."""

from datetime import datetime, timedelta
from functools import partial

from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from .apify import ApifyError, BudgetExceeded
from .competitors import OPEN_STATUSES, collect_import, start_import
from .daily import Result, Stage
from .readiness import PROFILE_MISSING, analysis_ready
from .media import advance_job, remove_asset
from .models import Competitor, CompetitorImport, MediaAsset, MediaGeneration
from .signals import analysis_candidates, classification_hash, classify


def import_account(account):
    account.refresh_from_db()
    run = account.imports.filter(status__in=OPEN_STATUSES).first()
    if not run:
        if account.last_success_at and account.last_success_at > timezone.now()-timedelta(hours=23):
            return Result("success", "Färsk hämtning finns redan.", {"last_success_at": account.last_success_at.isoformat()})
        latest = account.imports.order_by("-started_at").first()
        if latest and latest.started_at > timezone.now()-timedelta(hours=23):
            collect_import(latest, allow_fallback=False)
            return Result("attention", "Senaste försöket behöver kontroll; ingen ny betald start inom 23 timmar.", {"import_id": latest.pk})
        try:
            run = start_import(account)
        except BudgetExceeded as exc:
            # The ceiling is policy, not a provider failure: nothing started, tomorrow's run takes it.
            return Result("blocked", str(exc))
    if not run.actor_run_id:
        return Result("attention", "Apify-starten är obekräftad. Kontrollera körningen i appen före nytt försök.", {"import_id": run.pk})
    result = collect_import(run)
    account.refresh_from_db()
    data = {"import_id": result.pk, "actor_run_id": result.actor_run_id, "actor": result.actor,
            "posts": result.item_count, "skipped": result.skipped_count, "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None}
    if result.status in OPEN_STATUSES or account.imports.filter(status__in=OPEN_STATUSES).exists():
        return Result("pending", "Apify arbetar; samma körnings-id återupptas.", data)
    if result.status == "succeeded" or (result.status == "partial" and account.last_success_at and account.last_success_at >= result.started_at):
        return Result("success", "Poster och snapshots sparade." + (" Enstaka dataluckor, ingen extra reservkörning." if result.status == "partial" else ""), data)
    return Result("attention", "Tillgängliga poster sparade; importen behöver kontroll.", data)


def competitor_units(company):
    units = []
    for account in Competitor.objects.filter(company=company, active=True):
        from .sync import state_for, refresh_due
        from .scraper_efficiency import discovery_due
        state = state_for(company,account.platform,account.username)
        if not discovery_due(state) and not refresh_due(state,timezone.now()) and not account.imports.filter(status__in=OPEN_STATUSES).exists():
            continue
        if account.last_success_at and account.last_success_at > timezone.now()-timedelta(hours=23) and not account.imports.filter(status__in=OPEN_STATUSES).exists():
            continue
        # A manual early check must not mark a later-due refresh done for the entire day.
        anchor = account.last_success_at.isoformat() if account.last_success_at else "first"
        units.append((f"{account.pk}:{anchor}", partial(import_account, account)))
    batchable = [u.args[0] for _, u in units if u.args[0].platform == "instagram"
                 and not u.args[0].imports.filter(status__in=OPEN_STATUSES).exists()]
    if len(batchable) >= 2:
        # Start them together first; each account's own unit then only collects its part of the shared run.
        units.insert(0, ("batch", partial(start_batch, "instagram", batchable)))
    return units


def start_batch(kind, accounts):
    """One shared Apify run per company (and per country/limit for ads) instead of one run per account."""
    from . import ads, competitors
    try:
        started = (competitors.start_batch if kind == "instagram" else ads.start_batch)(accounts)
    except BudgetExceeded as exc:
        return Result("blocked", str(exc))
    runs = sorted({r.actor_run_id for r in started if r.actor_run_id})
    if not started:
        return Result("skipped", "Inget konto behövde en ny hämtning.")
    return Result(message=f"{len(started)} konton startade i {len(runs)} Apify-körning(ar).",
                  data={"accounts": len(started), "runs": runs})


def analyze_post(post, company):
    fingerprint = classification_hash(post, company)
    classify(post, company)
    return Result(data={"post_id": post.pk, "classification_hash": fingerprint})


def imports_running(company):
    """Collect today's started imports that already finished at Apify; True while a known job still runs.

    Instagram runs are done in seconds, but the import stage is only polled again after a whole pass – which the
    ad stages can stretch over the full time budget – so waiting on the step status starved the analysis.
    """
    runs = CompetitorImport.objects.filter(competitor__company=company, competitor__active=True,
                                           status__in=OPEN_STATUSES).exclude(actor_run_id=None)
    for run in runs:
        try:
            collect_import(run)
        except ApifyError:
            pass  # still counted as running below; the import stage reports it
    return runs.all().exists()  # a fresh query, not the cache from the loop above


def analysis_units(company):
    # Failed imports do not prohibit analysis of already stored observations.
    # Wait only for known active provider jobs, not uncertain starts needing human attention.
    if (company.daily_steps.filter(run__day=timezone.localdate(), stage="competitor_import", status="pending").exists()
            and imports_running(company)):
        return [("await_imports", lambda: Result("pending", "Inväntar pågående importer före analys."))]
    if not analysis_ready(company):
        return [("needs-profile", lambda: Result("attention", PROFILE_MISSING))] if company.competitors.exists() else []
    return [("await_imports", lambda: Result("skipped", "Inga pågående importer."))] + [
        (f"{p.pk}:{classification_hash(p, company)}", partial(analyze_post, p, company)) for p in analysis_candidates(company)
    ]


def collect_media(job):
    job.refresh_from_db()
    # Daily never starts paid generation, including a queued image job left by a browser.
    if job.status == "queued":
        return Result("attention", "Öppna genereringen i appen för att starta den.")
    if job.status == "running" and not job.provider_id:
        return Result("attention", "Genereringen saknar bekräftat provider-id. Kontrollera leverantörskontot.")
    result = advance_job(job)
    data = {"job_id": str(job.pk), "run_id": str(job.run_id), "provider_id": job.provider_id, "assets": list(job.assets.values_list("id", flat=True))}
    data["assets"] = [str(value) for value in data["assets"]]
    if result.status == "completed":
        return Result(data=data)
    if result.status in ("running", "starting", "saving"):
        return Result("pending", "Generation pågår; inget nytt betalt anrop startas.", data)
    return Result("attention", "Genereringen behöver kontroll i appen.", data)


def media_units(company):
    return [(str(j.pk), partial(collect_media, j)) for j in MediaGeneration.objects.filter(run__workspace=company).filter(
        Q(status__in=("queued", "starting", "running", "saving", "unknown")) | Q(updated_at__gte=timezone.now()-timedelta(hours=24)))]


def expire_asset(asset):
    if not MediaAsset.objects.filter(pk=asset.pk).exists():
        return Result("success", "Filen har redan rensats.")
    if asset.storage_backend == "local" and settings.MEDIA_STORAGE != "local":
        return Result("attention", "Lokal fil kan inte rensas från R2-miljön. Kontrollera ursprunglig värd.")
    remove_asset(asset)
    return Result(message="Utgången oanvänd förhandsvisning rensad.")


def cleanup_units(company):
    return [(str(a.pk), partial(expire_asset, a)) for a in MediaAsset.objects.filter(
        company=company, expires_at__lte=timezone.now(), used_at__isnull=True).exclude(
        variations__status__in=("queued", "starting", "running", "unknown")).distinct()[:1000]]


STAGES = (
    Stage("competitor_import", competitor_units),
    Stage("media_collect", media_units),
    Stage("media_cleanup", cleanup_units),
    Stage("competitor_analysis", analysis_units, parallel=True),
)


def import_ads(account):
    from . import ads
    state = ads.account_state(account)
    if state.coverage == "limited":
        return Result("attention", "Annonsurvalet nådde resultatgränsen. Sparat underlag kan användas; kontrollera täckningen i Insikter.")
    try:
        request = ads.start(account)
    except BudgetExceeded as exc:
        return Result("blocked", str(exc))
    if not request:
        return Result("skipped", "Ingen annonskontroll behövs ännu.")
    if request.status in ("starting", "unknown") and not request.actor_run_id:
        return Result("attention", "Apify-starten behöver kontroll; ingen ny start görs.")
    request = ads.collect(request, account)
    data = {"request_id":request.pk, "actor":request.actor, "actor_run_id":request.actor_run_id,
            "cost_usd":str(request.cost_usd) if request.cost_usd is not None else None, **request.result}
    return Result("pending" if request.status in ("starting", "running") else
                  ("success" if request.status == "succeeded" else "attention"),
                  "Annonser kontrollerade; observationer sparade." if request.status == "succeeded" else "Annonskontrollen är pågående eller behöver åtgärd.", data)


def ads_units(company):
    from .ads import account_state
    result = []
    for account in company.ad_accounts.filter(active=True).select_related("sync"):
        state = account_state(account)
        from .scraper_efficiency import discovery_due
        from .sync import refresh_due
        if not discovery_due(state) and not refresh_due(state,timezone.now()) and not state.requests.filter(status__in=OPEN_STATUSES).exists():
            continue
        if state.next_attempt_at and state.next_attempt_at > timezone.now() and not state.requests.filter(status__in=OPEN_STATUSES).exists():
            # A failed dataset can be repaired/reprocessed in the UI without another paid run.
            latest = state.requests.order_by("-created_at").first()
            if latest and latest.status == "succeeded":
                for step in company.daily_steps.filter(run__day=timezone.localdate(), stage="ads_import", status__in=("attention", "failed"), result__request_id=latest.pk):
                    result.append((step.key, partial(import_ads, account)))
            continue
        result.append((f"{account.pk}:{state.watermark.isoformat() if state.watermark else 'first'}", partial(import_ads, account)))
    from .ads import batchable
    pages = [u.args[0] for key, u in result if not key.startswith(("batch",)) and batchable(u.args[0])
             and not account_state(u.args[0]).requests.filter(status__in=OPEN_STATUSES).exists()]
    if len(pages) >= 2:
        result.insert(0, ("batch", partial(start_batch, "ads", pages)))
    return result


def ads_analysis_units(company):
    from .ads import classification_hash, classify
    from .models import CompetitorAd
    if not analysis_ready(company):
        return [("needs-profile", lambda: Result("attention", PROFILE_MISSING))] if company.ad_accounts.exists() else []
    candidates = CompetitorAd.objects.filter(account__company=company, account__active=True).order_by("-last_seen_at", "-pk")[:100]
    units = []
    for ad in candidates:
        key = classification_hash(ad, company)
        if ad.classification and ad.classification_hash == key:
            continue
        def work(ad=ad, key=key):
            classify(ad, company)
            return Result(data={"ad_id":ad.pk, "classification_hash":key})
        units.append((f"{ad.pk}:{key}", work))
        if len(units) >= 3:
            break
    return units


def learning_units(company):
    from .learning import dataset, train, TARGETS
    from .models import OwnOutcome
    from .sync import fingerprint
    def work(channel,target):
        result = train(company, channel,target)
        return Result("skipped" if result["status"].startswith("insufficient") else "success",
                      "Learning: " + result["status"], result)
    result=[]
    for channel in ("organic","paid"):
        targets={TARGETS[channel],*OwnOutcome.objects.filter(prediction__run__workspace=company,prediction__channel=channel).exclude(target="").values_list("target",flat=True)}
        for target in sorted(targets):
            result.append((f"{channel}:{fingerprint([target,[r.pk for r in dataset(company,channel,target=target)]])}",partial(work,channel,target)))
    return result


def own_discovery_units(company):
    from .own_performance import discover
    if company.postiz_ciphertext and company.postiz_channels:
        from cryptography.fernet import InvalidToken
        try:
            company.postiz_key  # Validate runner configuration even when today's discovery was already completed.
        except InvalidToken as exc:
            raise ValueError("Postiz-kopplingen kunde inte dekrypteras. Kontrollera CONTENT_POSTIZ_ENCRYPTION_SECRET på körvärden.") from exc
    def work():
        from .postiz import PostizError
        try:
            data=discover(company)
        except PostizError as exc:
            if exc.status_code not in (401, 403):
                raise
            # A rejected key or lapsed plan needs a person, not a retry; the message is our own text.
            return Result("attention", str(exc), {"http_status": exc.status_code})
        return Result(data.pop("status","success"),data.get("message","Egna publiceringar kontrollerade."),data)
    return [("published",work)]


def own_snapshot_units(company):
    from .own_performance import collect
    def work(post):
        data=collect(post)
        return Result(data.pop("status","success"),data.get("message","Egen performance sparad."),data)
    return [(str(p.pk),partial(work,p)) for p in company.own_posts.filter(finalized_at=None).filter(Q(next_check_at=None)|Q(next_check_at__lte=timezone.now())).order_by("published_at","pk")[:10]]


def own_learning_units(company):
    from .own_performance import update_baselines, create_outcomes
    from .models import OwnSnapshot
    from .sync import fingerprint
    key=fingerprint(list(OwnSnapshot.objects.filter(post__company=company).values_list("pk",flat=True)))
    def work():
        return Result(data={**update_baselines(company),**create_outcomes(company)})
    return [(key,work)]


# Ad collection (a DB round trip per ad) and AI analysis wait on I/O; they run side by side (DAILY_PARALLEL).
STAGES = (*STAGES, Stage("ads_import", ads_units, parallel=True), Stage("ads_analysis", ads_analysis_units, parallel=True),
    Stage("own_discovery",own_discovery_units),Stage("own_snapshots",own_snapshot_units),
    Stage("own_outcomes",own_learning_units), Stage("learning", learning_units))

from .market import daily_units as market_units

STAGES = (*STAGES, Stage("market_intelligence", market_units))


def breakdown_reference(company, url, video_url=""):
    from .references import fetch, service

    try:
        ref = service.process(company, url, video_url=video_url)
    except fetch.FetchError as exc:
        status = "attention" if "429" in str(exc) else "skipped"
        return Result(status, str(exc)[:300], {"url": url})
    return Result("success", f"Referens nedbruten: {ref.breakdown.get('summary', '')}"[:300],
                  {"reference_id": str(ref.pk), "url": url, "cost_usd": str(ref.cost_usd)})


def reference_units(company):
    """Break down the best new competitor ads (running ≥ REFERENCE_MIN_DAYS) so 'our version' is one call away.
    At most REFERENCE_DAILY_LIMIT per company and day (default 2, 0 turns it off); an ad without video is tried once."""
    import os

    from .models import DailyStep
    from .references import service

    limit = int(os.environ.get("REFERENCE_DAILY_LIMIT", "2") or 0)
    if limit <= 0 or not os.environ.get("OPENROUTER_API_KEY", "").strip():
        return []
    min_days = int(os.environ.get("REFERENCE_MIN_DAYS", "14") or 0)
    tried = set(DailyStep.objects.filter(company=company, stage="reference_breakdown")
                .exclude(status="attention").values_list("key", flat=True))
    units = []
    for row in service.candidates(company, limit=60):
        if len(units) >= limit:
            break
        key = row["ad_id"] if row["kind"] == "ad" else f"{row['platform']}:{row['post_id']}"
        if row["reference_id"] or key in tried or (row["kind"] == "ad" and row["days_running"] < min_days):
            continue
        units.append((key, partial(breakdown_reference, company, row["url"], row.get("video_url", ""))))
    return units


STAGES = (*STAGES, Stage("reference_breakdown", reference_units))


def idea_units(company):
    """Pitch new hits (own posts first) and send at most IDEA_WEEKLY_MAX idea cards a week to Discord (engine/ideas).
    Off with IDEA_DAILY_LIMIT=0 or without an OpenRouter key."""
    import os

    from .ideas import service
    from .review.service import ReviewError

    if service.daily_breakdowns() <= 0 or not os.environ.get("OPENROUTER_API_KEY", "").strip():
        return []

    def work():
        try:
            data = service.daily(company)
        except ReviewError as exc:
            return Result("attention", f"Idékortet kunde inte skickas: {exc}"[:300])
        if data["sent"]:
            sent = f" Skickat: {data['sent']}."
        elif data["week_full_until"]:
            until = timezone.localtime(datetime.fromisoformat(data["week_full_until"]))
            sent = (f" Inget kort skickat – veckans {service.weekly_max()} kort är redan skickade, nästa går tidigast "
                    f"{until.day}/{until.month} {until:%H:%M}. {data['waiting']} idéer väntar.")
        else:
            sent = f" Inget kort skickat – ingen idé nådde fit {service.min_fit()}."
        status = "attention" if data["errors"] and not data["pitched"] else "success"
        return Result(status, f"{len(data['pitched'])} nya idéer bedömda.{sent}"[:300], data)

    return [("ideas", work)]


STAGES = (*STAGES, Stage("ideas", idea_units, always=True))


# Morning start phase: Apify runs take seconds to minutes, so starting them about half an hour before the full run
# lets that run collect finished data instead of spending its time budget waiting.
START_STAGES = tuple(stage for stage in STAGES if stage.name in ("competitor_import", "ads_import"))
