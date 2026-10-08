# TIER-BOARD — the spec for the `tierlist` style

**Added 2026-08-27.** Jad sent one frame and said: *"i want you to add a 3rd style of editing this
is tierlist and i want it to look like this."*

One frame, not a torn-down reel — so the **geometry here is measured off it and scaled to
1080×1920, and the MOTION is ours**, because a still shows none. Everything marked *measured* came
off the frame; everything marked *our call* is a decision, and the reasoning is written down so it
can be argued with later.

Build it by **copying `components/tier-board.html`**. Do not re-type it. Re-typing the CTA arrow
instead of copying it is exactly how that drifted (`cta-arrow-is-copied`), and this board has more
measured numbers in it than the CTA does.

---

## 0 · The precondition — read this before agreeing to the style

**NO RANKING, NO BOARD.**

Read the transcript and list the things he **names and grades**. Fewer than four and the board sits
three-quarters empty for a minute — which is this format's own retention mechanic pointed the wrong
way round. The empty rows are supposed to say *there is more coming*; a board that stays empty says
*this is over*.

| | |
|---|---|
| minimum | **4** items placed |
| good | 6–8, and **at least one re-ranked** |
| fails the test | use `house`. Do not build a board and fill the rows with unranked b-roll. |

This is the same shape as persa's precondition (no 15s+ demo → wrong style). Each of the three
styles now has one, and they are the first thing to check at step 0.

---

## 1 · The layout

*Measured off the reference frame (862×1520 screen capture of a 9:16 video) and scaled ×1.253.*

```
 0     ┌────────────────────────────────────────────┐
       │              --tier-void  #0B0B0B          │
 84    ├──────────┬─────────────────────────────────┤   rows region, height 800
       │    S     │  ▢  ▢  ▢                        │   rowH = 800 / N
 244   ├──────────┼─────────────────────────────────┤   (160 at N=5)
       │    A     │  ▢  ▢                           │
 404   ├──────────┼─────────────────────────────────┤
       │    B     │                                 │
 564   ├──────────┼─────────────────────────────────┤
       │    C     │                                 │
 724   ├──────────┼─────────────────────────────────┤
       │    D     │                                 │
 884   ├──────────┴─────────────────────────────────┤   caption band, height 100
       │                  ONE  WORD                 │
 984   ╞════════════════════════════════════════════╡   THE SEAM — hard, no feather
       │                                            │
       │              the camera, uncut             │   1080 × 936, cover
       │                                            │
1920   └────────────────────────────────────────────┘
```

| | at 1080×1920 | |
|---|---|---|
| void | 0 → 984 | *measured* |
| rows region | 84 → 884 | *measured* |
| row height | 800 / N — **160** at N=5 | *derived* |
| label column | 0 → **210**, flush left, bleeds off the edge | *measured* |
| content column | 210 → 1080, width 870 | |
| card | **140 × 140**, radius 18 | *measured* |
| card pitch | **150** (10px gutter) | *measured* |
| first card left | **226** (210 + 16 pad) | *measured* |
| cards per row | **5 max** — 5 × 150 + 16 = 766 of 870 | *derived* |
| caption band | 884 → 984 | *measured* — the reference word centres at 934 |
| seam | **984** | *measured* |
| camera | 0, 984, 1080 × 936, `object-fit:cover` | *measured* |

**The rows region and the seam do not move when N changes.** Only `rowH` does. That is why those
two are the fixed numbers and why `tierSlot()` takes N — a six-row board (S A B C D F) still ends
at 884 with 133.33px rows.

**The label column bleeds off the left edge.** It is not inset and it has no left margin. An inset
chip reads as a card; this is a table.

---

## 2 · The palette — do not invent one

```
--tier-s #FF7F7F   --tier-a #FFBF7F   --tier-b #FFDF7F
--tier-c #FFFF7F   --tier-d #BFFF7F   --tier-e #7FFF7F   --tier-f #7FFFFF
--tier-void #0B0B0B   --tier-row #141414   --tier-rule #2E2E2E (2px)
--tier-label-ink #1A1A1A   --tier-card #FFFFFF
```

These are the **tiermaker defaults, unaltered**. A tier board is a recognised object — the viewer
knows what a tier list looks like before the first word lands, and that recognition is doing work.
Re-hue it to `--coral` and it stops being a tier list and starts being a chart.

