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
from pydantic import BaseModel, Field

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


def judging() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip()) and os.environ.get("EDIT_STOCK_JUDGE", "1") != "0"


def min_judge() -> int:
    try:
        return int(os.environ.get("EDIT_STOCK_MIN_JUDGE", "6"))
    except ValueError:
        return 6


def acceptable(asset) -> bool:
    """A stored stock clip may be reused when the judge passed it, or when no judge is available to ask."""
    if not judging():
        return True
    tags = getattr(asset, "ad_tags", None)
    judged = [h.get("judge") for h in (tags.highlights if tags else []) or [] if isinstance(h, dict)]
    return any(isinstance(j, int) and j >= min_judge() for j in judged)


def _orientation(fmt: str) -> str:
    return "landscape" if fmt == "16:9" else "portrait"


def _file_ok(link: str) -> bool:
    url = urlparse(link or "")
    host = (url.hostname or "").lower()
    return url.scheme == "https" and any(host == h or host.endswith("." + h) for h in FILE_HOSTS)


def pick_file(video: dict, fmt: str, *, small: bool = False) -> dict | None:
    """The mp4 rendition closest to 1080 on the short side (small=True: the smallest one of at least 360, for
    scoring), in the right orientation, never above 4K."""
    portrait = _orientation(fmt) == "portrait"
    target, floor = (360, 360) if small else (1080, 720)
    files = []
    for f in video.get("video_files") or []:
        width, height = int(f.get("width") or 0), int(f.get("height") or 0)
        if f.get("file_type") != "video/mp4" or not width or not height or not _file_ok(f.get("link")):
            continue
        if (height >= width) != portrait or max(width, height) > 3840:
            continue
        short = min(width, height)
        files.append((abs(short - target) + (1000 if short < floor else 0), f))
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


def candidate_count() -> int:
    try:
        return max(1, min(5, int(os.environ.get("EDIT_STOCK_CANDIDATES", "3"))))
    except ValueError:
        return 3


def _download(client, link: str) -> bytes | None:
    try:
        response = client.get(link)
    except httpx.HTTPError as exc:
        log.warning("Pexels download failed: %s", exc)
        return None
    data = response.content
    return data if response.status_code == 200 and data and len(data) <= MAX_BYTES else None


class Pick(BaseModel):
    scores: list[int] = Field(description="Betyg 1–10 per bild i samma ordning: passar scenen och ser ut som riktig, "
                                          "snygg film (inte stockig, inte AI, inte kitschig)")
    why: str = Field(description="En kort mening på svenska om den bästa bilden")


JUDGE = ("Du väljer b-roll till en svensk social annons (Reels/TikTok). Du får filmens idé och stämning, en "
         "beskrivning av scenen och en bild ur varje kandidatklipp, i ordning. Betygsätt varje bild för sig: visar den "
         "exakt det scenen beskriver, i filmens årstid, ljus och miljö (svensk/nordisk), och ser den ut som äkta, "
         "snygg film (naturligt ljus, tydligt motiv, ingen stockfoto-pose, inga vattenstämplar, ingen text i bilden, "
         "ingen uppenbar AI)? Fel motiv (t.ex. en annan skylt än den som efterfrågas), fel årstid eller tid på dygnet, "
         "eller uppenbart utländsk miljö ger högst 3. Var sträng; 7 betyder fullt användbart.")


def judge(scene: str, frames: list[bytes], *, context: str = "") -> dict | None:
    """One cheap vision call scoring each candidate frame against the scene and the film's mood. None when it cannot
    be asked."""
    import base64

    if not judging():
        return None
    from engine.openrouter import OpenRouterError, structured_analysis

    images = ["data:image/jpeg;base64," + base64.b64encode(f).decode("ascii") for f in frames]
    try:
        result, meta = structured_analysis(system=JUDGE, schema=Pick, operation="stock_pick", max_tokens=300,
                                           payload={"film": context, "scene": scene, "candidates": len(frames)},
                                           images=images)
    except OpenRouterError as exc:
        log.info("Stock judge failed: %s", exc)
        return None
    if len(result.scores) < len(frames):
        return None
    return {"scores": [max(1, min(10, int(v))) for v in result.scores[:len(frames)]], "why": result.why[:200],
            "cost_usd": meta.get("cost_usd")}


