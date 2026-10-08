#!/usr/bin/env python3
"""
The density gate. Consistency you have to remember decays; this one fails the build.

Measured across 21 shipped videos: the cuts that feel alive hold their longest
"nothing changed" gap at 5.3-6.3s. The ones that feel dead (atlas 10.6, agent-skills 10.1,
and my first tp-0808 at 10.2) all sit above 10. Average graphics-per-minute is NOT the
signal — tp-0808 had the highest gfx/min in the whole corpus and still felt empty.

    python scripts/check-density.py videos/<slug>            # one video
    python scripts/check-density.py --all                    # back-test the corpus

RULES
  1. no gap > MAX_GAP between top-zone changes            (warn)  > HARD_GAP (fail)
  2. consecutive beats must differ in KIND                 (fail)
  3. nothing on screen longer than 6s without a change     (warn)

TIERLIST COUNTS TIMELINE MOTION, NOT data-starts (added 2026-09-05)
  Its cards never leave the board, so a card's data-start is only the moment it is
  PRESENTED — the flight into its slot and any re-rank are gsap calls with no markup of
  their own. Those instants are harvested from tierPresent/tierMove/tierDemote by call
  NAME. The spotlight is not counted: the spec calls it a state marker, and its times sit
  next to a place and a present anyway, so it would close every gap while changing nothing.

MOVING MEDIA RESETS THE CLOCK (added 2026-08-27, for the persa style)
  A gap is only dead if nothing on screen is MOVING. A <video> surface — a real screen
  recording, a demo, b-roll — keeps changing every frame, so a long hold on one is the
  persa "demo spine", not a hole. A still does NOT count: tp-0827's first cut held a
  static terminal PNG for 8.7s and that was correctly failed.

  So gaps spanned by a live <video> clip are excluded, and reported separately as holds.
  Pass --strict to score them as gaps anyway (the house rule).
"""
import json, re, sys, glob, os

MAX_GAP, HARD_GAP = 4.0, 6.0

# ⛔ YAPPING RUNS ON A DIFFERENT CLOCK, and the house numbers reject correct work.
# Its media cadence is a measured 5-10s (YAPPING.md §3) against a 6.0s hard fail, so every
# yapping cut ever shipped — _yapping, tp-0901b, tp-0901c, tp-0902 — trips this gate. The
# style earns it: with the caption changing 2.2x/second and the frame never holding still,
# the floor is never in doubt. Detected off `yap-cap` in the markup.
# ⚠ AND THE THRESHOLDS ARE CARRIED PER ROW, not read back off the globals in report() —
# reading the globals there is precisely the bug this exists to avoid, because the corpus
# run mixes styles and every row would be scored against whichever style ran last.
YAP_MAX, YAP_HARD = 10.0, 14.0

# ⛔ TIERLIST RUNS ON A DIFFERENT CLOCK TOO — and until 2026-09-05 it had no mode here at
# all, despite TIER-BOARD.md §12 and styles/tierlist.json both stating one was added on
# 2026-08-27. It was not: nothing in this file ever mentioned the style. tp-0827d scored a
# 14.2s "worst gap" and shipped anyway, which is the decay this script's own opening line
# is about. (Same shape as the yapping mode, which a memory also claimed was already here.)
#
# The style's beats are TIMELINE MOTION on clips that never leave, not new data-starts: a
# card's data-start is the frame it is PRESENTED, and everything after — the flight into its
# slot, a re-rank — is a gsap call. So the instants are harvested from the script below.
# Thresholds are the style's own stated cadence (TIER-BOARD §4: "one placement per 3-5s"),
# with the fail set where a board stops being a thing that changes and becomes a static
# scoreboard.
TIER_MAX, TIER_HARD = 5.0, 8.0

# The beat-carrying calls, and how many leading time arguments each one takes. Keyed by
# NAME rather than by argument position, and every nested call and options object is
# stripped before the numbers are read — a bare `tierSlot(2, 3)` inside a tierMove would
# otherwise be harvested as two beats at t=2 and t=3.
# ⚠ DO NOT read these off argument INDEX: changing a helper's arity then silently measures
# the wrong instants, which is exactly how this gate lied once before.
TIER_CALLS = {"tierPresent": 2,   # (tl, id, tPresent, tPlace, opts)
              "tierMove":    1,   # (tl, id, t, fromSlot, opts)
              "tierDemote":  1,   # (tl, id, t, toSlot, opts)
              }

