# Motion grammar

All frame counts are **@30fps**, already converted from REF-B's 23.976fps
(×1.2513). See `reference-log.md` before re-measuring.

Animate **transforms only** — `opacity, x, y, scale, scaleX/Y, rotation` — plus
`filter: blur()`. Never `top/left/width/height`. Bars and rails grow with
`scaleX` + `transform-origin`.

---

## 1 · ⭐ The churn — this is the style

REF-B 4.0–4.85s, native frame strip: three paper cards each hold an icon, and
**the icons swap between cards every 2–3 frames**. The cards jitter in rotation
at the same cadence. Yellow sparkles blink on and off. Nothing eases; every
state is held then replaced.

This is stop-motion on 2s, and it is what makes the edit read as *vibe coded*
rather than designed. Get this wrong and you have a nice flat-design video.

```
--vc-hold: 2      /* every churning property updates every 2 frames */
```

**How to build it:** step the value, don't tween it. A GSAP timeline with
`ease: 'steps(n)'`, or discrete keyframes at 2-frame spacing. A smooth tween
between the same two states is not the same effect and reads as a glitch.

**What churns:**
- icon / content position within a set of cards, while the set is arriving
- card rotation, ±`--vc-jitter-rot` (1.2°)
- card position, ±`--vc-jitter-pos` (0.3cqh)
- sparkle visibility, on 2 / off 2

**What does NOT churn:** the ground, the talking head, display type once
settled, and anything the viewer is being asked to read. Churn is texture around
the message, never the message.

**Where to spend it:** the 1–2s while a group is assembling, and idle beats
where a layout is held. Once the viewer needs to read the frame, the churn stops
and the frame is still.

## 2 · Arrivals

Paper arrives with a **rotational overshoot and settle** — REF-B's timeline card
at 26.2–27.05s rotates past level and comes back over ~25 frames.

| Move | Frames | Notes |
|---|---|---|
| Paper card in | **7** | scale .92→1, rotate ±4°→`--vc-tilt`, opacity 0→1 |
| Card settle | **25** | the overshoot decaying; overlaps the next beat |
| Stagger between siblings | **3** | a row of three tiles takes 7 + 2×3 = 13f |
| Sticker in | **7** | same, plus a 2-frame scale punch at 1.04 |
| Anything out | **4** | scale 1→.96, opacity→0. Never slides off. |

Ease in: `back.out(1.7)`. Ease out: `power2.in`.

## 3 · The negation

Two red strokes, drawn on with a stroke-dash reveal.

| | Frames |
|---|---|
| Stroke 1 draws | **5** |
| Stroke 2 starts after stroke 1 begins | **3** |
| Total for one X | **8** |
| Between successive tiles being crossed | **14** |

A strike-through on a line of text is the same move with one stroke, drawn
left→right, slightly off-horizontal (REF-A 14.6s runs about 1.5° up).

The stroke **overshoots the card** on both ends. A red X contained neatly inside
its tile looks drawn by a computer, which is the opposite of the intent.

## 4 · Captions hard-cut

`--vc-caption-in: 0`. **Zero frames.** No fade, no scale, no pop, in or out.

Verified on REF-A at 27.9–28.6s: the lozenge is present for 3 frames, gone on
the 4th, nothing in between.

This is the single easiest rule to break by accident, because every animation
library wants to give a new element an entrance. `check-vibecode.sh` greps for
transitions on `.vc-caption` and fails the render.

## 5 · The timeline builds

The centrepiece move. Clips arrive **left to right, one at a time**, each with
`scaleX 0→1` from `transform-origin: left center` over **5 frames**, staggered
**4 frames** apart. The playhead sweeps after the last clip lands, `x` across
the card, linear, over 30–45 frames depending on the beat.

Track order: cyan, then pink, then blue. Bottom track first if the tracks are
stacked — it reads as building up from the base layer.

## 6 · The ground never moves

No camera drift, no push-in on the plate, no parallax. REF-B holds the ground
absolutely still and lets the paper do the work. This is the opposite of
`motiongraphics`, and mixing the two habits is the most common way a vibecode
comp goes wrong.

The **head card** may drift — a slow scale 1.00→1.02 over 6s, linear — because
it is footage. The ground does not.

## 7 · Transitions between scenes

| Transition | Frames | Use |
|---|---|---|
| **Paper wipe** — a paper card scales up to fill, next scene revealed under it | 9 | default, most scene changes |
| **Whip** — 4-frame horizontal blur, x ±8cqh | 4 | inside a chapter, fast beats |
| **Hard cut** | 0 | on a hard word in the VO |
| **Ground swap** — old ground scales down as a paper card, new ground behind | 12 | chapter boundary only |

**Every one of these carries a sound.** No silent transitions, ever.

## Cheat sheet

```
churn hold ......... 2f      caption in/out ..... 0f
card in ............ 7f      clip in ............ 5f
settle ............. 25f     clip stagger ....... 4f
stagger ............ 3f      X stroke ........... 5f
out ................ 4f      X stroke lag ....... 3f
paper wipe ......... 9f      whip ............... 4f
```
