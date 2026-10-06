"""Company-scoped Ad Studio operations. Same functions for MCP and web."""

from __future__ import annotations

import re

from django.db import transaction
from pydantic import ValidationError as PydanticValidationError

from engine.models import Company, MediaAsset
from engine.operator_common import serialize_asset

from . import blueprints
from .brief import AdBrief, BriefNotReady
from .models import AdDraft, AssetTags

ROLE_VALUES = {"hook", "footage", "screen", "product", "proof", "end_card", "logo", "other"}

# Which question to ask next for each missing field. The assistant turns these
# into one short question with suggested answers (see golfkuponger-friskvard).
NEXT_QUESTION = {
    "message": "Vad är det enda tittaren ska komma ihåg?",
    "objective": "Vad ska annonsen åstadkomma: kännedom, övervägande, köp eller återaktivering?",
    "audience": "Vem pratar vi med?",
    "angle": "Föreslå tre olika vinklar med hook och låt användaren välja.",
    "assets": "Föreslå bilder ur banken (search_ad_assets) per scenroll och låt användaren markera, eller be om uppladdning.",
    "engine": "Remotion (gratis, mall) eller Higgsfield (AI-video, kostar)? Ge en rekommendation och kostnad.",
    "scenes": "Bygg storyboarden scen för scen. För Remotion: utgå från get_ad_template_blueprint.",
    "duration_s": "Hur lång ska annonsen vara?",
    "copy.headline": "Föreslå rubrik och primärtext för flödet.",
}


def _parse(data: dict) -> AdBrief:
    try:
        return AdBrief.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[:3]
        raise ValueError(
            "Ogiltig brief: " + "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in first)
        ) from exc


def serialize(draft: AdDraft) -> dict:
    brief = _parse(draft.brief)
    missing = brief.missing()
    return {
        "draft_id": str(draft.pk),
        "title": draft.title,
        "revision": draft.revision,
        "status": draft.status,
        "brief": brief.model_dump(mode="json", by_alias=True),
        "missing": missing,
        "next_question": NEXT_QUESTION.get(missing[0]) if missing else None,
        "problems": brief.problems(),
        "lockable": not missing and not brief.problems(),
        "motion_project_id": str(draft.motion_project_id) if draft.motion_project_id else None,
    }


def get_draft(company: Company, draft_id, *, lock=False) -> AdDraft:
    qs = AdDraft.objects.filter(company=company, pk=draft_id)
    if lock:
        qs = qs.select_for_update()
    draft = qs.first()
    if not draft:
        raise ValueError("Annonsutkastet finns inte för detta företag.")
    return draft


def _check_assets(company: Company, brief: AdBrief) -> None:
    ids = [a.asset_id for a in brief.assets if a.origin != "generate"]
    if not ids:
        return
    try:
        found = set(
            str(pk) for pk in MediaAsset.objects.filter(company=company, pk__in=ids).values_list("pk", flat=True)
        )
    except Exception as exc:  # malformed UUIDs
        raise ValueError("Ett eller flera asset_id är ogiltiga.") from exc
    unknown = [i for i in ids if i not in found]
    if unknown:
        raise ValueError("Dessa bilder/videor finns inte i företagets media: " + ", ".join(unknown))


def list_drafts(company: Company) -> list[dict]:
    return [serialize(d) for d in company.ad_drafts.exclude(status="archived")[:30]]


@transaction.atomic
def start_draft(company: Company, user, *, message: str = "", title: str = "") -> AdDraft:
    brief = AdBrief(company=company.name.casefold(), message=message.strip()[:200])
    return AdDraft.objects.create(
        company=company,
        author=user,
        title=(title or message or "Ny annons").strip()[:160],
        brief=brief.model_dump(mode="json", by_alias=True),
    )


@transaction.atomic
def update_draft(company: Company, draft_id, *, changes: dict, expected_revision: int) -> AdDraft:
    """Shallow merge: every top-level key in `changes` replaces that key in the brief."""
    draft = get_draft(company, draft_id, lock=True)
    if draft.revision != expected_revision:
        raise ValueError(f"Utkastet har ändrats (revision {draft.revision}). Läs om det och försök igen.")
    if draft.status != "draft":
        raise ValueError("Briefen är låst. Använd reopen_ad_brief för att ändra.")
    forbidden = {"status", "locked_at", "lock_hash", "version"} & set(changes)
    if forbidden:
        raise ValueError("Dessa fält sätts bara av systemet: " + ", ".join(sorted(forbidden)))
    merged = {**draft.brief, **changes}
    brief = _parse(merged)
    _check_assets(company, brief)
    draft.brief = brief.model_dump(mode="json", by_alias=True)
    if "message" in changes and brief.message and not draft.title:
        draft.title = brief.message[:160]
    draft.revision += 1
    draft.save()
    return draft


@transaction.atomic
def lock_draft(company: Company, draft_id, *, expected_revision: int) -> AdDraft:
    draft = get_draft(company, draft_id, lock=True)
    if draft.revision != expected_revision:
        raise ValueError(f"Utkastet har ändrats (revision {draft.revision}). Läs om det och försök igen.")
    brief = _parse(draft.brief)
    _check_assets(company, brief)
    if brief.engine and brief.engine.remotion_template_id:
        blueprints.template_fields(brief)  # fail now, not at render time
    try:
        locked = brief.lock()
    except BriefNotReady as exc:
        raise ValueError(str(exc)) from exc
    draft.brief = locked.model_dump(mode="json", by_alias=True)
    draft.status = "locked"
    draft.lock_hash = locked.lock_hash
    draft.revision += 1
    draft.save()
    return draft


