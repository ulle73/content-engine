# TYPE ROLES — the display type, torn down from the reference reels

**Added 2026-08-26**, from a frame-by-frame teardown of two @artzenmedia reels Jad sent
(the reference reels themselves are not included).

These are **display type**. They are not caption styles. There are still exactly **three**
caption styles — `c-par` · `c-ws` · `c-hl` — and BLACKLIST #15 still holds. Nothing here
replaces a caption; every treatment runs *alongside* the caption track.

**EXTENDED 2026-08-27 — there are THIRTEEN, not four.** Jad asked to see *all* the captions,
so every text treatment in both reels was catalogued and rebuilt, not just the four roles below.
The other nine are in `components/persa-captions/` (`build.py` → `out/captions.mp4`, 34s, check-clean):

| # | treatment | where he uses it |
|---|---|---|
| 1 | word caption | both reels, always on |
| 2 | emphasis outline — white | reel A 5.4 / 6.9 / 12.6 / 61.5s |
| 3 | emphasis outline — amber | reel A 7.0s, 62s — **the pain word** |
| 4 | **name tag** | reel A 18–31s — the 7-actor roll-call at 40% size |
| 5 | payoff word — coral, filled | hook and CTA |
| 6 | title stack (all four layers) | reel B 0–4.7s |
| 7 | **marker line** alone | inside the stack, and on its own |
| 8 | **pill label** alone | above the app mark |
| 9 | lime claim | reel B 24.4s |
| 10 | lime reaction | reel B 34.3s — **his has an emoji, ours never does** |
| 11 | **pixel speech bubble** | reel A 1–3s |
| 12 | **stacked repetition** | reel A 12–13s — "again and again and again" |
| 13 | **arced sentence** | reel A 8–10s |

Live proof: `components/type-roles-demo/` and `components/persa-captions/` — both `hyperframes check` clean and
rendered. Look at the render, never the snapshot.

---

## The one precondition

**Every role here needs a photographic ground and a dark one.**

His camera is full-bleed for the whole reel: one continuous photograph, and everything is
composited *into* it. Ours is a cream plate with the pop-out in the lower half, so on a
transparent or split beat there is no picture behind the top third — only cream — and the
outline word collapses into ordinary outlined type with a halo.

So: **roles 1, 2 and 3 belong on FULL FACE and B-ROLL FULL beats only.** Role 4 belongs
wherever a real UI owns the frame.

And his room is shadowed at the top; ours is a lit white wall. Add the vignette:

```css
/* on the MEDIA, under every graphic. BLACKLIST #3 bans a band behind text and explicitly
   allows darkening the media instead — this is that, not a band. */
.vig{position:absolute;left:0;top:0;width:1080px;height:1080px;
  background:linear-gradient(180deg,rgba(12,9,8,.60) 0%,rgba(12,9,8,.40) 46%,rgba(12,9,8,0) 100%)}
```

Without it the coral payoff word measures **1.2:1** against our wall and is unreadable.
This was found by rendering, not by reasoning — the first cut of the preview had no
vignette and the coral word disappeared.

---

## ROLE 1 · TITLE STACK — hook and CTA only

