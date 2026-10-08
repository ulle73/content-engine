# The PERSA scene vocabulary

Five layouts. That is the whole set — persa is a *narrow* style, and the variety
comes from the rate at which real media enters and leaves, not from inventing
new frames.

All geometry is a percentage of the frame, so the same numbers serve 9:16 and 16:9.
Measured values in the table are from the 1080×1920 reference.

---

## The five

### 1 · Clean Face
Graded plate, full frame. Word caption at 73%. Optionally an emphasis word at 25%
behind the head.

The rest beat, and **roughly 40% of the runtime**. Wall-to-wall media is the
amateur read; the reference returns to a clean face constantly and holds it for
6–10s at a stretch. The frame breathing is what makes the next panel land.

### 2 · Panel Over Face  ⭐ the signature
A media panel floats in the upper frame; the talking head stays full-frame behind
it; **the subject's matte is composited back on top**, so the head and shoulders
break the panel's bottom edge.

| | measured |
|---|---|
| Panel width | 929/1080 = **86%** (`--pa-panel-w`), inset ~73px each side |
| Panel top | **8%** (`--pa-panel-y`) |
| Radius | ~30px @1080w = **2.8%** (`--pa-radius`) |
| Edge | soft drop shadow, no stroke |
| Matte | subject on top, thin light rim (`--pa-rim`) |

Still: `stills/02-panel-over-face-matte.png`. The 3× crop
`stills/06-matte-edge-3x.png` shows the cap occluding the UI and the rim fringe.

### 3 · Media Full / Head Card
Inverted. The screen recording goes **full frame, punched in on the region that
matters**, and the talking head shrinks to a rounded card in the lower frame that
bleeds off the bottom edge.

| | measured |
|---|---|
| Card width | 854–888/1080 = **80%** (`--pa-card-w`) |
| Card top | **58–60%** (`--pa-card-y`) |
| Radius | 2.8%, **top corners only** — it runs off the bottom |
| Caption | still at 73% of the frame → lands on the chest inside the card |

Still: `stills/03-media-full-head-card.png`.

Use it when the screen content *is* the point and needs the whole frame. The
punch-in is mandatory: a full unzoomed 16:9 UI dropped into a 9:16 frame is
unreadable and reads as lazy.

### 4 · Split / Break the Box
Media in the top ~55%, head card below — and **the head breaks out through the
top edge of its own card**, overlapping the media above.

Still: `stills/04-split-break-the-box.png`.

The break is the whole point. A clean split with two boxes stacked is a different,
much worse style. If the framing does not let the head cross the seam, use scene 2.

### 5 · Hand-Note Beat
Clean face plus a hand-lettered line in `--pa-font-hand`, in `--pa-lime` for
approval ("free", "open source", "respect") or white for narration. Often set on
a **curved baseline that follows a real line in the shot** — a ceiling seam, a
desk edge, a doorframe.

That curve-matching is a real technique and it is worth the effort: text that
follows the room's geometry sits *in* the room. Straight text does not.

---

## ⭐ The rotation

**Never the same scene twice in a row. Never hold one past ~20s.** Every scene
change carries a transition **and** a sound.

But note what the reference actually does: it alternates hard between **1** and
**2/3/4** — clean face, media beat, clean face, media beat. Scene 5 is a spice,
used two or three times in a 40–70s reel. Two media scenes back to back happen
only when the second is a punch-in of the first.

---

## ⭐ Real media, not typeset text

Every beat that supports a point shows a **real resource**: a screen recording, a
real product UI, a docs page, a repo card, a real chat thread. The reference is
almost entirely screen recordings of the actual tool.

- **≥1 real media per 20s**, minimum 8 for a long-form cut.
- **Check every screenshot actually rendered content.** Login-walled and JS-heavy
  pages come back blank and ship as empty panels.
- **No random humans as b-roll.** Cut to a person only when that person *is* the
  subject of the line.
- **Never use emojis.** Build designed marks — a CSS glyph, a small SVG, a
  monogram. The reference's one "emoji-ish" mark is a drawn pointing hand, not an
  emoji.
- Sourced clips come back at 24/25/50/60fps or VFR. **Re-encode to 30fps CFR
  before they enter a composition**, then verify with `ffprobe`.

---

## 5 · The matte layer

