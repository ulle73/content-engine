#!/usr/bin/env python3
"""
vibecode — ground plate and torn-paper edges.

  make-paper.py ground --out assets/ground.png [--theme cobalt|cream|dark]
  make-paper.py edges  --out assets/edges.json [--count 24] [--seed 7]

`ground` rasterises the halftone plate once. Re-rasterising a dot grid every
frame in CSS is expensive and shimmers under render scaling; a PNG is steadier
and cheaper. The CSS in tokens.css draws the same thing and is fine for
snapshots — swap to the PNG for the final render.

`edges` writes deterministic clip-path polygons so no two paper cards in the
video share a silhouette. Same seed, same edges, every run.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, json, math, random, sys

THEMES = {
    "cobalt": dict(ground=(0x22, 0x6D, 0xE5), lift=(0x3A, 0x82, 0xF0),
                   deep=(0x14, 0x49, 0xA8), dot=(0x0B, 0x1E, 0x45), dot_a=0.20),
    "cream":  dict(ground=(0xF7, 0xF1, 0xDD), lift=(0xFF, 0xFC, 0xEF),
                   deep=(0xF4, 0xE8, 0xCC), dot=(0x78, 0x5C, 0x1E), dot_a=0.10),
    "dark":   dict(ground=(0x19, 0x14, 0x0A), lift=(0x2A, 0x21, 0x13),
                   deep=(0x0D, 0x0A, 0x05), dot=(0xD2, 0xA4, 0x50), dot_a=0.10),
}


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def build_ground(w, h, theme, dot_gap, dot_r):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit("Pillow is required:  pip install pillow")

    t = THEMES[theme]
    img = Image.new("RGB", (w, h), t["ground"])
    px = img.load()

    # radial lift at 50% x 34%, vignette to the corners
    cx, cy = w * 0.50, h * 0.34
    lift_r = math.hypot(w * 0.60, h * 0.50)
    vx, vy = w * 0.5, h * 0.5
    vig_r = math.hypot(w * 0.60, h * 0.50)
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy) / lift_r
            c = lerp(t["lift"], t["ground"], min(1.0, d / 0.68)) if d < 0.68 \
                else t["ground"]
            v = math.hypot(x - vx, y - vy) / vig_r
            if v > 0.42:
                c = lerp(c, t["deep"], min(1.0, (v - 0.42) / 0.58))
            px[x, y] = c

    # halftone dots
    dots = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(dots)
    fill = t["dot"] + (round(255 * t["dot_a"]),)
    y = 0
    while y < h + dot_gap:
        x = 0
        while x < w + dot_gap:
            d.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=fill)
            x += dot_gap
        y += dot_gap
    img = Image.alpha_composite(img.convert("RGBA"), dots).convert("RGB")
    return img


def torn_polygon(rng, n_per_side=4, amp=1.1):
    """A closed polygon just inside the unit box, wobbling by `amp` percent."""
    pts = []

    def side(x0, y0, x1, y1):
        for i in range(n_per_side):
            t = i / n_per_side
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            # push perpendicular to the edge, inward-biased
            j = rng.uniform(-amp, amp)
            if abs(y1 - y0) < 1e-6:          # horizontal edge
                y += j + (amp * 0.4 if y0 < 50 else -amp * 0.4)
            else:                            # vertical edge
                x += j + (amp * 0.4 if x0 < 50 else -amp * 0.4)
            pts.append((round(max(0.0, min(100.0, x)), 1),
                        round(max(0.0, min(100.0, y)), 1)))

    side(0, 0, 100, 0)
    side(100, 0, 100, 100)
    side(100, 100, 0, 100)
    side(0, 100, 0, 0)
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("ground")
    g.add_argument("--out", required=True)
    g.add_argument("--theme", default="cobalt", choices=sorted(THEMES))
    g.add_argument("--width", type=int, default=1920)
    g.add_argument("--height", type=int, default=1080)
    g.add_argument("--dot-gap", type=int, default=14)
    g.add_argument("--dot-radius", type=float, default=1.7)

    e = sub.add_parser("edges")
    e.add_argument("--out", required=True)
    e.add_argument("--count", type=int, default=24)
    e.add_argument("--seed", type=int, default=7)
    e.add_argument("--amp", type=float, default=1.1)

    a = ap.parse_args()

    if a.cmd == "ground":
        img = build_ground(a.width, a.height, a.theme, a.dot_gap, a.dot_radius)
        img.save(a.out)
        print(f"ground  {a.theme}  {a.width}x{a.height}  -> {a.out}")

    else:
        rng = random.Random(a.seed)
        out = []
        for i in range(a.count):
            pts = torn_polygon(rng, amp=a.amp)
            out.append({
                "id": f"edge-{i:02d}",
                "clipPath": "polygon(" + ", ".join(f"{x}% {y}%" for x, y in pts) + ")",
                # a hand-placed tilt to go with it, alternating sign
                "tilt": round(rng.uniform(0.7, 2.4) * (1 if i % 2 else -1), 2),
            })
        with open(a.out, "w") as f:
            json.dump(out, f, indent=2)
        print(f"edges   {a.count} polygons  seed={a.seed}  -> {a.out}")


if __name__ == "__main__":
    main()
