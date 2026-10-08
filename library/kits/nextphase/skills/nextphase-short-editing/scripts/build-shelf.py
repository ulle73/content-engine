#!/usr/bin/env python3
"""
THE SHELF — every usable animation in the library, as labelled contact sheets you can
actually READ in one pass.

    python scripts/build-shelf.py            # rebuild sheets + SHELF.html
    python scripts/build-shelf.py --open     # and open it

Written 2026-08-18, after Jad said the thing that made the problem obvious:

    "we have a massive, massive library with so many beautiful animations. I actually,
     unfortunately, don't see you doing. Please try to find the best way to organize this."

The diagnosis was not taste, it was VISIBILITY. `REGISTRY.html` and `BLOCK-PICKER.html`
both exist and both are correct, but they are long scrolling pages of live iframes: opening
one shows you six items at a time, so in practice the same four blocks got reached for on
every cut. tp-0817b used **2 of 356 registry items, 0 of 10 real UI crops and 0 of 24
mascots**.

A contact sheet fixes exactly that: 42 items per screen, each with its NAME under it and its
grade in the label colour, so the whole shelf is five images instead of an hour of scrolling.
Reading those five images is what put `locked-nucleus-orbit`, `avatar-cloud`, `apple-money-
count`, `notification-pileup` and `overwhelm-surround` on the table for tp-0818 — none of
which had ever been considered before.

Sheets are written to `shelf/`. Only `on-brand` and `needs-work` items appear: `off-palette`
is quarantined and `captured-device` only belongs when the subject genuinely IS that device.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, json, pathlib, subprocess, sys, webbrowser

def _find_repo():
    """Walk up until broll-library/ turns up, so this works whether the script sits at the
    project root or inside the skill package."""
    here = pathlib.Path(__file__).resolve()
    for d in here.parents:
        if (d / "broll-library").is_dir():
            return d
    return here.parent.parent


REPO = _find_repo()
REG = REPO / "broll-library" / "registry"
PREV = REG / "previews"
OUT = REPO / "shelf"
COLS, ROWS, CW, CH, PAD, LBL = 6, 7, 300, 180, 8, 22

ap = argparse.ArgumentParser()
ap.add_argument("--open", action="store_true")
ap.add_argument("--frame", type=int, default=55, help="preview frame to sample")
a = ap.parse_args()

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("build-shelf: needs Pillow —  pip install pillow")

grade = json.loads((REG / "brand-grade.json").read_text())
names = sorted((n for n, v in grade.items()
                if v["grade"] in ("on-brand", "needs-work") and (PREV / f"{n}.mp4").exists()),
               key=lambda n: (grade[n]["grade"] != "on-brand", n))
if not names:
    sys.exit("build-shelf: no rendered previews — run scripts/render-registry-previews.py")

OUT.mkdir(exist_ok=True)
(OUT / "f").mkdir(exist_ok=True)
for n in names:
    f = OUT / "f" / f"{n}.png"
    if not f.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(PREV / f"{n}.mp4"),
                        "-vf", f"select='eq(n\\,{a.frame})',scale={CW}:-1",
                        "-frames:v", "1", str(f)], capture_output=True)

try:
    F = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
except OSError:
    F = ImageFont.load_default()

per = COLS * ROWS
sheets = []
for s in range((len(names) + per - 1) // per):
    chunk = names[s * per:(s + 1) * per]
    W, H = COLS * (CW + PAD) + PAD, ROWS * (CH + LBL + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (28, 26, 24))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(chunk):
        x = PAD + (i % COLS) * (CW + PAD)
        y = PAD + (i // COLS) * (CH + LBL + PAD)
        try:
            im = Image.open(OUT / "f" / f"{n}.png").convert("RGB")
            im.thumbnail((CW, CH))
            sheet.paste(im, (x + (CW - im.width) // 2, y + (CH - im.height) // 2))
        except OSError:
            pass
        col = (150, 235, 150) if grade[n]["grade"] == "on-brand" else (235, 200, 140)
        d.text((x + 2, y + CH + 3), n[:38], fill=col, font=F)
    name = f"shelf-{s+1}.png"
    sheet.save(OUT / name)
    sheets.append((name, chunk))

on = sum(1 for n in names if grade[n]["grade"] == "on-brand")
html = ["<!doctype html><meta charset=utf-8><title>THE SHELF</title>",
        "<style>body{background:#1c1a18;color:#F0EDE4;font:15px/1.6 -apple-system,sans-serif;"
        "margin:0;padding:40px}h1{font-size:30px;margin:0 0 6px}p{color:#9a9186;max-width:70ch}"
        "img{width:100%;display:block;margin:26px 0 6px;border-radius:8px}"
        "b{color:#96eb96}i{color:#ebc88c;font-style:normal}</style>",
        f"<h1>THE SHELF — {len(names)} usable animations</h1>",
        f"<p><b>{on} on-brand</b> · <i>{len(names)-on} needs-work</i>. "
        "off-palette and captured-device are quarantined and not shown. "
        "Read all of these BEFORE assigning a beat — that is the whole point of the page.</p>"]
for name, chunk in sheets:
    html.append(f"<img src='{name}'>")
(OUT / "SHELF.html").write_text("\n".join(html))

print(f"build-shelf: {len(names)} items ({on} on-brand) -> {len(sheets)} sheets in shelf/")
print(f"             open shelf/SHELF.html — or read shelf/shelf-*.png directly")
if a.open:
    webbrowser.open((OUT / "SHELF.html").as_uri())
