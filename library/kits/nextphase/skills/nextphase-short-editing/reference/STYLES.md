# STYLES — there are THREE now, and you pick one before anything else

**Added 2026-08-27.** Jad: *"we have our own edits that we do, and I wanna add another style
of editing too. So sometimes I can switch between the one that we're using right now and the
one that I just gave you."* And later the same day: *"i want you to add a 3rd style of editing
this is tierlist."*

So this is **not** a migration. `house` is still the default and nothing about it changes.
`persa` and `tierlist` are presets he can call for.

```
styles/house.json      the cream plate. The default. Everything before 2026-08-27.
styles/persa.json      full bleed. From the two reels at refs/ig/.
styles/tierlist.json   a tier board owning the top half. From one reference frame.
```

**Choosing is step 0 of the order of work, before transcribe — and you ASK, every time:**

> **"Which style — A (house, the cream plate), B (persa, full bleed) or C (tierlist, the board)?"**

Do not infer it from the recording and do not default silently. Jad asked for this in as many
words on 2026-08-27: *"sometimes whenever I give you a video, you're like, which version do you
want it? A or B? Or, like, old one or new one? And I choose, and then you do it on that style."*

The only time you skip the question is when he names the style himself in the same message he
drops the recording — *"the other style"*, *"the Instagram style"*, *"the full-bleed one"*,
*persa*, *"the tier list one"*, *"the ranking one"*, *tierlist*.

---

## ⛔ Two of the three have a PRECONDITION, and it can veto his choice

Say so before you start building, not after.

| style | precondition | if it fails |
|---|---|---|
| **house** | none — it works on any talking-head recording | — |
| **persa** | the video has a real product demo worth **15s+ of screen time** | use house |
| **tierlist** | the transcript actually **ranks named things** — 4 minimum, 6–8 ideally, one of them re-ranked | use house |

Both preconditions are about the same thing: `persa` and `tierlist` each hold ONE treatment for
the whole video, so the *content* has to carry the clock. Without the demo, persa is a static
face. Without the ranking, tierlist is an empty table.

---


## The one-line difference

| | |
|---|---|
| **house** | The camera is a matted pop-out on a **cream plate**, and **the frame changes every beat**. |
| **persa** | The camera **is** the frame, and **the graphics change over a continuous take**. |
| **tierlist** | **Nothing moves.** A tier board owns the top half and the camera owns the bottom half for the whole video, and the density is **cards landing on the beat**. |

Everything below follows from that.

---

## Side by side

| | house | persa | tierlist |
|---|---|---|---|
| Ground | flat `--cream` #F0EDE4 | none — the photograph is the ground | flat **black** `--tier-void` #0B0B0B, top half |
| Camera | matted pop-out, lower half, one framing all video | full bleed; drops to a card only when a real UI owns the frame | **hard bottom half**, 1080×936, uncut |
| Matte | **required** | **required** — but only for the card treatment (see below) | **none. The only style without one.** |
| Media | in the top zone, ON the plate, no frame or shadow | composited INTO the photograph, or owning the frame | there is no free media zone — the board *is* the top half |
| Frame changes | one every ~3.8s, never held past 8s | one every 4.0–7.8s, and one treatment **held 18s** through the demo | **zero.** Hook and CTA only. |
| Captions | 3 styles, 4 bands (820 · 894 · 1400 · 1620) | 1 style, **1 band, 1400, never moves** | 1 style, **1 band, 934, never moves**, white on black |
| Display type | none | 4 roles — see `TYPE-ROLES.md` | none |
| Grade | none | `feComponentTransfer`, strength .75 | none |
| Accent | `--coral` #D97757 | `--display-coral` #E12A2B + amber + lime | the **tiermaker default** row hues, unaltered |
| Density from | layout change + designed scenes + the registry | **real product surfaces + a recurring cast** | **cards landing on the beat**, one per 3–5s |

Measured: tp-0821 changes frame 17× in 64.9s. Reel A cuts 16× in 67.7s, reel B **4×** in 38.8s.
And reel B's camera does not cut at all between 20.1s and the end — panels appear and disappear
over one continuous take. We never do that.

---

## The demo spine — the move that defines persa

Both reels do the same structural thing: **put a real product UI on screen and leave it there
for ~18 seconds.** Measured, not eyeballed:

| | demo spine | share of the video | camera cuts inside it |
|---|---|---|---|
| reel A | 14.0 → 32.2s — the agent chat | **27%** | 0 |
| reel B | 6 → 24s — the Premiere panel | **46%** | 1 |

