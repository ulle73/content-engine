#!/usr/bin/env python3
"""
MAKE-GRADE-FILTER — the persa grade, as an SVG feComponentTransfer.

    python scripts/make-grade-filter.py --derive videos/<slug>/assets/recording.mp4
    python scripts/make-grade-filter.py                          # the stored default
    python scripts/make-grade-filter.py --strength 0.6 --out grade.svg

Jad asked for "a filter kind of the same thing that he has there, I think it's something like
an SVG feComponentTransfer filter". That is exactly the right instrument: `type="table"` is a
per-channel lookup table, i.e. a curve, and a curve per channel is a grade.

## Two wrong turns worth not repeating

**1 · Histogram matching is not a grade.** Matching our CDF to his produces a LUT that crushes
mid-grey from 128 to ~70 and flattens everything between 32 and 160. That is not his look, it is
**his room's exposure** — his room is dimmer than ours (mean luma 91 vs 143) and a CDF cannot
tell a grade from a lighting setup.

**2 · Percentile bins lie.** Dividing exposure out by binning pixels into luma *deciles* and
measuring channel ratios looks right, but our 20th-percentile pixel sits at luma 80 while his
sits at 59 — so the two are compared at different parts of the curve. The filter built that way
*increased* the shadow error: it lifted blue there, because his shadows are blue relative to his
own mids, while ours were already blue.

**What is correct: compare at MATCHED ABSOLUTE LUMA.** For each luma band, measure each channel
as a ratio to the luma of that band, in both sources; the correction is his ÷ ours. Then the
difference is unambiguous:

      luma      HIS R/G/B          OURS R/G/B         correction
      35-55   0.91 1.06 0.95     1.09 0.96 0.95      0.83 1.10 0.99
      55-80   0.97 1.04 0.86     1.22 0.93 0.80      0.79 1.13 1.08
      80-110  1.04 1.02 0.81     1.27 0.92 0.74      0.82 1.11 1.10
     145-180  1.04 1.02 0.82     1.03 1.00 0.93      1.00 1.02 0.88

Our low-mids run **red** (1.22-1.27) — the tungsten lamp in the room. His do not. So most of the
correction is pulling red down and green up through the shadows and low-mids, then rolling blue
off in the highlights, which is what gives his frames warm highlights over cool, slightly green
shadows.

## Therefore: DERIVE IT PER RECORDING

The correction depends on the lighting of the take it is applied to. The stored default was
derived from `tp-0821` and holds for that room. **Shoot in different light and re-derive** with
`--derive`; the reference profile below is his and never changes.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    sys.exit("needs Pillow:  pip install pillow")

# ── HIS profile. Measured 2026-08-27 from 19 face/room frames across both reels. ──────────
# luma band centre -> (R, G, B) as a ratio to that band's own luma. This is the TARGET and is
# fixed; only the source side is ever re-measured.
HIS = [
    (10,  0.836, 1.005, 1.403),
    (28,  0.919, 1.046, 0.977),
    (45,  0.906, 1.058, 0.947),
    (68,  0.969, 1.043, 0.861),
    (95,  1.039, 1.017, 0.811),
    (128, 1.067, 1.011, 0.770),
    (162, 1.038, 1.017, 0.815),
    (198, 1.029, 1.011, 0.869),
    (236, 1.007, 1.002, 0.969),
]

# ── the stored default correction, derived from tp-0821's raw take ────────────────────────
DEFAULT_CORRECTION = [
    (10,  0.928, 0.996, 1.157),
    (28,  0.986, 1.036, 0.866),
    (45,  0.833, 1.098, 0.992),
    (68,  0.792, 1.127, 1.080),
    (95,  0.821, 1.111, 1.098),
    (128, 0.910, 1.064, 0.954),
    (162, 1.005, 1.020, 0.877),
    (198, 1.017, 1.007, 0.914),
    (236, 1.006, 0.998, 0.998),
]

# ── VLOG profile. Measured 2026-08-31 from 19 frames of refs/ig/Db_ZiibRJtT.mp4. ─────────
# A different reference, not a different room: this is a NIGHT STREET, and the numbers say so.
# The crossover sits at luma ~35 and the two halves point opposite ways —
#     shadows  (L 9-28):  R 0.56-1.01   B 1.29-1.29   → hard TEAL
#     mids up  (L 43+):   R 1.22-1.33   B 0.46-0.75   → hard ORANGE
# That split IS the look. Do not "balance" it; balancing it is how you get a grey night.
# The 215-256 band never filled — his frames have no near-white at all, so the top of the
# curve is held at the 198 value rather than invented.
VLOG = [
    (10,  0.561, 1.167, 1.291),
    (28,  1.010, 0.958, 1.189),
    (45,  1.292, 0.900, 0.748),
    (68,  1.325, 0.908, 0.623),
    (95,  1.244, 0.940, 0.668),
    (128, 1.290, 0.918, 0.662),
    (162, 1.226, 0.941, 0.714),
    (198, 1.219, 0.993, 0.463),
    (236, 1.219, 0.993, 0.463),
]

PROFILES = {"persa": HIS, "vlog": VLOG}

# Per-profile defaults. persa corrects one lit room toward another lit room, so it can run hot.
# vlog pushes an INDOOR take toward a NIGHT STREET, which is a much longer distance — past ~0.6
# the skin goes orange and the wall goes blue and it reads as a broken white balance, not a
# grade. And vlog gets NO black lift: persa's 0.030 is the haze in his blacks, where this
# reference is genuinely crushed (darkest band mean luma 9.0).
PROFILE_DEFAULTS = {"persa": (0.75, 0.030), "vlog": (0.55, 0.000)}

EDGES = [0, 20, 35, 55, 80, 110, 145, 180, 215, 256]
BLACK_LIFT = 0.030   # his darkest band never reaches 0 — the haze in his blacks
N = 33               # feComponentTransfer table resolution


def profile(paths):
    """Channel/luma ratio per ABSOLUTE luma band. Bands, not percentiles — see the docstring."""
    acc = [[0.0, 0.0, 0.0, 0.0, 0] for _ in range(len(EDGES) - 1)]
    for f in paths:
        for r, g, b in Image.open(f).convert("RGB").getdata():
            L = 0.299 * r + 0.587 * g + 0.114 * b
            for i in range(len(EDGES) - 1):
                if EDGES[i] <= L < EDGES[i + 1]:
                    a = acc[i]
                    a[0] += L; a[1] += r; a[2] += g; a[3] += b; a[4] += 1
                    break
    out = {}
    for i, a in enumerate(acc):
        if a[4] < 500:                       # too few pixels in this band to trust
            continue
        L = a[0] / a[4]
        out[i] = (L, a[1] / a[4] / L, a[2] / a[4] / L, a[3] / a[4] / L)
    return out


def sample_frames(video, tmp, n=11):
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
        capture_output=True, text=True).stdout.strip())
    out = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        p = os.path.join(tmp, f"{k:03d}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video,
                        "-frames:v", "1", "-vf", "scale=270:-1", p], check=True)
        out.append(p)
    return out


def derive(video, target=None, verbose=True):
    tmp = tempfile.mkdtemp()
    try:
        ours = profile(sample_frames(video, tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    corr = []
    if verbose:
        print(f"# derived from {video}", file=sys.stderr)
        print(f"#      band     his R/G/B            ours R/G/B           correction",
              file=sys.stderr)
    for i, (lc, hr, hg, hb) in enumerate(target or HIS):
        if i not in ours:
            corr.append((lc, 1.0, 1.0, 1.0))
            continue
        _, orr, og, ob = ours[i]
        c = (lc, hr / orr, hg / og, hb / ob)
        corr.append(c)
        if verbose:
            print(f"# {EDGES[i]:4d}-{EDGES[i+1]:<5d}  {hr:6.3f} {hg:6.3f} {hb:6.3f}   "
                  f"{orr:6.3f} {og:6.3f} {ob:6.3f}    {c[1]:6.3f} {c[2]:6.3f} {c[3]:6.3f}",
                  file=sys.stderr)
    return corr


def lerp(table, v):
    if v <= table[0][0]:
        return table[0][1:]
    if v >= table[-1][0]:
        return table[-1][1:]
    for a, b in zip(table, table[1:]):
        if a[0] <= v <= b[0]:
            f = (v - a[0]) / (b[0] - a[0])
            return tuple(a[k] + (b[k] - a[k]) * f for k in (1, 2, 3))
    return table[-1][1:]


def tables(correction, strength=0.75, lift=BLACK_LIFT, clamp=0.30):
    out = {}
    for ci, c in enumerate("RGB"):
        vals = []
        for k in range(N):
            v = k * 255 / (N - 1)
            r = lerp(correction, v)[ci]
            r = min(1 + clamp, max(1 - clamp, r))      # no channel moves more than ±30%
            r = 1.0 + (r - 1.0) * strength
            y = v * r
            falloff = (1.0 - v / 255.0) ** 3           # the lift belongs at the bottom only;
            y += 255.0 * lift * strength * falloff     # a linear falloff milks the whole frame
            vals.append(round(min(255.0, max(0.0, y)) / 255, 4))
        for k in range(1, N):                          # keep it monotonic
            vals[k] = max(vals[k], vals[k - 1])
        out[c] = vals
    return out


SVG = """<!-- {P} grade — scripts/make-grade-filter.py --profile {P} --strength {S}
     Apply with  style="filter:url(#{P}-grade)"  on the camera AND on every b-roll clip,
     so every photographic surface in the cut sits on the same curve. -->
