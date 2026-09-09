"""Register future performance/outcomes/shadow stages here; GitHub only starts run_daily."""

from datetime import timedelta
from functools import partial

from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from .competitors import OPEN_STATUSES, collect_import, start_import
from .daily import Result, Stage
from .media import advance_job, remove_asset
from .models import Competitor, MediaAsset, MediaGeneration
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
        run = start_import(account)
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
        if account.last_success_at and account.last_success_at > timezone.now()-timedelta(hours=23) and not account.imports.filter(status__in=OPEN_STATUSES).exists():
            continue
        # A manual early check must not mark a later-due refresh done for the entire day.
        anchor = account.last_success_at.isoformat() if account.last_success_at else "first"
        units.append((f"{account.pk}:{anchor}", partial(import_account, account)))
    return units


def analyze_post(post, company):
    fingerprint = classification_hash(post, company)
    classify(post, company)
    return Result(data={"post_id": post.pk, "classification_hash": fingerprint})


def analysis_units(company):
    # Failed imports do not prohibit analysis of already stored observations.
    # Wait only for known active provider jobs, not uncertain starts needing human attention.
    if company.daily_steps.filter(run__day=timezone.localdate(), stage="competitor_import", status="pending").exists():
        return [("await_imports", lambda: Result("pending", "Inväntar pågående importer före analys."))]
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
    if result.status in ("running", "starting"):
        return Result("pending", "Generation pågår; inget nytt betalt anrop startas.", data)
    return Result("attention", "Genereringen behöver kontroll i appen.", data)


def media_units(company):
    return [(str(j.pk), partial(collect_media, j)) for j in MediaGeneration.objects.filter(run__workspace=company).filter(
        Q(status__in=("queued", "starting", "running", "unknown")) | Q(updated_at__gte=timezone.now()-timedelta(hours=24)))]


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
    Stage("competitor_analysis", analysis_units),
)


def import_ads(account):
    from . import ads
    state = ads.account_state(account)
    if state.coverage == "limited":
        return Result("attention", "Annonsurvalet nådde resultatgränsen. Sparat underlag kan användas; kontrollera täckningen i Insikter.")
    request = ads.start(account)
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
        if state.next_attempt_at and state.next_attempt_at > timezone.now() and not state.requests.filter(status__in=OPEN_STATUSES).exists():
            # A failed dataset can be repaired/reprocessed in the UI without another paid run.
            latest = state.requests.order_by("-created_at").first()
            if latest and latest.status == "succeeded":
                for step in company.daily_steps.filter(run__day=timezone.localdate(), stage="ads_import", status__in=("attention", "failed"), result__request_id=latest.pk):
                    result.append((step.key, partial(import_ads, account)))
            continue
        result.append((f"{account.pk}:{state.watermark.isoformat() if state.watermark else 'first'}", partial(import_ads, account)))
    return result


def ads_analysis_units(company):
    from .ads import classification_hash, classify
    from .models import CompetitorAd
    if not company.profile.strip() or not company.current.strip():
        return []
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
    from .learning import dataset, train
    from .sync import fingerprint
    def work(channel):
        result = train(company, channel)
        return Result("skipped" if result["status"].startswith("insufficient") else "success",
                      "Learning: " + result["status"], result)
    return [(f"{channel}:{fingerprint([r.pk for r in dataset(company, channel)])}", partial(work, channel))
            for channel in ("organic", "paid")]


STAGES = (*STAGES, Stage("ads_import", ads_units), Stage("ads_analysis", ads_analysis_units), Stage("learning", learning_units))