**The ground is black, and that is the point.** Five saturated hues edge to edge plus white cards
need a dead ground. On cream the row colours go chalky and the cards disappear into the plate.
BLACKLIST **#10** fixes the *house* plate as flat cream; it does not claim cream is the only ground
in the skill — persa has no plate at all.

**Nothing goes behind the board.** No gradient, no grain, no vignette. Anything under five
saturated rows turns the whole top half to mud.

---

## 3 · The card

A **140px white plate**, radius 18, drop shadow, holding the product's **real square app mark** at
116px `object-fit:contain`.

**Not a wordmark.** A wordmark is type, and the caption is saying the product's name at that exact
moment — the same reasoning that keeps a wordmark out of TYPE-ROLES role 3. Square mark if one
exists.

**The escape hatch, and it is the only one:** a product with genuinely no square mark gets its
wordmark filling the card's full 116px inner width, which keeps cap height around 26px. If it
cannot reach that, **the product does not go on the board** — say the name in the caption and move
on.

**What we dropped from the reference, deliberately.** The frame sets a tiny letterspaced wordmark
*above* the mark inside each card. At 1080×1920 that is ~14px type — BLACKLIST **#1**, which bans
small text in any form, no exceptions for "it's just a label". We show the mark alone and let the
caption carry the name.

**⭐ A mark that carries its own opaque background FILLS the tile — give the card `bleed`.**
Found on tp-0827d: Codex, Fathom and Grok all ship as a dark rounded square, and inset at
116px on a white plate every one read as a **card inside a card** — which is what BLACKLIST
#2b is about. Full-bleed they read as app tiles, which is what a tier list is made of.
Test it rather than eyeballing it — if the four corner pixels are opaque, it bleeds:

```python
im = Image.open(f).convert('RGBA'); w,h = im.size
bleed = all(im.getpixel(p)[3] > 250 for p in [(2,2),(w-3,2),(2,h-3),(w-3,h-3)])
```

**Where the marks actually come from** (tp-0827d, 9 of them in one pass):
`https://cdn.simpleicons.org/<slug>` covers most of them and is vector. It does **not** have
OpenAI, Grok or Gamma, and its `fathom` is Fathom *Analytics*, not the meeting notetaker — check
you got the right product. For the rest: the vendor's own `apple-touch-icon` / `android-chrome-192`
(read the `<link rel="icon">` tags), or `https://www.google.com/s2/favicons?domain=<d>&sz=256`
when the site 403s curl, as gamma.app does. **OpenAI 403s everything** (`openai-com-sourcing`) and
publishes no separate square Codex mark — the official Codex VS Code extension icon is the
OpenAI blossom, and that is the closest real asset there is.

Every mark is a **real** asset fetched per `SOURCING.md`. A card you set in type is BLACKLIST #2.

---

## 4 · PRESENT, then PLACE — the signature move

*Our call. The reference is a still.*

```
   on the word that NAMES the product          ~1.1s later, on the TIER word
   ─────────────────────────────────           ────────────────────────────
   card appears at the CENTRE of the           it flies to its slot and shrinks
   board at 380px. The row CONTENT dims;       to 140. The rows come back. The
   the label chips stay lit.                   row's letter pulses once.
   0.30s, back.out(1.7)                        0.46s, power3.inOut
```

**Presenting and placing in one motion is the mistake.** The card is only ever 140px, nobody sees
what it is, and the beat reads as a logo twitching in a corner of a table. **The pause between the
two phases is the beat.** The first phase is *here is the thing*; the second is *and here is what I
think of it*. That is the whole rhetorical shape of a tier list video and it is worth 1.1 seconds.

```js
tierPresent(tl, "k_claude", 3.20, 4.30, {scrim:"tbscrim", label:"lab-s"});
```

Cadence: **one placement per 3–5s**, and a card lands on a **word**, not on a round number.

Every tween is a `fromTo` with an explicit from-state — `tl.to()` is not seek-safe and the render
path seeks (`HOW-WE-EDIT` §1).

---

## 5 · The re-rank — the move no other style can make

A card already on the board slides to a different row.

