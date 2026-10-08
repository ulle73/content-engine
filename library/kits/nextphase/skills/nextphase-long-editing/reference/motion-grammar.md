# Motion Grammar — the animation vocabulary (16:9)

This is the layer that keeps you creative. These are reusable *behaviors*, not fixed scenes.
Compose them freely to invent story-specific animation. Everything uses the eases and durations
in `tokens.css`. Rule of thumb: **motion should mean something** — it visualizes what he is
saying, it does not just decorate.

⇄ **The 16:9 amplitude note.** A 1920-wide frame is viewed further away than a phone-held 9:16
frame, so distances that feel right in a short feel jittery here. Translate distances scale with
the *frame*, not with the element: entrance offsets ~`26px` (unchanged, it is a fine-motion
value), but slide-across distances go to `540px` and full-layout pushes to `1920px`. Zoom
amplitudes are smaller (see `SKILL.md` §1).

## Entrances (vary them — never the same one twice in a row)
- **rise** — `translateY(26px)→0` + fade, `--ease-out`. Default for cards and blocks.
- **scale-in** — `scale(.86)→1` + fade, `--ease-overshoot`. Stats, emphasis, captions.
- **clip-reveal** — `clip-path inset(0 100% 0 0)→0`, `--ease-out`. Headlines, bars, lower thirds.
- **blur-in** — `filter blur(12px)→0` + fade. Soft, premium reveals. *(The one non-transform
  property sanctioned to animate — it is a compositing filter, not layout, so it does not stutter.)*
- **stagger** — children enter one by one at `--stagger` (80ms). Lists, options, grids, recaps.
- **type-on** — characters or words appear sequentially with a blinking caret. Search bars,
  terminals, prompts.
- **draw-on** — SVG `stroke-dashoffset len→0`, `--dur-draw`. Lines, arcs, charts, underlines.
- **count-up** — number animates 0→target with a cubic ease-out. Stats, prices, benchmarks.

## Emphasis (on a beat / key word)
- **pop** — `scale 1→1.06→1`, 180ms. Caption keyword hit.
- **glow-pulse** — a brief coral box-shadow bloom. Key term.
- **color-flash** — a quick coral background flash behind a word.
- **shake** — a small wrapper shake on an alarming word ("banned", "$300").
- **⇄ callout-draw** — a coral leader line draws from a label to the exact pixel on a screen
  recording, with a ring pulsing at the target. The long-form workhorse; see `screen-recording.md`.

## Exits (mandatory — pair every entrance)
- **fade-up-out** — fade + `translateY(-18px)`, `--dur-exit`. Default.
- **shrink-out** — `scale→.9` + fade. Stats and cards.
- **wipe-out** — clip-path close. The reverse of clip-reveal.
Exit begins at the graphic's OUT word (`editing-rules.md`). Never skip it.

## Transitions between beats and layouts (vary)
- **push** — outgoing `x:0→-540` + fade, incoming `x:540→0` + fade, `power3.out`, ~0.44s.
  For graphic swaps *inside* a layout.
- **⇄ whip-pan** — a fast directional slide of the whole frame with a motion-blur streak,
  `--dur-whip` (280ms). **The long-form workhorse for layout changes.** Always on a `swoosh`.
- **⇄ chapter wipe** — the dot-grid BG sweeps across on a coral leading edge, `--dur-chapter`
  (600ms), under the chapter card. Every chapter boundary.
- **dissolve** — 300ms crossfade for calm topic shifts inside a chapter.
- **flash** — a 1–2 frame coral/white flash on a hard cut. **Max ~3 per video** — the payoff
  spike and the turn. Used more, it stops meaning anything.
- **HyperFrames catalog** shader transitions (cinematic-zoom, light-leak, glitch, swirl) for big
  story turns — sparingly.

## Story devices (compose the above into narrative beats)
Patterns, not templates — adapt freely:
- **The spike** — a number counts up FAST while a bar or line shoots up and a coral glow
  intensifies; punctuate with a shake on the final value.
- **The timeline** — nodes draw on left→right one at a time as each date or step is narrated;
  the connecting line draws between them; past nodes dim as the newest lights coral.
- **Before / after** — two columns; the "old" side (muted) builds, then the "new" side (coral)
  builds and out-scales it.
- **The reveal ladder** — a list staggers in, then the "winner" row pops and the others recede.
- **The zoom-in** — a UI mockup scales up and a callout draws to the exact element named.
- **The morph** — one concept (logo, word, shape) transforms into another along a drawn path
  with a travelling dot.
- **⇄ The stack** — the long-form escalation device: each chapter's takeaway drops onto a
  growing stack at the frame edge, so the viewer *sees* the argument accumulating. Pays off at
  the recap, where the whole stack is already there and only needs highlighting.
- **⇄ The progress rail** — a thin coral rail along the bottom title-safe edge showing chapter
  N of M, advancing at each boundary. Cheap, and it measurably helps people stay for the next
  chapter. Keep it 4px, `--coral` at 60%, and never let it cross the caption band.

## Creative-freedom clause
You are NOT limited to the bricks in `components/`. Invent new scenes that serve THIS story —
hand-author custom HTML/GSAP, pull from the HyperFrames catalog, combine story devices in new
ways. The ONLY constraints: (1) obey the tokens, (2) obey the eases and durations, (3) obey the
safe zones and the pacing floor. Within those, go as far as the story deserves.
