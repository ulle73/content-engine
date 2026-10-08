#!/usr/bin/env python3
"""Assemble every src/<slide>.html into its own HyperFrames project under slides/<slide>/.

One project per slide means each slide checks, previews and renders on its own.
Placeholders filled in each src file:
  /*@CHROME@*/      shared/fonts.css + the other shared/*.css
  //@ENGINE@        shared/engine.js       (window.LC: easing, springs, ball path, bursts, ruler)
  //@PHOTO@         shared/photo.js        (window.PH: photo-mode layers; photo projects only)
  <!--@GRAIN@-->    animated film grain
  /*@GEO@*/ {}      assets/<slide>/geo.json (photo-mode geometry from prep_photo.py)
  /*@CUES@*/ {}     carousel.json -> cues.<slide> (photo-mode timing, shared with audio/make_audio.py)
  @DUR@             cues.<slide>.dur
The palette in theme.json is applied last (see the skill's references/house-style.md).
Files starting with "_" in src/ are skipped. Usage: python3 build.py [slide ...]
"""
import json
import re
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
SHARED = ROOT / "shared"

# The house palette the templates are written in. theme.json maps these to new colours.
BASE = {
    "hero": "#2041f2",
    "hero-hi": "#3a5cff",
    "hero-deep": "#1530c8",
    "paper": "#fff3e0",
    "accent": "#ff6a1f",
    "accent-hi": "#ff9a5c",
    "accent-deep": "#e4500d",
    "ink": "#0c1236",
}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def apply_theme(html, colors):
    for key, base in BASE.items():
        new = colors.get(key)
        if not new or new.lower() == base:
            continue
        html = re.sub(re.escape(base), new, html, flags=re.I)
        r, g, b = rgb(base)
        nr, ng, nb = rgb(new)
        html = re.sub(rf"rgba\(\s*{r}\s*,\s*{g}\s*,\s*{b}\s*,", f"rgba({nr}, {ng}, {nb},", html)
    return html


def silent_wav(path, seconds, sr=48000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00\x00\x00" * int(seconds * sr))


def read(path):
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def main():
    css = read(SHARED / "fonts.css") + "\n" + "\n".join(p.read_text(encoding="utf-8") for p in sorted(SHARED.glob("*.css")) if p.name != "fonts.css")
    engine = read(SHARED / "engine.js")
    photo = read(SHARED / "photo.js")
    grain = read(SHARED / "grain-overlay.html")
    grain = re.sub(r"<!--.*?-->", "", grain, count=1, flags=re.S).strip().replace("opacity: 0.15;", "opacity: 0.11;")
    theme = json.loads(read(ROOT / "theme.json") or "{}")
    cues_all = json.loads(read(ROOT / "carousel.json") or "{}").get("cues", {})
    colors = theme.get("colors", {})

    only = set(sys.argv[1:])
    built = 0
    for src in sorted(SRC.glob("*.html")):
        name = src.stem
        if name.startswith("_") or (only and name not in only):
            continue
        geo_path = ROOT / "assets" / name / "geo.json"
        html = (
            src.read_text(encoding="utf-8")
            .replace("/*@CHROME@*/", css)
            .replace("/*@CSS@*/", css)
            .replace("//@ENGINE@", engine)
            .replace("//@PHOTO@", photo)
            .replace("<!--@GRAIN@-->", grain)
            .replace("/*@GEO@*/ {}", read(geo_path).strip() or "{}")
        )
        cues = cues_all.get(name, {})
        html = html.replace("/*@CUES@*/ {}", json.dumps(cues)).replace("@DUR@", f"{cues.get('dur', 6):g}")
        html = apply_theme(html, colors)
        dest = ROOT / "slides" / name
        assets = dest / "assets"
        (assets / "fonts").mkdir(parents=True, exist_ok=True)
        (dest / "index.html").write_text(html, encoding="utf-8")
        for f in (SHARED / "fonts").glob("*.woff2"):
            shutil.copy2(f, assets / "fonts" / f.name)
        layer_dir = ROOT / "assets" / name
        if layer_dir.is_dir():
            for f in layer_dir.iterdir():
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp4"):
                    shutil.copy2(f, assets / f.name)
        m = re.search(r'data-composition-id="main"[^>]*data-duration="([\d.]+)"', html)
        if not m:
            sys.exit(f"{src.name}: the #root needs data-composition-id=\"main\" and data-duration")
        dur = float(m.group(1))
        mix = ROOT / "audio/out" / f"{name}.wav"
        target = assets / "audio/mix.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        if mix.exists():
            shutil.copy2(mix, target)
        else:
            silent_wav(target, dur)
            print(f"  (no audio/out/{name}.wav yet: using silence)")
        for meta in ("hyperframes.json", "package.json"):
            shutil.copy2(ROOT / meta, dest / meta)
        (dest / "meta.json").write_text(json.dumps({"id": f"live-carousel-{name}", "name": f"Live Carousel {name}"}, indent=2), encoding="utf-8")
        print(f"built slides/{name} ({dur:g}s, theme {theme.get('name', 'cobalt')})")
        built += 1
    if not built:
        sys.exit("nothing built: no matching src/*.html")


if __name__ == "__main__":
    main()
