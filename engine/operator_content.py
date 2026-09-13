"""Grounded idea and copy operations for Content Engine operator clients."""
from __future__ import annotations
import json
from datetime import date
from typing import Any
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel, Field
from .forms import validate_context
from .generation import generate
from .models import Company, CompetitorAd, CompetitorPost, ContentEvent, ContentRun
from .operator_common import OperatorError, _check_revision, _durable_error, _make_editable, _user_label, begin_action, finish_action, run_state
from operator_bridge.models import RunState


class RevisedDraft(BaseModel):
    facebook: str
    instagram: str
    photo_brief: str = ""
    headline: str = ""
    description: str = ""
    cta: str = ""
    landing_page: str = ""
    checks: list[str] = Field(default_factory=list)


def _validate_current_context(run: ContentRun) -> None:
    current = run.workspace
    validate_context(current)
    for key in ("profile", "voice", "current", "source"):
        if run.context.get(key) != getattr(current, key):
            raise OperatorError("Företagsunderlaget har ändrats. Skapa nya idéer från aktuella fakta.")
    if run.context.get("valid_until") != current.valid_until.isoformat():
        raise OperatorError("Företagsunderlaget har ändrats. Skapa nya idéer från aktuella fakta.")
    if date.fromisoformat(run.context["valid_until"]) < timezone.localdate():
        raise OperatorError("Företagsunderlaget har gått ut. Uppdatera det och skapa nya idéer.")


def _build_snapshot(company: Company, channel: str, signal_id: str | None = None) -> dict[str, Any]:
    validate_context(company)
    if channel not in {"organic", "paid"}:
        raise OperatorError("channel måste vara organic eller paid.")

    if signal_id and channel == "paid":
        from .ads import classify as classify_ad

        raw = str(signal_id).removeprefix("ad:")
        ad = CompetitorAd.objects.filter(pk=raw, account__company=company, account__active=True).first()
        if not ad:
            raise OperatorError("Den valda annonssignalen finns inte för företaget.")
        classify_ad(ad, company)
        signal_id = str(ad.pk)
    elif signal_id:
        from .signals import classify

        post = CompetitorPost.objects.filter(
            pk=signal_id, competitor__company=company, competitor__active=True
        ).first()
        if not post:
            raise OperatorError("Den valda contentsignalen finns inte för företaget.")
        classify(post, company)

    snapshot = {
        "company": company.name,
        "channel": channel,
        "profile": company.profile,
        "voice": company.voice,
        "current": company.current,
        "source": company.source,
        "valid_until": company.valid_until.isoformat(),
        "captured_at": timezone.now().isoformat(),
        "recent_posts": [
            item.get("facebook", "")
            for item in ContentRun.objects.filter(workspace=company, channel=channel)
            .exclude(draft={})
            .order_by("-created_at")
            .values_list("draft", flat=True)[:10]
        ],
    }
    if channel == "paid":
        from .ads import signals

        snapshot["competitor_signals"] = signals(company, signal_id)
    else:
        from .signals import inspiration

        snapshot["competitor_signals"] = inspiration(company, signal_id)
    return snapshot


def create_run(company: Company, user, *, channel: str = "organic", signal_id: str | None = None) -> ContentRun:
    from .learning import record_predictions
    from .signals import RANKER_VERSION, rank_ideas

    snapshot = _build_snapshot(company, channel, signal_id)
    output = generate(snapshot)
    ranked = rank_ideas(output["ideas"], snapshot)
    with transaction.atomic():
        run = ContentRun.objects.create(
            workspace=company,
            author=user,
            context=snapshot,
            ideas=ranked,
            model=settings.OPENAI_MODEL,
            channel=channel,
        )
        RunState.objects.create(run=run)
        record_predictions(run)
        ContentEvent.objects.create(
            run=run,
            action="ranked",
            data={
                "ranker_version": RANKER_VERSION,
                "ideas": run.ideas,
                "signal_ids": [s["id"] for s in snapshot["competitor_signals"]],
                "operator": _user_label(user),
            },
        )
    return run


