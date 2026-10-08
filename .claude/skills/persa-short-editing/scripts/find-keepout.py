#!/usr/bin/env python
"""
Measure the FACE KEEP-OUT for a yapping cut: how far down the frame a floating card may
reach before it starts covering him.

WHY THIS EXISTS. The first yapping build put its cards at a fixed top:640 — a number read
off her reels — and they landed square across his face. Her framing and ours are not the
same: she sits LOW with an empty top third, and our tripod takes put the head much higher.
"Where the head is" is a different pixel row in every recording, exactly like the matte cut
line, so it gets MEASURED, never hardcoded. See [[cutout-cut-line]] for the same lesson.

HOW. No matte and no face model needed. On a locked-off take the subject MOVES and the
background does not, so temporal variance over the centre columns finds him; the topmost
row carrying sustained variance is the top of the head. Verified against tp-0827d, where
it returned 804 and the drawn line sat exactly on the brim of his cap.

    python scripts/find-keepout.py videos/<slug>/assets/recording.mp4
    python scripts/find-keepout.py <recording> --card-aspect 1.78 --margin 28
"""
import argparse, subprocess, tempfile, os, glob, sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs numpy and pillow")

H, W = 1920, 1080

ap = argparse.ArgumentParser()
ap.add_argument("recording")
ap.add_argument("--margin", type=int, default=28,
                help="clear space between the card's bottom edge and the head top (px at 1920)")
ap.add_argument("--card-aspect", type=float, default=1.78,
                help="width/height of the card art, to size it into the free band")
ap.add_argument("--card-width", type=int, default=950)
ap.add_argument("--samples", type=int, default=60)
a = ap.parse_args()

tmp = tempfile.mkdtemp()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.recording,
                "-vf", f"fps=2,scale=270:480", "-frames:v", str(a.samples),
                os.path.join(tmp, "%04d.jpg")], check=True)
files = sorted(glob.glob(os.path.join(tmp, "*.jpg")))
if len(files) < 8:
    sys.exit("not enough frames sampled")

ims = np.stack([np.asarray(Image.open(f).convert("L")).astype(np.float32) for f in files])
V = ims.std(0)
band = V[:, 70:200]                    # centre columns — where a seated subject sits
row = band.mean(1)
thr = max(3.0, row.max() * 0.22)

head = None
for i in range(len(row)):
    if (row[i:i + 6] > thr).all():     # a sustained run, not one noisy row
        head = i
        break
if head is None:
    sys.exit("could not find the subject — is this a locked-off take?")

head_y = int(head / 480 * H)
max_bottom = head_y - a.margin
card_h = int(a.card_width / a.card_aspect)
card_top = max_bottom - card_h

print(f"\n  recording      {a.recording}")
print(f"  HEAD TOP       {head_y}  ({head_y / H * 100:.1f}% of frame height)")
print(f"  card may reach {max_bottom}  (head top - {a.margin} margin)")
print(f"  free band      0 .. {max_bottom}   =  {max_bottom}px of usable height\n")

if max_bottom < 300:
    print("  ⛔ NO ROOM. The head starts too high for a floating card to clear it.")
    print("     yapping wants a LOW, WIDE framing with an empty top third — she sits with")
    print("     her head around 40%+ of frame height. Options, in order of honesty:")
    print("       1  reshoot wider and lower (a production fix, not an editing one)")
    print("       2  use FULL-FRAME TAKEOVERS instead of floating cards for this cut")
    print("       3  build it as house, which owns the top zone by design")
    sys.exit(1)

if card_top < 0:
    fit_h = max_bottom - 20
    fit_w = int(fit_h * a.card_aspect)
    print(f"  ⚠ a {a.card_width}px-wide card is too TALL for the free band.")
    print(f"    Shrink it: width {fit_w} x height {fit_h}, top 20, bottom {max_bottom}.")
    print(f"    Or pair two smaller cards side by side — she does this repeatedly.\n")
else:
    print(f"  CARD BOX       left {(W - a.card_width)//2} · top {card_top} · "
          f"width {a.card_width} · height {card_h}")
    print(f"                 bottom lands at {max_bottom}, clear of the head\n")

print(f"  caption line   use .yap-cap-lo (baseline 1517) unless the card sits low")