@transaction.atomic
def reopen_draft(company: Company, draft_id) -> AdDraft:
    draft = get_draft(company, draft_id, lock=True)
    if draft.status == "producing":
        raise ValueError("Annonsen produceras redan. Skapa ett nytt utkast för en ny version.")
    brief = _parse(draft.brief).model_copy(update={"status": "draft", "locked_at": None, "lock_hash": None})
    draft.brief = brief.model_dump(mode="json", by_alias=True)
    draft.status = "draft"
    draft.lock_hash = ""
    draft.revision += 1
    draft.save()
    return draft


def produce(company: Company, user, draft_id, *, key: str) -> dict:
    """Start production from a locked brief. Never adds anything not in the brief."""
    from engine.motion import service as motion_service

    with transaction.atomic():
        draft = get_draft(company, draft_id, lock=True)
        brief = _parse(draft.brief)
        if draft.status not in {"locked", "producing"} or not brief.verify_lock() or brief.lock_hash != draft.lock_hash:
            raise ValueError("Bara en låst och oförändrad brief kan produceras. Lås briefen först.")

        engine = brief.engine.engine
        generate = [a for a in brief.assets if a.origin == "generate"]
        if engine in {"higgsfield", "hybrid"} and generate:
            return {
                "status": "needs_generation",
                "draft_id": str(draft.pk),
                "generation_requests": [
                    {"placeholder_asset_id": a.asset_id, "role": a.role, "prompt": a.generation_prompt} for a in generate
                ],
                "next": (
                    "Generera varje asset med preview_media_generation och start_reviewed_media_generation "
                    "(kostnaden är godkänd i briefen). Öppna sedan briefen igen, ersätt placeholder-id med "
                    "de nya asset-id:na, lås och kör produce_ad igen."
                ),
            }
        if not brief.engine.remotion_template_id:
            raise ValueError("Ren Higgsfield-produktion utan Remotion-mall görs via mediaverktygen.")

        spec = blueprints.compile_brief(brief)
        project = motion_service.create_project(
            company,
            user,
            title=(draft.title or brief.message or "Annons")[:160],
            spec=spec,
            key=key,
            logo_asset=company.official_logo,
        )
        draft.motion_project = project
        draft.status = "producing"
        draft.save(update_fields=["motion_project", "status", "updated_at"])
    return {
        "status": "motion_project_created",
        "draft_id": str(draft.pk),
        "motion_project_id": str(project.pk),
        "revision": project.current_revision,
        "next": "Kör render_motion_project med mode=preview, visa resultatet, godkänn och rendera final.",
    }


# ---- image bank ---------------------------------------------------------

_WORD = re.compile(r"[\wåäöÅÄÖ]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall(text.casefold()) if len(t) > 2}


def tag_asset(company: Company, asset_id, *, description: str, tags: list[str], roles: list[str],
              theme: str = "", season: str = "", mood: str = "", source: str = "", verified: bool = False) -> AssetTags:
    asset = MediaAsset.objects.filter(company=company, pk=asset_id).first()
    if not asset:
        raise ValueError("Media-asset finns inte för detta företag.")
    bad = set(roles) - ROLE_VALUES
    if bad:
        raise ValueError("Okända roller: " + ", ".join(sorted(bad)) + ". Tillåtna: " + ", ".join(sorted(ROLE_VALUES)))
    clean_tags = sorted({t.strip().casefold()[:40] for t in tags if t.strip()})[:30]
    obj, _ = AssetTags.objects.update_or_create(
        asset=asset,
        defaults=dict(
            description=description.strip()[:500], tags=clean_tags, roles=sorted(set(roles)),
            theme=theme.strip()[:60], season=season.strip()[:20], mood=mood.strip()[:60],
            source=source.strip()[:200], verified=verified,
        ),
    )
    return obj


def serialize_tags(tags: AssetTags | None) -> dict | None:
    if not tags:
        return None
    return {"description": tags.description, "tags": tags.tags, "roles": tags.roles, "theme": tags.theme,
            "season": tags.season, "mood": tags.mood, "source": tags.source, "verified": tags.verified}


def search_assets(company: Company, *, query: str = "", role: str = "", kind: str = "", limit: int = 12) -> dict:
    qs = MediaAsset.objects.filter(company=company, purpose="content").select_related("ad_tags")
    if kind in {"image", "video"}:
        qs = qs.filter(kind=kind)
    else:
        qs = qs.filter(kind__in=["image", "video"])
    wanted = _tokens(query)
    scored = []
    untagged = 0
    for asset in qs.order_by("-created_at")[:500]:
        tags = getattr(asset, "ad_tags", None)
        if tags is None:
            untagged += 1
        if role and (not tags or role not in tags.roles):
            continue
        hay = _tokens(" ".join([tags.search_text() if tags else "", asset.alt_text, asset.brief]))
        score = len(wanted & hay) if wanted else 0
        if wanted and score == 0:
            continue
        if tags and tags.verified:
            score += 0.5
        scored.append((score, asset, tags))
    scored.sort(key=lambda item: (-item[0], -item[1].created_at.timestamp()))
    limit = max(1, min(limit, 30))
    return {
        "results": [
            {**serialize_asset(asset), "score": score, "tags": serialize_tags(tags)} for score, asset, tags in scored[:limit]
        ],
        "untagged_count": untagged,
        "hint": (
            f"{untagged} bilder/videor saknar taggar. Titta på dem med view_media och tagga med tag_media_asset "
            "så blir förslagen bättre." if untagged else ""
        ),
    }


def untagged_assets(company: Company, limit: int = 20) -> list[dict]:
    qs = MediaAsset.objects.filter(company=company, purpose="content", kind__in=["image", "video"], ad_tags__isnull=True)
    return [serialize_asset(a) for a in qs.order_by("-created_at")[: max(1, min(limit, 50))]]