Reel B is the clearer case. Its whole structure is: 0–5s hook · **6–24s the UI owns the frame** ·
25–28s face · 28.5–32s the real GitHub repo · 33–38.8s face, annotation, CTA. Nearly half the
video is one product doing one thing.

House BLACKLIST #7 forbids this — never hold a treatment past ~8s. In persa it is the point.
The clock runs on **treatment + content**, and a live screen recording resets it: the frame is
static but the picture never stops changing, because a cursor is dragging a bezier handle the
whole time.

If the video has no real 15s+ demo to run, **persa is the wrong style for it.** Use house.

---

## The camera card — and the correction that cost a render

When a real UI owns the frame, the camera drops to a rounded card. Measured off reel B at 21.0s:

```
left 10.6%   width 79.7%   top 59.5%   radius 3.6% of width
at 1080x1920 →  left 114 · top 1143 · width 861 · height 777 · radius 39
no border · no shadow · no label
```

**His head is MATTED and pops out ABOVE the card's top edge, over the app chrome.** Verified at
16.4s, 19.0s and 23.5s. This was missed on the first pass and the card was built as a plain
clipped rect — it rendered as a floating rectangle with no connection to the frame.

It is **our own pop-out technique**, over a UI instead of over cream. Two layers from one source:

```html
<!-- the wrapper is UNTIMED. A <video data-start> nested inside a timed element renders FROZEN. -->
<div class="camcard">
  <video class="clip" src="assets/recording.mp4" data-start="..." data-media-start="..." ...>
</div>
<video class="clip camfree" src="assets/person-alpha.webm" data-start="..." ...>
```

Both layers share ONE position; the card's inner offsets are just the free layer's position
minus the card origin (114, 1143). The camera must be at least **0.797 scale** — it has to fill
the 861px card, or the app shows through inside it.

---

## ⚠ The production note — read this before promising the style

**Persa wants a wider recording than we shoot.**

| | |
|---|---|
| his head fills | **10.2%** of frame height |
| our head fills | **26.6%** of frame height |
| | our take is **2.6× tighter** |

To reproduce his card framing exactly, our camera would have to scale to **0.38** inside the
card and he would be tiny. At the 0.80 the card actually needs, the card's top edge lands near
his chin rather than mid-chest, and the fixed 72.9% caption sits on his collar rather than his
chest.

**Fix: sit further back when recording for this style.** It is a production change, not an
editing one — no amount of compositing recovers framing that was never shot. Until then, accept
the higher card edge and **do not move the caption line**, because one fixed line is the entire
point of the caption rule here.

---

## The grade

`persa` has one, `house` does not. It is an **SVG `feComponentTransfer`** — a per-channel
lookup table, which is a curve per channel, which is a grade.

```html
<!-- components/grade-persa.svg, dropped once at the top of <body> -->
<video class="clip cam" style="filter:url(#persa-grade)" ...>
```

**On the camera AND every b-roll clip**, so every photographic surface sits on one curve.
**Never on a product UI, page shot or captured device** — recolouring a real product's chrome
fabricates it (the same reasoning behind `brand-grade.json`'s `captured-device` class).

**His look, measured:** warm highlights over cool, slightly green shadows; blue rolled off ~20%
through the mids and highs; a small black lift, since his darkest band never reaches 0.

**Strength defaults to 0.75.** 1.00 is numerically closest to his profile — mean channel error
0.024 against 0.076 ungraded — but picks up a green cast in the shadows of skin, because his
profile is a different person in a different room. 0.75 still cuts the error to 0.036 and looked
best rendered side by side.

**Re-derive it when the lighting changes:**

```bash
python scripts/make-grade-filter.py --derive work/nextphase/videos/<slug>/assets/recording.mp4 \
       --out components/grade-<slug>.svg
```

This matters more than it sounds. **Most of the correction is removing OUR room's tungsten
cast** — our low-mids run R 1.22–1.27 where his run 0.97–1.04. That is lighting, not grade, so
the correction belongs to the take. The reference profile (his) is fixed and never re-measured.

Two wrong turns already made, so they do not get made again: **histogram matching ours→his
reproduces his room's EXPOSURE, not his grade** (it crushed mid-grey 128 to ~70 and flattened
everything from 32 to 160); and **binning by luma percentile compares different parts of the
curve** — our 20th percentile sits at luma 80, his at 59 — which made the shadow error *worse*.
Bin by absolute luma band and take his ÷ ours.

---

## The board — the move that defines tierlist

Full geometry and reasoning in **`TIER-BOARD.md`**; the component to copy is
`components/tier-board.html`. The short version:

