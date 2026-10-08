# PERSA — the operative style doc

**One line:** the camera **is** the frame, and **the graphics change over a continuous take.**

Torn down frame by frame from two reference reels (67.7s and 38.8s, 720×1280/30), then
shipped on 30+ cuts. Everything below is measured. Machine-readable version:
`styles/persa.json`.

---

## 1 · The precondition — check it before you build

**The video needs a real product demo worth 15s+ of screen time.** Persa holds ONE treatment
for long stretches, so the *content* has to carry the clock. Without a demo, persa is a static
face with captions. If the recording fails this, say so in one line before building.

**And it wants a WIDE recording.** The reference head fills ~10% of frame height. A tight take
(head ~26%) puts the card's top edge at the chin and the fixed caption on the collar. That is a
production fix — sit further back — not an editing one. Never move the caption line to
compensate.

---

## 2 · The demo spine — the move that defines the style

Put a real product UI on screen and **leave it there for ~18 seconds.**

| | demo spine | share of the video | camera cuts inside it |
|---|---|---|---|
| reel A | 14.0 → 32.2s — the agent chat | 27% | 0 |
| reel B | 6 → 24s — the plugin panel | **46%** | 1 |

Reel B's whole structure: 0–5s hook · **6–24s the UI owns the frame** · 25–28s face ·
28.5–32s the real GitHub repo · 33–38.8s face, annotation, CTA. Nearly half the video is one
product doing one thing. The clock runs on **treatment + content**: the frame is held but the
picture never stops changing (a cursor dragging, a result streaming in).

Cadence: reel A cuts every 4.0s, reel B every 7.8s — and reel B's camera does not cut at all
from 20.1s to the end. Panels appear and vanish over one take.

---

## 3 · The five treatments

| treatment | what's on screen |
|---|---|
| **full face** | the raw take, full bleed, captions + one display word |
| **UI owns the frame** | the app fills 1080×1920 (or the top 1143px band), camera drops to the card |
| **floating real window** | the real app window ~65% frame width in the top third over the LIVE take, *with* a drop shadow |
| **b-roll + one composited object** | real b-roll with the single real object being talked about, at the wrong scale |
| **handheld device** | a real phone in hand running the real app |

There is no "never two neighbours alike" rule and no max hold. The graphics change; the frame
does not have to.

---

## 4 · The camera card

When a real UI owns the frame the camera drops to a rounded card. Measured off reel B:

```
at 1080x1920 →  left 114 · top 1143 · width 861 · height 777 · radius 39
no border · no shadow · no label · camera scale ≥ 0.797 (it must FILL the card)
```

**His head is MATTED and pops out ABOVE the card's top edge, over the app.** A plain clipped
rect reads as a floating box — the pop-out is what connects him to the frame. Two layers from
one source at ONE position: the raw take clipped by the card, plus the alpha matte over it
unclipped. The UI layer carries a rounded-rect **hole** at the card (CSS `mask-image`, SVG
evenodd path) so nothing needs cropping.

**The card is solved per ACT.** Some takes cut their own framing (the creator leans in).
Probe for framing cuts before the beat map (frame-diff at 1–10 fps, peaks = cuts); the card rect
never moves, but the camera's offset inside it changes per act so the head lands in the same
band. Make act boundaries beat boundaries. Store it in `assets/geometry.json`
(`template/geometry.json` is a worked one).