def tier_beats(s, DUR):
    """present / place / re-rank instants, harvested by call NAME, not by position.

    The spotlight (tierSpot / spot) is deliberately NOT counted. TIER-BOARD §4 calls it a
    state marker and says outright that it does not fill a gap — and its on/off times sit
    0.46s after a place and 0.20s before the next present, so counting it would close every
    gap by construction while changing nothing on screen."""
    out = []
    for m in re.finditer(r'\b(' + "|".join(TIER_CALLS) + r')\s*\(', s):
        name = m.group(1)
        i, depth = m.end() - 1, 0
        for j in range(m.end() - 1, len(s)):          # find the matching close paren
            if s[j] == "(": depth += 1
            elif s[j] == ")":
                depth -= 1
                if depth == 0: i = j; break
        body = s[m.end():i]
        body = re.sub(r'\{[^{}]*\}', "", body)        # options object
        body = re.sub(r'\w+\s*\([^()]*\)', "", body)  # nested call, e.g. tierSlot(2, 3)
        nums = []
        for tok in body.split(","):
            tok = tok.strip()
            if re.fullmatch(r'-?\d+(?:\.\d+)?', tok):
                nums.append(float(tok))
        out += nums[:TIER_CALLS[name]]
    return [t for t in out if 0 <= t <= DUR]


def analyse(d):
    idx = os.path.join(d, "index.html")
    if not os.path.exists(idx): return None
    s = open(idx, encoding="utf-8").read()
    m = re.search(r'data-duration="([\d.]+)"', s)
    if not m: return None
    DUR = float(m.group(1))
    yap  = "yap-cap" in s
    tier = "tb-void" in s
    if yap:    mx, hard = YAP_MAX, YAP_HARD
    elif tier: mx, hard = TIER_MAX, TIER_HARD
    else:      mx, hard = MAX_GAP, HARD_GAP
    # Spans where a MOVING SURFACE is on screen. The camera does not count: it is present
    # in every frame of every cut, so if it qualified, every gap would be excused and the
    # gate would be worthless. Only a real screen recording / demo / b-roll resets the clock.
    CAMERA = re.compile(r'class="clip[^"]*\b(?:cam|cam-raw|cam-pop|cutout|camfree)\b')
    moving = []
    for mm in re.finditer(r'<video[^>]*>', s):
        tag = mm.group(0)
        if 'class="clip' not in tag or CAMERA.search(tag):
            continue
        if 'recording.mp4' in tag or 'person.webm' in tag or 'base.mp4' in tag:
            continue                                  # the camera by another name
        ms = re.search(r'data-start="([\d.]+)"', tag)     # not `d` — that is the directory
        md = re.search(r'data-duration="([\d.]+)"', tag)
        if ms and md:
            st = float(ms.group(1)); moving.append((st, st + float(md.group(1))))

    # A REGISTRY SUB-COMPOSITION MOUNT IS MOVING MEDIA TOO (added 2026-09-04, tp-0904).
    # The <video> scan above missed it because a mount is a <div data-composition-src=...>,
    # so an 8s thread-message-stack staggering its bubbles in read as an 8s hole. The
    # justification is identical to a screen recording's: the surface changes every frame.
    # A STILL still does not count, and the camera is still excluded.
    for mm in re.finditer(r'<div[^>]*data-composition-src=[^>]*>', s):
        tag = mm.group(0)
        if 'class="clip' not in tag or CAMERA.search(tag):
            continue
        ms = re.search(r'data-start="([\d.]+)"', tag)
        md = re.search(r'data-duration="([\d.]+)"', tag)
        if ms and md:
            st = float(ms.group(1)); moving.append((st, st + float(md.group(1))))

    starts = []
    for mm in re.finditer(r'<(?:div|span|video|img)[^>]*class="clip([^"]*)"[^>]*data-start="([\d.]+)"[^>]*>', s):
        cls, st, tag = mm.group(1), float(mm.group(2)), mm.group(0)
        if "cap" in cls: continue          # captions are not "something changing"
        starts.append(st)
        starts += [st + dl for dl in anim_delays(tag)]
    if tier:
        starts += tier_beats(s, DUR)
    starts = sorted(set(round(x, 2) for x in starts))
    if not starts: return dict(slug=os.path.basename(d), dur=DUR, n=0, worst=DUR, at=0.0,
                               gaps=[], mx=mx, hard=hard, yap=yap, tier=tier)
    pts = [0.0] + starts + [DUR]
    gaps = [(b - a, a) for a, b in zip(pts, pts[1:])]

    def covered(a, b):
        """is this whole gap spanned by one moving-media clip?"""
        return any(ms <= a + .05 and me >= b - .05 for ms, me in moving)

    strict = "--strict" in sys.argv
    holds = [] if strict else [g for g in gaps if g[0] > mx and covered(g[1], g[1] + g[0])]
    if holds:
        gaps = [g for g in gaps if g not in holds]
    worst, at = max(gaps) if gaps else (0.0, 0.0)
    return dict(slug=os.path.basename(d), dur=DUR, n=len(starts), worst=worst, at=at,
                gaps=[g for g in gaps if g[0] > mx], holds=holds,
                mx=mx, hard=hard, yap=yap, tier=tier)

