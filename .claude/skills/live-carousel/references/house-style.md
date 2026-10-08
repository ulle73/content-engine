# House style: the editorial big-word look

It looks like a magazine cover that moves. There is one saturated world colour, one hot accent and
cream type. A loud BIG WORD sits between two quiet italic lines. Everything is built from a few
strong decisions, so a slide still reads at thumbnail size.

## Canvas

- 1080 x 1350 (4:5 portrait), 30 fps, 72 px safe margin.
- Leave the top-right corner (the platform's "1/4" counter) and the bottom-right corner (the sound icon) empty.
- Frame 0 of every slide is complete and readable.

## Palette (one hero, one accent; neutrals are tinted, never pure black or white)

| token         | cobalt (default) | use                                                              |
| ------------- | ---------------- | ---------------------------------------------------------------- |
| `hero`        | `#2041F2`        | the world: every background, as a radial that is lighter at the top |
| `hero-hi`     | `#3A5CFF`        | the top of the radial glow                                         |
| `hero-deep`   | `#1530C8`        | background edges, panel fills                                    |
| `paper`       | `#FFF3E0`        | all type, hairlines, ghost outlines                               |
| `accent`      | `#FF6A1F`        | THE protagonist object and accent shapes only, never small text   |
| `accent-hi/-deep` | `#FF9A5C` / `#E4500D` | highlight and shade of the accent object                   |
| `ink`         | `#0C1236`        | hard shadows, text on accent and paper pills                    |

Templates are written in the cobalt values. `build.py` swaps them for the project's `theme.json`, so
you can switch the whole carousel by changing the theme. Write new colours as these tokens or their
hex values, and theming keeps working. Keep the `rgba(255, 106, 31, …)` style for alphas, because
the build rewrites those too.

| theme    | feel                                          | hero / accent / paper            |
| -------- | --------------------------------------------- | -------------------------------- |
| `cobalt` | confident, creator/tech default               | `#2041F2` / `#FF6A1F` / `#FFF3E0` |
| `tomato` | warm, loud: food, lifestyle, hot takes         | `#D93A26` / `#FFC531` / `#FFF4E2` |
| `forest` | calm, premium: money, wellness, slow topics   | `#1F6A4C` / `#FF7A2E` / `#F5EFDF` |
| `noir`   | editorial dark: AI, tech, serious tone        | `#1B1B21` / `#FF5B2E` / `#F3EEE5` |

To switch themes, re-scaffold with `--theme` or copy one entry from `.claude/skills/live-carousel/templates/themes.json` into
the project's `theme.json`, then rebuild. A brand palette is fine too: write its eight tokens into
`theme.json`. Keep the hero dark enough for paper-coloured type (contrast of at least 4.5:1 for text
under 40 px).

## Type (all free, bundled, SIL Open Font License)

- **BIG WORD: Anybody**, variable (`wdth` 50 to 150, `wght` 100 to 900), weight 900, caps. Animate the
  width axis: letters squash wider on impact and stretch narrower when they move fast.
  `LC.fitWord` picks the size and width that fill the column exactly.
- **Small lines: Fraunces Italic**, variable, 400 to 500, 64 to 80 px. This is the quiet half of the loud + quiet pair.
- **Labels and microtype: JetBrains Mono**, 500, 24 to 28 px, caps, tracking 0.12em.
- **Anton** is bundled for condensed numbers and photo-mode overlays.
- In-feed minimums: body text 32 px or more, labels 24 px or more.
- Each slide calls `document.fonts.load(...)` for its faces before it measures anything. Keep doing that.

## Layout grammar (every slide)

1. **Top bar**: left label (series name + orange dot), right `0N / 0M` counter, then a full-bleed
   hairline at y=118.
2. **The stack**: a small italic line, the BIG WORD, then another small italic line. The words carry
   the post. The big word is one word, two at most.
3. **Demo zone**: the protagonist proving the point.
4. **Bottom**: a mono triplet (`2 RULES · 1 BALL · 0 STILL FRAMES`) and the **timeline ruler**, full
   bleed at y 1190 to 1290. The ruler's frame numbers continue from slide to slide, and its playhead
   sweeps once per loop. Seen side by side, the slides read as one long timeline.
5. **Background**: the hero radial glow, a paper dot grid (the feel of a design canvas) that ripples
   on impacts, and fine animated grain.

## Motion rules

- Use physics, not tweens. The protagonist follows parabolic arcs, stretches along its velocity, and
  squashes on contact while keeping its volume (sx × sy ≈ 1). Onion-skin ghosts show the speed.
- Impacts are damped springs (`LC.kick`, `LC.settle`). Every hit lands on the 120 BPM grid (0.5 s).
- Give each slide one big moment. The rest supports it.
- **Continuity**: the protagonist leaves each slide at the right edge and enters the next from the
  left, so swiping feels like one shot.
- Ease in and out (never linear, unless the point is that linear looks robotic).

## Copy

- The hook names the reader's problem in four words or fewer, then flips it. For example, "your posts
  are STATIC." becomes ALIVE.
- Value slides give one rule each, named in the BIG WORD (`LINEAR.`, `WEIGHT.`), with a one-line
  why underneath.
- The CTA asks for one action with a keyword: "comment MOTION & I'll DM you the prompt". Mention
  the save or share in the bottom triplet.
- End the BIG WORD with a period. It reads like a verdict.

## Don'ts

- No gradient text, neon, cyan, or linear full-screen gradients.
- No accent-coloured text under 90 px (contrast). No platform logos and no handle in the art; the
  post shows the handle.
- Never more than one hero colour plus one accent on a slide.
