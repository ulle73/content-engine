"""LOCAL background generator — the free, offline alternative to `generate`.

Paints each slide's background procedurally with headless Chromium (bg_local.html):
midnight field, teal bloom from inside the scene, silhouette flora with rim light,
amber accents, starfield, vignette, grain. No API key, no network, no cost.

Per slide in plan.json (all optional):
    "bg_scene": "deep-bloom" | "far-field" | "starfield" | "dandelion"
                | "amber-meadow" | "mist" | "close-flora"
    "bg_seed":  <int>          # same seed + same scene => identical painting
    "bg_tweak": {...}          # raw overrides merged into the scene config

Usage:  python carousel_localbg.py <run_dir> [--force]
        python carousel_localbg.py --preview          # one PNG per scene, to compare
"""
from __future__ import annotations   # py3.9: allows `dict | None` in annotations

import json
import sys
from pathlib import Path

import carousel_config as cfg

TEMPLATE = Path(__file__).resolve().parent / "bg_local.html"

# --- Scene presets -----------------------------------------------------------
# bloom  : x/y as a fraction of the canvas, r as a fraction of the width
# flora  : density multiplier + height multiplier
# horizon: where the flora is rooted (fraction of height)
# topGuard: how much of the top is force-held to black for the headline
SCENES = {
    # the signature look — a bloom low-center, deep flora standing in it
    "deep-bloom": {
        "bloom": {"x": 0.50, "y": 0.74, "r": 0.42, "intensity": 1.0},
        "blooms2": [{"x": 0.28, "y": 0.80, "r": 0.16, "i": 0.55},
                    {"x": 0.74, "y": 0.78, "r": 0.13, "i": 0.45}],
        "flora": {"density": 1.0, "height": 1.0}, "horizon": 0.80,
        "stars": 170, "brightStars": 7, "spores": 30, "mist": 3, "amber": 0,
    },
    # wide, quiet, mostly sky — best for hooks with long headlines
    "far-field": {
        "bloom": {"x": 0.34, "y": 0.82, "r": 0.34, "intensity": 0.8},
        "blooms2": [{"x": 0.72, "y": 0.84, "r": 0.14, "i": 0.4}],
        "flora": {"density": 0.75, "height": 0.72}, "horizon": 0.86,
        "stars": 210, "brightStars": 9, "spores": 20, "mist": 2, "amber": 0,
        "topGuard": 0.46,
    },
    # near-empty black + stars; flora only skims the bottom edge
    "starfield": {
        "bloom": {"x": 0.55, "y": 0.90, "r": 0.30, "intensity": 0.62},
        "blooms2": [],
        "flora": {"density": 0.5, "height": 0.55}, "horizon": 0.93,
        "stars": 260, "brightStars": 12, "spores": 14, "mist": 1, "amber": 0,
        "topGuard": 0.40, "grain": 0.05,
    },
    # a hero dandelion catching the light — great for a single big idea
    "dandelion": {
        "bloom": {"x": 0.42, "y": 0.76, "r": 0.36, "intensity": 0.95},
        "blooms2": [{"x": 0.70, "y": 0.72, "r": 0.15, "i": 0.5}],
        "flora": {"density": 0.8, "height": 0.85}, "horizon": 0.83,
        "heroFlora": [{"type": "dandelion", "x": 0.72, "h": 0.34, "size": 0.075},
                      {"type": "umbel", "x": 0.20, "h": 0.24, "size": 0.030}],
        "stars": 180, "brightStars": 8, "spores": 34, "mist": 3, "amber": 0,
    },
    # the warm one — tiny amber florets in the foreground (use sparingly)
    "amber-meadow": {
        "bloom": {"x": 0.62, "y": 0.78, "r": 0.36, "intensity": 0.85},
        "blooms2": [{"x": 0.30, "y": 0.82, "r": 0.15, "i": 0.5}],
        "flora": {"density": 1.0, "height": 0.9}, "horizon": 0.81,
        "stars": 165, "brightStars": 6, "spores": 24, "mist": 3, "amber": 7,
    },
    # soft horizontal haze through the light — calm, cinematic
    "mist": {
        "bloom": {"x": 0.48, "y": 0.70, "r": 0.46, "intensity": 0.9},
        "blooms2": [{"x": 0.20, "y": 0.74, "r": 0.18, "i": 0.45},
                    {"x": 0.82, "y": 0.72, "r": 0.16, "i": 0.4}],
        "flora": {"density": 0.7, "height": 0.75}, "horizon": 0.86,
        "stars": 150, "brightStars": 5, "spores": 26, "mist": 6, "amber": 0,
    },
    # tall out-of-focus stems in front, light behind them — most depth
    "close-flora": {
        "bloom": {"x": 0.52, "y": 0.72, "r": 0.40, "intensity": 1.0},
        "blooms2": [{"x": 0.30, "y": 0.76, "r": 0.14, "i": 0.5}],
        "flora": {"density": 1.35, "height": 1.15}, "horizon": 0.78,
        "stars": 140, "brightStars": 5, "spores": 32, "mist": 4, "amber": 3,
        "topGuard": 0.44,
    },
}
DEFAULT_SCENE = "deep-bloom"
# a pleasing default rotation so a 6-slide set never repeats a scene back to back
ROTATION = ["deep-bloom", "far-field", "close-flora", "dandelion", "mist", "amber-meadow",
            "starfield"]


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def scene_config(scene: str, seed: int, tweak: dict | None = None) -> dict:
    base = SCENES.get(scene) or SCENES[DEFAULT_SCENE]
    conf = _merge(base, tweak or {})
    conf["seed"] = int(seed)
    conf["scale"] = cfg.RENDER_SCALE
    return conf