Four layers over the **live take**. Never on a plate, never in a card, never a typeset
title card (BLACKLIST #2).

```
  pill        the real product name + version, dark translucent capsule, 38px Inter
  mark        the product's SQUARE app mark, ~212px — NOT its wordmark
  marker      one handwritten line, 64px, white, ALL CAPS, must not wrap
  payoff      the coral word, FILLED, ~208–290px Anton
```

The mark is the **square app mark**, not the wordmark. A wordmark is type, and stacking type
on type is the exact thing this role exists to avoid. `claude-coral.svg` and
`si-github.svg` are right; `claude-code-wordmark-alpha.png` is not — it was tried in the
first preview and read as a second line of type.

This does not replace [[hook-names-the-product]] — it is *how* that rule gets executed. The
wordmark still goes up on the word, inside 3s; the stack is the frame it goes up in.

```css
.tstack{position:absolute;left:0;top:86px;width:1080px;
  display:flex;flex-direction:column;align-items:center;gap:16px}
.tpill{font:400 38px var(--font-ui);color:#fff;background:rgba(15,12,10,.5);
  padding:11px 32px;border-radius:var(--r-pill);letter-spacing:.01em}
.tmark{width:212px;height:212px;object-fit:contain;
  filter:drop-shadow(0 10px 26px rgba(0,0,0,.5))}
.tline{font-family:var(--font-marker);font-size:64px;color:#fff;letter-spacing:.02em;
  text-transform:uppercase;white-space:nowrap;
  filter:drop-shadow(0 5px 16px rgba(0,0,0,.6))}
```

The stack runs 86 → ~660px and will slightly overlap the top of his head. **That is correct** —
his own payoff word touches his cap. Do not shrink it to avoid the overlap.

---

## ROLE 2 · EMPHASIS OUTLINE — the "gradient" word

This is what Jad meant by "the gradient look". **It is not a gradient.**

The word is **hollow** — a whisper of fill, a ~4px stroke, no more — plus a wide soft bloom
in the stroke's own hue, composited `mix-blend-mode:screen`. The room's light comes through
the counters and blooms around the stroke, so the letters take the *scene's* colour ramp.
That is the entire trick, and it is why it can never look pasted on.

```css
.emph{
  position:absolute;left:0;width:1080px;text-align:center;
  font-family:var(--font-display-heavy);line-height:1;letter-spacing:.012em;
  text-transform:uppercase;
  color:var(--emph-fill);-webkit-text-fill-color:var(--emph-fill);
  -webkit-text-stroke-width:var(--emph-stroke);
  mix-blend-mode:screen;
}
.e-w{-webkit-text-stroke-color:var(--emph-white);filter:var(--glow-white)}
.e-a{-webkit-text-stroke-color:var(--emph-amber);filter:var(--glow-amber)}
```

**WHITE and AMBER only.** Coral is never an outline — checked against every emphasis word in
both reels (`SO`, `TO`, `AGAIN`, `TIRED` white; `MANUALLY`, `HOUR` amber). Coral appears only
as the filled title/CTA word. A coral outline was built in the first preview pass, rendered,
and it read as weak pink mush against the wall.

| | |
|---|---|
| cap height | **≈11%** of frame height → `font-size:290px` in Anton at 1080×1920 |
| position | centred at **≈25%** down → `top:300px`. Above his head, never over it |
| cadence | one every **3–5s**, only on the noun that carries the beat |
| fill | `--emph-fill` = `rgba(255,255,255,.09)`. **Not** fully transparent — `hyperframes check` fails `text_not_painted` on a zero-alpha fill, and a whisper of screened fill is closer to his anyway |

**Stamp the font-size, never leave it implicit** ([[render-path-ignores-implicit-size]]):

```python
EMPH_MAX, EMPH_FIT = 290, 940          # px, and the width to fit inside 1080
def emph_size(word):                    # Anton advance ≈ .46em per uppercase char
    return min(EMPH_MAX, int(EMPH_FIT / (0.46 * len(word))))
# THEM → 290 · MANUALLY → 255 · EVERYTHING → 204
```

Entrance is a **180ms scale-in** (`--dur-pop`, `--ease-overshoot`) in a real build. The preview
uses hard cuts because it has no GSAP timeline.

---

## ROLE 3 · PAYOFF WORD — coral, filled

Hook and CTA only. `--display-coral: #E12A2B` — **sampled identically in both reels**, so it
is his fixed brand red, not a per-video choice. This is the one place a flat colour word is
allowed on our frames.

```css
.payoff{position:absolute;left:0;width:1080px;text-align:center;
  font-family:var(--font-display-heavy);line-height:.9;text-transform:uppercase;
  color:var(--display-coral);letter-spacing:.008em;
  filter:drop-shadow(0 8px 30px rgba(0,0,0,.55))}
```

Needs the vignette under it. Do **not** put it on a scrim or a band.

**It does not touch the CTA.** BLACKLIST #9 — the CTA is the old one from `buzz`, and it is
not being redesigned. Role 3 is available for the hook; the CTA stays as it is unless Jad
says otherwise.

---

## ROLE 4 · ANNOTATION — a claim, typed into the UI

Lime pixel type with a soft glow, placed in the **product's own empty space** — the black
gutter of a graph, the dead area of a panel — aligned to that UI's grid. No box, no card, no
callout line. It reads as a note written on the thing itself.

```css
.annot{position:absolute;font-family:var(--font-pixel);font-weight:700;
  color:var(--annot-lime);filter:var(--glow-lime);line-height:1.45;letter-spacing:.02em;
  white-space:pre}
```

~62px at 1080 wide. Used for price and licence claims. His pairs a reaction version with a
real emoji — **we drop the emoji** (BLACKLIST #4); build a designed mark if a reaction beat
ever needs one.

This is the *only* new text that is allowed to sit on media, and it is allowed because it is
inside the media's own negative space rather than over its content.

---

## What was NOT adopted, and why

**The 73% caption line.** His caption sits at 73% of frame height in *every* treatment and
never moves, so the eye never re-finds it. We already sit at `top:1400` on full-face beats —
**1400/1920 = 72.9%, the same line.** But on the pop-out and split layouts we use the 820/894
seam band, because BLACKLIST #12 bans captions on his body and over the media.

So the difference is not the position — it is that he holds **one** line across every
treatment and we move between four (820 · 894 · 1400 · 1620). Unifying that would mean
reopening #12. **Left alone; flagged for Jad.**

**His CTA.** BLACKLIST #9. Not touched.

**The emoji.** BLACKLIST #4. Dropped from role 4.

---

## Tokens

All of it lives in `tokens.css` — `--display-coral`, `--emph-white/-amber`, `--emph-fill`,
`--emph-stroke`, `--annot-lime`, the `--glow-*` filter lists, and
`--font-display-heavy` (Anton) · `--font-marker` (Permanent Marker) · `--font-pixel`
(Silkscreen). Never a raw hex or font in a build.

See `PERSA.md` for the style.

---

## The other nine — specs

**4 · NAME TAG.** The emphasis outline at **120px, ~40% of the emphasis word**, over the UI the
actor operates. Seven names in reel A across 13s: one graphic, a different actor and a different
word each time. This is how he gets density without inventing seven graphics.

**7 · MARKER LINE alone.** Permanent Marker, white, all caps, 64–78px. **Must never wrap** — the
first render ran off the frame at 78px. Keep the line short or drop the size; do not let it break.

**8 · PILL LABEL alone.** Inter 400 / 38px on `rgba(15,12,10,.5)`, pill radius. The one place
small type is allowed (BLACKLIST #1), because it is a *label on something*, not content. It is
also what makes a demo credible — "Adobe Premiere Pro 2026" under a real panel says the footage
is real.

**11 · PIXEL SPEECH BUBBLE.** A word spoken *by* an actor instead of printed over the frame. The
caption keeps running underneath — this is a second voice, not a replacement. **The bubble must be
drawn at the actor's resolution:** stepped, aliased edges, no anti-aliasing. A smooth vector bubble
next to a pixel character looks broken. Ours is an inline SVG with `shape-rendering="crispEdges"`
so the steps are real, with Silkscreen 700 in near-black on white.

**12 · STACKED REPETITION.** The same word cascading down and right, each copy on the beat —
**outline first, then solid** — running off the frame. Offset ~230px each. The one treatment here
that is genuinely a *picture* rather than type: thumb over the words and the frame still means
something, which is exactly the test BLACKLIST #14 sets for numbers.

**13 · ARCED SENTENCE.** A whole line bent onto a curve — sentence case, lowercase, the only
treatment that is neither caps nor one word. Inter 600 / 80px. Build it as a **single SVG
`<textPath>`**, never per-character spans: glyphs rotate smoothly instead of stepping, and it
stays one text node so the layout checker does not read every adjacent letter as an overlapping
block (it does, and it fails the gate). His runs off both frame edges; size to taste.

---

## Two build traps found by rendering these

1. **`font-size:%d px` emits invalid CSS.** One space between the number and `px` and the whole
   declaration is dropped — the word silently never paints. Two of the thirteen were blank frames
   because of it, and the composition still passed `hyperframes check`. Stamp sizes with no space.
2. **Per-character arced text fails the layout gate.** Every adjacent rotated glyph reads as an
   overlapping text block — 28 errors from one sentence. `<textPath>` is both the better build and
   the one that passes.

See `components/persa-captions/build.py` for all thirteen in one file.
