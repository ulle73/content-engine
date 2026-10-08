#!/usr/bin/env python
"""
Measure where the cutout rectangle's top edge should sit, from the RVM alpha itself.

"Half of my head" / "neck" / "shoulders" is a different pixel row in every recording,
so never hardcode it. This reads the matte silhouette and finds the anatomy:

  head top  = first row with any solid alpha
  neck      = the row where the silhouette suddenly widens (head -> shoulders)
  mid-head  = halfway between those two   <- NextPhase house default

Then prints the geometry to feed cutout-hook.sh, already satisfying the seam
invariant (RECT_Y - CROP_Y == PERSON_Y).

    python scripts/find-cut-line.py --frames frames_rvm --cut mid-head --person-y 112

Aspect-agnostic: it measures ROWS in the alpha, so it is the correct tool for 16:9
too. It is the ONLY correct source for the cut line - the geometry defaults in
cutout-hook.sh are proportional ports, not measurements.

If you scale the source (SRC_W/SRC_H), multiply the printed rows by the same factor:
these are measured on the UNSCALED matte frames.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, glob, os, sys

p = argparse.ArgumentParser()
p.add_argument("--frames", required=True, help="dir of BGRA frames from rvm-matte.py")
p.add_argument("--cut", default="mid-head", choices=["mid-head", "neck", "shoulders"])
p.add_argument("--person-y", type=int, default=112,
               help="PERSON_Y used in the composite. 16:9 default 112 (the 9:16 value 200 "
                    "scaled by 1080/1920). Must match what you pass to cutout-hook.sh.")
p.add_argument("--sample", type=int, default=15, help="frames to sample and average")
a = p.parse_args()

import cv2, numpy as np

files = sorted(glob.glob(os.path.join(a.frames, "*.png")))
if not files:
    sys.exit(f"find-cut-line: no frames in {a.frames}")
step = max(1, len(files) // a.sample)
picks = files[::step][: a.sample]

head_tops, necks = [], []
for f in picks:
    img = cv2.imread(f, cv2.IMREAD_UNCHANGED)
    if img is None or img.shape[2] < 4:
        continue
    alpha = img[:, :, 3]
    widths = (alpha > 128).sum(axis=1)          # solid pixels per row
    solid = np.flatnonzero(widths > 8)
    if solid.size == 0:
        continue
    top = int(solid[0])
    head_tops.append(top)

    # Head width = median across the upper third of the silhouette.
    lo, hi = top, top + max(1, (len(widths) - top) // 3)
    band = widths[lo:hi]
    band = band[band > 0]
    if band.size == 0:
        continue
    head_w = float(np.median(band))
    # Neck = first row below the head where the body exceeds 1.6x the head width.
    below = np.flatnonzero(widths[top:] > head_w * 1.6)
    if below.size:
        necks.append(int(top + below[0]))

if not head_tops:
    sys.exit("find-cut-line: could not read any alpha — are these BGRA frames?")

head_top = int(np.median(head_tops))
neck = int(np.median(necks)) if necks else head_top + 600
mid_head = (head_top + neck) // 2

row = {"mid-head": mid_head, "neck": neck, "shoulders": neck + (neck - mid_head) // 2}[a.cut]

# The cut line is measured in SOURCE coords; the composite shifts the person down by
# PERSON_Y, so the rect edge lands PERSON_Y lower in the output.
rect_y = row + a.person_y
crop_y = row

print(f"measured over {len(picks)} frames")
print(f"  head top   y={head_top}")
print(f"  mid-head   y={mid_head}   <- house default")
print(f"  neck       y={neck}")
print()
print(f"cut = {a.cut}  ->  source row y={row}")
print("feed these to cutout-hook.sh:")
print(f"  RECT_Y={rect_y} CROP_Y={crop_y} PERSON_Y={a.person_y}")
print(f"  (seam check: {rect_y} - {crop_y} = {rect_y-crop_y} == PERSON_Y ✓)")
