"""Media ingest, generation and selection for Content Engine operator clients."""
from __future__ import annotations
import base64
import hashlib
import uuid
from typing import Any
from django.db import transaction
from django.utils import timezone
from .media import advance_job, create_job, default_brief, store_asset
from .media_storage import MediaError
from .models import ContentEvent, ContentRun, MediaAsset, MediaGeneration
from .operator_common import OperatorError, UnknownExternalState, _check_revision, _durable_error, _make_editable, begin_action, finish_action, run_state, serialize_asset
from operator_bridge.models import MediaProvenance


def ingest_image_base64(
    run: ContentRun,
    image_base64: str,
    *,
    brief: str = "",
    alt_text: str = "",
    provider: str = "chatgpt",
    select: bool = False,
    expected_revision: int | None = None,
) -> MediaAsset:
    state = _check_revision(run, expected_revision)
    if run.delivery_status != "draft" and not (run.delivery_status == "sent" and state.delivery_mode == "draft"):
        raise OperatorError("Media kan bara läggas till på lokala utkast eller icke-publicerade Postiz-draft.")
    value = (image_base64 or "").strip()
    if value.startswith("data:"):
        try:
            value = value.split(",", 1)[1]
        except IndexError as exc:
            raise OperatorError("Ogiltig data-URL för bilden.") from exc
    try:
        data = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise OperatorError("Bilden kunde inte avkodas från base64.") from exc
    digest = hashlib.sha256(data).hexdigest()
    existing = MediaAsset.objects.filter(
        company=run.workspace, sha256=digest, kind="image", purpose="content"
    ).order_by("created_at").first()
    if existing:
        asset = existing
    else:
        asset = store_asset(run.workspace, data, alt_text=alt_text)
        asset.origin = "generated"
        asset.provider = (provider[:20] or "chatgpt")
        asset.brief = brief[:6000]
        asset.save(update_fields=["origin", "provider", "brief"])
    MediaProvenance.objects.update_or_create(
        asset=asset,
        defaults={
            "source": "chatgpt",
            "metadata": {
                "source": "mcp",
                "generated_outside_content_engine": True,
                "provider": provider[:20] or "chatgpt",
            },
        },
    )
    ContentEvent.objects.create(
        run=run,
        idea_index=run.selected,
        action="media_ingested",
        data={"asset_id": str(asset.pk), "provider": asset.provider, "sha256": asset.sha256},
    )
    if select:
        select_run_asset(run, asset, expected_revision=expected_revision)
    return asset

def select_run_asset(
    run: ContentRun, asset: MediaAsset, *, expected_revision: int | None = None
) -> ContentRun:
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().select_related("workspace").get(pk=run.pk)
        state = _check_revision(locked, expected_revision, state=run_state(locked, lock=True))
        _make_editable(locked, state)
        chosen = MediaAsset.objects.select_for_update().filter(pk=asset.pk, company=locked.workspace).first()
        if not chosen or chosen.purpose != "content":
            raise OperatorError("Vald media finns inte för företaget.")
        if chosen.expires_at and chosen.expires_at <= timezone.now():
            raise OperatorError("Förhandsvisningen har gått ut. Generera ett nytt alternativ.")
        previous = str(locked.media_asset_id) if locked.media_asset_id else None
        chosen.expires_at = None
        chosen.used_at = chosen.used_at or timezone.now()
        chosen.save(update_fields=["expires_at", "used_at"])
        locked.media_asset = chosen
        locked.save(update_fields=["media_asset"])
        if previous != str(chosen.pk):
            state.revision += 1
            state.save(update_fields=["revision", "updated_at"])
            ContentEvent.objects.create(
                run=locked, idea_index=locked.selected, action="media_selected",
                data={
                    "before": previous, "asset_id": str(chosen.pk), "origin": chosen.origin,
                    "provider": chosen.provider,
                    "generation_id": str(chosen.generation_id) if chosen.generation_id else None,
                },
            )
    return ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)

