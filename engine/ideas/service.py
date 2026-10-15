"""Idea cards: monitoring finds a hit → break it down → pitch our spin in one sentence → only the best reach Discord.

A hit is a post with far more views than its account normally gets (our own account first: our own hits are the
best templates), or an ad that has kept running for a long time (an ad that runs for months is making money).
Each hit is broken down (engine/references) and pitched by a cheap text model, which also judges how good an idea it
is for us (fit 1–10). Cards below IDEA_MIN_FIT are never sent, and at most IDEA_WEEKLY_MAX are sent per company and
week, best first, at whatever time the daily job finds them: few notifications, each one worth opening.

👍 Skapa turns the pitch into a full plan (references.adapt) in the background and answers on the card with what the
company has to supply (photos, clips, facts), nothing more to read.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import timedelta
from decimal import Decimal

from django.db import close_old_connections
from django.utils import timezone
from pydantic import BaseModel, Field

from .models import IdeaCard

log = logging.getLogger(__name__)

PITCH_VERSION = "idea-pitch/1"


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def min_ratio() -> float:
    """A competitor's post must reach this many times its account's median views."""
    return _float("IDEA_MIN_RATIO", 3.0)


def own_min_ratio() -> float:
    """Our own post must reach this many times our own median views."""
    return _float("IDEA_OWN_MIN_RATIO", 3.0)


def min_ad_days() -> int:
    return _int("IDEA_MIN_AD_DAYS", 30)


def min_fit() -> int:
    return _int("IDEA_MIN_FIT", 7)


def weekly_max() -> int:
    return _int("IDEA_WEEKLY_MAX", 2)


def daily_breakdowns() -> int:
    """New hits broken down and pitched per company and day (each ≈ 0.02–0.03 USD)."""
    return _int("IDEA_DAILY_LIMIT", 2)


def source_key(row: dict) -> str:
    return f"ad:{row['ad_id']}" if row["kind"] == "ad" else f"{row['platform']}:{row['post_id']}"


def _why(row: dict) -> str:
    from engine.references.service import number

    if row["kind"] == "ad":
        text = f"{row['advertiser']}: annonsen har gått i {row['days_running']} dagar"
        text += ", fortfarande aktiv" if row.get("active") else ""
        if row.get("eu_reach"):
            text += f", {number(row['eu_reach'])} i EU-räckvidd"
        return text
    platform = "TikTok" if row["platform"] == "tiktok" else "Instagram"
    who = "Ert eget inlägg" if row.get("own") else f"{row['advertiser']} ({platform})"
    normal = "era vanliga" if row.get("own") else "kontots vanliga"
    unit = "gillningar" if row.get("metric") == "likes" else "visningar"
    return f"{who}: {number(row['views'])} {unit}, {row['ratio']:.1f}× {normal}"


def hits(company) -> list[dict]:
    """Monitored hits not yet carded, best first: our own posts, then posts by ratio and ads by days running."""
    from engine.references import service as references

    known = set(IdeaCard.objects.filter(company=company).values_list("source_key", flat=True))
    rows = []
    for row in references.candidates(company, limit=200):
        if source_key(row) in known:
            continue
        if row["kind"] == "ad":
            if row["days_running"] < min_ad_days():
                continue
            rank = (1, row["days_running"] / 30 * (2 if row.get("active") else 1))
        else:
            if row["ratio"] < (own_min_ratio() if row.get("own") else min_ratio()):
                continue
            rank = (2 if row.get("own") else 1, row["ratio"])
        rows.append({**row, "rank": rank})
    rows.sort(key=lambda r: r["rank"], reverse=True)
    return rows


class Pitch(BaseModel):
    summary: str = Field(description="Vad originalet är, en kort mening på svenska (max 140 tecken)")
    spin: str = Field(description="Vår version för bolaget i 1–2 korta meningar (max 220 tecken): krok och vinkel, "
                                  "konkret, utan att kopiera originalets text, personer eller varumärke")
    fit: int = Field(ge=1, le=10, description="Hur bra idé det är för bolaget just nu: passar målgruppen, går att göra "
                                              "med rimligt material, säsong. 7 = värd att göra.")
    fit_note: str = Field(description="Varför det betyget, en kort mening")


PITCH_SYSTEM = (
    "Du är kreativ chef för korta sociala videor (Reels/TikTok). Du får nedbrytningen av en video som gått riktigt "
    "bra (siffrorna står i 'signal') och en kort profil av vårt bolag. Föreslå VÅR version: samma grammatik (krok, "
    "format, rytm) men vårt innehåll och vår vinkel. Var kort – ägaren läser detta i mobilen. Kopiera aldrig "
    "originalets formuleringar, personer, varumärke eller påståenden. Bedöm ärligt hur bra idén är för oss: dra ner "
    "betyget om formatet inte passar målgruppen, om filmen bara fungerar med en kändis eller ett stort lag, eller om "
    "materialet är orimligt att ta fram. Skriv på svenska."
)


def pitch(card: IdeaCard) -> IdeaCard:
    from engine.openrouter import structured_analysis

    ref, company = card.reference, card.company
    b = ref.breakdown or {}
    payload = {
        "signal": {**card.signal, "why": card.why},
        "original": {k: b.get(k) for k in ("summary", "format", "hook", "structure", "why_it_works", "mechanics")},
        "our_company": {"name": company.name, "profile": company.profile[:1500], "voice": company.voice[:600],
                        "current": company.current[:800]},
        "season": timezone.localdate().isoformat(),
    }
    result, meta = structured_analysis(system=PITCH_SYSTEM, payload=payload, schema=Pitch, operation="idea_pitch",
                                       max_tokens=1200, temperature=0.4)
    card.summary, card.spin = result.summary[:300], result.spin[:600]
    card.fit, card.fit_note = result.fit, result.fit_note[:300]
    if meta.get("cost_usd") is not None:
        card.cost_usd += Decimal(str(meta["cost_usd"]))
    card.save()
    return card


def make_card(company, row: dict) -> IdeaCard:
    """Break the hit down (reusing an earlier breakdown of the same file) and pitch it. Raises on fetch/AI errors,
    after saving the card as failed so it is not retried every day."""
    from engine.references import service as references

    signal = {k: row.get(k) for k in ("kind", "platform", "advertiser", "views", "baseline_views", "metric", "ratio",
                                      "days_running", "active", "eu_reach", "published_at", "headline")}
    card, _ = IdeaCard.objects.update_or_create(
        company=company, source_key=source_key(row),
        defaults={"source_url": row["url"], "own": bool(row.get("own")), "signal": signal, "why": _why(row)[:300]})
    try:
        ref = references.process(company, row["url"], video_url=row.get("video_url", ""))
        card.reference = ref
        card.cost_usd = ref.cost_usd
        card.save(update_fields=["reference", "cost_usd"])
        pitch(card)
    except Exception as exc:
        card.status, card.error = "failed", str(exc)[:500]
        card.save(update_fields=["status", "error"])
        raise
    return card


def sent_this_week(company) -> int:
    return IdeaCard.objects.filter(company=company, sent_at__gte=timezone.now() - timedelta(days=7)).count()


def next_to_send(company) -> IdeaCard | None:
    """The best pitched card that clears the bar, if the week still has room. Older than 10 days → skipped."""
    stale = timezone.now() - timedelta(days=10)
    IdeaCard.objects.filter(company=company, status="pitched", created_at__lt=stale).update(status="skipped")
    IdeaCard.objects.filter(company=company, status="pitched", fit__lt=min_fit()).update(status="skipped")
    if sent_this_week(company) >= weekly_max():
        return None
    pitched = IdeaCard.objects.filter(company=company, status="pitched", fit__gte=min_fit())
    return pitched.order_by("-own", "-fit", "created_at").first()  # hits are pitched strongest first


def send(card: IdeaCard, *, client=None) -> IdeaCard:
    from engine.review import discord as review_discord

    from . import discord

    data = review_discord.post(discord.card(card), card.company, client=client)
    card.discord_channel_id = str(data.get("channel_id") or card.company.review_channel_id)
    card.discord_message_id = str(data.get("message_id") or data.get("id") or "")
    card.status, card.sent_at = "sent", timezone.now()
    card.save(update_fields=["discord_channel_id", "discord_message_id", "status", "sent_at"])
    return card


def _feedback(card: IdeaCard, kind: str, reviewer: dict, **fields) -> None:
    card.feedback = [*card.feedback, {"kind": kind, "by": reviewer.get("name", ""), "by_id": reviewer.get("id", ""),
                                      "at": timezone.now().isoformat(), **fields}]


def reject(card: IdeaCard, reviewer: dict) -> str:
    card.status, card.decided_at = "rejected", timezone.now()
    _feedback(card, "reject", reviewer)
    card.save(update_fields=["status", "decided_at", "feedback"])
    return "👎 Sparat. Skriv gärna en kommentar om varför, så blir nästa förslag bättre."


def rate(card: IdeaCard, rating: int, reviewer: dict) -> str:
    if not 1 <= rating <= 10:
        raise ValueError("Betyget måste vara 1–10.")
    card.rating = rating
    _feedback(card, "rating", reviewer, rating=rating)
    card.save(update_fields=["rating", "feedback"])
    return f"Betyg {rating}/10 sparat."


def comment(card: IdeaCard, text: str, reviewer: dict) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("Kommentaren är tom.")
    _feedback(card, "comment", reviewer, text=text[:2000])
    card.save(update_fields=["feedback"])
    return "💬 Kommentaren är sparad."


def background(work) -> None:
    """Run `work` after the Discord interaction has been answered (planning takes 30–60 s)."""
    def run():
        try:
            work()
        except Exception:  # noqa: BLE001 – logged; the card keeps status/error
            log.exception("Idea background work failed")
        finally:
            close_old_connections()

    threading.Thread(target=run, daemon=True, name="idea-plan").start()


def approve(card: IdeaCard, reviewer: dict) -> str:
    if card.status == "approved":
        return "Den här idén är redan på gång."
    card.status, card.decided_at = "approved", timezone.now()
    _feedback(card, "approve", reviewer)
    card.save(update_fields=["status", "decided_at", "feedback"])
    background(lambda: plan(card.pk))
    return "👍 Kör! Jag tar fram vad som behövs och svarar på kortet om någon minut."


MATERIAL_NEEDS = {"filma": "🎥 Filma", "produktbild": "📷 Bild"}


def needs_from(plan_: dict) -> list[str]:
    """What the company must supply, one short line each: shots to film, product photos, facts to confirm."""
    lines, seen = [], set()
    for scene in plan_.get("scenes", []):
        label = MATERIAL_NEEDS.get(scene.get("material"))
        detail = (scene.get("material_detail") or scene.get("shows") or "").strip()
        if label and detail and detail.casefold() not in seen:
            seen.add(detail.casefold())
            lines.append(f"{label}: {detail}")
    for shot in plan_.get("to_film", []):
        if shot.strip().casefold() not in seen and not any(shot.strip().casefold() in s for s in seen):
            seen.add(shot.strip().casefold())
            lines.append(f"🎥 Filma: {shot.strip()}")
    for fact in plan_.get("facts_to_verify", []):
        lines.append(f"✔️ Bekräfta: {fact.get('claim', '').strip()}")
    return [line[:220] for line in lines][:8]


def plan(card_id) -> IdeaCard:
    """👍 → our full version (references.adapt) → the list of what the company supplies, posted on the card."""
    from engine.references import service as references

    from . import discord

    card = IdeaCard.objects.select_related("company", "reference").get(pk=card_id)
    try:
        entry = references.plan_our_version(card.reference, angle=card.spin)
        card.adaptation_id = entry["id"]
        card.needs = needs_from(entry["plan"])
        if entry.get("cost_usd") is not None:
            card.cost_usd += Decimal(str(entry["cost_usd"]))
        card.error = ""
        card.save(update_fields=["adaptation_id", "needs", "cost_usd", "error"])
    except Exception as exc:
        card.error = str(exc)[:500]
        card.save(update_fields=["error"])
        discord.reply(card, f"Kunde inte ta fram planen: {str(exc)[:200]}. Säg till Claude så tar vi den manuellt.")
        raise
    discord.reply(card, discord.needs_text(card, entry["plan"]))
    return card


def daily(company) -> dict:
    """Pitch up to IDEA_DAILY_LIMIT new hits, then send the best card if the week has room."""
    made, errors = [], []
    for row in hits(company)[:daily_breakdowns()]:
        try:
            made.append(make_card(company, row))
        except Exception as exc:  # noqa: BLE001 – one bad hit must not stop the rest
            errors.append(f"{source_key(row)}: {str(exc)[:200]}")
    card = next_to_send(company)
    sent = None
    if card:
        sent = send(card)
    return {"pitched": [{"why": c.why, "fit": c.fit, "spin": c.spin} for c in made],
            "sent": sent.why if sent else None, "errors": errors}
