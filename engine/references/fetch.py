"""Get the video file behind a URL: a direct video link, a Meta Ad Library ad, an Instagram/TikTok/YouTube/Facebook post.

Direct links are streamed with httpx. Everything else goes through yt-dlp (it has extractors for facebook:ads, reels,
TikTok and YouTube). Facebook rate-limits the Ad Library quickly (HTTP 429 after ~8 requests), so callers fetch one
ad at a time; a 429 is reported as such and never retried in a loop.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

MAX_BYTES = 200 * 1024 * 1024
AD_LIBRARY = re.compile(r"facebook\.com/ads/library/?\?(?:.*&)?id=(\d+)")


class FetchError(ValueError):
    pass


@dataclass
class Fetched:
    data: bytes
    mime: str
    source_url: str
    author: str = ""
    title: str = ""


def ad_library_url(ad_id: str) -> str:
    return f"https://www.facebook.com/ads/library/?id={ad_id}"


def ad_library_id(url: str) -> str:
    match = AD_LIBRARY.search(url or "")
    if match:
        return match.group(1)
    parsed = urlparse(url or "")
    if parsed.hostname and parsed.hostname.endswith("facebook.com") and parsed.path.startswith("/ads/library"):
        return (parse_qs(parsed.query).get("id") or [""])[0]
    return ""


def check_url(url: str) -> str:
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise FetchError("Ange en hel länk som börjar med https://.")
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".local") or re.fullmatch(r"[\d.]+|\[?[0-9a-f:]+\]?", host):
        raise FetchError("Länken måste gå till en publik webbplats.")
    return url


def _direct(url: str) -> Fetched | None:
    """Stream the URL when it answers with a video file; None when it is a web page."""
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(60, connect=10),
                          headers={"User-Agent": "Mozilla/5.0 ContentEngine/1.0"}) as response:
            mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if response.status_code >= 400 or not mime.startswith("video/"):
                return None
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FetchError("Videon är större än 200 MB.")
                chunks.append(chunk)
            return Fetched(b"".join(chunks), mime, url)
    except httpx.HTTPError:
        return None


def _yt_dlp(url: str) -> Fetched:
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise FetchError("yt-dlp saknas på servern.") from exc
    with tempfile.TemporaryDirectory() as tmp:
        options = {
            "outtmpl": str(Path(tmp) / "video.%(ext)s"),
            # One file with picture and sound; no merging (the server has no ffmpeg binary, only PyAV).
            "format": "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]/best",
            "noplaylist": True, "playlist_items": "1", "max_filesize": MAX_BYTES,
            "quiet": True, "no_warnings": True, "noprogress": True, "retries": 1, "socket_timeout": 30,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            message = str(exc)
            if "429" in message:
                raise FetchError("Facebook begränsar antalet hämtningar just nu (HTTP 429). Försök igen om en stund.") \
                    from exc
            if "No video formats" in message:
                raise FetchError("Ingen video hittades på länken (det kan vara en bild- eller textannons).") from exc
            if "login" in message.lower() or "cookies" in message.lower():
                raise FetchError("Sidan kräver inloggning för att visa videon. Ladda ner den själv och ladda upp "
                                 "filen, eller ge en annan länk.") from exc
            raise FetchError("Videon kunde inte hämtas: " + message.replace("ERROR: ", "")[:200]) from exc
        files = [p for p in Path(tmp).iterdir() if p.is_file() and not p.name.endswith(".part")]
        if not files:
            raise FetchError("Ingen video hittades på länken.")
        path = max(files, key=lambda p: p.stat().st_size)
        if path.stat().st_size > MAX_BYTES:
            raise FetchError("Videon är större än 200 MB.")
        info = info or {}
        if info.get("entries"):
            info = info["entries"][0] or {}
        ext = path.suffix.lstrip(".").lower() or "mp4"
        return Fetched(path.read_bytes(), "video/" + ("mp4" if ext in {"mp4", "m4v"} else ext), url,
                       author=str(info.get("uploader") or info.get("channel") or "")[:200],
                       title=str(info.get("title") or info.get("description") or "")[:300])


def fetch(url: str) -> Fetched:
    url = check_url(url)
    return _direct(url) or _yt_dlp(url)