# ── A CSS-DELAY CHILD IS A CHANGE TOO (added 2026-09-20, tp-0920b) ─────────────────────────
# persa builds a beat as ONE clip that owns a stack of children, each entering on its own
# `animation-delay` (reference/HOW-WE-EDIT.md's clipify: a child needs its own data-start, and
# that data-start is the GROUP's, with the timing carried in the delay). So every landing inside
# a beat shared one instant here and the gate saw a hole where eleven things land. It scored
# tp-0919c 12.1s, tp-0918c 6.5s and tp-0919b 5.4s — all three shipped, all three were wrong.
# The delay is read off the shorthand: `name .30s ease 2.06s both` -> the SECOND time is the
# delay. Easing parens are stripped first so cubic-bezier's numbers cannot be misread, and an
# `infinite` animation (a blinking caret) is not a change.
_EASE = re.compile(r"\([^)]*\)")
_TIME = re.compile(r"(-?[\d.]+)s")


def anim_delays(tag):
    m = re.search(r'style="([^"]*)"', tag)
    if not m:
        return []
    style = m.group(1)
    out = []
    for dm in re.finditer(r"animation-delay:\s*([^;\"]+)", style):
        for t in _TIME.findall(_EASE.sub("", dm.group(1))):
            if float(t) > 0:
                out.append(float(t))
    am = re.search(r"(?:^|;)\s*animation:\s*([^;]*)", style)
    if am:
        # strip the easing BEFORE splitting: cubic-bezier(.16,1,.3,1) carries commas of its own
        for part in _EASE.sub("", am.group(1)).split(","):
            if "infinite" in part:
                continue
            ts = _TIME.findall(part)
            if len(ts) >= 2 and float(ts[1]) > 0:
                out.append(float(ts[1]))
    return out


def report(r):
    mx, hard = r.get("mx", MAX_GAP), r.get("hard", HARD_GAP)
    flag = "FAIL" if r["worst"] > hard else ("warn" if r["worst"] > mx else "ok  ")
    print(f"  {flag}  {r['slug']:16s} {r['dur']:6.1f}s  {r['n']:3d} changes  "
          f"worst gap {r['worst']:5.1f}s @ {r['at']:5.1f}s  "
          f"({len(r['gaps'])} over {mx}s"
          f"{', yapping' if r.get('yap') else ''}{', tierlist' if r.get('tier') else ''})"
          + (f"  · {len(r['holds'])} moving-media hold(s): "
             + ", ".join(f"{g:.1f}s@{a:.1f}" for g, a in r["holds"]) if r.get("holds") else ""))
    return r["worst"] <= hard

if __name__ == "__main__":
    args = sys.argv[1:]
    dirs = sorted(glob.glob("videos/*")) if (not args or args[0] == "--all") else args
    print(f"density gate — house: max {MAX_GAP}s / fail {HARD_GAP}s  ·  "
          f"yapping: max {YAP_MAX}s / fail {YAP_HARD}s  ·  "
          f"tierlist: max {TIER_MAX}s / fail {TIER_HARD}s\n")
    ok = True
    rows = [x for x in (analyse(d) for d in dirs if os.path.isdir(d)) if x]
    for r in sorted(rows, key=lambda x: -x["worst"]):
        ok &= report(r)
    n_fail = sum(1 for r in rows if r["worst"] > r.get("hard", HARD_GAP))
    print(f"\n{len(rows)} videos · {n_fail} would fail · "
          f"{sum(1 for r in rows if r.get('mx', MAX_GAP) < r['worst'] <= r.get('hard', HARD_GAP))}"
          f" would warn")
    sys.exit(0 if ok or args[:1] == ["--all"] else 1)
