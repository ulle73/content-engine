"""Safe orchestration helpers used by the MCP tool surface."""

from __future__ import annotations

import hashlib
from typing import Any

from django.utils import timezone

from .daily import AlreadyRunning, run_daily
from .models import ContentRun, MediaGeneration, OwnPost
from .media import cancel_job
from .media_references import serialize_generation_references
from .operator import (
    OperatorError,
    _durable_error,
    begin_action,
    create_run_once,
    finish_action,
    generate_media_once,
    media_options,
    select_idea_once,
    serialize_run,
)


def child_key(base: str, suffix: str) -> str:
    return "mcp:" + hashlib.sha256(f"{base}:{suffix}".encode()).hexdigest()


def refresh_company_once(company, user, *, idempotency_key: str) -> dict[str, Any]:
    """Run one non-blocking pass through the existing production daily stages for one company."""
    action, execute = begin_action(
        company,
        user,
        action="refresh_company",
        key=idempotency_key,
        payload={"company_id": str(company.pk), "day": timezone.localdate().isoformat()},
    )
    if not execute:
        return dict(action.result)
    try:
        try:
            result = run_daily(company_id=company.pk, wait_seconds=0)
            # run_daily returns a DailyRun in current implementation.
            result.refresh_from_db()
            data = {
                "daily_run_id": str(result.pk),
                "day": result.day.isoformat(),
                "status": result.status,
                "summary": result.summary,
            }
        except AlreadyRunning:
            data = {
                "status": "already_running",
                "message": "En säker daily-körning arbetar redan. Befintligt sparat underlag används; ingen parallell extern start gjordes.",
            }
        finish_action(action, result=data)
        return data
    except Exception as exc:
        finish_action(action, result={}, status="failed", error=_durable_error(exc))
        raise


def refresh_performance_once(company, user, *, idempotency_key: str) -> dict[str, Any]:
    """Read published Postiz content and outcomes, then run the existing learning stage."""
    action, execute = begin_action(
        company,
        user,
        action="refresh_performance",
        key=idempotency_key,
        payload={"company_id": str(company.pk), "observed_day": timezone.localdate().isoformat()},
    )
    if not execute:
        return dict(action.result)
    try:
        from .own_performance import collect, create_outcomes, discover, update_baselines
        from .daily_stages import learning_units

        discovery = discover(company)
        snapshots = []
        due = OwnPost.objects.filter(company=company, finalized_at=None).filter(
            models_Q_next_check_due()
        ).order_by("published_at", "pk")[:20]
        for post in due:
            snapshots.append(collect(post))
        baseline = update_baselines(company)
        outcomes = create_outcomes(company)
        learning = []
        for key, work in learning_units(company):
            result = work()
            learning.append({"key": key, "status": result.status, "message": result.message, "data": result.data})
        data = {
            "discovery": discovery,
            "snapshots": snapshots,
            "baseline": baseline,
            "outcomes": outcomes,
            "learning": learning,
        }
        finish_action(action, result=data)
        return data
    except Exception as exc:
        finish_action(action, result={}, status="failed", error=_durable_error(exc))
        raise


def models_Q_next_check_due():
    # Keep the import local so this module has no ORM work at import time.
    from django.db.models import Q

    return Q(next_check_at=None) | Q(next_check_at__lte=timezone.now())


