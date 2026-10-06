#!/usr/bin/env python3
"""Enrich Golfkuponger golf-club JSON with verified image URLs.

Design goals:
- deterministic and resumable;
- official website as the discovery source;
- actual image bytes are inspected before an image is accepted;
- existing `images` arrays are never changed;
- no external database, workflow engine, paid API, browser farm, or AI service.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import html
import json
import os
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, asdict
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from PIL import ImageFile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (compatible; GolfkupongerImageEnricher/1.0; "
    "+https://www.svenskagolfkuponger.se/)"
)

PAGE_KEYWORDS = {
    "bana": 8,
    "banan": 10,
    "golfbana": 12,
    "golfbanan": 12,
    "course": 10,
    "hole": 8,
    "hal": 7,
    "hål": 9,
    "galleri": 8,
    "gallery": 8,
    "spela": 6,
    "golf": 4,
    "anlaggning": 5,
    "anläggning": 5,
}

IMAGE_POSITIVE = {
    "golf": 8,
    "course": 8,
    "bana": 8,
    "banan": 8,
    "golfbana": 10,
    "golfbanan": 10,
    "fairway": 12,
    "green": 10,
    "hole": 10,
    "hal": 7,
    "hål": 9,
    "tee": 6,
    "klubbhus": 4,
    "clubhouse": 4,
    "drone": 5,
    "aerial": 5,
}

IMAGE_NEGATIVE = {
    "logo": -40,
    "logga": -40,
    "sponsor": -35,
    "partner": -20,
    "icon": -40,
    "ikon": -40,
    "avatar": -35,
    "portrait": -25,
    "profil": -18,
    "staff": -24,
    "personal": -24,
    "team": -18,
    "menu": -20,
    "meny": -20,
    "food": -20,
    "mat": -16,
    "drink": -20,
    "map": -24,
    "karta": -24,
    "scorecard": -24,
    "scorekort": -24,
    "shop": -10,
    "produkt": -12,
    "product": -12,
    "facebook": -30,
    "instagram": -30,
    "favicon": -50,
}

URL_OVERRIDES = {
    "Billingens GK": "https://billingensgk.se/",
    "Bjurholms GK": "https://www.bjurholmsgk.se/",
    "Bodens GK, Sävast": "https://bodensgk.se/",
    "Borås GK": "https://www.borasgolfklubb.se/",
    "Drottningholms GK": "https://kdrgk.se/",
    "Dalsjö GK": "https://www.dalsjogolf.se/",
    "Eksjö GK": "https://eksjogk.se/",
    "Falkenbergs GK": "https://www.falkenbergsgk.se/",
    "Falsterbo GK": "https://www.falsterbogk.se/",
    "Finspångs GK": "https://finspangsgk.se/",
    "Fjällbacka GK": "https://fjallbackagk.se/",
    "Flommens GK": "https://flommensgk.se/",
    "Flädje GK": "https://fladjegolf.se/",
    "Friibergh GK": "https://friiberghsgk.se/",
    "Glasrikets GK": "https://www.glasriketsgk.se/",
    "Göran Knutsson Golf Academy": "https://gkgolf.se/",
    "Hagge GK": "https://haggegk.se/",
    "Kiruna GK": "https://kiruna.golf/",
    "Lysingsbadets Golfbana": "https://vastervikresort.se/upplev/sportiga-aktiviteter/golf/",
    "Malmö Burlöv Golfklubb": "https://www.malmoburlovgk.com/",
    "Malungs GK": "https://malungsgk.se/",
    "Michael Wigh Golf AB": "https://www.golfstore.se/butik/bosjokloster/",
    "Naturligtvis GCC": "https://www.naturligtvisgcc.se/",
    "Nya Johannesberg G & CC": "https://www.johannesbergsgolf.se/",
    "När GK": "https://www.nargk.se/",
    "Orust GK": "https://www.orustgk.se/",
    "Oskarshamns GK": "https://oskarshamnsgk.se/",
    "Saltsjöbadens Golfshop/Pro Swede Golf AB": "https://saltsjobadensgolfshop.se/",
    "Sundsta Golf": "https://www.sundsta.se/golf-norrtalje/",
    "Sundsvalls GK": "https://sundsvallsgk.se/",
    "Timrå GK": "https://www.timragk.se/",
    "Tyresö GK": "https://tyresogolf.se/",
    "Åda GK": "https://adagolf.se/",
}

INSECURE_PUBLIC_HOSTS = {"haggegk.se"}

MANUAL_CANDIDATES = {
    # Official-site images used only where the site blocks automated page fetches.
    # Pixel dimensions are still verified from the real image bytes before acceptance.
    "Sundsvalls GK": [
        "https://sundsvallsgk.se/wp-content/uploads/2021/08/DJI_0258.jpg",
    ],
    "Timrå GK": [
        "https://www.timragk.se/wp-content/uploads/2026/06/Header_-Timra-GK_summer-stor.png",
    ],
}

IMG_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp)(?:$|[?#])", re.I)
CSS_URL_RE = re.compile(r"url\((['\"]?)(.*?)\1\)", re.I)
WP_SIZE_RE = re.compile(r"-(\d{2,5})x(\d{2,5})(?=\.(?:jpe?g|png|webp)$)", re.I)
SPACE_RE = re.compile(r"\s+")

_tls = threading.local()


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        respect_retry_after_header=True,
    )
    session.mount("http://", HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8))
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8))
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.7",
        }
    )
    return session


def get_session() -> requests.Session:
    if not hasattr(_tls, "session"):
        _tls.session = build_session()
    return _tls.session


def normalize_start_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        return "https://" + url.lstrip("/")
    return url


def normalize_url(url: str) -> str:
    """Normalize enough for de-duplication without breaking signed/CDN URLs."""
    try:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return url
        # Remove tracking-only query params; preserve transform/signature params.
        params = [
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
        ]
        return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, "", urlencode(params), ""))
    except Exception:
        return url


def host_key(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h


def verify_tls(url: str) -> bool:
    return host_key(url) not in INSECURE_PUBLIC_HOSTS


def same_site(url: str, official_host: str) -> bool:
    h = host_key(url)
    if not h or not official_host:
        return False
    return h == official_host or h.endswith("." + official_host) or official_host.endswith("." + h)


def clean_text(value: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(value or "")).strip().lower()


def keyword_score(text: str, weights: dict[str, int]) -> int:
    text = clean_text(text)
    return sum(weight for word, weight in weights.items() if word in text)


def url_score_for_page(url: str, label: str = "") -> int:
    text = f"{url} {label}"
    return keyword_score(text, PAGE_KEYWORDS)


def make_absolute(raw: str, base: str) -> str:
    raw = html.unescape((raw or "").strip())
    if not raw or raw.startswith(("data:", "blob:", "javascript:", "mailto:", "tel:")):
        return ""
    return urljoin(base, raw)


def choose_srcset(srcset: str, base: str) -> list[str]:
    out: list[tuple[int, str]] = []
    for part in (srcset or "").split(","):
        bit = part.strip()
        if not bit:
            continue
        tokens = bit.split()
        u = make_absolute(tokens[0], base)
        if not u:
            continue
        rank = 0
        if len(tokens) > 1:
            m = re.match(r"(\d+)(w|x)$", tokens[-1], re.I)
            if m:
                rank = int(m.group(1)) * (10000 if m.group(2).lower() == "x" else 1)
        out.append((rank, u))
    return [u for _, u in sorted(out, key=lambda x: x[0], reverse=True)]


@dataclass
class Candidate:
    url: str
    source_page: str
    context: str
    source_type: str
    pre_score: int = 0


@dataclass
class VerifiedImage:
    url: str
    width: int
    height: int
    score: int
    source_page: str
    context: str
    source_type: str


@dataclass
class ClubResult:
    index: int
    name: str
    status: str
    official_url: str
    final_home_url: str = ""
    pages_checked: int = 0
    candidates_found: int = 0
    candidates_probed: int = 0
    images: list[dict] | None = None
    error: str = ""


def extract_candidates(page_url: str, body: str) -> tuple[list[Candidate], list[tuple[str, str]]]:
    soup = BeautifulSoup(body, "html.parser")
    candidates: list[Candidate] = []
    links: list[tuple[str, str]] = []

    def add(raw: str, context: str, source_type: str) -> None:
        u = make_absolute(raw, page_url)
        if not u:
            return
        candidates.append(Candidate(u, page_url, clean_text(context), source_type))

    for img in soup.find_all("img"):
        context = " ".join(
            str(img.get(k) or "") for k in ("alt", "title", "class", "id")
        )
        for key in ("src", "data-src", "data-lazy-src", "data-original", "data-url"):
            if img.get(key):
                add(str(img.get(key)), context, key)
        for key in ("srcset", "data-srcset"):
            if img.get(key):
                for u in choose_srcset(str(img.get(key)), page_url)[:3]:
                    add(u, context, key)

    for source in soup.find_all("source"):
        context = " ".join(str(source.get(k) or "") for k in ("media", "type", "class"))
        for key in ("srcset", "data-srcset"):
            if source.get(key):
                for u in choose_srcset(str(source.get(key)), page_url)[:3]:
                    add(u, context, "source-srcset")

    for meta in soup.find_all("meta"):
        prop = str(meta.get("property") or meta.get("name") or "").lower()
        if prop in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
            add(str(meta.get("content") or ""), prop, prop)

    for link in soup.find_all("link"):
        rel = " ".join(link.get("rel") or []).lower()
        as_attr = str(link.get("as") or "").lower()
        if "image_src" in rel or ("preload" in rel and as_attr == "image"):
            add(str(link.get("href") or ""), rel, "link-image")

    for tag in soup.find_all(style=True):
        for _, raw in CSS_URL_RE.findall(str(tag.get("style") or "")):
            add(raw, str(tag.get("class") or ""), "inline-style")

    # A small amount of CSS-in-HTML background discovery.
    for style_tag in soup.find_all("style"):
        text = style_tag.get_text(" ", strip=False)
        for _, raw in CSS_URL_RE.findall(text):
            add(raw, "stylesheet background", "style-tag")

    # Catch CMS/lazy-loader attributes that do not use standard img/src names.
    # This is especially useful for Wix/Elementor/custom themes using data-bg,
    # data-background-image, data-bgset, or JSON-ish image attributes.
    for tag in soup.find_all(True):
        context = " ".join(str(tag.get(k) or "") for k in ("alt", "title", "class", "id"))
        for key, value in tag.attrs.items():
            if key in {"src", "data-src", "data-lazy-src", "data-original", "data-url", "srcset", "data-srcset", "href", "style"}:
                continue
            values = value if isinstance(value, list) else [value]
            for raw_value in values:
                text_value = str(raw_value or "")
                if not text_value:
                    continue
                if "srcset" in key.lower() or "bgset" in key.lower():
                    for u in choose_srcset(text_value, page_url)[:4]:
                        add(u, context, f"attr:{key}")
                    continue
                for _, raw in CSS_URL_RE.findall(text_value):
                    add(raw, context, f"attr:{key}")
                # Absolute/relative image-looking attribute values.
                if (IMG_EXT_RE.search(text_value) or "wp-content/uploads/" in text_value.lower()
                        or "static.wixstatic.com/media/" in text_value.lower()):
                    add(text_value, context, f"attr:{key}")

    for a in soup.find_all("a", href=True):
        href = make_absolute(str(a.get("href") or ""), page_url)
        if href:
            label = a.get_text(" ", strip=True)
            links.append((href, label))

    return candidates, links


def original_variant(url: str) -> Optional[str]:
    try:
        p = urlparse(url)
        # WordPress resized derivative -> original upload.
        new_path = WP_SIZE_RE.sub("", p.path)
        if new_path != p.path:
            return urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment))
        # Wix transformed delivery URL -> original media asset. This also avoids
        # automatic AVIF transforms that Pillow/servers may negotiate differently.
        if p.netloc.lower().endswith("wixstatic.com") and "/media/" in p.path and "/v1/" in p.path:
            original_path = p.path.split("/v1/", 1)[0]
            return urlunparse((p.scheme, p.netloc, original_path, "", "", ""))
    except Exception:
        pass
    return None


def fetch_text(url: str, timeout: tuple[float, float] = (6, 18)) -> tuple[str, str]:
    session = get_session()
    headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"}
    r = session.get(url, timeout=timeout, headers=headers, allow_redirects=True, verify=verify_tls(url))
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    if "text/" not in ctype and "html" not in ctype and "xml" not in ctype and ctype:
        raise ValueError(f"not HTML/XML: {ctype}")
    if len(r.content) > 6_000_000:
        raise ValueError("page larger than 6 MB")
    r.encoding = r.encoding or r.apparent_encoding or "utf-8"
    return r.url, r.text


def discover_sitemap_pages(home_url: str, official_host: str, max_urls: int = 8) -> list[str]:
    root = urlunparse((urlparse(home_url).scheme, urlparse(home_url).netloc, "/sitemap.xml", "", "", ""))
    try:
        final, body = fetch_text(root, timeout=(5, 12))
    except Exception:
        return []

    soup = BeautifulSoup(body, "html.parser")
    locs = [x.get_text(strip=True) for x in soup.find_all("loc")]
    # If sitemap is an index, inspect only a few likely child sitemaps.
    if locs and all(("sitemap" in x.lower() or x.lower().endswith(".xml")) for x in locs[: min(5, len(locs))]):
        child_urls = sorted(locs, key=lambda u: url_score_for_page(u), reverse=True)[:4]
        expanded: list[str] = []
        for child in child_urls:
            try:
                _, child_body = fetch_text(child, timeout=(5, 12))
                child_soup = BeautifulSoup(child_body, "html.parser")
                expanded.extend(x.get_text(strip=True) for x in child_soup.find_all("loc"))
            except Exception:
                continue
        if expanded:
            locs = expanded

    scored = []
    for u in locs:
        if same_site(u, official_host):
            score = url_score_for_page(u)
            if score > 0:
                scored.append((score, u))
    seen = set()
    out = []
    for _, u in sorted(scored, key=lambda x: x[0], reverse=True):
        n = normalize_url(u)
        if n in seen:
            continue
        seen.add(n)
        out.append(u)
        if len(out) >= max_urls:
            break
    return out


def discover_wordpress_media(home_url: str, max_items: int = 100) -> list[Candidate]:
    """Use a site's public WordPress media endpoint as a cheap fallback."""
    p = urlparse(home_url)
    if not p.scheme or not p.netloc:
        return []
    api = urlunparse((p.scheme, p.netloc, "/wp-json/wp/v2/media", "", "", ""))
    try:
        r = get_session().get(
            api,
            params={
                "per_page": min(max_items, 100),
                "media_type": "image",
                "orderby": "date",
                "order": "desc",
                "_fields": "source_url,media_details,alt_text,caption,title",
            },
            timeout=(6, 18),
            headers={"Accept": "application/json"},
            allow_redirects=True,
            verify=verify_tls(api),
        )
        r.raise_for_status()
        items = r.json()
        if not isinstance(items, list):
            return []
    except Exception:
        return []

    out: list[Candidate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        context_parts = [str(item.get("alt_text") or "")]
        for key in ("caption", "title"):
            value = item.get(key)
            if isinstance(value, dict):
                context_parts.append(str(value.get("rendered") or ""))
        context = clean_text(" ".join(context_parts))
        urls = []
        source = str(item.get("source_url") or "").strip()
        if source:
            urls.append(source)
        media = item.get("media_details")
        if isinstance(media, dict):
            sizes = media.get("sizes")
            if isinstance(sizes, dict):
                full = sizes.get("full")
                if isinstance(full, dict) and full.get("source_url"):
                    urls.append(str(full.get("source_url")))
        for u in urls:
            out.append(Candidate(u, home_url, context, "wordpress-rest"))
    return out


def probe_image(url: str, referer: str = "", max_header_bytes: int = 2_000_000) -> tuple[Optional[tuple[int, int]], str, str]:
    """Read real image bytes until Pillow knows the pixel dimensions, then stop."""
    session = get_session()
    headers = {
        "Accept": "image/webp,image/jpeg,image/png,image/*;q=0.8,*/*;q=0.3",
        "Referer": referer or url,
    }
    try:
        with session.get(url, stream=True, timeout=(6, 20), headers=headers, allow_redirects=True, verify=verify_tls(url)) as r:
            r.raise_for_status()
            ctype = (r.headers.get("content-type") or "").lower()
            if ctype and "image" not in ctype and not IMG_EXT_RE.search(r.url):
                return None, r.url, f"content-type={ctype}"
            parser = ImageFile.Parser()
            read = 0
            for chunk in r.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                read += len(chunk)
                parser.feed(chunk)
                if parser.image is not None:
                    w, h = parser.image.size
                    if w > 0 and h > 0:
                        return (int(w), int(h)), r.url, ""
                if read >= max_header_bytes:
                    break
            return None, r.url, "dimensions not found within header budget"
    except Exception as exc:
        return None, url, str(exc)[:240]


def candidate_score(c: Candidate, width: int, height: int) -> int:
    text = f"{c.url} {c.context} {c.source_page}"
    score = keyword_score(text, IMAGE_POSITIVE) + keyword_score(text, IMAGE_NEGATIVE)
    score += url_score_for_page(c.source_page)
    score += min(width, 4000) // 160
    score += min(height, 2500) // 220
    ratio = width / max(height, 1)
    if 1.3 <= ratio <= 2.2:
        score += 14
    elif 1.15 <= ratio <= 2.8:
        score += 6
    elif ratio > 3.2:
        score -= 14
    if c.source_type in {"srcset", "data-srcset", "source-srcset"}:
        score += 4
    if c.source_type.startswith("og:"):
        score += 2
    return int(score)


def candidate_group_key(url: str) -> str:
    p = urlparse(url)
    path = WP_SIZE_RE.sub("", p.path.lower())
    # Remove common CDN size/query variants from dedupe key, but not from the actual URL.
    query = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in {"w", "width", "h", "height", "q", "quality", "fit", "crop"}]
    return urlunparse(("", p.netloc.lower(), path, "", urlencode(query), ""))