Scenes 2 and 4, and every emphasis word, need the subject cut out.

Use the existing RVM pipeline — it is already installed, already validated, and
shared with the other two styles:

```bash
source library/.venv/Scripts/activate
python library/kits/nextphase/skills/nextphase-long-editing/scripts/rvm-matte.py \
    --src assets/plate.mp4 --out assets/matte --frames 300
```

Full detail: `library/kits/nextphase/skills/nextphase-long-editing/reference/cutout-compositing.md`. The
environment, the seam invariant and the flicker findings all carry over unchanged.

### ⚠ Keep the rim
Other styles treat the light fringe on the matte edge as a defect to erode away.
**Persa keeps it.** It is clearly visible in the reference at 3× and it is what
separates the subject from a busy screen recording behind them. `--pa-rim` makes
it deliberate and even instead of leaving it to the matter's luck.

What you still fix: *flicker*. A rim that crawls frame to frame is a bad matte,
not a style. That is what RVM's recurrent state is for — do not swap in a
per-frame matter.

---

## Safe zones

`--pa-safe-x` 6.5% · `--pa-safe-y` 4.5%. Nothing outside them, ever.

**Suspended for the subject only** — the person legitimately spans the frame,
because they *are* the frame. Graphics stay inside.

For 9:16 delivery also keep the bottom **12%** clear of anything that must be
read: platform UI sits there. The caption at 73% is safely clear.

---

## ⭐ 16:9 — the default for this studio

The style was **measured** in 9:16. The 16:9 rules below were **derived on real
16:9 footage** (a centred medium-close talking head, `videos/aug25-10k-website-sold`)
rather than by scaling the portrait numbers — because scaling them does not work,
and the three ways it fails are the useful part.

Put `class="pa-frame pa-16x9"` on the composition root. Six tokens change
(`assets/tokens.css` §16:9 explains each). What follows is what changes in the
scenes.

### 1 · The occlusion turns horizontal
In 9:16 the head is a column and cuts the **bottom** off a word. In 16:9 the
head sits in the middle of a wide frame and cuts through the word's **middle**,
leaving letters readable on both sides. That still reads correctly — it is what
the reference does with `PLUGIN` — but it only works if the word is wide enough.

- **Long words (8+ characters)** — run them nearly frame-wide, centred. The head
  takes the middle third; the outer thirds carry the read.
- **Short words** — a short word centred behind a centred head **disappears
  entirely**. Offset it (`--pa-emph-x`, around 68–72%) so the head clips one
  edge. `PROOF` centred is invisible; `PROOF` pushed right is a persa frame.

⚠ This is the single thing most likely to go wrong in a 16:9 persa edit, and it
fails silently — the word is *there*, it is just behind his face.

### 2 · The caption centres on the SUBJECT, not the frame
In 9:16 those are the same point, always, so the reference never has to state
it. The moment the speaker moves into a corner card, a frame-centred caption
strands itself in the middle of the media. Set `--pa-cap-x` to the card's centre
whenever the subject is off-centre. `--pa-cap-y` stays at 73%.

### 3 · Media uses the width — a row, not a stack
An 86%-wide panel above the speaker leaves nothing in a frame 1080 tall. In 16:9
scene 2 becomes a **row of three panels across the top** (each ~28% of frame
width, 16:9, `--pa-radius` corners, 26px gaps, top at 8%), with the head breaking
up into the middle one. Three real resources at once instead of one — which suits
a claim about a *category* of thing far better than a single screenshot does.

### The scene table in 16:9

| # | Scene | 16:9 form |
|---|---|---|
| 1 | Clean Face | unchanged |
| 2 | Panel Over Face | a **row of 3** panels across the top; head breaks the middle one |
| 3 | Media Full / Head Card | media full-frame; head card is a **corner card**, `--pa-card-w` 34%, `--pa-card-x` 60%, still bleeding off the bottom |
| 4 | Split | media left ~58%, head card right; head crosses the vertical seam |
| 5 | Hand-Note Beat | unchanged, but there is far more room — use the empty side of the frame |

### What does NOT change
The grade. The z-order. The zero-frame caption cut. `--pa-cap-y` at 73%. The
radius in absolute pixels. The whole motion table. The rotation rule. Every one
of those transfers untouched.
