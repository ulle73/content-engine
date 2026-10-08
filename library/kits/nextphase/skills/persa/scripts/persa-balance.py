#!/usr/bin/env python3
"""
persa-balance.py — neutralise a plate so the persa curve lands on target.

    python scripts/persa-balance.py assets/recording.mp4              # print the filter
    python scripts/persa-balance.py assets/recording.mp4 --out assets/plate-bal.mp4

WHY THIS EXISTS
The persa curve in persa-grade.sh is calibrated against a NEUTRAL source: fed a
grey ramp it lands exactly on the measured reference anchors. Real footage is not
neutral, and its own cast rides straight through the curve — so a plate shot under
cool daylight comes out of persa-grade.sh still failing grade-check.py, and no
amount of nudging the persa curve fixes it without breaking the look for the next
video.

The fix is upstream, and it is mechanical: measure what the source's own cast is
per luma band, cancel it, then grade. This script does the measuring and writes
the cancelling curve.

Derived on a real 16:9 talking head (cool shadow fill, already-warm highlights).
Balancing first took it from 4 readings out of tolerance to a clean pass.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, glob, os, shutil, subprocess, sys, tempfile

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs numpy + pillow:  pip install numpy pillow")

BANDS = [(0, 60, "shadows"), (60, 140, "mids"), (140, 200, "highlights")]

def sample(src, n):
    d = tempfile.mkdtemp(prefix="persa-bal-")
    subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", "fps=2,scale=480:-1",
                    "-frames:v", str(n), os.path.join(d, "%03d.png")], check=True)
    fs = sorted(glob.glob(os.path.join(d, "*.png")))
    if not fs:
        shutil.rmtree(d, ignore_errors=True); sys.exit("no frames extracted")
    A = np.stack([np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) for f in fs])
    shutil.rmtree(d, ignore_errors=True)
    return A

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--out", help="write the balanced clip here (otherwise just print)")
    ap.add_argument("--frames", type=int, default=40)
    a = ap.parse_args()

    A = sample(a.clip, a.frames)
    L = A.mean(axis=3)

    print(f"\nsource cast — {os.path.basename(a.clip)}")
    pts = {"g": [(0.0, 0.0)], "b": [(0.0, 0.0)]}
    for lo, hi, label in BANDS:
        m = (L >= lo) & (L < hi)
        if m.sum() < 20000:
            print(f"  {label:11s} (too few pixels — skipped)")
            continue
        r, g, b = [float(A[..., i][m].mean()) for i in range(3)]
        lvl = float(L[m].mean())
        print(f"  {label:11s} level {lvl:5.1f}   G-R {g-r:+6.1f}   B-R {b-r:+6.1f}")
        # cancel the cast: at this input level, map each channel back onto red
        x = lvl / 255.0
        pts["g"].append((round(g / 255.0, 4), round(r / 255.0, 4)))
        pts["b"].append((round(b / 255.0, 4), round(r / 255.0, 4)))
    for k in pts:
        pts[k] = sorted(set(pts[k]))
        pts[k].append((1.0, 1.0))
        pts[k] = sorted(set(pts[k]))

    def fmt(k):
        return " ".join(f"{x}/{y}" for x, y in pts[k])
    vf = f"curves=g='{fmt('g')}':b='{fmt('b')}'"

    print("\nbalance filter:")
    print(f"  {vf}")
    print("\nthen grade and verify:")
    print("  bash scripts/persa-grade.sh <balanced> <plate> plate")
    print("  python scripts/grade-check.py <plate>")

    if a.out:
        print(f"\nwriting {a.out} ...")
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "warning", "-stats", "-i", a.clip,
                        "-vf", vf, "-r", "30", "-fps_mode", "cfr",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-c:a", "copy", a.out, "-y"], check=True)
        print("done. Now grade it with `plate` strength.")

if __name__ == "__main__":
    main()
