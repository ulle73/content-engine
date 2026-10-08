#!/usr/bin/env python3
"""Per-beat on-screen head top, measured off the RVM alpha — never off an act average.

`find-keepout.py` reports an ACT's MINIMUM head row, i.e. the frames where he happens to sit
back, and a display word placed against that figure runs into his cap on the beats where he
does not (take-cuts-its-own-framing). This takes the HIGHEST row of solid alpha per BEAT,
five samples each, and converts it through that beat's own camera solve.

    python3 measure-head.py            # after assets/alpha.mkv exists
"""
import json, pathlib, subprocess, sys
import numpy as np

D = pathlib.Path(__file__).parent
FPS = 30
ALPHA = D / "assets/alpha.mkv"
BEATS = json.load(open(D / "beats.json", encoding="utf-8")) if (D / "beats.json").exists() else None
GEO = json.loads((D / "assets/geometry.json").read_text(encoding="utf-8"))
ACTS = GEO["acts"]
CAMS = GEO["cam"]


def act_of(t):
    for s, e, k in ACTS:
        if s <= t < e:
            return k
    return ACTS[-1][2]


def head_src(t):
    """Highest row with >=24 solid-alpha pixels, in SOURCE coordinates."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(ALPHA),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    if len(raw) < 1080 * 1920:
        return None
    a = np.frombuffer(raw[:1080 * 1920], dtype=np.uint8).reshape(1920, 1080)
    rows = np.nonzero((a > 200).sum(axis=1) >= 24)[0]
    return int(rows[0]) if len(rows) else None


def main():
    if not ALPHA.exists():
        sys.exit("measure-head: assets/alpha.mkv not there yet")
    out, acts = {}, {}
    for i, (s, e, kind) in enumerate(BEATS):
        ts = [s + (e - s) * f for f in (.10, .30, .50, .70, .90)]
        hs = [h for h in (head_src(t) for t in ts) if h is not None]
        if not hs:
            continue
        k = act_of(s)
        src = int(min(hs))                     # the HIGHEST his head gets in this beat
        acts.setdefault(k, []).append(src)
        if kind in ("face", "full", "cta"):
            on = src                           # 1:1 — the camera is the frame
        else:
            c = CAMS[k]
            on = int(round(src * c["scale"] + c["top"]))
        out[str(i)] = on
        print(f"  {i:02d} {kind:5s} {s:6.2f}-{e:6.2f}  act {k:5s}  src {src:4d}  "
              f"on-screen {on:4d}   samples {hs}")
    g = json.loads((D / "assets/geometry.json").read_text(encoding="utf-8"))
    g["head_on_screen"] = out
    g["head_src_per_act"] = {k: {"min": min(v), "max": max(v)} for k, v in acts.items()}
    (D / "assets/geometry.json").write_text(json.dumps(g, indent=2), encoding="utf-8")
    print("\nwrote head_on_screen for", len(out), "beats")


if __name__ == "__main__":
    main()