def start_media_generation(
    run: ContentRun,
    *,
    kind: str = "image",
    brief: str = "",
    count: int = 3,
    shape: str = "portrait",
    include_logo: bool = False,
    source_asset_id: str | None = None,
    end_asset_id: str | None = None,
    token: str | None = None,
    expected_revision: int | None = None,
    priority: str = "balanced",
) -> MediaGeneration:
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().select_related("workspace").get(pk=run.pk)
        state = _check_revision(locked, expected_revision, state=run_state(locked, lock=True))
        reopened = _make_editable(locked, state)
        if reopened:
            state.revision += 1
            state.save(update_fields=["revision", "updated_at"])
    run = ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)
    if not brief:
        brief = default_brief(run, kind)
    source = None
    end_source = None
    if source_asset_id:
        source = MediaAsset.objects.filter(pk=source_asset_id, company=run.workspace, kind="image").first()
        if not source:
            raise OperatorError("Startbilden finns inte för företaget.")
    if end_asset_id:
        end_source = MediaAsset.objects.filter(pk=end_asset_id, company=run.workspace, kind="image").first()
        if not end_source:
            raise OperatorError("Slutbilden finns inte för företaget.")
        if not source:
            raise OperatorError("Välj en startbild innan du väljer en slutbild.")
    try:
        job_token = uuid.UUID(token) if token else uuid.uuid4()
    except ValueError as exc:
        raise OperatorError("token måste vara ett UUID.") from exc
    job = create_job(
        run,
        token=job_token,
        kind=kind,
        brief=brief,
        count=count,
        shape=shape,
        source=source,
        end_source=end_source,
        include_logo=include_logo,
        priority=priority,
    )
    return advance_job(job)

def media_options(run: ContentRun) -> list[dict[str, Any]]:
    assets = MediaAsset.objects.filter(company=run.workspace, generation__run=run).order_by("created_at", "pk")
    return [serialize_asset(asset, selected=run.media_asset_id == asset.pk) for asset in assets]

def select_media_once(
    run: ContentRun,
    user,
    *,
    asset: MediaAsset,
    expected_revision: int | None,
    idempotency_key: str,
) -> ContentRun:
    action, execute = begin_action(
        run.workspace,
        user,
        action="select_media",
        key=idempotency_key,
        payload={"run_id": str(run.pk), "asset_id": str(asset.pk), "expected_revision": expected_revision},
        run=run,
    )
    if not execute:
        return ContentRun.objects.get(pk=run.pk, workspace=run.workspace)
    try:
        updated = select_run_asset(run, asset, expected_revision=expected_revision)
        finish_action(action, result={"run_id": str(run.pk), "asset_id": str(asset.pk)})
        return updated
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise

def ingest_image_once(
    run: ContentRun,
    user,
    *,
    image_base64: str,
    brief: str,
    alt_text: str,
    select: bool,
    expected_revision: int | None,
    idempotency_key: str,
    provider: str = "chatgpt",
) -> tuple[MediaAsset, ContentRun]:
    encoded = (image_base64 or "").strip()
    content_hash = hashlib.sha256(encoded.encode()).hexdigest()
    action, execute = begin_action(
        run.workspace,
        user,
        action="ingest_image",
        key=idempotency_key,
        payload={
            "run_id": str(run.pk),
            "content_hash": content_hash,
            "brief": brief,
            "alt_text": alt_text,
            "select": select,
            "expected_revision": expected_revision,
            "provider": provider,
        },
        run=run,
    )
    if not execute:
        asset_id = action.result.get("asset_id")
        if not asset_id:
            raise OperatorError("Idempotent bildoperation saknar tidigare asset-id.")
        return MediaAsset.objects.get(pk=asset_id, company=run.workspace), ContentRun.objects.get(pk=run.pk)
    try:
        asset = ingest_image_base64(
            run,
            image_base64,
            brief=brief,
            alt_text=alt_text,
            provider=provider,
            select=select,
            expected_revision=expected_revision,
        )
        current = ContentRun.objects.get(pk=run.pk)
        finish_action(action, result={"run_id": str(run.pk), "asset_id": str(asset.pk), "selected": select})
        return asset, current
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise

