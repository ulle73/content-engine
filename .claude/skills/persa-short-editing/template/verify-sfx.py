#!/usr/bin/env python3
"""Measure every cue on SILENCE, and report it against the local VOICE peak.

    python3 verify-sfx.py            # out/sfx-only.wav vs out/tp-0925b-audio.wav

WHY ON SILENCE. Two instruments lie here and both were believed once:
  · a delta against the visual-only render is invalid wherever the cue lands under a loud
    word (sfx-delta-is-invalid-in-silence);
  · a voice-NULLED mix does not cancel, because both sides are AAC — the control window
    reads -0.5 dB where it should read -90 (sfx-null-on-silence).
The cue sheet mixed onto digital silence is the only control that reads -90, so each cue's
measured peak can be checked against `gain x that sound's own source peak`.

TWO WINDOW TRAPS, both of which have cost a pass:
  · a cue with leading silence reads dead at ANY gain if the window opens at the cue time,
    so the window opens at cue + that sound's measured lead (sfx-measure-at-cue-plus-lead);
  · a window long enough to hold the sound is long enough to hold the NEXT one, so it runs
    to the next cue's onset, capped at 0.9s (sfx-measure-window-and-click).
"""
import json, pathlib, subprocess, sys

def _find_skill(start):
    """The skill lives in <repo>/.claude/skills/persa-short-editing; videos live in
    <repo>/work/persa-short/videos/<slug>/ (content-engine layout), so walk up to find it."""
    for p in [start.resolve(), *start.resolve().parents]:
        s = p / ".claude" / "skills" / "persa-short-editing"
        if s.exists():
            return s
    sys.exit(f"cannot find .claude/skills/persa-short-editing above {start}")

D = pathlib.Path(__file__).parent
SK = _find_skill(D)
LEAD = json.loads((SK / "sfx/leading-silence.json").read_text(encoding="utf-8"))
SFX = sys.argv[1] if len(sys.argv) > 1 else "out/sfx-only.wav"
MIX = sys.argv[2] if len(sys.argv) > 2 else "out/tp-0925b-audio.wav"


def vol(f, ss, t):
    # ⚠ NOT -v error: volumedetect prints its summary at INFO level, so -v error silently
    # returns nothing and every window reads the default.
    o = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{ss:.3f}", "-t", f"{t:.3f}", "-i", f,
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    g = {}
    for ln in o.splitlines():
        for k in ("mean_volume", "max_volume"):
            if k in ln:
                g[k] = float(ln.split(":")[1].replace("dB", "").strip())
    return g.get("mean_volume", -99), g.get("max_volume", -99)


cues = []
for ln in (D / "sfx-cues.txt").read_text(encoding="utf-8").splitlines():
    ln = ln.strip()
    if ln and not ln.startswith("#"):
        p = ln.split()
        cues.append((float(p[0]), p[1], float(p[2]) if len(p) > 2 else 0.12))
cues.sort()

ctl = vol(SFX, 18.0, 2.0)[1]
print(f"control window on the sfx-only track (18.0-20.0s, no cue): peak {ctl:.1f} dB "
      f"{'OK' if ctl < -60 else '<< BROKEN CONTROL'}\n")

import math
print(f"{'cue':>7}  {'sound':<18}{'gain':>6}{'win':>6}{'peak':>8}{'expect':>8}{'vs voice':>10}")
hot = []
for i, (t, s, g) in enumerate(cues):
    lead = LEAD.get(s, {}).get("lead", 0.0)
    src = LEAD.get(s, {}).get("peak", 0.0)
    nxt = cues[i + 1][0] if i + 1 < len(cues) else t + 1.0
    ss = t + lead
    w = max(0.10, min(nxt - ss, 0.9))
    pk = vol(SFX, ss, w)[1]
    exp = src + 20 * math.log10(g)
    vpk = vol(MIX, max(0, t - 0.4), 1.0)[1]
    print(f"{t:7.2f}  {s:<18}{g:6.3f}{w:6.2f}{pk:8.1f}{exp:8.1f}{vpk - pk:+10.1f}")
    if vpk - pk < 8:
        hot.append((t, s, vpk - pk))
print(f"\n{len(cues)} cues.  {len(hot)} sitting less than 8 dB under the local voice peak"
      f"{': ' + ', '.join(f'{t:.2f} {s} ({d:+.1f})' for t, s, d in hot) if hot else ''}")
