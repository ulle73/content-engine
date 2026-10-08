"""Fetch freely-licensed photographs from Wikimedia Commons for the Archival style.

The Archival Swiss Poster sheet says "the photograph supplies every other color in the
system" — so each slide needs its OWN photograph, not a variation of one scene. This
pulls real, freely-licensed images and records the credit line for every one, which the
template then prints in the slide's `Archive` metadata field.

Only files whose license is public domain or a CC licence are kept; anything else is
skipped rather than silently used.

Usage:
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_photos.py <outdir> "<search 1>" "<search 2>" ...
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_photos.py --credits <outdir>        # print the credit table
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "CarouselGeneratorKit/1.0 (local, educational; contact: local user)"
OK_LICENCE = re.compile(r"(public domain|^cc[ -]|cc0|attribution)", re.I)


def _get(url: str, tries: int = 4) -> bytes:
    """Commons rate-limits hard; back off and retry rather than dropping the photo."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2.5 * (attempt + 1))
    raise last


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


# Commons serves standard thumbnail steps; 3840px stays sharp at the 2x render scale
# (1080px slides are rendered at 2160px wide). Override with CAROUSEL_PHOTO_WIDTH.
import os
PHOTO_WIDTH = os.environ.get("CAROUSEL_PHOTO_WIDTH", "3840")


def search(term: str, limit: int = 12) -> list[dict]:
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {term}", "gsrnamespace": "6", "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": PHOTO_WIDTH,
    })
    data = json.loads(_get(f"{API}?{q}"))
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = _strip(meta.get("LicenseShortName", {}).get("value", ""))
        if not OK_LICENCE.search(lic):
            continue                      # not clearly free — skip it
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < 1200 or h < 700 or w / max(1, h) < 1.2:
            continue                      # need a wide, big photo
        out.append({
            "title": p.get("title", "").replace("File:", ""),
            "url": ii.get("thumburl") or ii.get("url"),
            "original": ii.get("url"),
            "page": ii.get("descriptionurl", ""),
            "licence": lic,
            "author": _strip(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "w": w, "h": h,
        })
    return out


def fetch(outdir: Path, terms: list[str]):
    outdir.mkdir(parents=True, exist_ok=True)
    credits_path = outdir / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    used_titles = {c["title"] for c in credits.values()}

    for i, term in enumerate(terms, 1):
        slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")[:40]
        dest = outdir / f"{i:02d}-{slug}.jpg"
        if dest.exists():
            print(f"[{i}] exists, skipping: {dest.name}")
            continue
        try:
            hits = [h for h in search(term) if h["title"] not in used_titles]
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] search failed for {term!r}: {e}")
            continue
        if not hits:
            print(f"[{i}] no freely-licensed match for {term!r}")
            continue
        hit = hits[0]
        try:
            dest.write_bytes(_get(hit["url"]))
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] download failed: {e}")
            continue
        used_titles.add(hit["title"])
        credits[dest.name] = {**hit, "search": term}
        credits_path.write_text(json.dumps(credits, indent=2), encoding="utf-8")
        time.sleep(1.5)          # be polite to Commons
        print(f"[{i}] {dest.name}  <-  {hit['title']}  ({hit['licence']})")

    print(f"\n{len(credits)} photo(s) in {outdir}")


def show_credits(outdir: Path):
    credits = json.loads((outdir / "credits.json").read_text(encoding="utf-8"))
    for k, v in credits.items():
        print(f"{k:34s} {v['licence']:22s} {v['author'][:46]:46s} {v['title'][:50]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        raise SystemExit(1)
    if args[0] == "--credits":
        show_credits(Path(args[1]))
    else:
        fetch(Path(args[0]), args[1:])