```
   0 ─── --tier-void #0B0B0B ────────────────────────
  84 ─── S │ ▢ ▢ ▢          rows region, height 800
 244 ─── A │ ▢ ▢            rowH = 800 / N  (160 at N=5)
 404 ─── B │                label column 0→210, bleeds off the edge
 564 ─── C │                content column 210→1080, five cards max
 724 ─── D │                card 140×140 r18, pitch 150, first at 226
 884 ─── ONE WORD ─────────  caption band, 96px white, NEVER moves
 984 ═══ THE SEAM ═════════  hard edge, no feather
       the camera, 1080×936, uncut, NO MATTE
1920 ─────────────────────────────────────────────────
```

**The board is on screen from ~0:02 to the CTA and it arrives EMPTY, every row visible.** That
is the retention mechanic — the viewer counts the open slots and knows how much video is left.
Revealing rows one at a time throws it away.

**PRESENT, then PLACE.** On the word that names the product, the card appears at the **centre of
the board at 380px** and the rows dim. ~1.1s later, on the word that names the tier, it flies to
its slot and shrinks to 140. Presenting and placing in one motion is the mistake to avoid: the
card is only ever 140px, nobody sees what it is, and the beat reads as a logo twitching in the
corner of a table. **The pause between the two phases is the beat.** One placement per 3–5s, and
a card lands on a WORD, not on a round number.

**The re-rank is the payoff and no other style can make it.** A placed card slides to a different
row — *"…actually, no."* Write the script so at least one thing gets moved; it is the reason the
board earns being on screen the whole time instead of being revealed at the end.

**No matte.** This is the only style in the skill that never runs `rvm-matte.py`. In the
reference frame he sits well below the seam and his head does not break it. Do not add a pop-out
back "for polish" — a head crossing into the D row is the camera damaging the board.

**The two things the gates will not catch**, so check them on the rendered mp4: a **sixth card in
a row** runs off the right edge (`tierSlot()` will happily compute col 5), and the camera's
**`object-position`** — `50% 32%` is a starting value, not the answer, and a wrong one crops his
forehead off while every gate passes.

---

## Which BLACKLIST rules are house-only

This is the part that makes the two styles genuinely separate rather than a set of toggles.
Most of `BLACKLIST.md` is universal. **Four rules are house-style rules**, and the other two
styles suspend some of them deliberately:

| rule | in persa |
|---|---|
| **#2b** media in a frame / with a drop shadow | **suspended** — the floating-window treatment is a real app window *with* a drop shadow over the live take (reel A, 32–38s). Still banned: a card behind a page shot on a plate. |
| **#7** the same frame twice in a row | **suspended** — the 18s demo spine is one treatment held. |
| **#11** shrinking him | **suspended** — shrinking him to the card *is* the treatment. |
| **#12** captions on his body | **suspended** — the caption sits at 72.9%, on his chest, in every treatment, deliberately. |

And `tierlist` suspends **three of the same four** — but not the same three:

| rule | in tierlist |
|---|---|
| **#2b** media in a frame / with a drop shadow | **suspended FOR THE CARD ONLY** — a tier card *is* a white rounded plate with a shadow; that is the object being reproduced. A page shot on the board still gets no card behind it. |
| **#7** the same frame twice in a row | **suspended** — the frame never changes for the entire video. |
| **#11** shrinking him | **suspended** — a fixed 1080×936 bottom-half crop is the layout, not a shrink for a beat. |
| **#12** captions on his body | **IN FORCE.** The band sits on the black void between the last row and the seam — not on him, not over media. This is where tierlist and persa differ. |

Everything else still applies to all three, including **#9 (do not redesign the CTA)**,
**#4 (no emojis)** and **#1 (small text)** — #1 is why tierlist drops the tiny wordmark the
reference frame sets inside each card.

---

## What does NOT change

The order of work, the gates, `check-density.py`, the SFX pass, the transcribe-then-fact-check
opening, the sourcing rules, and the library step. Both styles run the same pipeline; they
differ in what gets built inside it.

**Live demo of persa:** `videos/_type-roles/` — check-clean, 26s, rendered to
`out/type-roles.mp4`. It shows all four type roles and the camera-card treatment with the
matted pop-out.

**Live demo of tierlist:** `videos/_tierlist/` — rendered to `out/tierlist.mp4`. Empty board,
four present-then-place beats, one re-rank.

See `TYPE-ROLES.md` for the display type and `refs/ig/` for the source reels; see
`TIER-BOARD.md` for the board geometry and `components/tier-board.html` for the component to
COPY (never re-type).