def fetch(company, shot: str, query: str, *, fmt: str, min_duration: float, skip=(), client=None, scene: str = "",
          context: str = ""):
    """Like the best editors: look at several candidates, keep the best one and only its best window.

    Up to EDIT_STOCK_CANDIDATES (3) unused search hits are downloaded small and scored (engine/edit/shots.py:
    sharpness, exposure, motion, no cut inside the window); a vision model scores one frame from each best window
    against the scene and the film's idea and mood (`context`). Candidates the judge scores under
    EDIT_STOCK_MIN_JUDGE (6) are dropped: a missing scene is better than a wrong one (a summer bus-stop sign in a
    Swedish winter-night film). The final score is 40 % technique, 60 % judge. Only the winner is downloaded in full
    quality into the media bank, with its best window and judge score in AssetTags.highlights. None when nothing
    usable was found.
    """
    from engine.ad_studio.models import AssetTags
    from engine.media import describe_file
    from engine.media_storage import MediaError, put
    from engine.models import MediaAsset

    from . import shots

    own = client is None
    client = client or _client()
    dark_ok = any(word in query for word in ("night", "dark", "northern lights", "evening"))
    try:
        candidates = []
        for video in search(query, fmt=fmt, min_duration=min_duration, client=client):
            asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{company.pk}:pexels:{video['id']}:{fmt}")
            if str(asset_id) in skip:
                continue
            existing = MediaAsset.objects.filter(pk=asset_id, company=company).select_related("ad_tags").first()
            if existing:
                if acceptable(existing):
                    return existing
                continue  # downloaded before but not passed by the judge
            small = pick_file(video, fmt, small=True)
            data = _download(client, small["link"]) if small else None
            window = shots.best_window(shots.analyze(data), min_duration, dark_ok=dark_ok) if data else None
            if window is None:
                continue
            frame = shots.frame_jpeg(data, (window["start"] + window["end"]) / 2)
            candidates.append({"video": video, "asset_id": asset_id, "window": window, "frame": frame,
                               "score": window["score"]})
            if len(candidates) >= candidate_count():
                break
        if not candidates:
            return None
        frames, looked = [c["frame"] for c in candidates], len(candidates)
        verdict = judge(scene or query, frames, context=context) if all(frames) else None
        if verdict:
            for c, judged in zip(candidates, verdict["scores"]):
                c["judge"] = judged
                c["score"] = round(0.4 * c["window"]["score"] + 0.6 * judged, 2)
            candidates = [c for c in candidates if c["judge"] >= min_judge()]
            if not candidates:
                log.info("Pexels %r: no candidate passed the judge (%s).", query, verdict["scores"])
                return None
        for c in sorted(candidates, key=lambda c: -c["score"]):
            video, asset_id = c["video"], c["asset_id"]
            data = _download(client, pick_file(video, fmt)["link"])
            if not data:
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
                brief=(f"Pexels {video.get('url', '')} – tillfälligt för {shot} tills egen film finns. Valt bland "
                       f"{looked} kandidater, betyg {c['score']}/10"
                       + (f": {verdict['why']}" if verdict else ".")),
                sha256=hashlib.sha256(data).hexdigest(), **metadata)
            AssetTags.objects.update_or_create(asset=asset, defaults={
                "description": f"Stockklipp ({query})"[:500], "tags": [shot], "roles": ["footage", "stock"],
                "source": f"Pexels: {author}, {video.get('url', '')}"[:200], "verified": False,
                "highlights": [{**{k: c["window"][k] for k in ("start", "end", "score")},
                                **({"judge": c["judge"]} if "judge" in c else {})}]})
            return asset
    except (httpx.HTTPError, ValueError, StockError) as exc:
        log.warning("Pexels search %r failed: %s", query, exc)
    finally:
        if own:
            client.close()
    return None
