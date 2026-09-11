"""Safe Postiz delivery for Content Engine runs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from operator_bridge.models import OperatorAction

from .forms import validate_context
from .media_storage import MediaError, open_asset
from .models import ContentEvent, ContentRun
from .operator import OperatorError, _durable_error, begin_action, content_hash, finish_action, run_state
from .postiz import PostizError, make_payload, request as postiz_request

STOCKHOLM = ZoneInfo("Europe/Stockholm")
MODES = {"draft", "schedule", "now"}


def _parse_schedule(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperatorError("schedule_at måste vara ett ISO 8601-datum, till exempel 2026-09-13T19:00:00+02:00.") from exc
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=STOCKHOLM)
    return parsed.astimezone(dt_timezone.utc)


def _validate_context(run: ContentRun) -> None:
    brand = run.workspace
    validate_context(brand)
    if run.context.get("valid_until", "") < timezone.localdate().isoformat():
        raise OperatorError("Företagsunderlaget har gått ut. Skapa ett nytt ContentRun från aktuella fakta.")
    for key in ("current", "source", "profile", "voice"):
        if run.context.get(key) != getattr(brand, key):
            raise OperatorError("Företagsunderlaget har ändrats. Skapa ett nytt ContentRun före leverans.")


def _channels(run: ContentRun, channel_ids: list[str] | None) -> list[dict]:
    configured = run.workspace.postiz_channels
    if not configured:
        raise OperatorError("Företaget saknar valda Postiz-kanaler.")
    if not channel_ids:
        return list(configured)
    requested = {str(item) for item in channel_ids}
    chosen = [channel for channel in configured if str(channel.get("id")) in requested]
    if len(chosen) != len(requested):
        raise OperatorError("Minst en vald Postiz-kanal hör inte till företaget.")
    return chosen


def _delivery_flow(run: ContentRun, state, mode: str) -> str:
    if run.delivery_status == "draft":
        if run.delivery_result and state.delivery_mode == "draft":
            return "replace_remote_draft"
        return "fresh"
    if run.delivery_status == "sent" and state.delivery_mode == "draft" and mode in {"schedule", "now"}:
        # Postiz cannot safely assign a new date when merely promoting a draft. Create the real scheduled/now
        # object first, replace Content Engine's external identity, then best-effort delete the superseded draft.
        return "supersede_draft"
    raise OperatorError("Leveransen har redan startat eller slutförts i ett läge som inte kan ersättas automatiskt.")


def _restore_definite_failure(run_id, *, status: str, mode: str, scheduled_for) -> None:
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().get(pk=run_id)
        if locked.delivery_status == "sending":
            locked.delivery_status = status
            locked.save(update_fields=["delivery_status"])
        state = run_state(locked, lock=True)
        state.delivery_mode = mode
        state.scheduled_for = scheduled_for
        state.save(update_fields=["delivery_mode", "scheduled_for", "updated_at"])


def deliver_to_postiz(
    run: ContentRun,
    user,
    *,
    mode: str,
    idempotency_key: str,
    schedule_at: str | None = None,
    channel_ids: list[str] | None = None,
    expected_revision: int | None = None,
) -> ContentRun:
    """Transfer one persisted ContentRun to Postiz exactly once for this idempotency key."""
    mode = (mode or "").strip().lower()
    if mode not in MODES:
        raise OperatorError("mode måste vara draft, schedule eller now.")
    if run.channel != "organic":
        raise OperatorError("Betalda annonsutkast skickas inte till Postiz som organiska inlägg.")
    _validate_context(run)
    if not run.workspace.postiz_key:
        raise OperatorError("Anslut Postiz för företaget först.")
    if not run.draft.get("facebook") or not run.draft.get("instagram"):
        raise OperatorError("Facebook- och Instagramcopy måste finnas före leverans.")

    scheduled = _parse_schedule(schedule_at)
    if mode == "schedule":
        if scheduled is None:
            raise OperatorError("schedule_at krävs när mode är schedule.")
        if scheduled <= timezone.now() + timedelta(minutes=2):
            raise OperatorError("Schemaläggningstiden måste ligga minst två minuter framåt.")
    elif schedule_at:
        raise OperatorError("schedule_at får bara anges när mode är schedule.")

    chosen = _channels(run, channel_ids)
    payload_identity = {
        "run_id": str(run.pk),
        "mode": mode,
        "schedule_at": scheduled.isoformat() if scheduled else None,
        "channel_ids": [str(channel["id"]) for channel in chosen],
        "revision": expected_revision,
    }
    action, execute = begin_action(
        run.workspace,
        user,
        action=f"postiz_{mode}",
        key=idempotency_key,
        payload=payload_identity,
        run=run,
    )
    if not execute:
        return ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)

    asset = run.media_asset
    previous_status = run.delivery_status
    previous_mode = ""
    previous_scheduled = None
    previous_result = list(run.delivery_result or [])
    flow = ""
    post_created = False
    try:
        # Validate the final Postiz payload before claiming the run or making any network write.
        make_payload(
            chosen,
            run.draft["facebook"],
            run.draft["instagram"],
            [{}] if asset else [],
            mode=mode,
            scheduled_for=scheduled,
        )
        with transaction.atomic():
            locked = ContentRun.objects.select_for_update().select_related("workspace", "media_asset").get(pk=run.pk)
            state = run_state(locked, lock=True)
            if expected_revision is not None and state.revision != expected_revision:
                raise OperatorError(
                    f"Inlägget har ändrats sedan det lästes (revision {state.revision}). Hämta runnet igen före leverans."
                )
            if locked.media_asset_id != run.media_asset_id:
                raise OperatorError("Vald media ändrades precis före leverans. Hämta runnet igen.")
            flow = _delivery_flow(locked, state, mode)
            previous_status = locked.delivery_status
            previous_mode = state.delivery_mode
            previous_scheduled = state.scheduled_for
            previous_result = list(locked.delivery_result or [])
            locked.delivery_status = "sending"
            locked.save(update_fields=["delivery_status"])
            state.delivery_mode = mode
            state.scheduled_for = scheduled
            state.revision += 1
            state.save(update_fields=["delivery_mode", "scheduled_for", "revision", "updated_at"])
            ContentEvent.objects.create(
                run=locked,
                idea_index=locked.selected,
                action="approved",
                data={
                    "mode": mode,
                    "schedule_at": scheduled.isoformat() if scheduled else None,
                    "channels": chosen,
                    "media_asset_id": str(asset.pk) if asset else None,
                    "operator_action_id": str(action.pk),
                    "delivery_flow": flow,
                    "supersedes": [item.get("postId") for item in previous_result if isinstance(item, dict)]
                    if flow in {"supersede_draft", "replace_remote_draft"} else [],
                },
            )

        media = []
        if asset:
            if asset.company_id != run.workspace_id:
                raise OperatorError("Vald media hör inte till företaget.")
            with open_asset(asset) as source:
                uploaded = postiz_request(
                    run.workspace.postiz_key,
                    "POST",
                    "/upload",
                    files={"file": (asset.storage_key.rsplit("/", 1)[-1], source, asset.mime_type)},
                )
            if not isinstance(uploaded, dict) or not uploaded.get("id") or not uploaded.get("path"):
                raise PostizError("Postiz kunde inte bekräfta mediauppladdningen.", uncertain=True)
            media = [{"id": uploaded["id"], "path": uploaded["path"]}]

        result = postiz_request(
            run.workspace.postiz_key,
            "POST",
            "/posts",
            json=make_payload(
                chosen,
                run.draft["facebook"],
                run.draft["instagram"],
                media,
                mode=mode,
                scheduled_for=scheduled,
            ),
        )
        if not isinstance(result, list) or len(result) != len(chosen) or not all(
            isinstance(item, dict) and item.get("postId") for item in result
        ):
            raise PostizError("Postiz-svaret gick inte att bekräfta.", uncertain=True)
        post_created = True

        normalized = []
        for channel, item in zip(chosen, result, strict=True):
            row = dict(item)
            row.setdefault("integration", channel["id"])
            row.setdefault("mode", mode)
            if scheduled:
                row.setdefault("scheduledFor", scheduled.isoformat())
            normalized.append(row)

        cleanup_failed = []
        if flow in {"supersede_draft", "replace_remote_draft"}:
            for old in previous_result:
                old_id = old.get("postId") if isinstance(old, dict) else None
                if not old_id:
                    continue
                try:
                    postiz_request(run.workspace.postiz_key, "DELETE", f"/posts/{old_id}")
                except PostizError:
                    # The old object is only a draft. Keep the confirmed new schedule/publication authoritative and
                    # surface the cleanup warning instead of risking a duplicate scheduled POST retry.
                    cleanup_failed.append(str(old_id))

        with transaction.atomic():
            locked = ContentRun.objects.select_for_update().get(pk=run.pk)
            if locked.delivery_status != "sending":
                raise OperatorError("ContentRun lämnade sending-state under leveransen. Kontrollera Postiz manuellt.")
            locked.delivery_status = "sent"
            locked.delivery_result = normalized
            locked.save(update_fields=["delivery_status", "delivery_result"])
            state = run_state(locked, lock=True)
            state.revision += 1
            state.synced_hash = content_hash(locked)
            state.save(update_fields=["revision", "synced_hash", "updated_at"])
            event_name = {"draft": "postiz_draft", "schedule": "postiz_schedule", "now": "postiz_publish"}[mode]
            ContentEvent.objects.create(
                run=locked,
                idea_index=locked.selected,
                action=event_name,
                data={
                    "posts": normalized,
                    "mode": mode,
                    "scheduled_for": scheduled.isoformat() if scheduled else None,
                    "operator_action_id": str(action.pk),
                    "delivery_flow": flow,
                    "superseded_posts": [item.get("postId") for item in previous_result if isinstance(item, dict)]
                    if flow in {"supersede_draft", "replace_remote_draft"} else [],
                    "superseded_cleanup_failed": cleanup_failed,
                    "synced_hash": state.synced_hash,
                },
            )
        finish_action(
            action,
            result={
                "run_id": str(run.pk),
                "mode": mode,
                "scheduled_for": scheduled.isoformat() if scheduled else None,
                "posts": normalized,
                "superseded_cleanup_failed": cleanup_failed,
            },
        )
        return ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)
    except PostizError as exc:
        if exc.uncertain:
            ContentRun.objects.filter(pk=run.pk, delivery_status="sending").update(delivery_status="unknown")
            finish_action(action, result={"run_id": str(run.pk)}, status="unknown", error=_durable_error(exc))
            raise OperatorError(
                "Postiz-leveransen kunde inte bekräftas. ContentRun är markerat unknown; kontrollera Postiz innan någon retry."
            ) from exc
        _restore_definite_failure(
            run.pk, status=previous_status, mode=previous_mode, scheduled_for=previous_scheduled
        )
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise OperatorError(str(exc)) from exc
    except MediaError as exc:
        _restore_definite_failure(
            run.pk, status=previous_status, mode=previous_mode, scheduled_for=previous_scheduled
        )
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise OperatorError(str(exc)) from exc
    except Exception as exc:
        if post_created:
            ContentRun.objects.filter(pk=run.pk, delivery_status="sending").update(delivery_status="unknown")
            finish_action(action, result={"run_id": str(run.pk)}, status="unknown", error=_durable_error(exc))
            raise OperatorError(
                "Postiz bekräftade den externa posten men lokal slutlagring misslyckades. Kontrollera Postiz; ingen automatisk retry görs."
            ) from exc
        _restore_definite_failure(
            run.pk, status=previous_status, mode=previous_mode, scheduled_for=previous_scheduled
        )
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise


def reset_unknown_delivery(
    run: ContentRun,
    user,
    *,
    confirmed_no_post_exists: bool,
    idempotency_key: str,
) -> ContentRun:
    if not confirmed_no_post_exists:
        raise OperatorError("Återställning kräver uttrycklig bekräftelse att ingen ny motsvarande Postiz-post finns.")
    action, execute = begin_action(
        run.workspace,
        user,
        action="reset_unknown_delivery",
        key=idempotency_key,
        payload={"run_id": str(run.pk), "confirmed_no_post_exists": True},
        run=run,
    )
    if not execute:
        return ContentRun.objects.get(pk=run.pk)
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().get(pk=run.pk)
        if locked.delivery_status not in {"unknown", "sending"}:
            raise OperatorError("Endast en osäker eller avbruten Postiz-leverans kan återställas.")
        state = run_state(locked, lock=True)
        previous_draft = bool(locked.delivery_result) and all(
            isinstance(item, dict) and item.get("mode") == "draft" for item in locked.delivery_result
        )
        local_matches_previous_draft = previous_draft and bool(state.synced_hash) and state.synced_hash == content_hash(locked)
        locked.delivery_status = "sent" if local_matches_previous_draft else "draft"
        locked.save(update_fields=["delivery_status"])
        state.delivery_mode = "draft" if previous_draft else ""
        state.scheduled_for = None
        state.revision += 1
        state.save(update_fields=["delivery_mode", "scheduled_for", "revision", "updated_at"])
        # The human/operator has established that the uncertain external write did not create the new Postiz post.
        # Mark prior reservations safe-to-retry instead of leaving them permanently blocked.
        OperatorAction.objects.filter(
            company=locked.workspace,
            run=locked,
            action__startswith="postiz_",
            status__in=("started", "unknown"),
        ).update(
            status="failed",
            error="Reconciled after explicit confirmation that no new Postiz post exists.",
            updated_at=timezone.now(),
        )
        ContentEvent.objects.create(
            run=locked,
            idea_index=locked.selected,
            action="delivery_reset",
            data={
                "confirmed_no_post_exists": True,
                "operator_action_id": str(action.pk),
                "restored_previous_draft": previous_draft,
                "local_matches_previous_draft": local_matches_previous_draft,
            },
        )
    finish_action(
        action,
        result={
            "run_id": str(run.pk),
            "state": "sent" if local_matches_previous_draft else "draft",
            "restored_previous_draft": previous_draft,
            "local_matches_previous_draft": local_matches_previous_draft,
        },
    )
    return ContentRun.objects.get(pk=run.pk)
