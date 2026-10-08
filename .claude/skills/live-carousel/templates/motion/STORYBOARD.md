---
message: "Static posts get scrolled past. Two motion rules make anything feel alive."
mode: autonomous
canvas: 1080x1350
fps: 30
bpm: 120
---

## Frame 1
status: outline
src: slides/01-hook/index.html
duration: 6.0s (3 bars)
rules: motion-blur-streak, hacker-flip-3d (glyph flip, no scramble), particle-burst, sine-wave-loop, svg-path-draw
- 0.0–0.5: "this post is STATIC." sits dead still inside a design-tool selection box
  (`static.png`), with a `0 FPS` pill.
- 0.3–2.0: the orange ball drops in and hits S on the downbeat (impact, shake, grid shockwave,
  selection handles fly off, `60 FPS`). It skips across S·T·A·T·I·C·. on eighth notes with a
  rising xylophone run.
- 2.0–2.5: it launches off the period and the word flips letter by letter to "ALIVE.".
- 2.5: SLAM on ALIVE. and the beat drops: ring burst, keyframe-diamond confetti, the word squashes wide.
- 2.5–4.5: the letters bob on the beat and the ball hops I → V → E → . → floor → out the right edge.
- 4.5–5.3: tape-stop; the word flips back to STATIC., the selection box redraws, and FPS counts down to 0.
- 5.3–6.0: dead still again, with a "swipe" nudge (loops to frame 0).

## Frame 2
status: outline
src: slides/02-easing/index.html
duration: 8.0s (4 bars)
rules: chart-scrub-readout (curve icons), svg-path-draw (strike), stat-bars-and-fills (spacing ticks), spring-pop-entrance
- "never move / LINEAR. / ease in. ease out. like everything real."
- Two lanes: a hollow LINEAR ball (robot) and the orange EASE IN-OUT ball (alive). Spacing ticks
  stamp every 2 frames, evenly spaced vs bunched at the ends. Each lane has a mini curve icon
  with a dot riding it.
- The ball enters from the left. Run 1 goes left to right, then the "same distance · same 1.00s" callout,
  run 2 comes back, an orange marker strikes LINEAR., run 3 goes left to right, and the ball hops out
  the right edge.

## Frame 3
status: outline
src: slides/03-weight/index.html
duration: 8.0s (4 bars)
rules: motion-blur-streak, svg-path-draw (callout leaders), particle-burst, press-release-spring
- "give it / WEIGHT. / stretch on the way down. squash on impact."
- The ball arcs in and bounces on the word WEIGHT. with a decaying rhythm. The ball stretches in
  the fall and squashes on contact, and the word squashes too (via the width axis). Strobe ghosts
  build a chronophotograph. Callouts: STRETCH = speed, SQUASH = impact, VOLUME STAYS THE SAME.
  The word trampolines the ball out the right edge.

## Frame 4
status: outline
src: slides/04-cta/index.html
duration: 8.0s (4 bars)
rules: cursor-click-ripple, discrete-text-sequence, press-release-spring, particle-burst
- "comment the word / M●TION / & I'll DM you the prompt behind this post."
- The ball enters, bounces on M, and snaps into the dashed O slot to become the O. A comment bar types
  MOTION, a cursor presses Post, your comment bubble pops up, then a reply bubble ("sent ✓ check your
  DMs") and hearts. Triplet: SAVE · SHARE · FOLLOW FOR RULE 03. Everything resets, and the ball
  hops out to the right.