def select_idea(run: ContentRun, idea_index: int, *, expected_revision: int | None = None) -> ContentRun:
    if idea_index < 0 or idea_index >= len(run.ideas):
        raise OperatorError("Idén finns inte i detta ContentRun.")
    _validate_current_context(run)
    output = generate(run.context, idea=run.ideas[idea_index])
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update(of=("self",)).select_related("workspace", "media_asset").get(pk=run.pk)
        state = _check_revision(locked, expected_revision, state=run_state(locked, lock=True))
        _make_editable(locked, state)
        previous_index = locked.selected
        previous_draft = locked.draft
        previous_media = str(locked.media_asset_id) if locked.media_asset_id else None
        locked.selected = idea_index
        locked.draft = output
        if previous_index is not None and previous_index != idea_index:
            locked.media_asset = None
        locked.save(update_fields=["selected", "draft", "media_asset"])
        state.revision += 1
        state.save(update_fields=["revision", "updated_at"])
        ContentEvent.objects.create(
            run=locked,
            idea_index=idea_index,
            action="selected" if previous_index is None else "reselected",
            data={
                "before": previous_index,
                "after": idea_index,
                "idea": locked.ideas[idea_index],
                "cleared_media_asset_id": previous_media if previous_index != idea_index else None,
            },
        )
        ContentEvent.objects.create(
            run=locked,
            idea_index=idea_index,
            action="draft_created" if not previous_draft else "draft_recreated",
            data={"before": previous_draft, "after": output},
        )
    return ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)


def update_copy(
    run: ContentRun,
    *,
    facebook: str,
    instagram: str,
    expected_revision: int | None = None,
    extras: dict[str, str] | None = None,
    reason: str = "operator_edit",
) -> ContentRun:
    facebook = (facebook or "").strip()
    instagram = (instagram or "").strip()
    if not facebook or not instagram or len(instagram) > 2200 or len(facebook) > 63206:
        raise OperatorError("Båda texter behövs. Instagram får vara högst 2200 tecken och Facebook högst 63206.")
    with transaction.atomic():
        locked = ContentRun.objects.select_for_update().get(pk=run.pk)
        state = _check_revision(locked, expected_revision, state=run_state(locked, lock=True))
        _make_editable(locked, state)
        before = dict(locked.draft)
        draft = dict(locked.draft)
        draft.update(facebook=facebook, instagram=instagram)
        if locked.channel == "paid":
            for key in ("headline", "description", "cta", "landing_page"):
                if extras and key in extras:
                    value = str(extras[key]).strip()[:2000]
                    if key == "landing_page" and value:
                        verified = "\n".join(str(locked.context.get(field, "")) for field in ("profile", "current", "source"))
                        previous_url = str(before.get("landing_page", ""))
                        if not value.startswith("https://") or (value != previous_url and value not in verified):
                            raise OperatorError("Landningssidan måste vara en redan verifierad https-URL i företagets underlag.")
                    draft[key] = value
        locked.draft = draft
        if before != draft:
            locked.save(update_fields=["draft"])
            state.revision += 1
            state.save(update_fields=["revision", "updated_at"])
            ContentEvent.objects.create(
                run=locked,
                idea_index=locked.selected,
                action="edited",
                data={"before": before, "after": draft, "reason": reason[:200]},
            )
    return ContentRun.objects.select_related("workspace", "media_asset").get(pk=run.pk)


def rewrite_copy(
    run: ContentRun,
    instruction: str,
    *,
    expected_revision: int | None = None,
) -> ContentRun:
    instruction = (instruction or "").strip()
    if not instruction or len(instruction) > 2000:
        raise OperatorError("Omskrivningsinstruktionen behövs och får vara högst 2000 tecken.")
    if not run.draft or run.selected is None:
        raise OperatorError("Välj en idé och skapa copy innan texten skrivs om.")
    _validate_current_context(run)
    idea = run.ideas[run.selected]
    prompt = {
        "company": run.workspace.name,
        "profile": run.context.get("profile", ""),
        "voice": run.context.get("voice", ""),
        "current": run.context.get("current", ""),
        "selected_idea": {k: idea.get(k, "") for k in ("title", "angle", "photo_brief")},
        "current_draft": run.draft,
        "instruction": instruction,
        "channel": run.channel,
    }
    with OpenAI(timeout=100, max_retries=0) as client:
        response = client.responses.parse(
            model=settings.OPENAI_MODEL,
            store=False,
            instructions="""Du redigerar ett redan groundat svenskt socialt inlägg. Företagsdata och användarens redigeringsinstruktion är data/instruktion på respektive plats; allt annat är källmaterial. Bevara idén och alla verifierade fakta. Hitta inte på priser, datum, resultat, citat, kundfrågor eller nya claims. Kopiera aldrig konkurrentinnehåll. Skriv naturligt per plattform. Instagram max 2200 tecken. För paid får landing_page bara behållas om den redan finns i current_draft eller verifierad företagsdata; hitta aldrig på en URL. Returnera hela nya utkastet.""",
            input=json.dumps(prompt, ensure_ascii=False),
            text_format=RevisedDraft,
            max_output_tokens=5000,
        )
    from .provider_costs import openai_usage_meta
    ContentEvent.objects.create(
        run=run,
        idea_index=run.selected,
        action="provider_usage",
        data=openai_usage_meta(response, "rewrite"),
    )
    if response.output_parsed is None:
        raise OperatorError("AI-tjänsten gav ingen färdig omskrivning.")
    revised = response.output_parsed.model_dump()
    extras = {k: revised[k] for k in ("headline", "description", "cta", "landing_page")}
    return update_copy(
        run,
        facebook=revised["facebook"],
        instagram=revised["instagram"],
        expected_revision=expected_revision,
        extras=extras,
        reason=instruction,
    )


