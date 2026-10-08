# The look

One sentence: **the frame is a workspace that somebody built out of cut paper,
and it is being operated on while you watch.**

Everything below is a consequence of that. If a choice doesn't serve it, it isn't
vibecode.

---

## 1 · The ground

A flat saturated cobalt, `--vc-ground` `#226DE5`, with three things over it:

- a **radial lift** to `--vc-ground-lift` at 50% × 34% — the frame is brighter
  where the content sits;
- a **vignette** to `--vc-ground-deep` in the corners;
- a **halftone dot grid**, `--vc-dot` at `--vc-dot-gap` pitch, over the whole
  plate.

`.vc-frame` builds all three in `::before` / `::after`. Do not hand-roll it and
do not put a photo behind it — the ground is flat, always.

Two alternate grounds ship in `tokens.css` and are the **only** sanctioned
variation:

| Class | Ground | Use it for |
|---|---|---|
| *(none)* | cobalt `#226DE5` | the default — most of the runtime |
| `.vc-cream` | cream `#F7F1DD` | calm chapters, money/spec beats, the payoff |
| `.vc-dark` | `#19140A` | the "coming up" teaser and the CTA only |

**One ground per chapter.** Switching mid-chapter reads as a mistake; switching
at a chapter boundary reads as a new act, and that is a strong beat — give it a
transition and a sound.

## 2 · Paper is the only material

Every card, tile, panel, sticker and lozenge is cut from the same paper,
`--vc-paper` `#FEFEF5`. It has three non-negotiable properties:

1. **A torn edge.** `.vc-paper` clips a wobbly polygon. Straight-edged rectangles
   are the fastest way to make this look like a generic template.
2. **A hard offset shadow** — `--vc-shadow-card`, offset down-right with **zero
   blur**. A soft shadow makes it float; a hard one makes it *cut out*.
3. **A hand-placed tilt** — `--vc-tilt`, ~1.6°, and **never the same angle
   twice** in one frame. Alternate the sign, vary the magnitude.

Ruled surfaces (`.vc-paper-ruled`) add notebook rules in `--vc-rule`. The
timeline and any list live on ruled paper.

**Real assets get scissored.** A screenshot, app icon, repo card or logo goes
inside `.vc-sticker` — a white paper border, torn edge, hard shadow. A raw
un-cut rectangle dropped on the ground is not this style. REF-B's Premiere icon
at 11.2s is the canonical example.

## 3 · The fringe

Paper and display type carry a **chromatic misregistration** — magenta on the
leading edge, cyan on the trailing (`--vc-fringe-a` / `--vc-fringe-b`, applied
by `.vc-fringe`). It reads as cheap print, which is the point.

It is **off in `.vc-cream`** — REF-A has no fringe, and adding one there makes
the cream ground look broken rather than printed.

Use it on hero paper and display type. Fringing every element at once turns the
frame to mud.

## 4 · Red means no

`--vc-red` `#E54926` has exactly one job: **negation**. The X across a tile, the
strike through a line. That is all.

- Never fill a card red.
- Never colour type red.
- Never use it as a third accent because a frame needs more colour.

Its scarcity is what makes the negation land. Both references spend red this way
and nowhere else.

## 5 · The accents

| Token | Job |
|---|---|
| `--vc-yellow` `#FFDD36` | arrows, sparkles, the highlighted caption word, meter fill |
| `--vc-cyan` `#3DDEFE` | timeline track 1 |
| `--vc-pink` `#FF9EC0` | timeline track 2 |
| `--vc-blue` `#2F68E0` | timeline track 3 |
| `--vc-mascot` `#EE8A4E` | the agent character, and nothing else |

The three clip colours are **track identities**, not decoration. Keep a given
kind of work on its own colour for the whole video — if cuts are cyan in chapter
one they are cyan in chapter five.

## 6 · The agent character

Both references give the AI a body that is not a person: REF-B a pixel blob,
REF-A a wooden robot. vibecode keeps this. Build one designed mark — a small
pixel-grid creature in `--vc-mascot` — and reuse it for every beat where "the
agent did something".

This is also how the style satisfies the house rule about b-roll: **no random
humans.** The agent character fills the slot a stock cutaway would have.

## 7 · What this style is not

- Not glossy. No gradients on cards, no glass, no glow, no bevels.
- Not soft. Shadows are hard, edges are torn, motion is stepped.
- Not sparse. The frame carries two to four paper objects at a time and they
  change constantly — see `motion-grammar.md`.
- Not typeset. **Real media on every claim**, cut out with scissors. Text is for
  captions, labels and the one poster line per beat.
