"""Free stock video (Pexels) as a stand-in for own footage that has not been filmed yet.

Only shots listed in stock_queries.json qualify: mood, environment and generic people. Product proof, the product
itself, customers, brand screens and same-framing match cuts never come from stock. A downloaded clip is stored in the
company's media bank, tagged with the shot id and the roles footage + stock, so the planner reuses it, but own footage
with the same shot id always ranks above it. The Pexels license allows commercial use without attribution; the
photographer and the source URL are kept in AssetTags.source anyway.

Needs PEXELS_API_KEY (free at pexels.com/api). EDIT_STOCK=0 turns it off.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import httpx

log = logging.getLogger(__name__)

QUERIES = Path(__file__).with_name("stock_queries.json")
SEARCH_URL = "https://api.pexels.com/videos/search"
FILE_HOSTS = ("pexels.com", "vimeo.com")
MAX_BYTES = 60 * 1024 * 1024
PROVIDER = "pexels"


class StockError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(os.environ.get("PEXELS_API_KEY", "").strip()) and \
        os.environ.get("EDIT_STOCK", "1").strip() not in {"0", "false", "off"}


@lru_cache(maxsize=1)
def queries() -> dict[str, str]:
    data = json.loads(QUERIES.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def query_for(shot_ids) -> tuple[str, str] | None:
    """(shot id, English query) for the first shot that may come from stock, else None."""
    for shot in shot_ids or []:
        if shot in queries():
            return shot, queries()[shot]
    return None


def is_stock(asset) -> bool:
    tags = getattr(asset, "ad_tags", None)
    return asset.provider == PROVIDER or bool(tags and "stock" in (tags.roles or []))


def _orientation(fmt: str) -> str:
    return "landscape" if fmt == "16:9" else "portrait"


def _file_ok(link: str) -> bool:
    url = urlparse(link or "")
    host = (url.hostname or "").lower()
    return url.scheme == "https" and any(host == h or host.endswith("." + h) for h in FILE_HOSTS)


def pick_file(video: dict, fmt: str) -> dict | None:
    """The mp4 rendition closest to 1080 on the short side, in the right orientation, never above 4K."""
    portrait = _orientation(fmt) == "portrait"
    files = []
    for f in video.get("video_files") or []:
        width, height = int(f.get("width") or 0), int(f.get("height") or 0)
        if f.get("file_type") != "video/mp4" or not width or not height or not _file_ok(f.get("link")):
            continue
        if (height >= width) != portrait or max(width, height) > 3840:
            continue
        files.append((abs(min(width, height) - 1080) + (1000 if min(width, height) < 720 else 0), f))
    return min(files, key=lambda x: x[0])[1] if files else None


def _client() -> httpx.Client:
    return httpx.Client(timeout=60, follow_redirects=True)


def search(query: str, *, fmt: str, min_duration: float, client: httpx.Client) -> list[dict]:
    response = client.get(SEARCH_URL, params={"query": query, "orientation": _orientation(fmt), "size": "medium",
                                              "per_page": 15},
                          headers={"Authorization": os.environ["PEXELS_API_KEY"].strip()})
    if response.status_code != 200:
        raise StockError(f"Pexels svarade {response.status_code}.")
    videos = response.json().get("videos") or []
    return [v for v in videos if float(v.get("duration") or 0) >= min_duration and pick_file(v, fmt)]


def fetch(company, shot: str, query: str, *, fmt: str, min_duration: float, skip=(), client=None):
    """Download the best matching clip into the media bank and tag it; None when nothing usable was found."""
    from engine.ad_studio.models import AssetTags
    from engine.media import describe_file
    from engine.media_storage import MediaError, put
    from engine.models import MediaAsset

    own = client is None
    client = client or _client()
    try:
        for video in search(query, fmt=fmt, min_duration=min_duration, client=client):
            asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{company.pk}:pexels:{video['id']}:{fmt}")
            if str(asset_id) in skip:
                continue
            existing = MediaAsset.objects.filter(pk=asset_id, company=company).first()
            if existing:
                return existing
            chosen = pick_file(video, fmt)
            try:
                response = client.get(chosen["link"])
            except httpx.HTTPError as exc:
                log.warning("Pexels download %s failed: %s", video.get("id"), exc)
                continue
            data = response.content
            if response.status_code != 200 or not data or len(data) > MAX_BYTES:
                continue
            try:
                metadata = describe_file(data)
            except MediaError:
                continue
            if metadata["kind"] != "video":
                continue
            key = f"{company.pk}/{asset_id}.{metadata.pop('extension')}"
            backend = put(key, data, metadata["mime_type"])
            author = (video.get("user") or {}).get("name") or "okänd"
            asset = MediaAsset.objects.create(
                pk=asset_id, company=company, storage_backend=backend, storage_key=key, byte_size=len(data),
                origin="uploaded", provider=PROVIDER, alt_text=f"Stockklipp: {query}"[:500], purpose="content",
                brief=f"Pexels {video.get('url', '')} – tillfälligt för {shot} tills egen film finns"[:2000],
                sha256=hashlib.sha256(data).hexdigest(), **metadata)
            AssetTags.objects.update_or_create(asset=asset, defaults={
                "description": f"Stockklipp ({query})"[:500], "tags": [shot], "roles": ["footage", "stock"],
                "source": f"Pexels: {author}, {video.get('url', '')}"[:200], "verified": False})
            return asset
    except (httpx.HTTPError, ValueError, StockError) as exc:
        log.warning("Pexels search %r failed: %s", query, exc)
    finally:
        if own:
            client.close()
    return None