def process_club(index: int, club: dict, max_pages: int, max_probes: int, max_images: int) -> ClubResult:
    name = str(club.get("name") or "")
    official = normalize_start_url(URL_OVERRIDES.get(name, str(club.get("url") or club.get("website_source") or "")))
    result = ClubResult(index=index, name=name, status="error", official_url=official, images=[])
    if not official:
        result.status = "no_url"
        result.error = "club has no official URL in JSON"
        return result

    wp_candidates = discover_wordpress_media(official, max_items=100)
    try:
        final_home, home_body = fetch_text(official)
    except Exception as exc:
        # One safe protocol fallback for old http URLs.
        alt = ""
        if official.startswith("http://"):
            alt = "https://" + official[len("http://") :]
        elif official.startswith("https://"):
            alt = "http://" + official[len("https://") :]
        if alt:
            try:
                final_home, home_body = fetch_text(alt)
            except Exception:
                if wp_candidates:
                    final_home, home_body = official, ""
                else:
                    result.status = "fetch_failed"
                    result.error = str(exc)[:300]
                    return result
        elif wp_candidates:
            final_home, home_body = official, ""
        else:
            result.status = "fetch_failed"
            result.error = str(exc)[:300]
            return result

    result.final_home_url = final_home
    official_host = host_key(final_home)

    all_candidates: list[Candidate] = list(wp_candidates)
    for manual_url in MANUAL_CANDIDATES.get(name, []):
        all_candidates.append(Candidate(manual_url, official, "official-site manual fallback", "manual-official"))
    page_queue: list[tuple[int, str]] = [(999, final_home)]
    seen_pages: set[str] = set()
    queued: set[str] = {normalize_url(final_home)}

    def enqueue(url: str, label: str = "") -> None:
        if not same_site(url, official_host):
            return
        n = normalize_url(url)
        if n in queued or n in seen_pages:
            return
        s = url_score_for_page(url, label)
        if s <= 0:
            return
        queued.add(n)
        page_queue.append((s, url))

    # Parse home immediately and use it to discover useful internal pages.
    if home_body:
        cands, links = extract_candidates(final_home, home_body)
        all_candidates.extend(cands)
        seen_pages.add(normalize_url(final_home))
        result.pages_checked = 1
        for href, label in links:
            enqueue(href, label)
    else:
        seen_pages.add(normalize_url(final_home))
        result.pages_checked = 0

    # Sitemap can rescue sparse homepages without adding a browser dependency.
    if len(page_queue) <= 2:
        for u in discover_sitemap_pages(final_home, official_host, max_urls=max_pages * 2):
            enqueue(u)

    while page_queue and result.pages_checked < max_pages:
        page_queue.sort(key=lambda x: x[0], reverse=True)
        _, page = page_queue.pop(0)
        n = normalize_url(page)
        if n in seen_pages:
            continue
        seen_pages.add(n)
        try:
            final_page, body = fetch_text(page)
        except Exception:
            continue
        result.pages_checked += 1
        cands, links = extract_candidates(final_page, body)
        all_candidates.extend(cands)
        for href, label in links:
            enqueue(href, label)

    # Add full-size WordPress variants when a page references a resized file.
    expanded: list[Candidate] = []
    for c in all_candidates:
        expanded.append(c)
        orig = original_variant(c.url)
        if orig:
            expanded.append(Candidate(orig, c.source_page, c.context, c.source_type + ":wp-original", c.pre_score + 3))

    dedup: dict[str, Candidate] = {}
    for c in expanded:
        u = normalize_url(c.url)
        if not u.startswith(("http://", "https://")):
            continue
        if not IMG_EXT_RE.search(u) and not any(x in u.lower() for x in ("image", "img", "media", "cdn", "upload")):
            continue
        # Cheap pre-score so obviously useful candidates are probed first.
        c.pre_score = (
            keyword_score(f"{c.url} {c.context}", IMAGE_POSITIVE)
            + keyword_score(f"{c.url} {c.context}", IMAGE_NEGATIVE)
            + url_score_for_page(c.source_page)
        )
        old = dedup.get(u)
        if old is None or c.pre_score > old.pre_score:
            dedup[u] = c

    candidates = sorted(dedup.values(), key=lambda c: c.pre_score, reverse=True)
    result.candidates_found = len(candidates)

    verified: list[VerifiedImage] = []
    probed = 0
    for c in candidates:
        if probed >= max_probes:
            break
        probed += 1
        dims, final_url, _err = probe_image(c.url, c.source_page)
        if not dims:
            continue
        w, h = dims
        if w < 1200 or h < 600:
            continue
        ratio = w / max(h, 1)
        if ratio < 1.10 or ratio > 4.2:
            continue
        score = candidate_score(c, w, h)
        verified.append(
            VerifiedImage(
                url=final_url,
                width=w,
                height=h,
                score=score,
                source_page=c.source_page,
                context=c.context,
                source_type=c.source_type,
            )
        )
    result.candidates_probed = probed

    # Keep only the best version from each image family.
    by_group: dict[str, VerifiedImage] = {}
    for v in sorted(verified, key=lambda x: (x.score, x.width * x.height), reverse=True):
        key = candidate_group_key(v.url)
        if key not in by_group:
            by_group[key] = v
    selected = sorted(by_group.values(), key=lambda x: (x.score, x.width * x.height), reverse=True)[:max_images]

    result.images = [{"url": v.url, "width": v.width, "height": v.height} for v in selected]
    result.status = "ok" if selected else "no_approved_images"
    return result


