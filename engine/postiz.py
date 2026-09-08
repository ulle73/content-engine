"""Postiz public API. No scheduling, retries or provider OAuth in this app."""

from datetime import datetime, timezone

import httpx

API_ROOT = "https://api.postiz.com/public/v1"
SUPPORTED = {"facebook", "instagram", "instagram-standalone"}


class PostizError(Exception):
    pass


def request(key, method, path, **kwargs):
    if not key:
        raise PostizError("Lägg in Postiz-nyckeln under Anslut Postiz först.")
    try:
        response = httpx.request(method, API_ROOT + path, headers={"Authorization": key}, timeout=60, **kwargs)
        if response.is_error:
            raise PostizError(
                f"Postiz svarade med HTTP {response.status_code}. Kontrollera kontot och anslutningen i Postiz."
            )
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PostizError(
            "Anropet till Postiz kunde inte bekräftas. Kontrollera Postiz innan du försöker igen."
        ) from exc


def list_channels(key):
    result = request(key, "GET", "/integrations")
    if not isinstance(result, list):
        raise PostizError("Postiz returnerade en oväntad kontolista.")
    return [
        {key: item[key] for key in ("id", "name", "identifier")}
        for item in result
        if item.get("identifier") in SUPPORTED and not item.get("disabled")
    ]


def make_payload(channels, facebook, instagram, media):
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
        "type": "draft",
        "date": datetime.now(timezone.utc).isoformat(),
        "shortLink": False,
        "tags": [],
        "posts": posts,
    }
