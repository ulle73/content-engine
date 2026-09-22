"""Postiz public API adapter used by both the web UI and the operator bridge."""

from datetime import datetime, timezone

import httpx

API_ROOT = "https://api.postiz.com/public/v1"
SUPPORTED = {"facebook", "instagram", "instagram-standalone"}
POST_TYPES = {"draft", "schedule", "now"}


class PostizError(Exception):
    def __init__(self, message, *, uncertain=False):
        super().__init__(message)
        self.uncertain = bool(uncertain)


def request(key, method, path, **kwargs):
    if not key:
        raise PostizError("Lägg in Postiz-nyckeln under Anslut Postiz först.")
    method = method.upper()
    mutating = method in {"POST", "PUT", "PATCH", "DELETE"}
    try:
        response = httpx.request(method, API_ROOT + path, headers={"Authorization": key}, timeout=60, **kwargs)
        if response.is_error:
            # A rejected 4xx is definitive. A server-side failure after a POST may have accepted the write.
            raise PostizError(
                f"Postiz svarade med HTTP {response.status_code}. Kontrollera kontot och anslutningen i Postiz.",
                uncertain=mutating and response.status_code >= 500,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise PostizError(
                "Postiz returnerade ett svar som inte kunde bekräftas.", uncertain=mutating
            ) from exc
    except PostizError:
        raise
    except httpx.HTTPError as exc:
        raise PostizError(
            "Anropet till Postiz kunde inte bekräftas. Kontrollera Postiz innan du försöker igen.",
            uncertain=mutating,
        ) from exc


def list_channels(key):
    result = request(key, "GET", "/integrations")
    if not isinstance(result, list):
        raise PostizError("Postiz returnerade en oväntad kontolista.")
    return [
        {field: item[field] for field in ("id", "name", "identifier")}
        for item in result
        if item.get("identifier") in SUPPORTED and not item.get("disabled")
    ]


def make_payload(channels, facebook, instagram, media, *, mode="draft", scheduled_for=None):
    mode = str(mode or "").lower()
    if mode not in POST_TYPES:
        raise PostizError("Postiz-läge måste vara draft, schedule eller now.")
    if mode == "schedule" and scheduled_for is None:
        raise PostizError("Schemalagd publicering kräver ett datum.")
    if mode != "schedule" and scheduled_for is not None:
        raise PostizError("Schematid får endast anges för schedule.")
    if scheduled_for is not None:
        if scheduled_for.tzinfo is None:
            raise PostizError("Schematiden måste innehålla tidszon.")
        publish_date = scheduled_for.astimezone(timezone.utc).isoformat()
    else:
        publish_date = datetime.now(timezone.utc).isoformat()

    posts = []
    for channel in channels:
        provider = channel["identifier"]
        if provider not in SUPPORTED:
            raise PostizError("Den här versionen stöder Facebook och Instagram.")
        is_instagram = provider.startswith("instagram")
        if is_instagram and not media:
            raise PostizError("Välj en bild eller MP4-video för Instagram.")
        settings = {"__type": provider}
        if is_instagram:
            settings["post_type"] = "post"
        posts.append(
            {
                "integration": {"id": channel["id"]},
                "value": [{"content": instagram if is_instagram else facebook, "image": media}],
                "settings": settings,
            }
        )
    if not posts:
        raise PostizError("Välj minst en kanal.")
    return {
        "type": mode,
        "date": publish_date,
        "shortLink": False,
        "tags": [],
        "posts": posts,
    }