def atomic_json_write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        raise ValueError("Expected a JSON array of club objects")
    return data


def validate_output(baseline: list[dict], output: list[dict]) -> list[str]:
    errors: list[str] = []
    if len(baseline) != len(output):
        return [f"object count changed: {len(baseline)} -> {len(output)}"]
    for i, (before, after) in enumerate(zip(baseline, output)):
        b = copy.deepcopy(before)
        a = copy.deepcopy(after)
        before_images = b.pop("images", None)
        after_images = a.pop("images", None)
        if a != b:
            errors.append(f"object {i} ({before.get('name')}) changed outside images")
        if isinstance(before_images, list) and before_images:
            if after_images != before_images:
                errors.append(f"object {i} ({before.get('name')}) existing images changed")
            # Existing image schemas are grandfathered: preserve them byte-for-byte
            # instead of forcing newly added-image validation onto old data.
            continue
        if after_images is not None:
            if not isinstance(after_images, list):
                errors.append(f"object {i} ({before.get('name')}) images is not a list")
                continue
            if len(after_images) > 5:
                errors.append(f"object {i} ({before.get('name')}) has >5 images")
            for j, img in enumerate(after_images):
                if not isinstance(img, dict):
                    errors.append(f"object {i} image {j} is not an object")
                    continue
                if not isinstance(img.get("url"), str) or not img.get("url"):
                    errors.append(f"object {i} image {j} missing url")
                if int(img.get("width") or 0) < 1200:
                    errors.append(f"object {i} image {j} width <1200")
                if int(img.get("height") or 0) <= 0:
                    errors.append(f"object {i} image {j} invalid height")
    return errors


