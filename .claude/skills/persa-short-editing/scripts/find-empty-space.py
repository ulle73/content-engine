#!/usr/bin/env python3
"""
FIND-EMPTY-SPACE — where an annotation is allowed to go on a page shot.

    python scripts/find-empty-space.py <image> [--max-y 1143] [--min-w 400] [--json]

Written 2026-08-27, after Jad rejected a caption beat twice in a row:

    "you took a screenshot, right, and then you just fucking put it into the frame,
     makes no sense … It's overlaying my face. It's small. It's not full screen."

The first half of that was a box bug (see BLACKLIST #16). The second half is this: even
once the UI owns the frame, a lime annotation typed at a guessed `top:` lands on the UI's
own headline or buttons. In the reference reels it never does — it sits in the black gutter
of the curve graph, in real negative space, aligned to the UI's grid.

So stop guessing. This finds the largest genuinely empty rectangle in the shot and prints
the box to place text in. Downsamples to a cell grid, marks a cell empty when its local
standard deviation is below a threshold, then solves the classic maximal-rectangle problem
over that binary grid.

`--max-y` clips the search to the area ABOVE the camera card (1143 in the persa style), so
it never proposes a region the card will cover.
"""
import argparse
import json
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("needs Pillow:  pip install pillow")

CELL = 10          # px per grid cell
FLAT = 6.0         # a cell is "empty" if its std-dev is under this


def empty_grid(im, cell=CELL, flat=FLAT):
    """Binary grid: 1 where the image is flat enough to write on."""
    g = im.convert("L")
    W, H = g.size
    cols, rows = W // cell, H // cell
    px = g.load()
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x0, y0 = c * cell, r * cell
            vals = [px[x0 + dx, y0 + dy] for dy in range(0, cell, 3) for dx in range(0, cell, 3)]
            n = len(vals)
            mean = sum(vals) / n
            var = sum((v - mean) ** 2 for v in vals) / n
            row.append(1 if var ** 0.5 <= flat else 0)
        grid.append(row)
    return grid, cols, rows


def largest_rect(grid, cols, rows):
    """Maximal all-ones rectangle, by the histogram method. Returns (r0,c0,r1,c1)."""
    best = (0, None)
    heights = [0] * cols
    for r in range(rows):
        for c in range(cols):
            heights[c] = heights[c] + 1 if grid[r][c] else 0
        stack = []                                   # (start_col, height)
        for c in range(cols + 1):
            h = heights[c] if c < cols else 0
            start = c
            while stack and stack[-1][1] >= h:
                s, sh = stack.pop()
                area = sh * (c - s)
                if area > best[0]:
                    best = (area, (r - sh + 1, s, r, c - 1))
                start = s
            stack.append((start, h))
    return best[1]


def find(path, max_y=None, min_w=400, cell=CELL, flat=FLAT):
    im = Image.open(path)
    W, H = im.size
    if max_y:
        im = im.crop((0, 0, W, min(max_y, H)))
    grid, cols, rows = empty_grid(im, cell, flat)
    box = largest_rect(grid, cols, rows)
    if not box:
        return None
    r0, c0, r1, c1 = box
    rect = {
        "left": c0 * cell, "top": r0 * cell,
        "width": (c1 - c0 + 1) * cell, "height": (r1 - r0 + 1) * cell,
    }
    rect["right"] = rect["left"] + rect["width"]
    rect["bottom"] = rect["top"] + rect["height"]
    if rect["width"] < min_w:
        rect["warning"] = f'only {rect["width"]}px wide — too narrow for an annotation'
    return {"image": str(path), "size": [W, H], "searched_above_y": max_y, "empty": rect}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--max-y", type=int, default=None,
                    help="only search above this y (use 1143 to stay clear of the camera card)")
    ap.add_argument("--min-w", type=int, default=400)
    ap.add_argument("--cell", type=int, default=CELL)
    ap.add_argument("--flat", type=float, default=FLAT)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    res = find(a.image, a.max_y, a.min_w, a.cell, a.flat)
    if not res:
        sys.exit("no empty region found — try --flat 10")
    if a.json:
        print(json.dumps(res, indent=2))
        return
    e = res["empty"]
    print(f'{res["image"]}  {res["size"][0]}x{res["size"][1]}'
          + (f'  (searched above y={res["searched_above_y"]})' if res["searched_above_y"] else ""))
    print(f'  largest empty box:  left {e["left"]} · top {e["top"]} · '
          f'{e["width"]}x{e["height"]}   (down to y={e["bottom"]})')
    pad = 40
    print(f'  place text at:      left:{e["left"] + pad}px; top:{e["top"] + pad}px;  '
          f'max width {e["width"] - 2 * pad}px')
    if "warning" in e:
        print(f'  ⚠ {e["warning"]}')


if __name__ == "__main__":
    main()