def prepare_best_content(
    company,
    user,
    *,
    idempotency_key: str,
    channel: str = "organic",
    signal_id: str | None = None,
    refresh_first: bool = True,
    generate_media: bool = True,
    media_count: int = 3,
    media_shape: str = "portrait",
    include_logo: bool = False,
) -> dict[str, Any]:
    """Prepare the best currently ranked run. Delivery is a separate explicit operation."""
    refresh_result = None
    if refresh_first:
        refresh_result = refresh_company_once(company, user, idempotency_key=child_key(idempotency_key, "refresh"))
    run = create_run_once(
        company,
        user,
        channel=channel,
        signal_id=signal_id,
        idempotency_key=child_key(idempotency_key, "create"),
    )
    current = serialize_run(run)
    if run.selected is None:
        run = select_idea_once(
            run,
            user,
            idea_index=0,
            expected_revision=current["revision"],
            idempotency_key=child_key(idempotency_key, "idea-1"),
        )
    job = None
    if generate_media and channel == "organic" and run.media_asset_id is None:
        current = serialize_run(run)
        job = generate_media_once(
            run,
            user,
            kind="image",
            brief=run.draft.get("photo_brief", ""),
            count=media_count,
            shape=media_shape,
            include_logo=include_logo,
            source_asset_id=None,
            expected_revision=current["revision"],
            idempotency_key=child_key(idempotency_key, "media"),
        )
    state = serialize_run(ContentRun.objects.get(pk=run.pk))
    assets = media_options(run)
    return {
        "refresh": refresh_result,
        "run": state,
        "media_job": {
            "id": str(job.pk),
            "status": job.status,
            "error": job.error,
        } if job else None,
        "media_options": assets,
        "next_actions": (
            ["Inspect media with view_media, choose the strongest option with select_media, then call the matching Postiz delivery tool if the user requested delivery."]
            if assets and not state["media"]
            else ["The ContentRun is ready for further editing or explicit Postiz delivery."]
        ),
    }


def poll_generation(job: MediaGeneration) -> MediaGeneration:
    from .media import advance_job

    job.refresh_from_db()
    return advance_job(job) if job.status != "queued" else job


GENERATION_STATUS_COPY = {
    "queued": "Sparad och väntar på start.",
    "starting": "Skickar till leverantören.",
    "running": "Genereras hos leverantören.",
    "saving": "Resultatet är klart och sparas i Content Engine.",
    "completed": "Klar och säkrad i Content Engine.",
    "failed": "Genereringen misslyckades.",
    "nsfw": "Stoppad av leverantörens innehållskontroll.",
    "canceled": "Avbruten.",
    "unknown": "Starten kan ha debiterats men kunde inte bekräftas. Ingen automatisk retry görs.",
}


def serialize_generation(job: MediaGeneration, *, diagnostics=False) -> dict[str, Any]:
    creative = job.parameters.get("creative", {}) if isinstance(job.parameters, dict) else {}
    estimate = job.usage.get("estimate", {}) if isinstance(job.usage, dict) else {}
    data = {
        "job_id": str(job.pk),
        "run_id": str(job.run_id),
        "kind": job.kind,
        "status": job.status,
        "status_message": GENERATION_STATUS_COPY.get(job.status, "Okänd intern status."),
        "error": job.error,
        "model": job.parameters.get("model") if isinstance(job.parameters, dict) else None,
        "estimated_usd": estimate.get("usd"),
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "asset_ids": [str(value) for value in job.assets.values_list("pk", flat=True)[:8]],
    }
    if diagnostics:
        safe_parameters = {
            key: value for key, value in (job.parameters or {}).items()
            if key in {"model", "count", "size", "quality", "duration", "aspect_ratio"}
        }
        data["diagnostics"] = {
            "provider": job.provider,
            "provider_request_id": job.provider_id or None,
            "original_request": job.brief,
            "compiled_prompt": job.prompt,
            "parameters": safe_parameters,
            "structured_brief": creative.get("brief", {}),
            "complexity": creative.get("complexity"),
            "model_selection": creative.get("selection", {}),
            "preflight": creative.get("preflight", []),
            "inspiration_ids": creative.get("inspiration_ids", []),
            "compiler_version": creative.get("compiler_version"),
            "registry_version": creative.get("registry_version"),
            "references": serialize_generation_references(job),
        }
    return data


def list_recent_generations(company, *, limit=10) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 50))
    jobs = MediaGeneration.objects.filter(run__workspace=company).select_related("source_asset").prefetch_related("assets", "references__asset").order_by("-created_at", "-id")[:limit]
    return [serialize_generation(job) for job in jobs]


def cancel_generation(job: MediaGeneration) -> MediaGeneration:
    return cancel_job(job)
