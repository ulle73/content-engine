#!/usr/bin/env python3
"""check-contrast.py - the zak-specific render gate.

The zak caption has NO shadow, NO stroke and NO box. That is measured, not an
oversight: in the reference, pixels 2-3px outside the glyphs were *brighter*
than pixels 8px out, so there is no halo whatsoever. White type sits straight
on the footage.

Which means the plate is the only thing making the caption readable, and a
bright plate kills it silently - the render succeeds, the frame looks fine in
a thumbnail, and the words are gone. In the reference the band behind the
caption held luma 126 (min 121, max 129) for every one of 120 sampled frames.
That stability is the style working.

This script measures that band per frame and tells you which spans fail.

  usage:  python check-contrast.py out/seg-01.mp4
          python check-contrast.py out/seg-01.mp4 --aspect 9x16
          python check-contrast.py out/seg-01.mp4 --fps 4 --max 150

Exit 0 = every frame readable.  Exit 1 = fix the plate before you ship.

Fix it at the plate, not the type. Adding a shadow to rescue a bright shot is
fixing the wrong layer and it stops being zak. Re-grade the shot, reframe onto
a darker part of it, or move the caption off that beat.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, subprocess, sys
import numpy as np

# Caption band as a fraction of the WINDOW, measured off the reference:
# glyph box y 994..1042 in a window spanning 476..1444, padded to +-6%.
BAND_LO, BAND_HI = 0.47, 0.65

# window geometry per aspect: (w_frac, h_frac, y_frac)
GEOM = {"16x9": (0.8958, 0.6778, 0.1611),
        "9x16": (0.8963, 0.5042, 0.2479)}


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True).stdout.strip()
    w, h = (int(v) for v in out.split("x")[:2])
    return w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--aspect", choices=sorted(GEOM), default=None,
                    help="default: inferred from the frame size")
    ap.add_argument("--fps", type=float, default=4.0, help="sampling rate")
    ap.add_argument("--cap-y", type=float, default=None,
                    help="caption centre as %% of FRAME height, when the scene "
                         "overrides --zk-cap-y (16:9 talking heads usually do — "
                         "see layouts.md 16:9). Default: the token position.")
    ap.add_argument("--max", type=float, default=150.0,
                    help="max mean luma behind the caption (token --zk-cap-band-max)")
    a = ap.parse_args()

    W, H = probe(a.video)

    # This measures a COMPOSED frame — it locates the window inside the frame
    # and reads the band behind the caption. Handed a bare plate (the output of
    # zak-plate.sh, 1720x732 or 968x968) it would look for a window inside a
    # window and report nonsense, so refuse rather than mislead.
    if (W, H) not in ((1920, 1080), (1080, 1920)):
        print(f"check-contrast: {W}x{H} is not a zak composition size.", file=sys.stderr)
        print("  Expected 1920x1080 or 1080x1920 — this runs on the RENDERED", file=sys.stderr)
        print("  segment, not on the plate from zak-plate.sh.", file=sys.stderr)
        return 2

    aspect = a.aspect or ("16x9" if W >= H else "9x16")
    wf, hf, yf = GEOM[aspect]

    win_w, win_h = int(W * wf), int(H * hf)
    win_x, win_y = (W - win_w) // 2, int(H * yf)
    if a.cap_y is not None:
        # band centred on the real caption, same height as the measured one
        band_h = max(2, int(win_h * (BAND_HI - BAND_LO)))
        band_y = int(H * a.cap_y / 100.0) - band_h // 2
        band_y = max(win_y, min(band_y, win_y + win_h - band_h))
    else:
        band_y = win_y + int(win_h * BAND_LO)
        band_h = max(2, int(win_h * (BAND_HI - BAND_LO)))

    # sample the band small; we want its brightness, not its detail
    sw, sh = 160, 24
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", a.video,
         "-vf", f"crop={win_w}:{band_h}:{win_x}:{band_y},"
                f"scale={sw}:{sh}:flags=area,fps={a.fps}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True).stdout
    n = len(raw) // (sw * sh)
    if n == 0:
        print("check-contrast: decoded nothing - is the path right?", file=sys.stderr)
        return 2
    f = np.frombuffer(raw, np.uint8)[:n * sw * sh].reshape(n, sh, sw).astype(np.float32)

    # The white caption is itself inside this crop. Take the 60th percentile so
    # the type does not drag its own background reading upward.
    lum = np.percentile(f.reshape(n, -1), 60, axis=1)

    print(f"check-contrast: {a.video}  {W}x{H} {aspect}")
    print(f"  window {win_w}x{win_h} at ({win_x},{win_y})   caption band y {band_y}..{band_y+band_h}")
    print(f"  plate luma behind caption: mean {lum.mean():5.1f}   "
          f"min {lum.min():5.1f}   max {lum.max():5.1f}   (reference 126, ceiling {a.max:.0f})")

    bad = np.where(lum > a.max)[0]
    if len(bad) == 0:
        print("\nclean - the caption reads on every sampled frame.")
        return 0

    # collapse to spans
    spans, s = [], bad[0]
    for i in range(1, len(bad)):
        if bad[i] != bad[i - 1] + 1:
            spans.append((s, bad[i - 1])); s = bad[i]
    spans.append((s, bad[-1]))

    print(f"\n  {len(bad)} of {n} sampled frames are too bright behind the caption:")
    for s0, s1 in spans:
        print(f"    {s0/a.fps:7.2f}s - {s1/a.fps:7.2f}s   peak luma {lum[s0:s1+1].max():.0f}")
    print("\ncheck-contrast FAILED. Fix the PLATE, not the type:")
    print("  - re-grade that shot darker (scripts/zak-plate.sh)")
    print("  - or reframe the window onto a darker part of the source")
    print("  - or move the caption off that beat")
    print("Do NOT add a text-shadow. That stops being zak.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
