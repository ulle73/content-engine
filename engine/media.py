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
from .media_storage import MediaError, check_storage, delete_file, open_asset, put
from .creative_core import ReferenceRole
from .media_references import add_generation_reference, ensure_source_reference, generation_reference_signature
from .models import Company, ContentEvent, ContentRun, MediaAsset, MediaGeneration

PENDING = ("queued", "starting", "running", "saving")
ACTIVE = PENDING + ("unknown",)
TERMINAL = ("completed", "failed", "nsfw", "canceled", "unknown")


def _audio_metadata(container, stream, extension):
    allowed = {"aac", "mp3", "mp3float", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_f64le"}
    if not stream or stream.codec_context.name not in allowed:
        raise MediaError("Ljud ska vara WAV, MP3 eller M4A/AAC.")
    duration = float(stream.duration * stream.time_base) if stream.duration is not None else (
        container.duration / av.time_base if container.duration else None)
    if not duration or not 0 < duration <= 1200 or not 8000 <= stream.codec_context.sample_rate <= 192000:
        raise MediaError("Ljudet ska ha giltig samplingsfrekvens och vara h\u00f6gst 20 minuter.")
    frame = next(container.decode(audio=0), None)
    if not frame:
        raise MediaError("Ljudfilen saknar l\u00e4sbart ljud.")
    return {"kind": "audio", "mime_type": {"wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4"}[extension],
            "extension": extension, "duration_seconds": duration}


def describe_file(data):
    if len(data) > 80 * 1024 * 1024 or not data:
        raise MediaError("V\u00e4lj en fil mellan 1 byte och 80 MB.")
    is_mp4 = len(data) >= 12 and data[4:8] == b"ftyp"
    is_wav = data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    is_mp3 = data[:3] == b"ID3" or (len(data) > 2 and data[0] == 255 and data[1] & 224 == 224)
    if is_mp4 or is_wav or is_mp3:
        try:
            with av.open(io.BytesIO(data)) as container:
                stream = next(iter(container.streams.video), None)
                if stream is None:
                    return _audio_metadata(container, next(iter(container.streams.audio), None),
                        "m4a" if is_mp4 else "wav" if is_wav else "mp3")
                if not is_mp4 or stream.codec_context.name != "h264" or data[8:12] == b"qt  ":
                    raise MediaError("Video ska vara MP4 med H.264-kodning.")
                if stream.width * stream.height > 16_777_216 or stream.width < 1 or stream.height < 1:
                    raise MediaError("Video f\u00e5r vara h\u00f6gst 16 megapixel.")
                duration = float(stream.duration * stream.time_base) if stream.duration is not None else (
                    container.duration / av.time_base if container.duration else None)
                if not duration or not 0 < duration <= 1200:
                    raise MediaError("Video f\u00e5r vara h\u00f6gst 20 minuter.")
                frame = next(container.decode(video=0), None)
                if not frame:
                    raise MediaError("Videon saknar l\u00e4sbar bild.")
                return {"kind": "video", "mime_type": "video/mp4", "extension": "mp4", "width": frame.width,
                        "height": frame.height, "duration_seconds": duration}
        except (av.error.FFmpegError, ValueError, OverflowError) as exc:
            raise MediaError("Filen kunde inte l\u00e4sas. V\u00e4lj H.264 MP4, WAV, MP3 eller M4A/AAC.") from exc
    if len(data) > 8 * 1024 * 1024:
        raise MediaError("Bilder f\u00e5r vara h\u00f6gst 8 MB. Video och ljud f\u00e5r vara h\u00f6gst 80 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as img:
                if img.format not in {"PNG", "JPEG", "WEBP"} or img.width * img.height > 40_000_000:
                    raise MediaError("V\u00e4lj JPEG, PNG eller WebP, h\u00f6gst 40 megapixel.")
                kind, width, height = img.format, img.width, img.height
                img.verify()
        return {"kind": "image", "mime_type": Image.MIME[kind], "extension": {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[kind],
                "width": width, "height": height}
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise MediaError("Filen kunde inte l\u00e4sas som bild, video eller ljud.") from exc


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


def extract_video_frame_png(asset, *, selector="final"):
    """Decode one deterministic frame from a stored video without calling a provider."""
    if asset.kind != "video":
        raise MediaError("Frame-extraktion kräver en video.")
    if selector != "final":
        raise MediaError("Endast slutbild stöds i Output Chain just nu.")
    if asset.expires_at and asset.expires_at <= timezone.now():
        raise MediaError("Videons förhandsvisning har gått ut.")

    try:
        with open_asset(asset) as file:
            with av.open(file) as container:
                stream = next(iter(container.streams.video), None)
                if not stream:
                    raise MediaError("Videon saknar ett läsbart videospår.")
                last_frame = None
                frame_index = -1
                for frame_index, frame in enumerate(container.decode(video=0)):
                    last_frame = frame
                if last_frame is None:
                    raise MediaError("Videon saknar en läsbar slutbild.")
                timestamp_seconds = None
                if last_frame.pts is not None and last_frame.time_base is not None:
                    timestamp_seconds = float(last_frame.pts * last_frame.time_base)
                image = last_frame.to_image().convert("RGB")
                out = io.BytesIO()
                image.save(out, "PNG")
                return out.getvalue(), {
                    "frame_selector": "final",
                    "frame_index": frame_index,
                    "pts": int(last_frame.pts) if last_frame.pts is not None else None,
                    "timestamp_seconds": timestamp_seconds,
                    "width": image.width,
                    "height": image.height,
                }
    except MediaError:
        raise
    except (av.error.FFmpegError, OSError, ValueError) as exc:
        raise MediaError("Slutbilden kunde inte extraheras från videon.") from exc


def store_derived_image(company, data, *, generation, alt_text="", brief="", asset_id=None):
    """Persist a generated/derived image through the normal MediaAsset storage path."""
    if generation.run.workspace_id != company.pk:
        raise MediaError("Den härledda bilden måste tillhöra generationens företag.")
    metadata = describe_file(data)
    if metadata["kind"] != "image":
        raise MediaError("Den härledda filen måste vara en bild.")
    asset_id = asset_id or uuid.uuid4()
    existing = MediaAsset.objects.filter(pk=asset_id).first()
    if existing:
        if existing.company_id != company.pk or existing.sha256 != hashlib.sha256(data).hexdigest():
            raise MediaError("Den h\u00e4rledda filen har redan sparats med annat inneh\u00e5ll.")
        return existing
    key = f"{company.pk}/{asset_id}.{metadata.pop('extension')}"
    backend = put(key, data, metadata["mime_type"])
    return MediaAsset.objects.create(
        pk=asset_id,
        company=company,
        storage_backend=backend,
        storage_key=key,
        byte_size=len(data),
        origin="generated",
        provider=generation.provider,
        generation=generation,
        brief=(brief or generation.brief)[:6000],
        alt_text=alt_text[:500],
        purpose="content",
        sha256=hashlib.sha256(data).hexdigest(),
        generation_base_key="",
        expires_at=None,
        **metadata,
    )


def default_brief(run, kind):
    """Start from the user's latest visual intent, not an invented video script."""
    idea = run.ideas[run.selected] if run.selected is not None and 0 <= run.selected < len(run.ideas) else {}
    return run.draft.get("photo_brief") or idea.get("photo_brief") or idea.get("angle") or ""


def create_job(run, *, token, kind, brief, count=2, shape="portrait", source=None, end_source=None, include_logo=False, priority="balanced", recipe_id=None, model_override=""):
    check_storage()
    if kind not in {"image", "video"} or not brief.strip() or len(brief) > 6000:
        raise MediaError("Beskrivningen behövs och får vara högst 6000 tecken.")
    if priority not in {"quality", "balanced", "economy"}:
        raise MediaError("Välj Bäst resultat, Balanserad eller Spara kostnad.")
    if source and source.purpose == "logo" and source.pk != run.workspace.official_logo_id:
        raise MediaError("Endast företagets officiella logga får användas som videoreferens.")
    if source and (source.company_id != run.workspace_id or source.kind != "image"):
        raise MediaError("Startbilden ska tillhöra företaget.")
    if end_source and end_source.purpose == "logo" and end_source.pk != run.workspace.official_logo_id:
        raise MediaError("Endast företagets officiella logga får användas som videoreferens.")
    if end_source and (kind != "video" or end_source.company_id != run.workspace_id or end_source.kind != "image"):
        raise MediaError("Slutbilden ska vara en bild som tillhör företaget och används för video.")
    if end_source and not source:
        raise MediaError("Välj en startbild innan du väljer en slutbild.")
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
        if end_source:
            end_source = MediaAsset.objects.select_for_update().get(pk=end_source.pk)
            if end_source.expires_at and end_source.expires_at <= timezone.now():
                raise MediaError("Slutbildens förhandsvisning har gått ut.")

        # Prompt Library is untrusted inspiration only. Retrieval is company scoped
        # and bounded, and its raw prompt text is never copied into the provider prompt.
        inspirations = retrieve_inspiration(company.owner, company.pk, brief, limit=3)
        try:
            plan = build_plan(locked, brief, kind=kind, source=source, end_source=end_source, shape=shape, count=count,
                              priority=priority, inspirations=inspirations, recipe_id=recipe_id,
                              model_override=model_override)
        except ValueError as exc:
            raise MediaError("Kreativ kontroll stoppade generationen: " + str(exc)) from exc

        params = dict(plan.parameters)
        params["aspect_ratio"] = plan.brief.aspect_ratio
        params["model_override"] = plan.selection.model_id if plan.selection.manual_override else ""
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

        job = MediaGeneration.objects.create(
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
        if source:
            ensure_source_reference(job)
        if end_source:
            add_generation_reference(job, end_source, ReferenceRole.end_image)
        return job


def preview_job(job):
    """Persist a reviewable plan without creating paid provider work."""
    job.refresh_from_db()
    if job.status != "queued":
        return job
    usage = dict(job.usage or {})
    # An unsuccessful fresh check must not leave an older approval usable.
    for key in ("reviewed_at", "reviewed_reference_signature", "approved_max_usd", "estimate"):
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
    usage["reviewed_reference_signature"] = generation_reference_signature(job)
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
        if locked.usage.get("reviewed_reference_signature") != generation_reference_signature(locked):
            raise MediaError("Start- eller slutbilden har ändrats sedan granskningen. Uppdatera priskontrollen före start.")
        if locked.kind == "video" and isinstance((locked.parameters or {}).get("sequence"), dict):
            from .sequence import SequenceError, assert_sequence_generation_video_ready
            try:
                assert_sequence_generation_video_ready(locked)
            except SequenceError as exc:
                raise MediaError(str(exc)) from exc
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
    if job.provider == "remotion":
        from .motion.jobs import wake_worker
        wake_worker()
        job.refresh_from_db()
        return job
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
    if job.provider == "remotion":
        from .motion.service import cancel_render
        cancel_render(job.run.workspace, job.motion_render.id)
        job.refresh_from_db()
        return job
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
        ).exclude(provider="remotion").select_related("run__workspace", "source_asset", "logo_asset").order_by("updated_at", "pk")[:limit]
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


def publishable_assets(assets):
    """Motion previews belong to project review, never to publishing choices."""
    return assets.exclude(motion_outputs__mode="preview").exclude(motion_storyboards__isnull=False).exclude(kind="audio")


def validate_publishable_asset(asset):
    if asset.kind == "audio":
        raise MediaError("Ljud kan användas i Motion, inte som bild eller video i ett inlägg.")
    if asset.motion_outputs.filter(mode="preview").exists() or asset.motion_storyboards.exists():
        raise MediaError("Godkänn Motion-förhandsvisningen och skapa en färdig video först.")


def select_asset(run, asset):
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().get(pk=run.pk)
        chosen = MediaAsset.objects.select_for_update().get(pk=asset.pk, company=run.workspace)
        validate_publishable_asset(chosen)
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
        if locked.purpose == "logo" or locked.used_at or locked.content_runs.exists() or locked.logo_generations.exists() or locked.official_for.exists() or locked.variations.filter(status__in=ACTIVE).exists() or locked.generation_references.filter(generation__status__in=ACTIVE).exists() or locked.sequence_anchors.exists() or locked.sequence_anchor_revisions.exists():
            raise MediaError("Media som används av ett sparat inlägg, en sequence-anchor/version eller en pågående generation kan inte tas bort.")
        if locked.motion_references.exists() or locked.motion_outputs.exists() or locked.motion_storyboards.exists():
            raise MediaError("Media som anv\u00e4nds i ett Motion-projekt kan inte tas bort.")
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
