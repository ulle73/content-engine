# Captions

**Read this first. It is the core of the style, and it is the part most likely
to be built wrong out of habit from `persa`.**

---

## 1 · A phrase, not a word

Zak captions are **2 to 4 words** on one line: `sunshine and rainbows`,
`up every single day`, `for a job with`, `at a cost`.

This is the loudest single difference from `persa`, which puts **one** word on
screen. A one-word zak caption is not a stylistic variation; it is a different
style, and `scripts/check-zak.sh` fails the render for it.

Never two lines. Never a wrapping block. Never an accumulating line that adds
words as they are spoken. One line, replaced whole.

## 2 · No shadow. No stroke. No box.

Measured, not assumed. Sampling rings around the glyphs at 3× on a source
frame:

| Ring from the glyph edge | Mean luma |
|---|---|
| the glyph itself | 252 |
| 2–3px out | 86 |
| 7–9px out | 82 |
| 15–20px out | 87 |

If there were a halo, the 2–3px ring would be *darker* than the rings further
out. It is brighter. There is no shadow, no stroke, no blur, no plate, no pill.
White type sits directly on the footage.

**This is the single most fragile thing in the style, and the fix is never the
type.** The caption is readable only because the plate under it is dark — in
the reference that band held luma 126 across all 120 sampled frames, and never
went above 129. On a bright plate the words simply vanish, the render succeeds,
and nobody notices until it is published.

So: `python scripts/check-contrast.py` on every rendered segment. When it
fails, fix the **plate** — re-grade the shot, reframe the window onto a darker
part of it, or move the caption off that beat. Adding a `text-shadow` to
rescue a bright shot is fixing the wrong layer, and it stops being zak.

## 3 · No punctuation. None.

Every caption in the reference: `longest time` · `realized I'm human` ·
`good all the time` · `a job that I` · `passion is so deep` ·
`up every single day` · `sunshine and rainbows` · `at a cost`.

No full stops, no commas, no question marks, no ellipses. Not one, in 53
captions. The cut already does the punctuating — the phrase ends because the
next one replaces it — so a trailing full stop has no work to do and instantly
reads as a subtitle track rather than a designed caption.

Two things follow, and `scripts/build-captions.py` does both:
- **Strip it**, except a comma inside a number (`120,000` keeps its comma).
- **Never let a caption cross a full stop.** A caption that ends one sentence
  and opens the next (`people do. I miss`) is the same defect wearing a
  different hat: the eye finishes the line and the thought has not.

And case follows natural speech, not the ASR: it capitalises a word because it
thinks a sentence starts there, which inside a caption gives you `Right So`.
Lowercase any non-leading word that is not `I…` and not a name.

## 4 · It hard-cuts, and the cadence is the whole edit

XOR of the thresholded caption band between consecutive frames, across all
1198 frames of the reference:

```
  f101   delta =    99      the frame before
  f102   delta = 10894      the change
  f103   delta =   159      the frame after
```

Every one of the 53 changes looks like that. **Zero frames of transition.** No
fade, no scale, no pop, no blur, no slide, no stagger, no per-word reveal.
The next phrase simply replaces the one before it on its onset frame.

| | Frames @30fps | Seconds |
|---|---|---|
| Mean hold | 22 | 0.73 |
| Floor | 7 | 0.23 |
| Ceiling | 44 | 1.47 |
| Rate | — | 80 changes / minute |

⚠ **Those numbers are what 2–4 words COST at that speaker's rate (~240 wpm).**
They are not a metronome. Forcing 22 frames onto a slower speaker chops
phrases in half. `scripts/build-captions.py` derives the target from the
transcript's own rate and reports both, which is the right behaviour — what is
invariant is *2–4 words changing on a word onset*, not the clock.

What the cadence is FOR: nothing else in this frame moves. The camera is
locked, the window is locked, the title is set once. The caption changing
roughly three times a second is the only motion in the design, and it is
carrying the entire sense that the video is alive. Let it slow down and the
frame dies instantly.

## 5 · Position is fixed within a shot — but it is set against the SUBJECT

Within a shot it never moves: it does not track the speaker, does not reflow,
does not move for a long phrase, does not shift between scenes.

But **`--zk-cap-y` is a per-shot decision in 16:9, not an inherited constant.**
The token's 54.07% reproduces the reference, where the caption sits over the
speaker's *chest* — which works there because that creator sits far back in a
square frame and their head is only 28% of the window height. On a normal 16:9
talking head the head is 55-65% of the window, and the token position lands
**across the mouth**. There is usually no crop that recovers the reference
proportion; the source is not tall enough.

So: measure where the subject's collar is and put the caption below the chin,
on the shirt — which is also the darkest part of most plates and therefore the
best surface for unshadowed white type. On a real medium shot that landed at
**74%**. Set it once per shot on the composition root and leave it there.
`scripts/check-contrast.py --cap-y <pct>` measures the band you actually used.

A phrase too long for `--zk-cap-max` is **re-chunked, never shrunk and never
wrapped**. That is what `--max-chars` in the builder is for.

## 6 · Building them

```bash
python scripts/build-captions.py assets/transcript-tight.json \
    --out seg-01-cold-open/captions.html --offset <segment start>
```

It emits `data-in` / `data-out` **frame indices**, not seconds — derive spans
from frame numbers, never from subtracted seconds. It reports rate, hold
distribution and words-per-caption against the reference, and warns on holds
past the ceiling or under the floor.

⚠ Timing comes from `assets/transcript-tight.json` and nothing else. The
tighten pass moves every word onset; timing against the original transcript
shows up as "the captions are all slightly early", never as an error.
