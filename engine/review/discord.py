"""Discord review cards, posted and answered through the owner's existing n8n Discord bot.

content-engine never holds the bot token. It sends the finished card to an n8n relay webhook, which uploads the video
(or links it when it is above Discord's upload limit) with the "AI Radar Discord Bot". Button clicks reach the bot's
single interactions endpoint in n8n; every custom_id starting with "ce:" is answered there immediately (deferred) and
forwarded here, so Render's cold start never breaks Discord's 3-second rule.

custom_id protocol:
    ce:ok:<review>      👍 approve          ce:no:<review>        👎 reject
    ce:rate:<review>    1–10 select menu    ce:note:<review>      opens comment modal  → ce:notetext:<review>
    ce:edit:<review>    opens change modal  → ce:edittext:<review>
"""

from __future__ import annotations

import hmac
import os

import httpx

from . import service
from .models import Review

DEFAULT_REVIEWERS = "388380559606546432,1080945367673229362"  # Jonas, colleague


def reviewers() -> set[str]:
    return {r.strip() for r in os.environ.get("DISCORD_REVIEWERS", DEFAULT_REVIEWERS).split(",") if r.strip()}


def upload_limit() -> int:
    return int(float(os.environ.get("DISCORD_UPLOAD_LIMIT_MB", "10")) * 1024 * 1024)


def secret_ok(header: str) -> bool:
    secret = os.environ.get("CONTENT_N8N_SECRET", "")
    return bool(secret) and hmac.compare_digest(secret, header or "")


def _summary(review: Review) -> str:
    manifest = review.manifest or {}
    used = [f"{i['label']}" for i in manifest.get("global", [])][:3]
    effects = [i["label"] for s in manifest.get("scenes", []) for i in s["items"]
               if i["type"] in {"effect", "transition", "text", "sound", "music"}]
    used += list(dict.fromkeys(effects))[:6]
    return ("**Byggd av:** " + ", ".join(used)) if used else ""


STATUS = {"approved": "✅ Godkänd", "rejected": "❌ Nej", "changes": "✏️ Ändras", "superseded": "🔁 Ersatt av ny version"}


def card_content(review: Review, by: str = "") -> str:
    """Public first line of the card, updated after every verdict so everyone in the channel sees the state."""
    parts = [f"🎬 **{review.company.name}** · ny video att granska (v{review.version})"]
    if review.status in STATUS:
        parts.append(STATUS[review.status] + (f" av {by}" if by and review.status != "superseded" else ""))
    if review.rating:
        parts.append(f"⭐ {review.rating}/10")
    return " · ".join(parts)


def card(review: Review) -> dict:
    link = service.video_link(review)
    attach = bool(review.asset.byte_size) and review.asset.byte_size <= upload_limit()
    description = "\n\n".join(filter(None, [
        (review.caption or "")[:1500],
        _summary(review),
        f"[▶️ Öppna videon]({link})" + ("" if attach else " (för stor för att bifogas i Discord)"),
    ]))
    rid = str(review.pk)
    buttons = [
        {"type": 2, "style": 3, "label": "Godkänn", "emoji": {"name": "👍"}, "custom_id": f"ce:ok:{rid}"},
        {"type": 2, "style": 4, "label": "Nej", "emoji": {"name": "👎"}, "custom_id": f"ce:no:{rid}"},
        {"type": 2, "style": 1, "label": "Ändra", "emoji": {"name": "✏️"}, "custom_id": f"ce:edit:{rid}"},
        {"type": 2, "style": 2, "label": "Kommentar", "emoji": {"name": "💬"}, "custom_id": f"ce:note:{rid}"},
    ]
    rating = {"type": 3, "custom_id": f"ce:rate:{rid}", "placeholder": "Betygsätt 1–10",
              "options": [{"label": f"{n}/10", "value": str(n)} for n in range(10, 0, -1)]}
    return {
        "channel_id": review.discord_channel_id or review.company.review_channel_id,
        "message": {
            "content": card_content(review),
            "embeds": [{"title": review.title[:256], "description": description[:4000], "url": link}],
            "components": [{"type": 1, "components": buttons}, {"type": 1, "components": [rating]}],
        },
        "attachment": {"url": link, "filename": f"{review.company.name}-v{review.version}.mp4".replace(" ", "-")}
        if attach else None,
    }


def send(review: Review, *, client=None) -> Review:
    url = os.environ.get("CONTENT_N8N_DISCORD_URL", "")
    payload = card(review)
    if not url or not os.environ.get("CONTENT_N8N_SECRET"):
        raise service.ReviewError("Discord-kopplingen är inte konfigurerad (CONTENT_N8N_DISCORD_URL/CONTENT_N8N_SECRET).")
    if not payload["channel_id"]:
        raise service.ReviewError(f"{review.company.name} har ingen Discord-kanal för granskning.")
    own = client is None
    client = client or httpx.Client(timeout=120)
    try:
        response = client.post(url, json=payload, headers={"X-Content-Engine-Secret": os.environ["CONTENT_N8N_SECRET"]})
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise service.ReviewError(f"Kunde inte posta i Discord: {exc}") from exc
    finally:
        if own:
            client.close()
    review.discord_channel_id = str(data.get("channel_id") or payload["channel_id"])
    review.discord_message_id = str(data.get("message_id") or data.get("id") or "")
    review.save(update_fields=["discord_channel_id", "discord_message_id"])
    return review


def handle(data: dict) -> dict:
    """Answer one forwarded interaction. Returns {"reply": text} for n8n to show (only to the clicker)."""
    parts = str(data.get("custom_id", "")).split(":")
    if len(parts) != 3 or parts[0] != "ce":
        return {"reply": "Knappen känns inte igen."}
    action, review_id = parts[1], parts[2]
    user = data.get("user") or {}
    if str(user.get("id", "")) not in reviewers():
        return {"reply": "Du kan se videon men inte godkänna eller betygsätta den. "
                         f"Be Jonas lägga till ditt Discord-ID: `{user.get('id', '?')}`"}
    review = Review.objects.select_related("company", "asset").filter(pk=review_id).first() if len(review_id) == 36 else None
    if not review:
        return {"reply": "Videon finns inte längre."}
    if review.status == "superseded" and action in {"ok", "no", "edit"}:
        return {"reply": "Det finns en nyare version av videon. Granska den i stället."}
    reviewer = {"id": str(user.get("id", "")), "name": str(user.get("name", ""))}
    try:
        if action == "ok":
            reply = service.decide(review, "approve", reviewer)
        elif action == "no":
            reply = service.decide(review, "reject", reviewer)
        elif action == "rate":
            reply = service.rate(review, int((data.get("values") or ["0"])[0]), reviewer)
        elif action in {"notetext", "edittext"}:
            reply = service.comment(review, data.get("text", ""), reviewer, change=action == "edittext")
        else:
            return {"reply": "Knappen känns inte igen."}
    except (service.ReviewError, ValueError) as exc:
        return {"reply": str(exc)}
    return {"reply": reply, "card_content": card_content(review, reviewer["name"])}