**The head top is measured per BEAT, never per act** (`template/measure-head.py`: highest row
of solid alpha, five samples per beat, through that act's solve). An act average reports the
frames where he sits back and a display word lands in his cap.

The two head bands a graphic must clear:

| beat | his head starts at (on screen) |
|---|---|
| **ui** (card) | ≈ 1062 — the pop-out, *not* the card top at 1143 |
| **face** (1:1) | the measured head top, e.g. 375–575 |

---

## 5 · The caption — one line, one word, never moves

- Plain white all-caps geometric sans, tracking ≈.06em, soft shadow, **one word at a time**
  on its own transcript onset.
- Pinned at **y 1400 = 72.9% of the full frame**. It does not move for the card, for b-roll,
  for anything. In a card beat it lands inside the card, on his chest. One line the eye never
  re-finds.
- No box, no band, no highlight, no colour, no bounce. Dropped for the CTA.
- If 1400 lands on a bright collar and the white measures < 3:1, a tight dark **halo on the
  glyphs** is allowed. A band never is.

---

## 6 · The display type — half the style

Full spec: `TYPE-ROLES.md`. Built and rendered: `components/persa-captions/`.

The four core roles:
1. **Title stack** (hook + CTA) — dark translucent pill naming the product · the real SQUARE
   app mark (not the wordmark) · a white marker line · the payoff word in coral `#E12A2B`,
   FILLED, ~85% frame width. ONE stack: mark → marker line → payoff word, top to bottom.
2. **Emphasis outline** — heavy condensed caps, stroke only, no fill, soft glow. **White** for
   the neutral word, **amber** for the pain word. **Coral is never an outline.** One per 3–5s,
   only on the noun that carries the beat. ⚠ On a bright wall (luma > ~130) the hollow outline
   vanishes — use the filled coral word or solid white instead.
3. **Payoff word** — coral, filled.
4. **Annotation** — lime `#B9DA31` pixel/mono, **typed into the product's own empty space**
   (`scripts/find-empty-space.py <shot> --max-y 1143`). The space must be empty for the
   annotation's whole duration.

Plus nine more: name tag · marker line alone · pill label alone · lime reaction · pixel speech
bubble · stacked repetition · arced sentence (one SVG `<textPath>`, not per-character spans).

Size display words to WIDTH (`min(cap, box / (0.516 × len))` for Anton caps) and never set an
explicit size that overrides the fitter — it runs off both edges and no gate sees it.

---

## 7 · The asset rule — six literal mappings, zero taste

| he says… | on screen |
|---|---|
| a product name | its real mark / real UI, **on the word** (not 8s later) |
| a person or agent | one pixel actor, cast once, reused every time that name is spoken |
| an action in a product | the real screen recording of **that exact action**, readable |
| a place or object | the real object composited into real b-roll at the wrong scale |
| a claim | typed in lime into the product's own empty space |
| anything else | caption only — the face carries it (~40% of both reels) |

Where the moving media comes from, best first:
1. **The vendor's own film / announcement page** — it is the fact-check AND the b-roll.
   yt-dlp when their CDN 403s; the same film is often on their YouTube.
2. **The live product, recorded on the video clock** — drive the vendor's web tool frame by
   frame (Playwright, paused clock) so each result lands on the creator's word. Shoot the
   element at ~340 CSS px wide so the app goes into its own mobile layout and the type is big.
   A demo instance (`demo.<vendor>.com`) or their release build run locally beats marketing
   stills.
3. **Their page entrances, replayed** — `document.getAnimations()` paused and stepped per
   frame turns a one-shot hero animation into footage.
4. **A designed animation carrying their real copy** — when there is genuinely nothing moving.

Never: a page of text with a highlighter, a scrolling GitHub page, a YouTube demo with someone
else's webcam bubble, a landscape 1920×1080 film shrunk into a card (its type is unreadable —
use one column of it, or shoot narrower).

---

## 8 · The layer order — this IS the technique

```
raw camera (untouched)  →  mid layer: the UI (with the card hole) + display type
                        →  his matte at 1:1 (same YUV, alpha-merged — no RGB round trip)
                        →  fg layer: captions, lime claims, anything in front of him
```

DOM order paints, not `data-track-index`: emit the card and the cutout AFTER the surface they
sit on. The camera never goes through the browser (Chrome's decode tints it ~G+4 with identical
colour tags): mid and fg render as transparent `--format mov` layers and `template/composite.py`
lays them onto the untouched recording in ffmpeg.

---

## 9 · BLACKLIST rules persa suspends — deliberately

| rule | in persa |
|---|---|
| **#2b** media in a frame / with a drop shadow | suspended — the floating real window HAS a shadow. A card behind a page shot is still banned. |
| **#7** the same frame twice in a row | suspended — the 18s demo spine is one treatment held. |
| **#11** shrinking him | suspended — the card IS the treatment. |
| **#12** captions on his body | suspended — the caption sits at 72.9%, on his chest, always. |

Everything else applies, including **#4 no emojis** and **#9 do not redesign the CTA**.
The house-plate rules (#10 graph paper, the cream plate, the 4-frame rotation, the 3 caption
styles and 4 caption bands) do not exist in persa.

---

## 10 · The grade — optional, and never a darkening

`components/grade-persa.svg` is an SVG `feComponentTransfer` matched to the reference look
(warm highlights over cool, slightly green shadows, blue rolled off ~20%, a small black lift),
strength 0.75. Re-derive per recording:
`python scripts/make-grade-filter.py --derive assets/recording.mp4 --out components/grade-<slug>.svg`.

**Apply only if the creator asks for it.** Recent cuts shipped with **no grade** — the creator
grades their own footage and does not want the picture changed. If you use it: photographic
surfaces only (camera, b-roll), **never** a product UI or captured screen. And never a
vignette, scrim or darkening layer to rescue type — solve contrast on the type.

---

## 11 · The CTA

The old CTA, copied from `components/cta-old.html`, never re-typed: `COMMENT` + the keyword +
a real down-arrow with a head, in the top half; **the creator in the bottom half** (the camera
must actually be emitted for the CTA beat — a dropped camera loop leaves a card on empty
ground and every gate passes). Captions drop out for the CTA. Sound: `pop` on the chip.

---

## 12 · Sound — thin

See `sound-design.md` § PERSA. `swell` on every layout change · `riser` once, cresting on the
hook payoff · `camera-shutter` per syllable of a product name, once · `futuristic-click` 2–3
per video where a real UI does the thing · `pop` on the CTA. **Banned: ping, swoosh, confirm,
beep** — and a banned cue is not replaced; the beat lands silent on the type. Every cue sits
≥ 8 dB under the local voice peak, measured on silence (`template/verify-sfx.py`).