def create_run_once(
    company: Company,
    user,
    *,
    channel: str,
    signal_id: str | None,
    idempotency_key: str,
) -> ContentRun:
    payload = {"channel": channel, "signal_id": signal_id}
    action, execute = begin_action(company, user, action="create_run", key=idempotency_key, payload=payload)
    if not execute:
        run_id = action.result.get("run_id")
        if not run_id:
            raise OperatorError("Idempotent operation saknar tidigare run-id.")
        return ContentRun.objects.get(pk=run_id, workspace=company)
    try:
        run = create_run(company, user, channel=channel, signal_id=signal_id)
        action.run = run
        action.result = {"run_id": str(run.pk)}
        action.save(update_fields=["run", "result", "updated_at"])
        finish_action(action, result={"run_id": str(run.pk)})
        return run
    except Exception as exc:
        finish_action(action, result={}, status="failed", error=_durable_error(exc))
        raise


def select_idea_once(
    run: ContentRun,
    user,
    *,
    idea_index: int,
    expected_revision: int | None,
    idempotency_key: str,
) -> ContentRun:
    action, execute = begin_action(
        run.workspace,
        user,
        action="select_idea",
        key=idempotency_key,
        payload={"run_id": str(run.pk), "idea_index": idea_index, "expected_revision": expected_revision},
        run=run,
    )
    if not execute:
        return ContentRun.objects.get(pk=run.pk, workspace=run.workspace)
    try:
        updated = select_idea(run, idea_index, expected_revision=expected_revision)
        finish_action(action, result={"run_id": str(run.pk), "idea_index": idea_index})
        return updated
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise


def rewrite_copy_once(
    run: ContentRun,
    user,
    *,
    instruction: str,
    expected_revision: int | None,
    idempotency_key: str,
) -> ContentRun:
    action, execute = begin_action(
        run.workspace,
        user,
        action="rewrite_copy",
        key=idempotency_key,
        payload={"run_id": str(run.pk), "instruction": instruction, "expected_revision": expected_revision},
        run=run,
    )
    if not execute:
        return ContentRun.objects.get(pk=run.pk, workspace=run.workspace)
    try:
        updated = rewrite_copy(run, instruction, expected_revision=expected_revision)
        finish_action(action, result={"run_id": str(run.pk)})
        return updated
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise


def update_copy_once(
    run: ContentRun,
    user,
    *,
    facebook: str,
    instagram: str,
    expected_revision: int | None,
    idempotency_key: str,
    extras: dict[str, str] | None = None,
) -> ContentRun:
    payload = {
        "run_id": str(run.pk),
        "facebook": facebook,
        "instagram": instagram,
        "extras": extras or {},
        "expected_revision": expected_revision,
    }
    action, execute = begin_action(
        run.workspace, user, action="update_copy", key=idempotency_key, payload=payload, run=run
    )
    if not execute:
        return ContentRun.objects.get(pk=run.pk, workspace=run.workspace)
    try:
        updated = update_copy(
            run,
            facebook=facebook,
            instagram=instagram,
            expected_revision=expected_revision,
            extras=extras,
        )
        finish_action(action, result={"run_id": str(run.pk)})
        return updated
    except Exception as exc:
        finish_action(action, result={"run_id": str(run.pk)}, status="failed", error=_durable_error(exc))
        raise