```js
tierMove(tl, "k_gem", 16.20, tierSlot(2,0), {label:"lab-a"});   // out of B col 0
```

A card's `style` left/top is its **final resting slot** — where it sits when the video ends — and
every motion is an offset back to that one home. So a card that gets re-ranked is *presented* with
`{slot: tierSlot(2,0)}` to land in B first, and `tierMove` just returns it home.

**Write the script so at least one thing gets moved.** *"…actually, no."* It is the payoff beat, it
is the reason the board is on screen the whole time rather than being revealed at the end, and it
is the one thing `house` and `persa` structurally cannot do.

Sound: `vinyl-rewind.mp3` on the lift, `pop.wav` on the land.

---

## 6 · The camera — no matte, for the first time

Hard bottom half: **full width, uncut, no card, no radius, no border, and no matte.**

**This is the only style in the skill that does not run `rvm-matte.py`.** In the reference frame he
sits well below the seam and his head does not break it. That is a real saving on every edit in
this style — do not add a pop-out back "for polish", because a head crossing the seam into the D
row is the board being damaged by the camera.

`object-fit:cover` on a 1080×936 box of a 1080×1920 source crops the middle. **Measure
`object-position` per take** — his eyeline wants the upper third of the 936px box, not the centre.
`50% 32%` is the starting value, not the answer.

One framing for the whole video, same as house.

---

## 7 · The caption

**One style (`c-ws`), one band (884–984), in white, and it never moves** — not for a present, not
for a move, not for the CTA. 96px type centred in the 100px gap.

It sits on the **void**: not on his body, not over media. So BLACKLIST **#12 stays in force here**,
which is the difference from persa — persa suspends #12 to pin the line on his chest, `tierlist`
does not need to because the black gap is already a clean band.

