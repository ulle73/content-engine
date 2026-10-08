# Motion grammar

Read this before animating anything. Every duration below was **frame-counted at 30fps**
off the references and lives in `assets/tokens.css` — use the token, not the number.

**Transforms only.** `opacity, x, y, scale, scaleX/Y, rotation` plus `filter: blur()`.
Bars, rings and rails grow with `scaleX` + `transform-origin`, never `width`.

---

## The three standing rules

### 1 · Nothing on screen is ever perfectly still
Every held scene carries a continuous slow drift for its whole life — typically
`scale 1.00 → 1.04`, `--mg-ease-drift` (linear), no easing in or out. On object stages
the camera also translates. This is the single difference between "a motion graphic"
and "a slide", and it is why REF-A can hold one composition for 25 seconds without it
going dead.

```js
gsap.to(scene, { scale: 1.04, duration: sceneLength, ease: "none" }, 0);
```

### 2 · Enter slow, leave fast
Entrances are `--mg-ease-out` over ~0.3–0.6s. Exits are **`--mg-dur-exit` — 3 frames**.
Elements in this style are *gone*, not dissolved. A 0.5s fade-out reads as hesitant and
immediately breaks the cadence.

### 3 · Overlap the handoff by 2 frames
⌁ REF-B 46.40–46.47s: the outgoing tiles are still sliding off while the incoming
headline is already on screen. `--mg-overlap`. **Never leave a gap** — a frame of empty
stage between two beats reads as a mistake.

---

## The five signature moves

### Word build — a title assembles itself
⌁ REF-A 28.0–28.9s. The move that opens most chapters.

- Each word fades `0 → 1` over **`--mg-dur-word`** (8f / 267ms).
- Word onsets are **`--mg-dur-cadence`** (7f / 233ms) apart — so words overlap slightly.
- **The whole line re-centres continuously** as each word lands. This is the tell; a
  line that is pre-laid-out and just fades in looks completely different.
- **No scale.** Opacity plus the line's x translation, nothing else.
- Cut to the background **~4 frames before the first word**. The empty beat is deliberate.
- On settle, bloom a glow up from the bottom edge over ~0.5s.

```js
const tl = gsap.timeline();
words.forEach((w, i) => {
  tl.fromTo(w, { opacity: 0 }, { opacity: 1, duration: 0.267, ease: "power2.out" }, i * 0.233);
});
// and, on the SAME timeline, the line re-centring as it grows:
tl.to(line, { x: () => -(line.scrollWidth - startWidth) / 2, duration: total, ease: "none" }, 0);
```

### Bar wipe — the highlight box behind a slam word
⌁ REF-B 25.2–25.6s.

- `scaleX: 0 → 1`, `transform-origin: left center`, **`--mg-dur-wipe`** (12f / 400ms),
  `--mg-ease-out`.
- The bar carries a horizontal gradient so the **leading edge reads brightest**
  (`.mg-hl::before` in tokens already does this).
- The word inside fades in **after the bar has passed it**, not with it.
- Never animate `width`.

### Light leak — the signature transition
⌁ REF-B 24.7–25.2s. **`--mg-dur-leak`** (12f / 400ms) total:

| Phase | Frames | What |
|---|---|---|
| bloom | 5f | `.mg-leak-core` opacity `0 → .55`, drifting across on x, rotated ~-18° |
| white-out | 3f | opacity `→ 1`, scale up ~1.3 — the frame is essentially white-lavender |
| reveal | 4f | opacity `→ 0` fast; the new scene is **already composited underneath** |

The incoming scene sits under the leak from the first frame — this is a **wash over a
cut**, not a dissolve between two clips. Always sounded: `swoosh` on the bloom with a
`riser` tail cresting on the white-out.

### Ring draw — the late second beat
⌁ REF-B 47.0–47.4s. A conic progress ring sweeping clockwise over **`--mg-dur-ring`**
(18f / 600ms) — but it **starts ~0.5s after the lockup has already settled**. That
delay is the point: it gives the composition a second beat instead of one flat reveal.

