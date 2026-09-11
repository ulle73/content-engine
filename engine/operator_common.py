"""Shared Content Engine operator state, serialization and idempotency primitives."""
from __future__ import annotations
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any
from django.db import transaction
from django.utils import timezone
from .media_storage import MediaError
from .models import Company, ContentEvent, ContentRun, LearningModel, MediaAsset, OwnPost, Prediction
from operator_bridge.models import OperatorAction, RunState


class OperatorError(ValueError):
    """A safe, user-facing operator error."""

class UnknownExternalState(OperatorError):
    """An external side effect may have happened and must not be replayed automatically."""

def _durable_error(exc: Exception) -> str:
    """Keep durable operator ledgers free of arbitrary provider bodies, URLs or credentials."""
    if isinstance(exc, (OperatorError, MediaError)):
        return str(exc)[:500]
    status = getattr(exc, "status_code", None)
    suffix = f" HTTP {status}" if isinstance(status, int) else ""
    return f"{type(exc).__name__}{suffix}. Operationen misslyckades och behöver nytt försök eller kontroll."[:500]

def _user_label(user) -> str:
    return (getattr(user, "email", "") or getattr(user, "username", "") or str(user.pk)).strip().lower()

def resolve_company(user, company_ref: str) -> Company:
    """Resolve a UUID or exact company name inside the authenticated user's ownership scope."""
    value = str(company_ref or "").strip()
    if not value:
        raise OperatorError("Ange företagets id eller exakta namn.")
    owned = Company.objects.filter(owner=user)
    try:
        company_id = uuid.UUID(value)
    except ValueError:
        company_id = None
    if company_id:
        company = owned.filter(pk=company_id).first()
        if not company:
            raise OperatorError("Företaget finns inte eller tillhör inte den autentiserade användaren.")
        return company
    matches = list(owned.filter(name__iexact=value)[:2])
    if len(matches) != 1:
        raise OperatorError("Företagsnamnet saknas eller är inte entydigt. Använd företagets UUID.")
    return matches[0]

def list_companies(user) -> list[dict[str, Any]]:
    return [company_summary(c) for c in Company.objects.filter(owner=user).order_by("name")]

def company_summary(company: Company) -> dict[str, Any]:
    return {
        "id": str(company.pk),
        "name": company.name,
        "profile": company.profile,
        "voice": company.voice,
        "current": company.current,
        "source": company.source,
        "valid_until": company.valid_until.isoformat() if company.valid_until else None,
        "updated_at": company.updated_at.isoformat(),
        "postiz_connected": bool(company.postiz_ciphertext),
        "postiz_channels": [
            {k: channel.get(k) for k in ("id", "name", "identifier")}
            for channel in company.postiz_channels
        ],
        "official_logo_asset_id": str(company.official_logo_id) if company.official_logo_id else None,
    }

def content_hash(run: ContentRun) -> str:
    return hashlib.sha256(
        json.dumps(
            {"draft": run.draft, "media_asset_id": str(run.media_asset_id) if run.media_asset_id else None},
            sort_keys=True, ensure_ascii=False, default=str,
        ).encode()
    ).hexdigest()

def run_state(run: ContentRun, *, lock: bool = False) -> RunState:
    qs = RunState.objects.select_for_update() if lock else RunState.objects
    state, created = qs.get_or_create(run=run)
    if created and run.delivery_status == "sent":
        latest = run.events.filter(action__in=("postiz_draft", "postiz_schedule", "postiz_publish")).order_by("-created_at").first()
        if latest:
            state.delivery_mode = {"postiz_draft": "draft", "postiz_schedule": "schedule", "postiz_publish": "now"}[latest.action]
            raw_schedule = latest.data.get("scheduled_for") or latest.data.get("schedule_at")
            if raw_schedule:
                try:
                    state.scheduled_for = datetime.fromisoformat(str(raw_schedule).replace("Z", "+00:00"))
                except ValueError:
                    state.scheduled_for = None
            state.synced_hash = content_hash(run)
            state.save(update_fields=["delivery_mode", "scheduled_for", "synced_hash", "updated_at"])
    return state

def _make_editable(locked: ContentRun, state: RunState) -> bool:
    if locked.delivery_status == "draft":
        return False
    if locked.delivery_status == "sent" and state.delivery_mode == "draft":
        locked.delivery_status = "draft"
        locked.save(update_fields=["delivery_status"])
        ContentEvent.objects.create(
            run=locked, idea_index=locked.selected, action="postiz_draft_reopened",
            data={"posts": locked.delivery_result, "synced_hash": state.synced_hash},
        )
        return True
    raise OperatorError("Endast lokala utkast eller icke-publicerade Postiz-draft kan redigeras från ChatGPT.")

def _check_revision(run: ContentRun, expected_revision: int | None, *, state: RunState | None = None) -> RunState:
    state = state or run_state(run)
    if expected_revision is not None and state.revision != expected_revision:
        raise OperatorError(
            f"Inlägget har ändrats sedan det lästes (revision {state.revision}). Hämta runnet igen innan du skriver över något."
        )
    return state

