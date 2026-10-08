#!/bin/sh
# usage: tools/snap.sh <fmt: 9x16|4x5|1x1> <times comma> <name> [height]
cd "$(dirname "$0")/.." || exit 1
(cd film && ../../../library/.venv/Scripts/python.exe build_index.py >/dev/null)
case "$1" in 9x16) P=film;; 4x5) P=film-4x5;; 1x1) P=film-1x1;; esac
rm -rf scratch/snap-$3
(cd $P && npx hyperframes snapshot --at "$2" --no-end -o ../scratch/snap-$3 >/dev/null 2>&1)
../../library/.venv/Scripts/python.exe - "$3" "${4:-640}" <<'PY'
import sys, glob
from PIL import Image, ImageDraw
n, h = sys.argv[1], int(sys.argv[2])
fs = sorted(glob.glob(f"scratch/snap-{n}/frame-*.png"))
ims = [Image.open(f).convert("RGB") for f in fs]
row = [im.resize((int(im.width * h / im.height), h)) for im in ims]
W = sum(r.width for r in row) + 4 * len(row)
o = Image.new("RGB", (W, h + 20), "#111"); d = ImageDraw.Draw(o); x = 0
for f, r in zip(fs, row):
    o.paste(r, (x, 20)); d.text((x + 4, 4), f.split("-at-")[-1][:-4], fill="#eee"); x += r.width + 4
o.save(f"scratch/{n}.jpg", quality=85)
print(f"scratch/{n}.jpg", len(fs))
PY
