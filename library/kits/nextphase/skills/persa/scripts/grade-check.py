#!/usr/bin/env python3
"""
grade-check.py — measure a clip against the PERSA grade targets.

    python scripts/grade-check.py clip.mp4 [--frames 40]

The targets are the readings taken off the two reference reels (see
reference/grade.md). This does NOT tell you the shot is beautiful; it tells you
the shot is in the same colour space as the reference. Run it on:
  * every graded plate, before it enters a composition
  * out/final.mp4, before delivery

What it GATES on is the channel RELATIONSHIPS (G-R and B-R per luma band) plus
saturation, because those are the look and they hold across both reference reels.
Black and white points are reported but NOT gated: they swing with whatever is in
the shot (reel A read a 207 ceiling, reel B 252, on the same grade).
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, glob, os, shutil, subprocess, sys, tempfile

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs numpy + pillow:  pip install numpy pillow")

# ── Measured off the reference reels. The two reels are the same look at two
#    densities, so each target is their MIDPOINT and each tolerance is wide
#    enough to admit both. Raw per-reel readings: reference/grade.md §3.
#         reel A (hazier)          reel B (cleaner)
#    black  6/ 9/ 5                 0/ 0/ 0
#    white  207/191/168             243/227/224
#    mids   G-R -3.4  B-R -28.3     G-R +3.9  B-R -17.7
#    highs  G-R +4.8  B-R -24.9     G-R +5.1  B-R -17.3
TARGETS = {
    "black":  {"val": (3, 5, 3)},       # informational — see info() below
    "white":  {"val": (225, 209, 196)}, # informational — varies hugely by shot
    "shadow": {"gr": +1.6, "br":  -1.5, "tol": 6},
    "mid":    {"gr": +0.3, "br": -23.0, "tol": 10},
    "high":   {"gr": +5.0, "br": -21.0, "tol": 9},
    "sat":    {"val": 0.255,            "tol": 0.09},
}

def frames(src, n):
    d = tempfile.mkdtemp(prefix="persa-grade-")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps=1,scale=540:-1",
         "-frames:v", str(n), os.path.join(d, "%03d.png")],
        check=True)
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--frames", type=int, default=40)
    a = ap.parse_args()

    d = frames(a.clip, a.frames)
    fs = sorted(glob.glob(os.path.join(d, "*.png")))
    if not fs:
        sys.exit("no frames extracted")
    A = np.stack([np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) for f in fs])
    shutil.rmtree(d, ignore_errors=True)
    L = A.mean(axis=3)

    rows, fails = [], 0
    def check(label, got, want, tol, unit=""):
        """Gating reading — the channel relationships that ARE the look."""
        nonlocal fails
        ok = abs(got - want) <= tol
        if not ok:
            fails += 1
        rows.append(f"  {'ok ' if ok else 'OFF'}  {label:<22} {got:+8.1f}{unit}   target {want:+.1f} +/-{tol}")

    def info(label, got, want):
        """Informational only. Endpoints depend on whether a blown window or a
        specular is in the shot — reel A read 207/191/168 and reel B 252/247/247
        on the SAME look. Judge these by eye, do not gate on them."""
        rows.append(f"  --   {label:<22} {got:+8.1f}   reference {want:+.0f}")

    bp = [float(np.percentile(A[..., i], 1)) for i in range(3)]
    wp = [float(np.percentile(A[..., i], 99)) for i in range(3)]
    for i, ch in enumerate("RGB"):
        info(f"black point {ch}", bp[i], TARGETS["black"]["val"][i])
    for i, ch in enumerate("RGB"):
        info(f"white point {ch}", wp[i], TARGETS["white"]["val"][i])

    for lo, hi, key, label in [(0, 60, "shadow", "shadows"),
                               (60, 140, "mid", "mids"),
                               (140, 200, "high", "highlights")]:
        m = (L >= lo) & (L < hi)
        if m.sum() < 20000:
            rows.append(f"  --   {label:<22} (too few pixels to judge)")
            continue
        r, g, b = [float(A[..., i][m].mean()) for i in range(3)]
        check(f"{label} G-R", g - r, TARGETS[key]["gr"], TARGETS[key]["tol"])
        check(f"{label} B-R", b - r, TARGETS[key]["br"], TARGETS[key]["tol"])

    mx, mn = A.max(axis=3), A.min(axis=3)
    sat = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0).mean())
    check("mean saturation", sat, TARGETS["sat"]["val"], TARGETS["sat"]["tol"])

    print(f"\nPERSA grade check — {os.path.basename(a.clip)}  ({len(fs)} frames)")
    print("\n".join(rows))
    if fails:
        print(f"\n{fails} reading(s) outside tolerance.")
        print("The channel RELATIONSHIPS (G-R / B-R) are the look — fix those first.")
        print("B-R too high  -> blue is not pulled down enough; lower the b curve.")
        print("G-R too low   -> lift g at the 0.25 and 0.75 anchors.")
        print("sat too high  -> lower eq=saturation; the look sits near 0.26.")
        sys.exit(1)
    print("\nin the persa colour space.")

if __name__ == "__main__":
    main()