# A 2160x2700 canvas can finish its script before the compositor has drawn it —
# on a cold first run that produced a blank PNG. So: wait for the done flag, let two
# frames pass, then check the result actually has ink in it before moving on.
_BLANK_BYTES = 80_000          # a real painted scene is ~1.5-2.5 MB; blank is ~25 KB


def _paint(page, conf: dict, out: Path, tries: int = 3):
    html = TEMPLATE.read_text(encoding="utf-8").replace("__CONFIG__", json.dumps(conf))
    for attempt in range(tries):
        page.set_content("<!doctype html><body></body>")      # clear any stale done flag
        page.set_content(html, wait_until="load")
        page.wait_for_function("document.body.dataset.done === '1'", timeout=30000)
        # two animation frames guarantees the canvas is composited before capture
        page.evaluate("() => new Promise(r => requestAnimationFrame("
                      "() => requestAnimationFrame(r)))")
        page.screenshot(path=str(out), clip={"x": 0, "y": 0,
                                             "width": cfg.CANVAS_W, "height": cfg.CANVAS_H})
        if out.stat().st_size >= _BLANK_BYTES:
            return
        print(f"  (blank capture, repainting — attempt {attempt + 2})")
    print(f"  WARNING: {out.name} still looks blank after {tries} attempts")


def _browser(pw):
    b = cfg.launch_browser(pw)
    return b, b.new_page(viewport={"width": cfg.CANVAS_W, "height": cfg.CANVAS_H},
                         device_scale_factor=cfg.RENDER_SCALE)


def generate(run_dir, force: bool = False):
    from playwright.sync_api import sync_playwright

    run_dir = Path(run_dir)
    plan_path = run_dir / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    media = run_dir / "media"
    media.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser, page = _browser(pw)
        for i, slide in enumerate(plan["slides"]):
            idx = slide["index"]
            out = media / f"slide{idx:02d}.png"
            if out.exists() and slide.get("bg_file") and not force:
                print(f"[slide {idx}] bg exists, skipping (--force to repaint)")
                continue
            scene = slide.get("bg_scene") or ROTATION[i % len(ROTATION)]
            seed = slide.get("bg_seed")
            if seed is None:
                seed = 1000 + idx * 37
            _paint(page, scene_config(scene, seed, slide.get("bg_tweak")), out)
            slide["bg_scene"], slide["bg_seed"] = scene, seed
            slide["bg_file"] = str(out)
            print(f"[slide {idx}] painted '{scene}' (seed {seed}) -> {out}")
            plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        browser.close()

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"\nPainted {len(plan['slides'])} background(s) locally -> {media}  (no API used)")


def preview(dest: Path | None = None, seed: int = 7):
    """One PNG per scene so you can eyeball the whole vocabulary at once."""
    from playwright.sync_api import sync_playwright
    dest = Path(dest or (cfg.OUTPUT_DIR / "_bg-preview"))
    dest.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser, page = _browser(pw)
        for name in SCENES:
            out = dest / f"{name}.png"
            _paint(page, scene_config(name, seed), out)
            print(f"[{name}] -> {out}")
        browser.close()
    print(f"\nScene previews -> {dest}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--preview":
        preview(args[1] if len(args) > 1 else None)
    elif args:
        generate(args[0], force="--force" in args)
    else:
        print(__doc__)
        raise SystemExit(1)
