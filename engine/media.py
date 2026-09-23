"""Media attached to existing content runs. No queue, worker service, or new publishing path."""

import io
import hashlib
import uuid
import warnings
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from openai import APIConnectionError, APIError
from PIL import Image, UnidentifiedImageError
import av

from . import media_providers as providers
from .creative_director import build_plan
from .prompt_library import retrieve_inspiration
from .media_storage import MediaError, check_storage, delete_file, put
from .models import Company, ContentEvent, ContentRun, MediaAsset, MediaGeneration

PENDING = ("queued", "starting", "running", "saving")
ACTIVE = PENDING + ("unknown",)
TERMINAL = ("completed", "failed", "nsfw", "canceled", "unknown")


def describe_file(data):
    if len(data) > 80 * 1024 * 1024 or not data:
        raise MediaError("Välj en fil mellan 1 byte och 80 MB.")
    if len(data) >= 12 and data[4:8] == b"ftyp":
        try:
            with av.open(io.BytesIO(data)) as container:
                stream = next(iter(container.streams.video), None)
                if not stream or stream.codec_context.name != "h264" or data[8:12] == b"qt  ":
                    raise MediaError("Video ska vara MP4 med H.264-kodning.")
                frame = next(container.decode(video=0), None)
                duration = float(stream.duration * stream.time_base) if stream.duration is not None else (container.duration / av.time_base if container.duration else None)
                if not frame or not duration or duration <= 0:
                    raise MediaError("Videon saknar läsbar bild eller längd.")
                return {"kind": "video", "mime_type": "video/mp4", "extension": "mp4", "width": frame.width,
                        "height": frame.height, "duration_seconds": duration}
        except (av.error.FFmpegError, ValueError) as exc:
            raise MediaError("Videofilen kunde inte läsas. Välj MP4 med H.264-kodning.") from exc
    if len(data) > 8 * 1024 * 1024:
        raise MediaError("Bilder får vara högst 8 MB. Video ska vara MP4 och högst 80 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as img:
                if img.format not in {"PNG", "JPEG", "WEBP"} or img.width * img.height > 40_000_000:
                    raise MediaError("Välj JPEG, PNG eller WebP, högst 40 megapixel.")
                kind, width, height = img.format, img.width, img.height
                img.verify()
        return {"kind": "image", "mime_type": Image.MIME[kind], "extension": {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[kind],
                "width": width, "height": height}
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise MediaError("Filen kunde inte läsas som JPEG, PNG, WebP eller MP4.") from exc


def store_asset(company, data, *, job=None, index=0, alt_text="", purpose="content"):
    metadata = describe_file(data)
    if job and metadata["kind"] != job.kind:
        raise MediaError("Leverantören returnerade fel typ av media.")
    asset_id = uuid.uuid5(job.id, str(index)) if job else uuid.uuid4()
    existing = MediaAsset.objects.filter(pk=asset_id).first()
    if existing:
        return existing
    key = f"{company.pk}/{asset_id}.{metadata.pop('extension')}"
    base_key = ""
    if job and job.kind == "image" and job.logo_asset_id:
        from .branding import compose_logo

        base = data
        data = compose_logo(data, job.logo_asset)
        metadata = describe_file(data)
        metadata.pop("extension")
        base_key = f"{company.pk}/{asset_id}_base.png"
        put(base_key, base, "image/png")
    backend = put(key, data, metadata["mime_type"])
    asset, _ = MediaAsset.objects.get_or_create(pk=asset_id, defaults={
        "company": company, "storage_backend": backend, "storage_key": key, "byte_size": len(data),
        "origin": "generated" if job else "uploaded", "provider": job.provider if job else "user",
        "generation": job, "brief": job.brief if job else "", "alt_text": alt_text[:500],
        "purpose": purpose, "sha256": hashlib.sha256(data).hexdigest(), "generation_base_key": base_key,
        "expires_at": timezone.now() + timedelta(days=7) if job else None, **metadata,
    })
    return asset


def default_brief(run, kind):
    idea = run.ideas[run.selected] if run.selected is not None and run.selected < len(run.ideas) else {}
    if kind == "image":
        return idea.get("photo_brief") or run.draft.get("photo_brief", "")
    title = idea.get("title", run.title)
    angle = idea.get("angle", "Förklara en konkret lärdom från inlägget.")
    return (f"0–2 sek · Hook: {title}\n2–5 sek · Budskap: {angle}\n"
            "5–8 sek · Lärdom: Visa ett konkret nästa steg som stöds av texten.\n"
            "8–10 sek · CTA: Bjud in tittaren att reflektera eller prova nästa steg.\n"
            "Skapa en enkel visuell sekvens i stående format. Undvik påhittade resultat och siffror.")


def create_job(run, *, token, kind, brief, count=2, shape="portrait", source=None, include_logo=False, priority="balanced"):
    check_storage()
    if kind not in {"image", "video"} or not brief.strip() or len(brief) > 6000:
        raise MediaError("Beskrivningen behövs och får vara högst 6000 tecken.")
    if priority not in {"quality", "balanced", "economy"}:
        raise MediaError("Välj Bäst resultat, Balanserad eller Spara kostnad.")
    if source and (source.company_id != run.workspace_id or source.kind != "image" or source.purpose == "logo"):
        raise MediaError("Startbilden ska tillhöra företaget.")
    if not run.draft or run.delivery_status != "draft":
        raise MediaError("Skapa ett redigerbart utkast innan du väljer media.")
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().select_related("workspace").get(pk=run.pk)
        if locked.delivery_status != "draft":
            raise MediaError("Utkastet har redan skickats till Postiz.")
        existing = locked.media_jobs.filter(pk=token).first() or locked.media_jobs.filter(status__in=ACTIVE).first()
        if existing:
            return existing
        company = Company.objects.select_for_update().get(pk=run.workspace_id)
        logo = company.official_logo if include_logo and kind == "image" else None
        if include_logo and (kind != "image" or not logo):
            raise MediaError("Ladda upp företagets officiella logga i Inställningar först. Logga stöds för bilder.")
        if logo:
            if logo.company_id != company.pk or logo.purpose != "logo":
                raise MediaError("Den officiella loggan är inte korrekt kopplad till företaget.")
        if source:
            source = MediaAsset.objects.select_for_update().get(pk=source.pk)
            if source.expires_at and source.expires_at <= timezone.now():
                raise MediaError("Startbildens förhandsvisning har gått ut.")

        # Prompt Library is untrusted inspiration only. Retrieval is company scoped
        # and bounded, and its raw prompt text is never copied into the provider prompt.
        inspirations = retrieve_inspiration(company.owner, company.pk, brief, limit=3)
        try:
            plan = build_plan(locked, brief, kind=kind, source=source, shape=shape, count=count,
                              priority=priority, inspirations=inspirations)
        except ValueError as exc:
            raise MediaError("Kreativ kontroll stoppade generationen: " + str(exc)) from exc

        params = dict(plan.parameters)
        params["aspect_ratio"] = plan.brief.aspect_ratio
        params["creative"] = {
            "brief": plan.brief.model_dump(mode="json"),
            "context": plan.context.model_dump(mode="json"),
            "complexity": plan.complexity.value,
            "selection": plan.selection.model_dump(mode="json"),
            "recipe": plan.recipe.model_dump(mode="json"),
            "preflight": [item.model_dump(mode="json") for item in plan.preflight],
            "inspiration_ids": plan.inspiration_ids,
            "compiler_version": plan.compiler_version,
            "registry_version": plan.registry_version,
            "recipe_registry_version": plan.recipe_registry_version,
        }
        if logo:
            params["logo_sha256"] = logo.sha256

        return MediaGeneration.objects.create(
            id=token,
            run=locked,
            kind=kind,
            provider=plan.selection.provider,
            brief=brief,
            prompt=plan.prompt,
            parameters=params,
            source_asset=source,
            logo_asset=logo,
        )


def preview_job(job):
    """Persist a reviewable plan without creating paid provider work."""
    job.refresh_from_db()
    if job.status != "queued":
        return job
    usage = dict(job.usage or {})
    # An unsuccessful fresh check must not leave an older approval usable.
    for key in ("reviewed_at", "approved_max_usd", "estimate"):
        usage.pop(key, None)
    MediaGeneration.objects.filter(pk=job.pk, status="queued").update(usage=usage)
    if job.provider == "higgsfield":
        try:
            _, _, estimate = providers.estimate_video(job)
        except MediaError as exc:
            usage["provider_error"] = {"code": providers.provider_error_code(exc), "message": str(exc)[:300]}
            MediaGeneration.objects.filter(pk=job.pk, status="queued").update(
                usage=usage, error=str(exc)[:500], updated_at=timezone.now()
            )
            raise
        usage.update(estimate)
    else:
        usage["price_note"] = "OpenAI-bilder debiteras efter användning. Bindande prisestimat är inte tillgängligt här."
    usage["reviewed_at"] = timezone.now().isoformat()
    usage.pop("provider_error", None)
    MediaGeneration.objects.filter(pk=job.pk, status="queued").update(usage=usage, error="", updated_at=timezone.now())
    job.refresh_from_db()
    return job


def start_reviewed_job(job, *, expected_revision=None):
    with transaction.atomic():
        run = ContentRun.objects.select_for_update().get(pk=job.run_id)
        if expected_revision is not None:
            from .operator_common import _check_revision
            _check_revision(run, expected_revision)
        if run.delivery_status != "draft":
            raise MediaError("Utkastet har redan överförts. Öppna ett redigerbart utkast före start.")
        locked = MediaGeneration.objects.select_for_update().get(pk=job.pk)
        if locked.status != "queued":
            return locked
        reviewed = locked.usage.get("reviewed_at")
        from django.utils.dateparse import parse_datetime
        reviewed = parse_datetime(reviewed) if isinstance(reviewed, str) else None
        if not reviewed or timezone.is_naive(reviewed) or reviewed < timezone.now() - timedelta(minutes=10):
            raise MediaError("Granska inställningar och pris på nytt före start. Granskningen gäller i tio minuter.")
        if locked.provider == "higgsfield":
            locked.usage["approved_max_usd"] = locked.usage.get("estimate", {}).get("usd")
            if locked.usage["approved_max_usd"] is None:
                raise MediaError("Granska videons pris före start.")
            locked.save(update_fields=["usage"])
    return advance_job(locked)


def _mark_provider_error(job, exc, *, status=None):
    usage = dict(job.usage or {})
    usage["provider_error"] = {"code": providers.provider_error_code(exc), "message": str(exc)[:300]}
    fields = {"usage": usage, "error": str(exc)[:500], "updated_at": timezone.now()}
    if status:
        fields["status"] = status
    MediaGeneration.objects.filter(pk=job.pk).update(**fields)


def _persist_terminal_provider_status(job, remote_status, remote, *, expected_statuses=None):
    """Persist Higgsfield's terminal status and error without starting or retrying work."""
    provider_error = remote.get("error")
    provider_error = provider_error.strip()[:500] if isinstance(provider_error, str) and provider_error.strip() else ""
    defaults = {
        "failed": "Videoleverantören kunde inte slutföra generationen.",
        "nsfw": "Videoleverantören stoppade generationen i sin innehållskontroll.",
        "canceled": "Videogenereringen avbröts innan den slutfördes.",
    }
    message = provider_error or defaults.get(remote_status, "Videoleverantören returnerade ett terminalt fel.")
    usage = dict(job.usage or {})
    usage["provider_terminal"] = {
        "status": remote_status,
        "error": provider_error,
        "checked_at": timezone.now().isoformat(),
    }
    query = MediaGeneration.objects.filter(pk=job.pk)
    if expected_statuses:
        query = query.filter(status__in=expected_statuses)
    query.update(status=remote_status, error=message, usage=usage, updated_at=timezone.now())


def refresh_terminal_provider_status(job):
    """Re-read a terminal Higgsfield request to recover the provider's actual error text."""
    job.refresh_from_db()
    if job.provider != "higgsfield" or not job.provider_id or job.status not in {"failed", "nsfw", "canceled"}:
        return job
    remote = providers.video_status(job)
    if not isinstance(remote, dict):
        raise MediaError("Leverantörens status kunde inte läsas.")
    remote_status = remote.get("status")
    if remote_status not in {"failed", "nsfw", "canceled"}:
        raise MediaError("Higgsfield returnerar inte längre samma terminala status för jobbet.")
    _persist_terminal_provider_status(job, remote_status, remote)
    job.refresh_from_db()
    return job


def reconcile_video_job(job):
    """Read provider status and persist a terminal result without new paid submits."""
    job.refresh_from_db()
    if job.status in {"completed", "failed", "nsfw", "canceled", "unknown"} or not job.provider_id:
        return job
    if job.status == "saving" and job.updated_at >= timezone.now() - timedelta(minutes=10):
        return job

    remote = providers.video_status(job)
    if not isinstance(remote, dict):
        raise MediaError("Leverantörens status kunde inte läsas. Samma jobb återanvänds.")
    remote_status = remote.get("status")
    if not isinstance(remote_status, str):
        raise MediaError("Leverantörens status kunde inte läsas. Samma jobb återanvänds.")
    if remote_status == "completed":
        now = timezone.now()
        if job.status == "running":
            claimed = MediaGeneration.objects.filter(pk=job.pk, status="running").update(status="saving", error="", updated_at=now)
        else:
            claimed = MediaGeneration.objects.filter(pk=job.pk, status="saving", updated_at=job.updated_at).update(error="", updated_at=now)
        if not claimed:
            job.refresh_from_db()
            return job
        try:
            payload = remote.get("payload") or {}
            video = remote.get("video") or (payload.get("video") if isinstance(payload, dict) else None) or {}
            if not isinstance(video, dict):
                raise MediaError("Leverantörens resultatlänk kunde inte läsas.")
            url = video.get("url")
            if not url:
                raise MediaError("Videoleverantören markerade jobbet klart men saknade resultatlänk.")
            data = providers.download_output(url)
            store_asset(job.run.workspace, data, job=job)
            MediaGeneration.objects.filter(pk=job.pk, status="saving").update(status="completed", error="", updated_at=timezone.now())
        except MediaError as exc:
            # Provider work is already complete. Keep a durable saving state so
            # recovery may retry download/storage without creating a new generation.
            _mark_provider_error(job, exc)
            raise
    elif remote_status in {"failed", "nsfw", "canceled"}:
        _persist_terminal_provider_status(job, remote_status, remote, expected_statuses=("running", "saving"))
    else:
        # Fair scheduling: an old, slow request must not starve all newer jobs.
        MediaGeneration.objects.filter(pk=job.pk, status="running").update(updated_at=timezone.now())
    job.refresh_from_db()
    return job


def advance_job(job):
    if job.status == "queued":
        claimed = MediaGeneration.objects.filter(pk=job.pk, status="queued").update(status="starting", updated_at=timezone.now())
        if not claimed:
            job.refresh_from_db()
            return job
        received_images = False
        try:
            if job.kind == "image":
                if job.logo_asset_id:
                    from .branding import read_logo
                    read_logo(job.logo_asset)  # Fail before charging if the official source is unavailable/changed.
                images, usage = providers.generate_images(job)
                received_images = True
                for index, data in enumerate(images):
                    store_asset(job.run.workspace, data, job=job, index=index)
                if not images:
                    raise MediaError("Bildtjänsten returnerade inget färdigt alternativ.")
                MediaGeneration.objects.filter(pk=job.pk).update(status="completed", usage=usage, error="", updated_at=timezone.now())
            else:
                remote, usage = providers.start_video(job)
                request_id = str(uuid.UUID(remote["request_id"]))
                MediaGeneration.objects.filter(pk=job.pk, status="starting").update(
                    status="running", provider_id=request_id, usage=usage, error="", updated_at=timezone.now()
                )
        except (providers.UncertainGeneration, APIConnectionError) as exc:
            _mark_provider_error(job, exc, status="unknown")
        except (providers.ProviderError, MediaError, APIError, ValueError, KeyError, TypeError) as exc:
            detail = str(exc) if isinstance(exc, MediaError) else f"Genereringen kunde inte slutföras (HTTP {getattr(exc, 'status_code', 'okänd')}). Kontrollera leverantörsåtkomst och lagring."
            usage = dict(job.usage or {})
            if isinstance(exc, providers.ProviderError):
                usage["provider_error"] = {"code": providers.provider_error_code(exc), "message": detail[:300]}
            code = getattr(exc, "status_code", 0) or 0
            uncertain = received_images or isinstance(exc, APIError) and (code in {408, 409} or code >= 500)
            if uncertain:
                detail = "Bildtjänsten svarade men resultatet kunde inte säkras fullständigt. Kontrollera sparade alternativ och leverantörskontot innan ett nytt betalt försök."
            MediaGeneration.objects.filter(pk=job.pk).update(status="unknown" if uncertain else "failed", error=detail[:500], usage=usage, updated_at=timezone.now())
    elif job.status == "running" and job.provider_id:
        return reconcile_video_job(job)
    elif job.status == "saving" and job.provider_id:
        return reconcile_video_job(job)
    elif job.status == "starting" and job.updated_at < timezone.now() - timedelta(minutes=10):
        # A process can die after a paid POST but before the request id is stored.
        # That state is deliberately terminal until a human reconciles the account.
        MediaGeneration.objects.filter(pk=job.pk, status="starting").update(
            status="unknown", error="Genereringen avbröts eller tog för lång tid. Kontrollera leverantörens konto innan ett nytt försök."
        )
    job.refresh_from_db()
    return job


def cancel_job(job):
    """Cancel without ever creating or retrying a generation request."""
    job.refresh_from_db()
    if job.status == "queued":
        MediaGeneration.objects.filter(pk=job.pk, status="queued").update(
            status="canceled", error="Jobbet avbröts innan leverantören anropades.", updated_at=timezone.now()
        )
    elif job.status == "running" and job.provider_id:
        providers.cancel_video(job)
        MediaGeneration.objects.filter(pk=job.pk, status="running").update(
            status="canceled", error="Avbokning accepterad av videoleverantören.", updated_at=timezone.now()
        )
    elif job.status in {"completed", "failed", "nsfw", "canceled"}:
        return job
    else:
        raise MediaError("Jobbet kan inte avbrytas säkert i sitt nuvarande läge. Kontrollera leverantörsstatus först.")
    job.refresh_from_db()
    return job


def recover_media_jobs(*, limit=25):
    """Bounded recovery pass. Never submits a new paid provider request."""
    limit = max(1, min(int(limit), 100))
    cutoff = timezone.now() - timedelta(minutes=10)
    jobs = list(
        MediaGeneration.objects.filter(
            Q(status="running") | Q(status="saving", updated_at__lt=cutoff) | Q(status="starting", updated_at__lt=timezone.now() - timedelta(minutes=10))
        ).select_related("run__workspace", "source_asset", "logo_asset").order_by("updated_at", "pk")[:limit]
    )
    result = {"checked": 0, "completed": 0, "failed": 0, "nsfw": 0, "canceled": 0, "unknown": 0, "pending": 0, "errors": 0}
    for job in jobs:
        result["checked"] += 1
        try:
            advance_job(job)
        except MediaError:
            result["errors"] += 1
            MediaGeneration.objects.filter(pk=job.pk, status="running").update(updated_at=timezone.now())
            job.refresh_from_db()
        key = job.status if job.status in result else "pending"
        result[key] += 1
    return result


def select_asset(run, asset):
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().get(pk=run.pk)
        chosen = MediaAsset.objects.select_for_update().get(pk=asset.pk, company=run.workspace)
        if locked.delivery_status != "draft":
            raise MediaError("Ändra media i Postiz efter överföringen.")
        if chosen.expires_at and chosen.expires_at <= timezone.now():
            raise MediaError("Förhandsvisningen har gått ut. Generera ett nytt alternativ.")
        chosen.expires_at = None
        chosen.used_at = chosen.used_at or timezone.now()
        chosen.save(update_fields=["expires_at", "used_at"])
        previous = str(locked.media_asset_id) if locked.media_asset_id else None
        locked.media_asset = chosen
        locked.save(update_fields=["media_asset"])
        if previous != str(chosen.pk):
            ContentEvent.objects.create(run=locked, idea_index=locked.selected, action="media_selected",
                                       data={"before": previous, "asset_id": str(chosen.pk), "origin": chosen.origin, "provider": chosen.provider, "generation_id": str(chosen.generation_id) if chosen.generation_id else None})


def remove_asset(asset):
    with transaction.atomic():
        locked = MediaAsset.objects.select_for_update().get(pk=asset.pk)
        if locked.purpose == "logo" or locked.used_at or locked.content_runs.exists() or locked.logo_generations.exists() or locked.official_for.exists() or locked.variations.filter(status__in=ACTIVE).exists():
            raise MediaError("Media som används av ett sparat inlägg eller en pågående generation kan inte tas bort.")
        delete_file(locked)
        locked.delete()


def cleanup_expired(company=None, limit=25):
    """Bounded cleanup on the next media write; a command also supports scheduled runs."""
    expired = MediaAsset.objects.filter(expires_at__lte=timezone.now(), used_at__isnull=True)
    if company:
        expired = expired.filter(company=company)
    removed = 0
    for asset in expired.order_by("expires_at")[:limit]:
        try:
            remove_asset(asset)
            removed += 1
        except (MediaError, MediaAsset.DoesNotExist):
            continue
    return removed
