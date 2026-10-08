# Layouts — the seven scenes

16:9, 1920×1080 @30fps. Root carries `.vc-frame` (plus `.vc-cream` or
`.vc-dark` when the chapter calls for it).

**Safe zone:** inset `--vc-safe-x` 6% × `--vc-safe-y` 5%. Nothing readable
outside it. Paper may bleed past the edge — that is good — but a label or a
number may not.

## The rotation

**Never the same scene twice in a row. Never hold one past ~20s.** The layout
rotation is the retention mechanism and it outranks beat-by-beat taste.

But do not run wall-to-wall graphics either: REF-B returns to a plain talking
head for 8+ seconds at a stretch around 42–60s. Scene 1 is a rest beat and it
should be roughly a third of the runtime.

| # | Scene | For |
|---|---|---|
| 1 | **Clean Face** | the rest beat |
| 2 | **Paper Timeline** ⭐ | the signature — work being done |
| 3 | **Tile Row** ⭐ | three things, then crossed off |
| 4 | **Poster** | the chapter title / the one big claim |
| 5 | **Workspace** | a step list + a media card + the head |
| 6 | **Sticker Wall** | real media, several pieces, churning |
| 7 | **Agent Beat** | the mascot doing the thing |

Plus `.vc-dark` **Teaser** as an interstitial between chapters, and the CTA card
at the end.

---

## Scene 1 · Clean Face

Full-frame footage, nothing on it but the caption lozenge and — if the chapter
uses it — the scrub rail. This is where the viewer rests.

Hold 6–10s. Come back to it constantly.

## Scene 2 · Paper Timeline ⭐

The signature. A ruled paper card, roughly 62% frame width, centred or offset
left, carrying two or three tracks of clip blocks and a playhead.

```html
<div class="vc-paper vc-paper-ruled vc-fringe vc-timeline">
  <div class="vc-track">
    <span class="vc-clip t1" style="left:4%;  width:22%"></span>
    <span class="vc-clip t1" style="left:29%; width:15%"></span>
  </div>
  <div class="vc-track">
    <span class="vc-clip t2" style="left:12%; width:18%"></span>
  </div>
  <div class="vc-playhead" style="left:52%"></div>
</div>
```

Clips build left→right (`motion-grammar.md` §5). Track colours are identities —
keep a kind of work on its own colour for the whole video.

Pair it with the head as a `.vc-head` card in a corner, or run it full-frame for
a pure "the machine is working" beat.

## Scene 3 · Tile Row ⭐

Three white paper tiles across the middle, each with a **navy pictogram** and a
`.vc-label` beneath. Tiles tilt at three *different* angles.

Then — the payoff — a red X lands on each in turn (`motion-grammar.md` §3).

This is the "here's the old way / here's what you don't need any more" beat, and
it is the strongest single move in the style. Use it once or twice per video,
not more.

Pictograms are **built, never emoji**: a diamond with arrows, a half-filled
circle, a gear. Flat navy, `--vc-ink-line` stroke weight, no gradients.

## Scene 4 · Poster

Two lines of display type on the bare ground, the second 1.7–1.8× the first,
with a yellow hand-cut arrow pointing in from the left. Often a small paper
element beneath — a timeline strip, a chip.

Left-aligned at the safe edge or centred; pick one per video and keep it.

## Scene 5 · Workspace

REF-A's layout, rebuilt in paper. Eyebrow top-left, a `.vc-step` list down the
left at ~48% width, a media `.vc-panel` bottom-left, the head as a `.vc-head`
card upper-right at ~42% width. `.vc-rail` pinned to the bottom.

Rows arrive one at a time; the **active** row is `is-active` (filled yellow
number, yellow hairline). Exactly one row is active at a time, and it advances
with the VO.

## Scene 6 · Sticker Wall

Three to five real assets — screenshots, repo cards, docs pages, app icons —
each in a `.vc-sticker`, scattered at different tilts and depths, churning
(`motion-grammar.md` §1) as they land.

This is where the **real media** requirement gets paid. Every asset is a real
resource, checked that it actually rendered content.

## Scene 7 · Agent Beat

The mascot on the bare ground, doing one thing: arriving, growing a brain,
firing a rocket, pointing at a paper card with a hand-drawn arrow. Yellow
sparkles blink around it.

Short — 1.5–3s. It is punctuation, not a scene you sit in.

## Interstitial · Teaser (`.vc-dark`)

Between chapters. The head as a small card on the left, a **heavily blurred**
preview of a graphic from the coming chapter on the right, and a line bottom-
right — "COMING UP" with the last word in yellow. 2s, then the next chapter's
ground swaps in.

---

## ⭐ Real media, not typeset text

Every beat that supports a point shows a real resource: a screenshot, a real
product UI, a repo card, a docs or pricing page, real footage. **≥1 per 20s,
minimum 8 per video.**

- **Check every screenshot actually rendered content.** Login-walled and
  JS-heavy pages come back blank and ship as empty panels.
- **No random humans as b-roll.** Cut to a person only when that person *is* the
  subject of the line. Otherwise: the real UI, the repo card, or the agent
  character.
- Re-encode every sourced clip to **30fps CFR** and verify with `ffprobe`.
  Sourced clips arrive at 24/25/50/60 or VFR.

## Copy is derived, never inherited

Write the actual on-screen copy into `PLAN.md` per beat **before authoring**.
That is where a factual error gets caught cheaply, and it is what
`check-vibecode.sh` compares against.
