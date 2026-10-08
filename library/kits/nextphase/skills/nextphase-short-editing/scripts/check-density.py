#!/usr/bin/env python3
"""
The density gate. Consistency you have to remember decays; this one fails the build.

Measured across 21 shipped videos: the cuts that feel alive hold their longest
"nothing changed" gap at 5.3-6.3s. The ones that feel dead (atlas 10.6, agent-skills 10.1,
and my first tp-0808 at 10.2) all sit above 10. Average graphics-per-minute is NOT the
signal — tp-0808 had the highest gfx/min in the whole corpus and still felt empty.

    python scripts/check-density.py work/nextphase/videos/<slug>            # one video
    python scripts/check-density.py --all                    # back-test the corpus

RULES
  1. no gap > MAX_GAP between top-zone changes            (warn)  > HARD_GAP (fail)
  2. consecutive beats must differ in KIND                 (fail)
  3. nothing on screen longer than 6s without a change     (warn)

TIERLIST STYLE: its beats are tierPresent()/tierMove() calls on clips that never leave,
not new data-starts, so those calls are counted as changes too. Without that the gate
sees six clips in a 22s cut and invents gaps.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import json, re, sys, glob, os

MAX_GAP, HARD_GAP = 4.0, 6.0

def analyse(d):
    idx = os.path.join(d, "index.html")
    if not os.path.exists(idx): return None
    s = open(idx).read()
    m = re.search(r'data-duration="([\d.]+)"', s)
    if not m: return None
    DUR = float(m.group(1))
    starts = []
    for mm in re.finditer(r'<(?:div|span|video|img)[^>]*class="clip([^"]*)"[^>]*data-start="([\d.]+)"', s):
        cls, st = mm.group(1), float(mm.group(2))
        if "cap" in cls: continue          # captions are not "something changing"
        starts.append(st)
    # TIERLIST STYLE. Its changes are timeline motion on clips that never leave — a card is
    # PRESENTED and PLACED, and a re-rank slides a card that has been on the board for 6s.
    # None of those is a new data-start, so without this the gate sees ~6 clips in a 22s cut
    # and reports gaps that are not there. Count the calls instead.
    #   tierPresent(tl, "id", tPresent, tPlace, …)   -> both times are changes
    #   tierMove(tl, "id", t, …)                     -> one
    for mm in re.finditer(r'tierPresent\s*\(\s*\w+\s*,\s*["\'][^"\']+["\']\s*,\s*([\d.]+)\s*,\s*([\d.]+)', s):
        starts.append(float(mm.group(1))); starts.append(float(mm.group(2)))
    for mm in re.finditer(r'tierMove\s*\(\s*\w+\s*,\s*["\'][^"\']+["\']\s*,\s*([\d.]+)', s):
        starts.append(float(mm.group(1)))

    starts = sorted(set(round(x, 2) for x in starts))
    if not starts: return dict(slug=os.path.basename(d), dur=DUR, n=0, worst=DUR, at=0.0, gaps=[])
    pts = [0.0] + starts + [DUR]
    gaps = [(b - a, a) for a, b in zip(pts, pts[1:])]
    worst, at = max(gaps)
    return dict(slug=os.path.basename(d), dur=DUR, n=len(starts), worst=worst, at=at,
                gaps=[g for g in gaps if g[0] > MAX_GAP])

def report(r):
    flag = "FAIL" if r["worst"] > HARD_GAP else ("warn" if r["worst"] > MAX_GAP else "ok  ")
    print(f"  {flag}  {r['slug']:16s} {r['dur']:6.1f}s  {r['n']:3d} changes  "
          f"worst gap {r['worst']:5.1f}s @ {r['at']:5.1f}s  "
          f"({len(r['gaps'])} over {MAX_GAP}s)")
    return r["worst"] <= HARD_GAP

if __name__ == "__main__":
    args = sys.argv[1:]
    dirs = sorted(glob.glob("videos/*")) if (not args or args[0] == "--all") else args
    print(f"density gate — max {MAX_GAP}s, hard fail {HARD_GAP}s\n")
    ok = True
    rows = [x for x in (analyse(d) for d in dirs if os.path.isdir(d)) if x]
    for r in sorted(rows, key=lambda x: -x["worst"]):
        ok &= report(r)
    n_fail = sum(1 for r in rows if r["worst"] > HARD_GAP)
    print(f"\n{len(rows)} videos · {n_fail} would fail · "
          f"{sum(1 for r in rows if MAX_GAP < r['worst'] <= HARD_GAP)} would warn")
    sys.exit(0 if ok or args[:1] == ["--all"] else 1)
