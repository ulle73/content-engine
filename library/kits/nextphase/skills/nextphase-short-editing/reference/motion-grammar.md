# Motion Grammar — the animation vocabulary

This is the layer that keeps you creative. These are reusable *behaviors*, not fixed scenes. Compose them freely to invent story-specific animation. Everything uses the eases/durations in `tokens.css`. Rule of thumb: **motion should mean something** — it visualizes what I'm saying, it doesn't just decorate.

## Entrances (vary them — never the same one twice in a row)
- **rise** — `translateY(26px)→0` + fade, `--ease-out`. Default for cards/blocks.
- **scale-in** — `scale(.86)→1` + fade, `--ease-overshoot`. For stats, emphasis, captions.
- **clip-reveal** — `clip-path inset(0 100% 0 0)→0`, `--ease-out`. For headlines/bars.
- **blur-in** — `filter blur(12px)→0` + fade. For soft/premium reveals.
- **stagger** — children enter one-by-one at `--stagger` (80ms). For lists, options, grids.
- **type-on** — characters/words appear sequentially with a blinking caret. For search bars, terminals, captions.
- **draw-on** — SVG `stroke-dashoffset len→0`, `--dur-draw`. For lines, arcs, charts, underlines.
- **count-up** — number animates 0→target with cubic ease-out. For stats/prices.

## Emphasis (on a beat / key word)
- **pop** — `scale 1→1.06→1`, 180ms. Caption keyword hit.
- **glow-pulse** — brief coral box-shadow bloom. Key term.
- **color-flash** — quick coral background flash behind a word.
- **shake** — small wrapper shake on an alarming word ("banned", "$300").

## Exits (mandatory — pair every entrance)
- **fade-up-out** — fade + `translateY(-18px)`, `--dur-exit`. Default.
- **shrink-out** — `scale→.9` + fade. For stats/cards.
- **wipe-out** — clip-path close. Reverse of clip-reveal.
- Exit begins at the graphic's OUT word (see `editing-rules.md`). Never skip it.

## Transitions between scenes (vary)
- **flash** — 1–2 frame coral/white flash on a hard cut.
- **whip-pan** — quick directional blur slide.
- **dissolve** — 300ms crossfade for calm topic shifts.
- **HyperFrames catalog** shader transitions (cinematic-zoom, light-leak, glitch, swirl) for big story turns — use sparingly.

## Story devices (compose the above into narrative beats)
These are patterns, not templates — adapt freely:
- **The spike** — a number counts up FAST while a bar/line shoots up and a coral glow intensifies; punctuate with a shake on the final value. (e.g. a cost/stat running away.)
- **The timeline** — nodes draw-on left→right one at a time as I narrate each date/step; the connecting line draws between them; past nodes dim as the newest lights coral.
- **Before / after** — two columns; the "old" side (muted/red) builds, then the "new" side (coral/green) builds and out-scales it.
- **The reveal ladder** — a list/options stagger in, then the "winner" row pops and the others recede.
- **The zoom-in** — a UI mockup scales up and a callout label draws to the exact element I mention.
- **The morph** — one concept (logo/word/shape) transforms into another along a drawn path with a travelling dot.

## Creative-freedom clause (put this mindset into every edit)
You are NOT limited to the bricks in `system/components/`. Invent new scenes that serve THIS story. Hand-author custom HTML/GSAP, pull from the HyperFrames catalog, combine story devices in new ways. The ONLY constraints are: (1) obey the tokens, (2) obey the motion grammar eases/durations, (3) obey the safe zones and the no-linger timing rule. Within those, go as far as the story deserves.