Apply the same idea generally: **the last element of a composition arrives late, on its
own.** A stat card's number counts up after the card lands. A panel's connectors draw
after the pills are in.

### Camera pull-back — the scene fits itself into shot
⌁ REF-A 0:29–0:58. **This corrects an earlier reading.** The stack does not scale down in
steps as panels are added. The camera pulls back **continuously for the entire
30-second sequence** — the section title lands large and near-filling the frame, and
everything shrinks steadily as panels arrive beneath it. One tween, `ease: "none"`,
running underneath every other animation in the scene.

```js
gsap.set(fit, {scale:1.55, y:150});
tl.to(fit, {scale:.82, y:0, duration: sceneLength, ease:"none"}, 0);   // never stops
```

Discrete re-fit steps read completely differently — like a layout reflowing. The
continuous version reads as a camera, and it is what makes each new panel feel like it is
being *fitted into shot* rather than appended to a list. `--mg-dur-refit` is still right
for a one-off element that must rescale on its own, but it is not how this scene is built.

---

## Entrances, by material

| Element | Entrance |
|---|---|
| **Glass tile** | scale `.86 → 1` + opacity, `--mg-dur-pop` (5f), `--mg-ease-slam` (overshoot). Siblings on `--mg-stagger` (90ms). |
| **Node pill** | opacity + `y: 14 → 0`, 0.3s, `--mg-ease-out`, staggered along the flow direction. |
| **Connector** | SVG `stroke-dashoffset` draw, 0.35s, starting **after** its destination pill has landed. |
| **Panel** | the outline draws/fades first, contents follow on a stagger. |
| **Media card** | rises from below, `y: 60 → 0`, `scale .92 → 1`, `blur(14px) → 0`, 0.55s. ⌁ REF-A's dashboards and app cards all enter this way. |
| **Point-stack line** | `blur(10px) → 0` + opacity + `y: 10 → 0`, 0.4s, lines on `--mg-stagger`. Exits as a **whole stack**, blurring out together. |
| **Floating panel over footage** | slides in from its own side, holds at ~60% opacity, drifts with parallax, slides back out the same side. |
| **Brand lockup** | `blur(12px) → 0` + opacity, 0.6s. Then **holds long** — ⌁ REF-A holds one for 12s. |

---

## Camera moves on object stages

⌁ REF-B 0:35–0:45. These are real camera moves, not element animations — they act on
the whole stage.

- **Dolly / orbit** — the stage translates and scales while children hold parallax
  offsets proportional to their depth. Slow, continuous, `ease: "none"`.
- **Dive-through** — the camera pushes into a row of tiles until they scale past the
  lens and out of frame, then **pulls back** to reveal the row again. ~1.5s in, ~0.8s
  back. Catalog: `zoom-through-transition`, `parallax-device-dive`.
- **Punch-in on the action** — on a screen stage, scale `1.0 → 1.35` toward the region
  where the cursor is working. Follows the cursor; never a random zoom.

## Face-only zooms

Only when the face is full-frame — never in the bubble, never on a split.

- **Slow push** (default): origin `50% 44%`, `scale 1.00 → 1.06`, `ease: "none"`.
- **Punch** (the turn / a warning): origin `50% 38%`, `scale 1.00 → 1.14`, `power2.inOut`.
- ⌁ REF-B 0:19–0:24 runs a 5s continuous push **with captions off** — the pure-delivery
  beat. Captions returning afterwards is itself a retention device.

Zoom the camera element only; captions and lower thirds do not zoom.

---

## Timing anchors — non-negotiable

- Every graphic enters **on, or a hair after, the tight-transcript word onset** it
  illustrates. Never before. Round-number and eyeballed timings are banned.
- Exit at the **OUT word + 0.3s**.
- **Cap a support graphic at 10s** — beyond that, evolve it (add a layer, advance a
  step, re-fit the stack) rather than let it sit.
- **One idea on screen at a time.**
- A new visual beat every ≤8s; never more than ~12s of uninterrupted talking head
  without a cut, a zoom change, or a graphic.
