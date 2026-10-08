# frame.md: Live Carousel / "The Bouncing Ball"

Concept angle: the bouncing ball, the first thing every animator learns, travels through
the whole carousel and proves each point by moving.

## Canvas
- 1080 x 1350 (Instagram 4:5), 30 fps, safe margin 72 px. Keep corners clear (IG puts its
  "1/4" counter top-right and the sound icon bottom-right).
- Each slide is a seamless loop: the last frame flows back into frame 0.
- Frame 0 of every slide is fully composed and readable, because it is the first thing
  people see after a swipe.

## Palette (house carousel style: one hero colour, one accent)
| token        | hex       | use                                                      |
| ------------ | --------- | -------------------------------------------------------- |
| --cobalt     | `#2041F2` | the world: every background (radial, lighter at top)     |
| --cobalt-deep| `#1530C8` | background edges, panel fills                            |
| --cream      | `#FFF3E0` | all type, hairlines, ghost outlines                       |
| --orange     | `#FF6A1F` | THE BALL and accent shapes only (never small text)        |
| --ink        | `#0C1236` | shadows, text on orange/cream pills                       |
Neutrals stay tinted (cream, ink), never pure #000 or #fff.

## Type
- BIG WORD: **Anybody** variable (wdth 50–150, wght 100–900), 900 weight, caps. The
  width axis is animated: letters physically squash wider and stretch narrower.
- Small lines: **Fraunces Italic** variable, 400–500, 64–80 px. This is the quiet half of the
  loud + quiet pairing.
- Labels and microtype: **JetBrains Mono** 500, 24–28 px, caps, tracking 0.12em.
- In-feed minimums: body 32 px or more, labels 24 px or more.

## Layout grammar (every slide)
1. Top bar: left label / right `0N / 04` counter, then a full-bleed hairline at y=118.
2. The stack: small italic line, then the BIG WORD, then a small italic line.
3. Demo zone: the ball doing the lesson.
4. Bottom: a mono triplet line, then the **timeline ruler** (full bleed, y 1190–1290). The ruler's
   frame numbers continue from slide to slide, and its orange playhead sweeps from left to
   right over the slide's duration. Seen side by side, the four slides read as one long timeline.
5. Background: a cobalt radial glow, a cream dot grid (the design-canvas feel) that ripples on
   impacts, and fine animated grain.

## Motion rules
- The ball is always a function of time: parabolic arcs, stretch along its velocity, squash at
  contact while keeping its volume (sx × sy ≈ 1), and onion-skin ghosts.
- Impacts are damped springs, not tweens. Every hit lands on the 120 BPM grid (beat = 0.5 s).
- Continuity: the ball leaves each slide at the right edge and enters the next from the left.

## Don'ts
- No gradient text, no neon, no cyan, and no linear full-screen gradients.
- No orange text under 90 px (contrast). No Instagram logos or handles.
