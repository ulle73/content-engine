#!/usr/bin/env python
"""
Generate the rounded-rectangle mask that carves the "window" in a cutout hook.

White rounded rect on black — fed to ffmpeg `alphamerge` so the source video shows
through the rect shape only.

    python scripts/make-rect-mask.py --w 1200 --h 803 --out assets/rect_mask_1200x803.png

cutout-hook.sh generates this for you, keyed by size. Call it by hand only to
pre-build a mask or to try a different radius. The 1000x670 defaults below are the
9:16 values and are the WRONG shape for a 1920x1080 frame - always pass --w/--h.

Radius must match --r-card (22px) x2 in the design tokens, or read as a deliberate
softer corner. 44px is the house default for the pop-out rect.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument("--w", type=int, default=1000)
p.add_argument("--h", type=int, default=670)
p.add_argument("--radius", type=int, default=44)
p.add_argument("--out", required=True)
a = p.parse_args()

img = Image.new("L", (a.w, a.h), 0)
ImageDraw.Draw(img).rounded_rectangle([0, 0, a.w - 1, a.h - 1], radius=a.radius, fill=255)
img.save(a.out)
print(f"make-rect-mask: {a.w}x{a.h} r{a.radius} -> {a.out}")