def append_audit(path: Path, record: ClubResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def write_summary_csv(path: Path, results: list[ClubResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "name", "status", "pages_checked", "candidates_found", "candidates_probed", "images_added", "error"])
        for r in sorted(results, key=lambda x: x.index):
            w.writerow([
                r.index,
                r.name,
                r.status,
                r.pages_checked,
                r.candidates_found,
                r.candidates_probed,
                len(r.images or []),
                r.error,
            ])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Add verified golf-course image URLs to Golfkuponger JSON.")
    p.add_argument("input", type=Path, help="Input golfbanor.json")
    p.add_argument("--output", type=Path, default=Path("output/golfbanor_med_bilder.json"))
    p.add_argument("--audit", type=Path, default=Path("output/audit.jsonl"))
    p.add_argument("--summary", type=Path, default=Path("output/summary.csv"))
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--max-pages", type=int, default=6)
    p.add_argument("--max-probes", type=int, default=36)
    p.add_argument("--max-images", type=int, default=5)
    p.add_argument("--limit", type=int, default=0, help="Process only N eligible clubs; 0 = all")
    p.add_argument("--prefix", action="append", default=[], help="Only names starting with prefix; repeatable")
    p.add_argument("--fresh", action="store_true", help="Ignore an existing output file instead of resuming it")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    baseline = load_json(args.input)

    if args.output.exists() and not args.fresh:
        working = load_json(args.output)
        if len(working) != len(baseline) or [x.get("name") for x in working] != [x.get("name") for x in baseline]:
            print("ERROR: existing output does not match input club ordering/names; use --fresh or another output path", file=sys.stderr)
            return 2
        # Never allow resume data to alter non-images fields relative to the baseline.
        pre_errors = validate_output(baseline, working)
        if pre_errors:
            print("ERROR: existing output failed validation:", file=sys.stderr)
            for e in pre_errors[:20]:
                print(" -", e, file=sys.stderr)
            return 2
    else:
        working = copy.deepcopy(baseline)
        args.audit.parent.mkdir(parents=True, exist_ok=True)
        args.audit.write_text("", encoding="utf-8")

    prefixes = tuple(p.casefold() for p in args.prefix)
    eligible: list[tuple[int, dict]] = []
    for i, club in enumerate(working):
        if club.get("active") is not True:
            continue
        existing = club.get("images")
        if isinstance(existing, list) and len(existing) > 0:
            continue
        name = str(club.get("name") or "")
        if prefixes and not name.casefold().startswith(prefixes):
            continue
        eligible.append((i, copy.deepcopy(club)))

    if args.limit > 0:
        eligible = eligible[: args.limit]

    if not eligible:
        print("Nothing to process. Existing images are preserved.")
        errs = validate_output(baseline, working)
        if errs:
            print("Validation failed:", *errs, sep="\n - ", file=sys.stderr)
            return 2
        atomic_json_write(args.output, working)
        return 0

    print(f"Processing {len(eligible)} clubs with {max(1, args.workers)} workers...")
    results: list[ClubResult] = []
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {
            pool.submit(process_club, i, club, args.max_pages, args.max_probes, args.max_images): (i, club)
            for i, club in eligible
        }
        for n, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
            i, club = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                result = ClubResult(
                    index=i,
                    name=str(club.get("name") or ""),
                    status="error",
                    official_url=str(club.get("url") or ""),
                    images=[],
                    error=str(exc)[:300],
                )
            results.append(result)
            # Only add images to clubs that still have none. This protects resumed/concurrent work.
            if not working[i].get("images"):
                working[i]["images"] = result.images or []
            append_audit(args.audit, result)
            atomic_json_write(args.output, working)
            print(
                f"[{n:>3}/{len(eligible)}] {result.name}: {result.status}, "
                f"{len(result.images or [])} images"
            )

    write_summary_csv(args.summary, results)
    errors = validate_output(baseline, working)
    if errors:
        print("\nVALIDATION FAILED:", file=sys.stderr)
        for e in errors[:50]:
            print(" -", e, file=sys.stderr)
        return 2

    added = sum(len(r.images or []) for r in results)
    ok = sum(1 for r in results if r.status == "ok")
    no_img = sum(1 for r in results if r.status == "no_approved_images")
    failed = len(results) - ok - no_img
    print(
        f"\nDone in {(time.time() - start)/60:.1f} min. "
        f"Clubs with images: {ok}; images added: {added}; "
        f"no approved images: {no_img}; other failures: {failed}."
    )
    print(f"Output: {args.output}")
    print(f"Audit: {args.audit}")
    print(f"Summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())