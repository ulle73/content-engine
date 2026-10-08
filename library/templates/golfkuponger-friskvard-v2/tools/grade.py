"""Bake the persa film grade (nextphase.short.grade-persa-svg tables) into the photographic assets,
so Chrome does not run an SVG filter on 2-4K layers every frame. Writes *-g.jpg / *-g.png."""
import re, sys
import numpy as np
from PIL import Image
svg = open("library/kits/nextphase/skills/nextphase-short-editing/components/grade-persa.svg", encoding="utf-8").read()
tabs = [np.array([float(v) for v in m.split()]) for m in re.findall(r'tableValues="([^"]+)"', svg)]
x = np.linspace(0, 1, len(tabs[0]))
lut = [np.interp(np.arange(256) / 255, x, t) * 255 for t in tabs]
A = "work/friskvard-v2/film/assets/"
def grade(src, dst):
    im = Image.open(A + src)
    a = np.asarray(im).astype(np.float32)
    for c in range(3):
        a[..., c] = lut[c][a[..., c].astype(np.uint8)]
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8), im.mode)
    if dst.endswith(".jpg"):
        out.convert("RGB").save(A + dst, quality=90, optimize=True)
    else:
        out.save(A + dst, optimize=True)
    print(dst, out.size)
for n in ["hero-skogsbana", "klubb-bro-hof-slott", "klubb-halmstad-gk", "klubb-falsterbo-gk", "klubb-osteraker-gk", "anvnd-friskvrdsbidraget-till-golf"]:
    grade(n + "@2x.jpg", n + "-g.jpg")
for n in ["hook-plate.jpg", "hook-sky.jpg", "hook-fg.png", "hook-golfer.png"]:
    grade(n, n.replace(".", "-g."))