No fourth caption style is introduced. There are still three (BLACKLIST #15).

---

## 8 · No display type

TYPE-ROLES needs a **photographic and darkened** ground — that is its stated precondition, and it
is the thing that makes the hollow-outline word read as painted rather than pasted. A black board
with five saturated rows behind it is not photographic. An emphasis outline there is a sticker.

So: the board's own S/A/B letters are the only large type in the style, and there is no grade
either — persa's `feComponentTransfer` exists to put a full-bleed photographic frame on one curve,
and here the only photographic surface is the bottom half, with nothing to match it to.

---

## 9 · Sound — BLACKLIST #8 with full force

Every card motion is a layout change and **none of them is silent**.

**THREE SOUNDS, THREE JOBS.** The whole style is one motion repeated, so the parts of that motion
have to be separable by ear or the pass collapses into a single texture:

| beat | cue | firings | band |
|---|---|---|---|
| the board wipes in | `swell` | 1 | +2..+5 dB |
| the card **appears** at the centre | `futuristic-click` | 5 | +1..+3 dB |
| the **flight** from centre to slot | `swoosh` (cue − 0.246) | 5 | +1..+3 dB |
| the **land** in the slot | `pop` (place + 0.46) | 6 | +1..+3 dB |
| a land in **S** | + `confirm` (cue − 0.031) | 1 | +2..+5 dB |
| the **re-rank** | `vinyl-rewind` (cue − 0.053) on the lift, `pop` on the land | 1 | +2..+5 dB |

Note the two offsets that are easy to get wrong: **the flight cue is the PLACE time, not the
present time**, and **the land cue is place + 0.46**, the tween's own length. A pop on the launch
frame reads as the card being fired rather than arriving.

Gain is per **sound**, from the source-peak table in `sound-design.md` — `pop` at −4.7 needs more
than `swoosh` at −1.2 and `futuristic-click` at −0.1 needs less than either. The values in
`videos/_tierlist/sfx-cues.txt` (0.30 / 0.42 / 0.55 / 0.45 / 0.48 / 0.40) measure across a **3 dB
spread**, −6.4 to −9.4 dB.

`vinyl-rewind` was not in `sfx/leading-silence.json`; measured 2026-08-27 — **lead 0.053 s,
peak −0.9 dB**.

Measure each cue over **its own sound's length starting at cue + lead** — four sounds in the
palette have leading silence and read dead at any gain if you window from the cue time
(`sfx-measure-at-cue-plus-lead`, `sfx-measure-window-and-click`).

**`mix-sfx.sh` needs the input to already have an audio stream.** A graphics-only render has
none and the mix fails with `Stream specifier ':a' … matches no streams`. A real edit keeps the
camera's audio so this never comes up; if you are mixing onto a silent cut, give it one first:

```bash
ffmpeg -i out/<slug>.mp4 -f lavfi -i anullsrc=r=48000:cl=stereo \
       -c:v copy -c:a aac -shortest -y out/_<slug>-silent.mp4
```

---

## 10 · The arc

```
 0:00–0:02   HOOK      full-frame face or a title. The board is not up yet.
 0:02        WIPE IN   the board arrives EMPTY, all N rows visible. riser.
 0:02–end    BODY      present → place, present → place. One per 3–5s.
                       Somewhere past the halfway mark: the re-rank.
 last ~5s    CTA       the board is replaced by the old CTA panel in the top half.
                       THE CAMERA DOES NOT MOVE — he stays in the bottom half.
```

**The board arrives empty with every row visible.** That is the retention mechanic: the viewer can
count how many slots are still open and knows how much video is left. Revealing rows one at a time
throws it away.

**The CTA is half and half** (`cta-is-half-and-half`) and this style gets it for free — he is
already in the bottom half and stays exactly where he is. Do not redesign the CTA (BLACKLIST #9);
copy it from `components/cta-old.html`.

---

## 11 · What this style does not have

- no matte, no pop-out — **the only style without one**
- no rotation of camera treatment — the frame never changes
- no display type
- no grade
- no cream plate
- **no free media zone in the top half.** The board *is* the top half. A b-roll takeover mid-body
  throws away the board and the viewer loses the count.

---

## 12 · The gates

`hyperframes check` runs unchanged. **`check-density.py` was PATCHED for this style** on
2026-08-27: its beats are `tierPresent()` / `tierMove()` calls on clips that never leave, not new
`data-start`s, so without the patch the gate saw six clips in a 22s cut and reported a 5.8s gap
that was not there. It now counts those calls. A gate you have to remember to ignore decays —
which is that script's own opening line.

**Three failures the gates caught on the first build of this style, all of which passed by eye:**

1. **`head_leaked_text`.** A CSS comment containing the literal string `</style>` **terminates
   the style element** — the HTML parser does not know it is inside a comment. Everything after
   it leaked into the document as visible text. Never write that string inside a stylesheet.
2. **`text_occluded` + a 2.33:1 contrast failure on `#lab-s`.** The present-scrim covered the
   whole board including the label chips. It now starts at x=210 — the content column only. That
   is also the better design: the tier letters stay legible while the card is in the air.
3. **`gsap_timeline_set_initial_hide`.** The scrim's `opacity:0` cannot live in a
   `tl.set(..., 0)` — a zero-duration set at 0 does not render while the playhead sits exactly at
   0, so frame 0 painted the scrim at .62. It belongs in the CSS.

Two more the gates will **not** catch, so check them by eye on the **rendered mp4**, never a
snapshot:

1. **A sixth card in a row** overflows the 870px content column and runs off the right edge. The
   board caps at five per row and `tierSlot()` will happily compute col 5 for you.
2. **`object-position` on the camera.** A guessed `50% 32%` put tp-0821's head *halfway down*
   the box with 135px of ceiling above it, and every gate passed. Measure it:

   ```bash
   ffmpeg -ss 8 -i assets/recording.mp4 -frames:v 1 -y work/nextphase/tmp/f.png
   python -c "
   from PIL import Image; import numpy as np
   im=np.array(Image.open('work/nextphase/tmp/f.png').convert('L')).astype(float)
   d=(im[:,380:700]<90).sum(axis=1)
   head=next(y for y in range(im.shape[0]) if d[y]>40)
   print('head top', head, '-> objectY', round((head-110)/(1920-936)*100,1), '%')"
   ```

   `objectY = (headTopInSource − 110) / (1920 − 936)`, where 110 is how far below the box's top
   edge his head should sit. tp-0821: head top 723 → **62.3%**.

And the one that has bitten every style: `class="clip"` must come **first** in the class attribute
or `check-density.py` silently ignores the element and invents holes (`clip-class-must-come-first`).