<svg class="grade-defs" width="0" height="0" aria-hidden="true"
     style="position:absolute;pointer-events:none">
  <filter id="{P}-grade" color-interpolation-filters="sRGB">
    <feComponentTransfer>
      <feFuncR type="table" tableValues="{R}"/>
      <feFuncG type="table" tableValues="{G}"/>
      <feFuncB type="table" tableValues="{B}"/>
    </feComponentTransfer>
  </filter>
</svg>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=sorted(PROFILES), default="persa",
                    help="which reference look to grade TOWARD. persa = his lit room (default). "
                         "vlog = the night street of refs/ig/Db_ZiibRJtT.mp4.")
    ap.add_argument("--derive", metavar="VIDEO",
                    help="re-derive the correction from this recording. DO THIS whenever the "
                         "lighting changes — the stored default is tuned to tp-0821's room. "
                         "REQUIRED for --profile vlog: there is no stored vlog default, because "
                         "the distance from an indoor take to a night street is all lighting.")
    ap.add_argument("--strength", type=float, default=None,
                    help="0 = untouched, 1 = the full measured correction. Defaults per profile "
                         "(persa 0.75, vlog 0.55); full strength reads sallow on warmer skin.")
    ap.add_argument("--lift", type=float, default=None)
    ap.add_argument("--out")
    a = ap.parse_args()

    d_strength, d_lift = PROFILE_DEFAULTS[a.profile]
    strength = d_strength if a.strength is None else a.strength
    lift = d_lift if a.lift is None else a.lift

    if a.derive:
        corr = derive(a.derive, target=PROFILES[a.profile])
    elif a.profile == "persa":
        corr = DEFAULT_CORRECTION
    else:
        sys.exit("--profile vlog has no stored default: pass --derive <recording>.")

    t = tables(corr, strength, lift)
    svg = SVG.format(P=a.profile, S=strength,
                     **{c: " ".join(f"{x:.4f}" for x in t[c]) for c in "RGB"})
    if a.out:
        open(a.out, "w", encoding="utf-8").write(svg + "\n")
        print(f"wrote {a.out}  (profile {a.profile}, strength {strength}, lift {lift})")
    else:
        print(svg)


if __name__ == "__main__":
    main()
