"""Fetch the real logo of a company/product for a carousel, as SVG + transparent PNG.

Why: when a carousel is about a specific company, its actual logo belongs on the
slides. The local HTML path embeds the SVG/PNG directly; the paid Higgsfield/kie
path uploads the PNG as a reference image so the model sees the real mark instead
of inventing one (see knowledge/logos.md).

Source: Wikimedia Commons (vector logos, with licence recorded). Every logo is
written to <outdir>/logos.json with its source page, so it can be verified and
swapped for an official brand-kit file if needed.

Usage:
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py <outdir> "Instagram" ["Instagram glyph" ...]
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py <outdir> "Instagram" --pick 2 --as instagram-glyph   # 2nd match, own name
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py --list "Instagram"                # show candidates only
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


def _get(url: str, tries: int = 4) -> bytes:
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2.0 * (attempt + 1))
    raise last


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def search(name: str, limit: int = 15) -> list[dict]:
    """Vector logo candidates for `name`, best first (title mentions name + 'logo')."""
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:drawing {name} logo", "gsrnamespace": "6", "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
    })
    pages = (json.loads(_get(f"{API}?{q}")).get("query") or {}).get("pages") or {}
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") != "image/svg+xml":
            continue
        title = p.get("title", "").replace("File:", "")
        norm = re.sub(r"[^a-z0-9]", "", title.lower())
        meta = ii.get("extmetadata") or {}
        out.append({
            "title": title, "url": ii.get("url"), "page": ii.get("descriptionurl", ""),
            "licence": _strip(meta.get("LicenseShortName", {}).get("value", "")) or "see page",
            # exact "<name> logo.svg" wins; otherwise prefer short titles that start
            # with the name (combined/sub-brand files like "Threads-Instagram…" sink)
            "score": (norm == f"{key}logosvg") * 5 + norm.startswith(key) * 2 + (key in norm)
                     + ("logo" in norm) - len(norm) / 40,
        })
    return sorted(out, key=lambda c: -c["score"])


def rasterize(svg: Path, png: Path, size: int = 1024):
    """SVG -> transparent PNG (longest side = size), keeping the logo's own aspect ratio."""
    import base64
    from playwright.sync_api import sync_playwright
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.read_bytes()).decode()
    html = ("<html><body style='margin:0;background:transparent'>"
            f"<img id=l src='{uri}' style='display:block'></body></html>")
    with sync_playwright() as p:
        import carousel_config as cfg
        b = cfg.launch_browser(p)
        pg = b.new_page(viewport={"width": size * 2, "height": size * 2})
        pg.set_content(html)
        pg.wait_for_function("document.getElementById('l').complete")
        # scale so the longest side is `size`, whatever the SVG's intrinsic size
        pg.evaluate(f"""() => {{ const i = document.getElementById('l');
            const w = i.naturalWidth || 1, h = i.naturalHeight || 1, k = {size} / Math.max(w, h);
            i.style.width = Math.round(w * k) + 'px'; i.style.height = Math.round(h * k) + 'px'; }}""")
        pg.locator("#l").screenshot(path=str(png), omit_background=True)
        b.close()


def fetch(outdir: Path, name: str, pick: int = 1, slug: str | None = None):
    outdir.mkdir(parents=True, exist_ok=True)
    cands = search(name)
    if not cands:
        raise SystemExit(f"No vector logo found on Commons for {name!r} — use the company's press/brand kit.")
    c = cands[min(pick, len(cands)) - 1]
    slug = slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    svg, png = outdir / f"{slug}.svg", outdir / f"{slug}.png"
    svg.write_bytes(_get(c["url"]))
    rasterize(svg, png)
    reg_path = outdir / "logos.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else {}
    reg[slug] = {"name": name, "svg": svg.name, "png": png.name,
                 "title": c["title"], "page": c["page"], "licence": c["licence"]}
    reg_path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    print(f"{name}: {c['title']}  ({c['licence']})\n  -> {svg}\n  -> {png}\n  source: {c['page']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); raise SystemExit(1)
    if a[0] == "--list":
        for i, c in enumerate(search(a[1]), 1):
            print(f"{i:2d}. {c['title'][:70]:70s} {c['licence'][:24]}")
        raise SystemExit(0)
    pick, slug = 1, None
    if "--pick" in a:
        i = a.index("--pick"); pick = int(a[i + 1]); del a[i:i + 2]
    if "--as" in a:
        i = a.index("--as"); slug = a[i + 1]; del a[i:i + 2]
    for n in a[1:]:
        fetch(Path(a[0]), n, pick, slug)
