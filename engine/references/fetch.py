"""Get the video file behind a URL: a direct video link, a Meta Ad Library ad, an Instagram/TikTok/YouTube/Facebook post.

Direct links are streamed with httpx. Everything else goes through yt-dlp (it has extractors for facebook:ads, reels,
TikTok and YouTube). Facebook rate-limits the Ad Library quickly (HTTP 429 after ~8 requests), so callers fetch one
ad at a time; a 429 is reported as such and never retried in a loop.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

MAX_BYTES = 200 * 1024 * 1024
AD_LIBRARY = re.compile(r"facebook\.com/ads/library/?\?(?:.*&)?id=(\d+)")
# One file with picture and sound.
FORMAT_SINGLE = "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]/best"
# With ffmpeg (locally): best video up to 1080p + audio merged to mp4, else the single file.
FORMAT_MERGED = "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/" + FORMAT_SINGLE
# Without ffmpeg (the server has only PyAV): a combined file when there is one, else video and audio as two files
# (the comma downloads both) that _remux puts in one mp4. Plain "best" comes last: on YouTube it is a stream-only file.
FORMAT_SEPARATE = ("best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]/"
                   "((bv*[height<=1080][vcodec^=avc1]/bv*[height<=1080]),(ba[ext=m4a]/ba))/best")
# yt-dlp only enables deno as JS runtime by default; node is what is installed locally. YouTube then gives only
# separate video and audio (DASH) formats: the clients with a combined file need PO tokens (HTTP 403 without).
JS_RUNTIMES = {"deno": {}, "node": {}}


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


def _remux(paths: list[Path], target: Path) -> Path:
    """Put the first video stream and the first audio stream from separate files in one mp4, without re-encoding."""
    import av

    inputs = [av.open(str(path)) for path in paths]
    try:
        streams = [s for s in (next((s for c in inputs for s in c.streams.video), None),
                               next((s for c in inputs for s in c.streams.audio), None)) if s is not None]
        if not streams:
            raise FetchError("Den hämtade videon gick inte att läsa.")
        with av.open(str(target), mode="w", format="mp4") as out:
            outputs = {s: out.add_stream_from_template(s) for s in streams}
            demuxers = {s: s.container.demux(s) for s in streams}
            pending = {s: next(demuxers[s], None) for s in streams}
            while any(p is not None for p in pending.values()):
                # Interleave by time: always write the packet that comes first.
                stream = min((s for s, p in pending.items() if p is not None),
                             key=lambda s: float((pending[s].dts or 0) * pending[s].time_base))
                packet = pending[stream]
                pending[stream] = next(demuxers[stream], None)
                if packet.dts is None:  # the demuxer's empty flush packet
                    continue
                packet.stream = outputs[stream]
                out.mux(packet)
    except av.FFmpegError as exc:
        raise FetchError("Bild och ljud kunde inte slås ihop: " + str(exc)[:200]) from exc
    finally:
        for container in inputs:
            container.close()
    return target


def _yt_dlp(url: str) -> Fetched:
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise FetchError("yt-dlp saknas på servern.") from exc
    can_merge = bool(shutil.which("ffmpeg"))
    with tempfile.TemporaryDirectory() as tmp:
        options = {
            "outtmpl": str(Path(tmp) / "video.%(format_id)s.%(ext)s"),
            "format": FORMAT_MERGED if can_merge else FORMAT_SEPARATE,
            "merge_output_format": "mp4", "js_runtimes": JS_RUNTIMES,
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
            if "Requested format is not available" in message:
                raise FetchError("Videon finns inte i något format som kan hämtas härifrån. Ladda ner den själv och "
                                 "ladda upp filen.") from exc
            if "login" in message.lower() or "cookies" in message.lower():
                raise FetchError("Sidan kräver inloggning för att visa videon. Ladda ner den själv och ladda upp "
                                 "filen, eller ge en annan länk.") from exc
            raise FetchError("Videon kunde inte hämtas: " + message.replace("ERROR: ", "")[:200]) from exc
        files = [p for p in Path(tmp).iterdir() if p.is_file() and not p.name.endswith(".part")]
        if not files:
            raise FetchError("Ingen video hittades på länken.")
        if sum(p.stat().st_size for p in files) > MAX_BYTES:
            raise FetchError("Videon är större än 200 MB.")
        path = _remux(files, Path(tmp) / "merged.mp4") if len(files) > 1 else files[0]
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
