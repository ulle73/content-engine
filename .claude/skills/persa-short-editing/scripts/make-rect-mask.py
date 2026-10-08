#!/usr/bin/env python
"""
Generate the rounded-rectangle mask that carves the "window" in a cutout hook.

White rounded rect on black — fed to ffmpeg `alphamerge` so the source video shows
through the rect shape only.

    python scripts/make-rect-mask.py --out /path/rect_mask.png          # 1000x670 r44
    python scripts/make-rect-mask.py --w 1000 --h 670 --radius 44 --out m.png

Radius must match --r-card (22px) x2 in the design tokens, or read as a deliberate
softer corner. 44px is the house default for the hook rect.
"""
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