def serialize_asset(asset: MediaAsset, *, selected: bool = False) -> dict[str, Any]:
    return {
        "id": str(asset.pk),
        "kind": asset.kind,
        "origin": asset.origin,
        "provider": asset.provider,
        "mime_type": asset.mime_type,
        "width": asset.width,
        "height": asset.height,
        "duration_seconds": asset.duration_seconds,
        "brief": asset.brief,
        "alt_text": asset.alt_text,
        "sha256": asset.sha256,
        "source_metadata": (getattr(asset, "operator_provenance", None).metadata if hasattr(asset, "operator_provenance") else {}),
        "selected": selected,
        "created_at": asset.created_at.isoformat(),
    }

def serialize_run(run: ContentRun) -> dict[str, Any]:
    run = ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)
    state = run_state(run)
    events = list(run.events.order_by("-created_at")[:20])
    latest_delivery = next((event for event in events if event.action.startswith("postiz_")), None)
    return {
        "id": str(run.pk),
        "company": {"id": str(run.workspace_id), "name": run.workspace.name},
        "channel": run.channel,
        "revision": state.revision,
        "state": run.delivery_status,
        "delivery_mode": state.delivery_mode or None,
        "scheduled_for": state.scheduled_for.isoformat() if state.scheduled_for else None,
        "created_at": run.created_at.isoformat(),
        "selected_idea_index": run.selected,
        "ideas": run.ideas,
        "draft": run.draft,
        "media": serialize_asset(run.media_asset, selected=True) if run.media_asset_id else None,
        "delivery_result": run.delivery_result,
        "last_delivery_event": latest_delivery.data if latest_delivery else None,
        "predictions": [
            {
                "idea_index": p.idea_index,
                "model_version": p.model_version,
                "mode": p.mode,
                "target": p.target,
                "value": p.value,
            }
            for p in run.predictions.order_by("idea_index", "created_at")
        ],
    }

def intelligence_summary(company: Company, *, limit: int = 5) -> dict[str, Any]:
    from .signals import catalog, evidence, recurring_patterns

    signals = catalog(company)
    organic = []
    for signal in signals[: max(1, min(limit, 20))]:
        item = evidence(signal)
        organic.append(
            {
                k: item.get(k)
                for k in (
                    "id",
                    "account",
                    "url",
                    "format",
                    "as_of",
                    "age_days",
                    "relative",
                    "metric",
                    "baseline",
                    "baseline_type",
                    "sample_size",
                    "confidence",
                    "score",
                    "score_parts",
                    "classification",
                )
            }
        )
    own = []
    for post in OwnPost.objects.filter(company=company).prefetch_related("snapshots").order_by("-published_at")[:10]:
        snap = post.snapshots.order_by("-observed_at").first()
        own.append(
            {
                "post_id": str(post.pk),
                "platform": post.platform,
                "format": post.format,
                "published_at": post.published_at.isoformat(),
                "url": post.url,
                "run_id": str(post.run_id) if post.run_id else None,
                "metrics": snap.metrics if snap else None,
                "baseline": snap.baseline if snap else None,
                "observed_at": snap.observed_at.isoformat() if snap else None,
            }
        )
    models = [
        {
            "channel": model.channel,
            "version": model.version,
            "target": model.target,
            "mode": model.mode,
            "trained_at": model.trained_at.isoformat(),
            "evaluation": model.evaluation,
        }
        for model in LearningModel.objects.filter(company=company).order_by("-trained_at")[:10]
    ]
    from .ads import signals as paid_signals
    return {
        "company": {"id": str(company.pk), "name": company.name},
        "organic_signals": organic,
        "paid_signals": paid_signals(company)[: max(1, min(limit, 20))],
        "recurring_patterns": recurring_patterns(signals),
        "own_recent_performance": own,
        "learning_models": models,
        "learning_labels": Prediction.objects.filter(run__workspace=company, outcomes__isnull=False).distinct().count(),
    }

def begin_action(
    company: Company,
    user,
    *,
    action: str,
    key: str,
    payload: dict[str, Any],
    run: ContentRun | None = None,
) -> tuple[OperatorAction, bool]:
    key = (key or "").strip()
    if len(key) < 8 or len(key) > 128:
        raise OperatorError("idempotency_key måste vara 8–128 tecken och återanvändas vid retry av samma åtgärd.")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    with transaction.atomic():
        existing = OperatorAction.objects.select_for_update().filter(company=company, key=key).first()
        if existing:
            if existing.action != action or existing.request_hash != digest:
                raise OperatorError("Samma idempotency_key har redan använts för en annan operation.")
            if existing.status == "succeeded":
                return existing, False
            if existing.status == "unknown":
                raise UnknownExternalState(
                    "Den tidigare operationens externa resultat är osäkert. Kontrollera destinationen innan någon ny write tillåts."
                )
            if existing.status == "started":
                raise OperatorError("Samma operation pågår redan eller avbröts utan säkert resultat.")
            existing.status = "started"
            existing.error = ""
            existing.result = {}
            existing.run = run or existing.run
            existing.user = user
            existing.save(update_fields=["status", "error", "result", "run", "user", "updated_at"])
            return existing, True
        return OperatorAction.objects.create(
            company=company,
            run=run,
            user=user,
            action=action,
            key=key,
            request_hash=digest,
            status="started",
        ), True

def finish_action(action: OperatorAction, *, result: dict[str, Any], status: str = "succeeded", error: str = "") -> None:
    OperatorAction.objects.filter(pk=action.pk).update(
        status=status,
        result=result,
        error=(error or "")[:500],
        updated_at=timezone.now(),
    )
