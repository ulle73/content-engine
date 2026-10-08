#!/usr/bin/env python3
"""build-captions.py - turn a tightened transcript into ZAK phrase captions.

    python scripts/build-captions.py assets/transcript-tight.json \
        --out seg-01-cold-open/captions.html

Zak captions are PHRASES, not words. That is the single loudest difference from
persa, and reading persa's habits into this style is the most likely way to get
it wrong. Measured off the reference at 30fps over 53 changes in 39.9s:

  * 2 to 4 WORDS on screen at a time, as one nowrap line - "sunshine and
    rainbows", "up every single day", "for a job with". Never one word alone,
    never a wrapped two-line block.
  * It HARD-CUTS. The change lands entirely on one frame: the frames either
    side of every measured change moved by ~0.03% while the change frame moved
    by 70%. No fade, no scale, no pop, no blur.
  * Position is FIXED, horizontally centred inside the window, and it does not
    reflow for a long phrase - it re-chunks instead.
  * Holds averaged 22 frames (0.73s), floor 7 frames, ceiling 44 frames. That
    is ~80 changes per minute, and it is what makes the still frame feel alive.
  * White, bold, tight, and NO shadow of any kind.

Chunking follows the speech, not the clock: this splits on the pauses the
tighten pass left behind, then on clause words, and only then on length. A
chunk that would run past --hold-max is split even if it reads oddly; a chunk
under --hold-min is merged forward. The result is checked and reported.

Timing MUST come from transcript-tight.json. The tighten pass moves every word
onset - timing against the original transcript shows up as "the captions are
all slightly early", never as an error.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, html, json, pathlib, re, sys

FPS = 30
# words that make a natural chunk boundary when one is needed
BREAK_BEFORE = {"and", "but", "so", "because", "that", "when", "if", "then",
                "which", "or", "for", "to", "with", "like", "just", "what"}
# A caption must not END on one of these. "love a" / "you signed" are legal by
# every timing rule and still read as a mistake, because the eye finishes the
# line and the phrase has not. This is the difference between captions that
# look chunked and captions that look written.
NO_DANGLE = {"a", "an", "the", "of", "to", "for", "and", "or", "but", "so",
             "my", "your", "his", "her", "our", "their", "its",
             "in", "on", "at", "with", "from", "as", "than", "into", "about"}


# The reference captions carry NO punctuation - no full stops, no commas, no
# question marks. "sunshine and rainbows", not "sunshine and rainbows." The
# words are cued by the cut, so the punctuation has no work to do and reads as
# a subtitle track. Commas INSIDE a number (120,000) stay.
_PUNCT = ".,!?;:\u2026\u2014"

def clean(s):
    out = []
    for w in s.split():
        core = w.strip(_PUNCT)
        # keep a comma that sits between two digits
        core = re.sub(r"(?<!\d),(?!\d)", "", core)
        if core:
            out.append(core)
    return " ".join(out)


def load_words(path):
    """Accept the shapes tighten-cuts.py can emit; fail loudly on anything else."""
    d = json.loads(pathlib.Path(path).read_text())
    if isinstance(d, dict):
        for k in ("words", "segments", "result"):
            if k in d:
                d = d[k]
                break
    if not isinstance(d, list):
        sys.exit("could not find a word list in the transcript JSON")
    out = []
    for w in d:
        if not isinstance(w, dict):
            continue
        text = w.get("word") or w.get("text") or w.get("value")
        start = w.get("start", w.get("s", w.get("from")))
        end = w.get("end", w.get("e", w.get("to")))
        if text is None or start is None:
            continue
        text = str(text).strip()
        if not text:
            continue
        out.append({"t": text, "s": float(start),
                    "e": float(end) if end is not None else float(start) + .25})
    if not out:
        sys.exit("transcript parsed but no timed words found")
    return out


def chunk(words, lo, target, hi, gap, max_words, max_chars):
    """Greedy forward chunker. Boundaries come from speech first, clock second.

    `target` is what actually sets the feel: the reference held a caption for a
    mean of 22 frames, so a chunk that would run past ~22f is closed even when
    there is more room before the 44f ceiling. Chunking to the ceiling instead
    produces captions that are individually legal and collectively too slow.
    """
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        dur = cur[-1]["e"] - cur[0]["s"]
        chars = sum(len(c["t"]) + 1 for c in cur) - 1

        if nxt is None:
            chunks.append(cur); cur = []; break

        # A caption that ends one sentence and opens the next reads as a
        # mistake - the reference never does it. Sentence-final punctuation is
        # a harder boundary than any timing rule.
        ends_sentence = cur[-1]["t"].rstrip('"\u2019\'').endswith((".", "!", "?"))

        pause = nxt["s"] - w["e"]                       # silence the tighten left
        span_if_kept = nxt["e"] - cur[0]["s"]
        chars_if_kept = chars + 1 + len(nxt["t"])

        cut = False
        if ends_sentence:
            cut = True                                  # never cross a full stop
        elif len(cur) >= max_words or chars_if_kept > max_chars:
            cut = True                                  # hard limits
        elif span_if_kept > hi:
            cut = True                                  # would outrun the ceiling
        elif len(cur) >= 2 and span_if_kept > target:
            cut = True                                  # past the measured feel
        elif dur >= lo and pause >= gap:
            cut = True                                  # a real breath
        elif dur >= lo and len(cur) >= 2 and nxt["t"].lower().strip(",.?!") in BREAK_BEFORE:
            cut = True                                  # a clause turn
        if cut and not ends_sentence \
                and cur[-1]["t"].lower().strip(",.?!\u2019'\"") in NO_DANGLE \
                and len(cur) < max_words and chars_if_kept <= max_chars \
                and span_if_kept <= hi:
            cut = False                                 # do not end on a dangler
        if cut:
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)

    # Two clean-up passes, both fixing things that read as mistakes on screen.
    # 1 - anything under the floor is unreadable; fold it into a neighbour.
    # 2 - a LONE WORD is persa, not zak. Fold it in too, whichever side has room.
    def fits(a, b):
        if a[-1]["t"].rstrip('"\u2019\'').endswith((".", "!", "?")):
            return False                                # never merge across a full stop
        return (len(a) + len(b) <= max_words + 1
                and b[-1]["e"] - a[0]["s"] <= hi
                and sum(len(c["t"]) + 1 for c in a + b) - 1 <= max_chars + 4)

    for rule in ("floor", "lone"):
        out = []
        for c0 in chunks:
            c = list(c0)            # copy: extending a shared list duplicated words
            weak = ((c[-1]["e"] - c[0]["s"]) < lo) if rule == "floor" else (len(c) == 1)
            if weak and out and fits(out[-1], c):
                out[-1].extend(c)
            else:
                out.append(c)
        # a weak chunk at the very front has no predecessor - merge it forward
        if len(out) > 1:
            first = out[0]
            weak = ((first[-1]["e"] - first[0]["s"]) < lo) if rule == "floor" else (len(first) == 1)
            if weak and fits(first, out[1]):
                out[0] = first + out.pop(1)
        chunks = out
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--out", required=True)
    ap.add_argument("--offset", type=float, default=0.0,
                    help="subtract this from every time (segment start)")
    ap.add_argument("--hold-min", type=float, default=7 / FPS)
    ap.add_argument("--hold-target", type=float, default=None,
                    help="mean hold to aim for. Default: derived from THIS "
                         "transcript's speech rate at 3 words per caption.")
    ap.add_argument("--hold-max", type=float, default=None,
                    help="ceiling. Default: max(44f, 1.5x the derived target), "
                         "because 44f is the reference SPEAKER's rate, not a law.")
    ap.add_argument("--gap", type=float, default=0.12,
                    help="a pause this long or longer is a chunk boundary")
    ap.add_argument("--max-words", type=int, default=4)
    ap.add_argument("--max-chars", type=int, default=26)
    a = ap.parse_args()

    words = load_words(a.transcript)

    # The reference held a caption for a mean of 22 frames - but that is what
    # 2-4 words COSTS at that speaker's rate (~240 wpm). Forcing 22f onto a
    # slower speaker chops phrases in half; forcing it onto a faster one runs
    # them together. What is actually invariant is 2-4 words changing on a word
    # onset, so the target is derived from this transcript unless overridden.
    span = words[-1]["e"] - words[0]["s"]
    wps = len(words) / span if span > 0 else 3.0
    target = a.hold_target if a.hold_target is not None else 3.0 / wps
    target = min(max(target, a.hold_min * 2),
                 (a.hold_max * 0.75) if a.hold_max is not None else 1.6)
    print(f"  speech rate {wps*60:.0f} wpm -> hold target {target*FPS:.0f}f "
          f"({target:.2f}s)   [reference: 240 wpm, 22f]")

    hold_max = a.hold_max if a.hold_max is not None else max(44 / FPS, target * 1.5)
    if a.hold_max is None and hold_max > 44 / FPS:
        print(f"  ceiling relaxed to {hold_max*FPS:.0f}f "
              f"(44f is the reference speaker's rate, not a law)")

    chunks = chunk(words, a.hold_min, target, hold_max,
                   a.gap, a.max_words, a.max_chars)

    lines, holds = [], []
    for c in chunks:
        s = c[0]["s"] - a.offset
        e = c[-1]["e"] - a.offset
        if e <= 0:
            continue
        s = max(s, 0.0)
        f0, f1 = round(s * FPS), round(e * FPS)
        if f1 <= f0:
            f1 = f0 + 1
        holds.append(f1 - f0)
        txt = html.escape(clean(" ".join(w["t"] for w in c)))
        # data-in / data-out are frame indices: derive spans from frame numbers,
        # never from subtracted seconds.
        lines.append(f'  <div class="clip zk-caption" data-in="{f0}" data-out="{f1}">{txt}</div>')

    pathlib.Path(a.out).write_text(
        "<!-- built by scripts/build-captions.py - zak phrase captions.\n"
        "     These HARD-CUT. Do not add a transition, a tween or a text-shadow. -->\n"
        + "\n".join(lines) + "\n")

    n = len(holds)
    dur = (max(h for h in holds) if holds else 0)
    total = (chunks[-1][-1]["e"] - chunks[0][0]["s"]) if chunks else 1
    print(f"{a.out}: {n} captions over {total:.1f}s = {n/total*60:.0f}/min "
          f"(reference 80/min)")
    if holds:
        mean = sum(holds) / n
        print(f"  holds: mean {mean:.1f}f ({mean/FPS:.2f}s)  min {min(holds)}f  "
              f"max {max(holds)}f   (reference mean 22f, floor 7f, ceiling 44f)")
        over = [h for h in holds if h > hold_max * FPS + 0.5]
        under = [h for h in holds if h < 7]
        if over:
            print(f"  ! {len(over)} caption(s) hold longer than {hold_max*FPS:.0f}f - the frame goes dead. "
                  f"Split them or cover the beat with a window swap.")
        if under:
            print(f"  ! {len(under)} caption(s) under 7f - unreadable. Merge them.")
    lone = [" ".join(w["t"] for w in c) for c in chunks if len(c) == 1]
    if lone:
        print(f"  ! {len(lone)} one-word caption(s) - that is persa, not zak. "
              f"Merge them by hand: {', '.join(lone[:8])}"
              + (" ..." if len(lone) > 8 else ""))

    wc = [len(c) for c in chunks]
    if wc:
        print(f"  words per caption: mean {sum(wc)/len(wc):.1f}  "
              f"(reference 2-4; a 1-word caption is persa, not zak)")


if __name__ == "__main__":
    sys.exit(main())