def ingest_image_url_once(
    run: ContentRun,
    user,
    *,
    image_url: str,
    brief: str,
    alt_text: str,
    select: bool,
    expected_revision: int | None,
    idempotency_key: str,
    provider: str = "chatgpt",
) -> tuple[MediaAsset, ContentRun]:
    from .media_providers import download_output

    action, execute = begin_action(
        run.workspace,
        user,
        action="ingest_image_url",
        key=idempotency_key,
        payload={
            "run_id": str(run.pk), "image_url_hash": hashlib.sha256(image_url.encode()).hexdigest(),
            "brief": brief, "alt_text": alt_text, "select": select,
            "expected_revision": expected_revision, "provider": provider,
        },
        run=run,
    )
    if not execute:
        asset_id = action.result.get("asset_id")
        if not asset_id:
            raise OperatorError("Idempotent bildoperation saknar tidigare asset-id.")
        return MediaAsset.objects.get(pk=asset_id, company=run.workspace), ContentRun.objects.get(pk=run.pk)
    try:
        data = download_output(image_url, limit=8 * 1024 * 1024)
        encoded = base64.b64encode(data).decode()
        asset = ingest_image_base64(
            run, encoded, brief=brief, alt_text=alt_text, provider=provider,
            select=select, expected_revision=expected_revision,
        )
        finish_action(action, result={"run_id": str(run.pk), "asset_id": str(asset.pk), "selected": select})
        return asset, ContentRun.objects.get(pk=run.pk)
    except MediaError as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise OperatorError(str(exc)) from exc
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise

def generate_media_once(
    run: ContentRun,
    user,
    *,
    kind: str,
    brief: str,
    count: int,
    shape: str,
    include_logo: bool,
    source_asset_id: str | None,
    expected_revision: int | None,
    idempotency_key: str,
    end_asset_id: str | None = None,
    priority: str = "balanced",
) -> MediaGeneration:
    action, execute = begin_action(
        run.workspace,
        user,
        action="generate_media",
        key=idempotency_key,
        payload={
            "run_id": str(run.pk), "kind": kind, "brief": brief, "count": count, "shape": shape,
            "include_logo": include_logo, "source_asset_id": source_asset_id, "end_asset_id": end_asset_id,
            "expected_revision": expected_revision, "priority": priority,
        },
        run=run,
    )
    if not execute:
        job_id = action.result.get("job_id")
        if not job_id:
            raise OperatorError("Idempotent mediagenerering saknar tidigare job-id.")
        return MediaGeneration.objects.get(pk=job_id, run=run)
    # Deterministic UUID means create_job also deduplicates if the process dies between provider completion and ledger update.
    job_token = uuid.uuid5(uuid.NAMESPACE_URL, f"content-engine:{run.workspace_id}:{run.pk}:{idempotency_key}")
    try:
        job = start_media_generation(
            run,
            kind=kind,
            brief=brief,
            count=count,
            shape=shape,
            include_logo=include_logo,
            source_asset_id=source_asset_id,
            end_asset_id=end_asset_id,
            token=str(job_token),
            expected_revision=expected_revision,
            priority=priority,
        )
        status = "unknown" if job.status == "unknown" else ("failed" if job.status == "failed" else "succeeded")
        finish_action(
            action,
            result={"run_id": str(run.pk), "job_id": str(job.pk), "job_status": job.status},
            status=status,
            error=job.error,
        )
        if job.status == "unknown":
            raise UnknownExternalState("Mediagenereringen kan ha startat hos leverantören. Kontrollera jobbet före retry.")
        if job.status == "failed":
            raise OperatorError(job.error or "Mediagenereringen misslyckades.")
        return job
    except (UnknownExternalState, OperatorError):
        raise
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise
