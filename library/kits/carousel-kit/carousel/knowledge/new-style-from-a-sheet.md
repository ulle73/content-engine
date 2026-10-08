# 09 — Building a NEW style from a reference sheet

This is the procedure for turning a style-sheet image the user hands you into a working
template. Follow it in order. It has been run three times; the shipped styles
(midnight / archival / celestial) are its output, so read one of those templates
alongside this document.

**Budget roughly 30–45 minutes of work.** Most of it is looking at renders and fixing
what you see. Do not skip step 7.

---

## 1. Read the sheet properly

Open the image and read it like a spec, not a mood board. Pull out **every** one of these:

| Panel | What to extract |
|---|---|
| **Palette** | Every swatch: the name AND the hex. Write them down exactly. |
| **The rules under the palette** | The most important part of the whole sheet. These are usually written as absolutes — *"X is structure, never type"*, *"all type is Y"*, *"Z appears only as …"*. They are constraints, not suggestions. |
| **Type specimen** | The display face, the accent treatment, the body/UI face, and how the headline is built (one word? set twice? clipped? in a capsule?). |
| **Component zoo** | Every UI part the system owns — pills, badges, stickers, frames, textures. |
| **Slide anatomy** | Where each element sits, top to bottom. Copy this layout literally. |
| **System notes** | Numbered constraints. Each one becomes a line of CSS or a rule in the template. |
| **The world** | What the imagery is: abstract atmosphere, real photographs, illustration. This decides step 3. |

Write the findings into `library/kits/carousel-kit/carousel/knowledge/style-<name>.md` before you write any code.
If you cannot state the rules in one page, you have not read the sheet closely enough.

## 2. Restate the rules as things a template can enforce

Turn each prose rule into a mechanical one. Examples from the shipped styles:

- *"Brick red is structure — never type"* → red is allowed on `background` of blocks and bar
  fills; it never appears in a `color:` declaration.
- *"All type is cloud white and always carries a soft shadow"* → one `--soft` shadow token,
  applied to every text element; no other text colour exists anywhere.
- *"Monarch orange appears only as butterflies"* → orange exists in exactly one SVG in the
  whole template, and is forbidden in the chart theme.
- *"The headline is always too big for the frame and always clipped"* → the headline is
  auto-fitted in JS to N× the plate width so it always overflows both edges.
- *"One hard seam per slide"* → a single `--seam` variable; block above, photo below.

## 3. Choose the background strategy

Read what the sheet's "world" panel shows, then pick one:

| The sheet shows | Use | How |
|---|---|---|
| Abstract atmosphere, light, texture, nothing a camera took | **Procedural** | Copy `bg_local.html` and rewrite the painter. Seeded, free, ~1s/slide. |
| Real photographs, or a rule like *"the photograph supplies every other colour"* | **Real photos, one per slide** | `fetch_photos.py` pulls freely-licensed images from Wikimedia Commons and records credits. **Never reuse one photo across slides.** |
| Photographic scenes you cannot source | **Paid AI** (only if the user asks and has a key) | `carousel_run.py generate` |

**Never generate seven variations of one scene and call them different.** If the sheet wants
photographs, get seven different photographs.

## 4. Build the template

Start from the closest existing template and keep **every placeholder** — the renderer
replaces a fixed set, and a missing one leaks raw `__TOKEN__` text onto the slide:

```
__BG__ __STAGECLASS__ __HEADLINE__ __HERO_WORD__ __SUBTITLE__ __KICKER__
__TOPIC_TAG__ __BRAND_LABEL__ __HANDLE__ __TAGLINE__ __INDEX__ __TOTAL__
__CONTENT__ __MASCOT__ __CTA_PILL__ __CTA_SOFT__ __MICROCOPY__
__META1__ __META2__ __META3__
```

Add new per-slide knobs by adding them to the `repl` dict in `carousel_render._slide_html`.
Anything that should vary slide-to-slide (a seam height, a layer position) belongs there —
**variety across the set is what stops a carousel looking like one layout repeated.**

Layout is absolutely positioned at 1080×1350. Build the anatomy from the sheet top-down.

## 5. Add a chart theme — and validate it

Add an entry to `THEMES` in `carousel_charts.py` with the same slots as the others.

The sheet's rules usually **forbid a categorical palette** (one hue per series), because they
reserve most colours for other jobs. That is fine — it pushes you to the better form anyway:

- **Emphasis** — the one series that matters gets the accent; everything else goes muted.
- **Ordinal** — a single-hue ramp when the data is magnitude.

Then check it rather than trusting your eye. From the dataviz skill's directory:

```
node scripts/validate_palette.js "<accent>,<muted>" --mode dark --surface "<panel hex>"
node scripts/validate_palette.js "<ramp,…>"        --mode dark --surface "<panel hex>" --ordinal
```

Aim for CVD ΔE ≥ 8 and normal-vision ≥ 15. If contrast against the panel WARNs, the relief is
**visible direct labels on every mark** — which these charts already do, so say so in a comment.

If the sheet's own colours cannot make a readable plate, darken or lighten one of them for the
panel only (e.g. archival uses deep ink; celestial deepens alpine slate). Do not invent a new hue.

## 6. Wire it up

```json
{ "template": "template-<name>.html", "theme": "<name>" }
```

`carousel_render.render` reads `theme` and calls `carousel_charts.use_theme` automatically.

## 7. Render, LOOK, and fix — this is the real work

Build a test run that exercises **every content type** (`line`, `column`, `dumbbell`, `meter`,
`bars`, `stats`, `image`) plus a hook and a CTA. Render it and open every PNG.

These are the faults that showed up every single time:

- **The data panel swallows the headline.** Panels are tall; the headline sits mid-plate. Cap
  panel/image heights and move the headline, then re-render.
- **A pasted screenshot overruns the frame.** Give `.shot img` a `max-height`, and crop the
  source image so it ends on a clean line.
- **Type disappears into the background.** Light type on a bright photo needs a much heavier
  shadow than looks right in CSS, or its own solid block.
- **Texture drowns the image.** Grain always wants to be about a third of what you first set.
- **The chart escapes its plot.** Check the axis covers the data maximum.
- **Numbers read wrong.** Don't append a unit that the title already states (`575.8k` under a
  title saying "in thousands" reads as thousands-of-thousands).
- **Decorative SVG reads as a blob.** A dove needs separate head, beak, tail and two wings, or
  it looks like a leaf. Draw shapes, not one clever path.

Iterate until each render is right. **Do not report a style as finished before looking at it.**

## 8. Register it

Add a row to the style table in `.claude/skills/carousel-kit/SKILL.md`, a short "specifics" section
listing the new per-slide fields, and save the sheet to
`library/kits/carousel-kit/carousel/assets/styles/<name>.png`.

---

## Technical gotchas that cost real time

- **Python 3.9** — `dict | None` in an annotation throws at import unless the file starts with
  `from __future__ import annotations`.
- **One page renders every slide.** Any top-level `const` in a template script collides on the
  second slide — wrap template JS in an IIFE.
- **`_esc()` escapes markup.** If a field should allow `<br>`, unescape it explicitly for that
  field only (see `__SUBTITLE__` in `carousel_render`).
- **f-strings on 3.9** cannot reuse the outer quote inside the expression: `f'{_T["k"]}'` is
  fine, `f'{_T['k']}'` is a syntax error.
- **Wikimedia rate-limits hard.** Back off and retry; do not hammer it.
- **Blur is expensive.** Blur a whole offscreen layer once, never per shape — it took one
  background from 30s to 1s.
