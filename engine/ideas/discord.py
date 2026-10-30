"""Idea cards in Discord: short, through the same n8n publisher and button protocol as the video review cards.

    ce:ok:<idea>    👍 Skapa      ce:no:<idea>    👎 Nej
    ce:rate:<idea>  1–10          ce:note:<idea>  comment modal → ce:notetext:<idea>
"""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse

from .models import IdeaCard

STATUS = {"approved": "👍 Skapa", "rejected": "👎 Nej"}


def card_content(card: IdeaCard, by: str = "") -> str:
    parts = [f"{'🔥' if card.own else '💡'} **{card.company.name}** · ny idé"]
    if card.status in STATUS:
        parts.append(STATUS[card.status] + (f" av {by}" if by else ""))
    if card.rating:
        parts.append(f"⭐ {card.rating}/10")
    return " · ".join(parts)


def card(card: IdeaCard) -> dict:
    description = "\n".join(filter(None, [
        f"**Originalet:** {card.summary}" if card.summary else "",
        f"**Vår spinn:** {card.spin}",
        f"[▶️ Se originalet]({card.source_url})",
    ]))
    cid = str(card.pk)
    buttons = [
        {"type": 2, "style": 3, "label": "Skapa", "emoji": {"name": "👍"}, "custom_id": f"ce:ok:{cid}"},
        {"type": 2, "style": 4, "label": "Nej", "emoji": {"name": "👎"}, "custom_id": f"ce:no:{cid}"},
        {"type": 2, "style": 2, "label": "Kommentar", "emoji": {"name": "💬"}, "custom_id": f"ce:note:{cid}"},
    ]
    rating = {"type": 3, "custom_id": f"ce:rate:{cid}", "placeholder": "Betygsätt idén 1–10",
              "options": [{"label": f"{n}/10", "value": str(n)} for n in range(10, 0, -1)]}
    return {
        "channel_id": card.discord_channel_id or card.company.review_channel_id,
        "message": {
            "content": card_content(card),
            "embeds": [{"title": card.why[:256], "description": description[:4000], "url": card.source_url}],
            "components": [{"type": 1, "components": buttons}, {"type": 1, "components": [rating]}],
        },
        "attachment": None,
    }


def upload_link(card: IdeaCard) -> str:
    return settings.APP_URL.rstrip("/") + reverse("engine:media_library", kwargs={"workspace_id": card.company_id})


def needs_text(card: IdeaCard, plan: dict) -> str:
    lines = [f"🎬 **{plan.get('title') or 'Vår version'}** · {round(plan.get('duration_s') or 0)} s"]
    if card.needs:
        lines.append("**Det här behöver vi från er:**")
        lines += [f"• {n}" for n in card.needs]
        lines.append(f"Ladda upp i mediabanken: {upload_link(card)}")
    else:
        lines.append("Allt material finns redan i mediabanken – inget behövs från er.")
    return "\n".join(lines)


def reply(card: IdeaCard, text: str) -> None:
    """A message in the card's channel, as a reply to the card when Discord allows it."""
    from engine.review import discord as review_discord

    message = {"content": text[:2000]}
    if card.discord_message_id:
        message["message_reference"] = {"message_id": card.discord_message_id, "fail_if_not_exists": False}
    review_discord.post({"channel_id": card.discord_channel_id or card.company.review_channel_id,
                         "message": message, "attachment": None}, card.company)


def handle(action: str, card_id: str, user: dict, data: dict) -> dict | None:
    """Answer a click on an idea card (the reviewer is already checked). None when the id is no idea card."""
    from . import service

    card = IdeaCard.objects.select_related("company").filter(pk=card_id).first() if len(card_id) == 36 else None
    if not card:
        return None
    reviewer = {"id": str(user.get("id", "")), "name": str(user.get("name", ""))}
    try:
        if action == "ok":
            reply_text = service.approve(card, reviewer)
        elif action == "no":
            reply_text = service.reject(card, reviewer)
        elif action == "rate":
            reply_text = service.rate(card, int((data.get("values") or ["0"])[0]), reviewer)
        elif action == "notetext":
            reply_text = service.comment(card, data.get("text", ""), reviewer)
        else:
            return {"reply": "Knappen känns inte igen."}
    except ValueError as exc:
        return {"reply": str(exc)}
    return {"reply": reply_text, "card_content": card_content(card, reviewer["name"])}
