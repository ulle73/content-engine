"""Orchestrator for the Soft Pastoral carousel generator (kie.ai edition, content-engine import).

Run from the repo root with the library venv, e.g.
  library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/carousel_run.py init "Friskvård golf"

Subcommands:
  init <topic> [--handle @x] [--brand "X"] [--template t.html]
                    create a fresh run folder (work/carousel-generator-kie/runs/...) + starter plan.json
  render <run>      overlay the template on each background -> 1080x1350 PNGs   (FREE)
  export <run>      copy final numbered slides into work/carousel-generator-kie/output/<slug>/
  build <run>       render + export (FREE): backgrounds = your own photos (`bg_file`) or the
                    template's plain sky field when a slide has no bg_file
  generate <run>    paint every slide background via kie.ai Nano Banana Pro (PAID)
  produce <run>     generate + render + export (PAID)

Handle/brand default to Golfkuponger (@golfkuponger) — override per plan, with the init flags,
or with CAROUSEL_HANDLE / CAROUSEL_BRAND.

APPROVAL GATE: never run `generate` / `produce` until the user has approved the plan.json
(backgrounds cost real kie.ai credits). `init` / `render` / `export` / `build` are free.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import carousel_config as cfg


def _slugify(s: str) -> str:
    s = s.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:48] or "carousel"


# Shared style sentence so every PAID background reads as one set. Edit once, applies to all.
_STYLE = (
    "Dreamy Studio-Ghibli-inspired photographic scene, warm pastel palette, bright airy "
    "sky with big soft cumulus clouds, soft golden light, gentle film grain, shallow depth "
    "of field with dreamy foreground bokeh. Keep the TOP HALF open (negative space for a "
    "headline). No text, no letters, no logos."
)


def _slide(index, role, headline, hero_word, subtitle, scene, topic_tag=""):
    return {
        "index": index,
        "role": role,                       # hook | body | cta (labels for you)
        "topic_tag": topic_tag,             # small pill top-left; "" hides it
        "headline": headline,
        "hero_word": hero_word,             # halftone accent word; "" hides it
        "subtitle": subtitle,               # pill text; "" hides the pill
        "image_prompt": f"{scene} {_STYLE}",   # PAID path only
        "subject_image": None,              # PAID path only: optional 2nd input image (public URL)
        "bg_url": None, "bg_file": None, "out_file": None,
    }


def _starter_plan(slug: str, stamp: str, opts: dict) -> dict:
    """A 6-slide starter (hook -> 4 value slides -> CTA). Edit before building.

    Carousel arc: slide 1 is the scroll-stopping HOOK, 2-5 deliver the value one
    idea per slide, slide 6 is the CTA. Keep it to 5-7 slides.
    """
    handle = opts.get("handle") or cfg.DEFAULT_HANDLE
    return {
        "slug": f"{stamp}-{slug}",
        "topic": opts.get("topic", ""),
        "created": stamp,
        "template": opts.get("template") or "template.html",
        "brand_label": opts.get("brand") or cfg.DEFAULT_BRAND,
        "handle": handle,
        "canvas": {"w": cfg.CANVAS_W, "h": cfg.CANVAS_H, "aspect": "4:5"},
        "slides": [
            _slide(1, "hook", "Byt rubrik här:", "krok",
                   "En rad som säger vem/vad.",
                   "A grassy hilltop with wildflowers under a wide open sky."),
            _slide(2, "body", "En idé per", "bild",
                   "Skriv en kort förklarande rad här.",
                   "A single sunlit meadow, calm and minimal, lots of open sky."),
            _slide(3, "body", "Visa beviset", "",
                   "Lägg ett kort med siffror eller en skärmbild i mitten.",
                   "Rolling pastel hills fading into soft clouds, painterly light."),
            _slide(4, "body", "Håll texten kort", "",
                   "Max en tanke per bild.",
                   "A tidy hilltop with a lone tree, clean negative space up top."),
            _slide(5, "body", "Rubriker är kod", "",
                   "Text renderas skarpt av mallen — aldrig av AI.",
                   "A bright valley at golden hour, warm and expansive."),
            _slide(6, "cta", "Din tur", "",
                   f"Spara inlägget. Följ {handle} för mer.",
                   "A glowing sunset sky over open fields, inviting and warm."),
        ],
    }


def _parse_init(args: list[str]) -> dict:
    opts, rest = {}, []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--") and a[2:] in ("handle", "brand", "template") and i + 1 < len(args):
            opts[a[2:]] = args[i + 1]
            i += 2
            continue
        rest.append(a)
        i += 1
    opts["topic"] = " ".join(rest)
    return opts


def cmd_init(topic: str, extra: list[str] | None = None):
    opts = _parse_init([topic] + (extra or []))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slugify(opts["topic"])
    run_dir = cfg.RUNS_DIR / f"{stamp}-{slug}"
    (run_dir / "media").mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(
        json.dumps(_starter_plan(slug, stamp, opts), indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(run_dir))


def cmd_generate(run_dir: str):
    import carousel_generate
    carousel_generate.generate(run_dir)


def cmd_render(run_dir: str):
    import carousel_render
    carousel_render.render(run_dir)


def cmd_export(run_dir: str):
    run_dir = Path(run_dir)
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    dest = cfg.OUTPUT_DIR / plan["slug"]
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for slide in plan["slides"]:
        src = slide.get("out_file")
        if src and Path(src).exists():
            shutil.copy2(src, dest / f"{slide['index']:02d}.png")
            n += 1
    print(f"Exported {n} slide(s) -> {dest}")


def cmd_build(run_dir: str):
    """FREE: render + export with whatever bg_file each slide has (own photos) or none."""
    cmd_render(run_dir)
    cmd_export(run_dir)


def cmd_produce(run_dir: str):
    cmd_generate(run_dir)
    cmd_render(run_dir)
    cmd_export(run_dir)


_CMDS = {
    "init": cmd_init,
    "generate": cmd_generate,
    "render": cmd_render,
    "export": cmd_export,
    "build": cmd_build,
    "produce": cmd_produce,
}


def _resolve_run(arg: str) -> str:
    """Accept a full path OR a bare run name (as printed by `init`)."""
    if Path(arg).is_dir():
        return arg
    candidate = cfg.RUNS_DIR / arg
    if candidate.is_dir():
        return str(candidate)
    raise SystemExit(f"Run not found: {arg}\nLooked in {cfg.RUNS_DIR}. Run `init` first.")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in _CMDS:
        print(__doc__)
        raise SystemExit(1)
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "init":
        cmd_init(arg, sys.argv[3:])
    else:
        _CMDS[cmd](_resolve_run(arg))
