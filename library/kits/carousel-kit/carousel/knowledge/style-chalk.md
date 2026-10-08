# Style — Chalk-on-Ground Editorial (`chalk`)

Sheet: `library/kits/carousel-kit/carousel/assets/styles/chalk.jpg` · template: `template-chalk.html` · theme: `chalk`
(`scripts/themes/chalk.json`). Plan: `{"template": "template-chalk.html", "theme": "chalk"}`.

## The sheet, read as a spec
**Palette** — Chalk White `#F5F5EF` · Highlight Yellow `#FCFC8C` · Sunlit Moss `#93942B` ·
Field Green `#5C6216` · Shadow Green `#141E08` · Muted Red `#C4584A`.

**Rules (absolutes)**
1. **All lettering is chalk white.** Headline, numbers, labels, chart marks, handle — chalk white
   at full or reduced opacity. No other type colour exists.
2. **One accent word per slide may break to highlight yellow — and only as an OUTLINE.**
   (`hero_word`.) Never a yellow fill, never two yellow words, never yellow anywhere else.
3. **Muted red appears ONLY in the footer lockup** — the small connector words ("FOR A").
4. **The greens are not chosen — they are whatever the ground gives.** The only greens on a slide
   come from the photograph. Moss / Field / Shadow Green are *descriptions* of the ground, not UI
   colours. (Shadow Green is used only as the darkening wash.)
5. **Every slide darkens sharply** — a heavy vignette pulls every edge down to near-black green.

**Type** — hand-drawn chalk block capitals (irregular widths, letters individually tilted and
resized, grass showing through the chalk), stacked in 3–5 short lines, **lying on the ground seen
from overhead**: the whole block rotated a few degrees with slight perspective. Small sans handle
above the block. Footer lockup: `FROM A` (condensed sans, chalk) over `Creator FOR A Creator`
(script words chalk white, `FOR A` in muted red).
Fonts: **Londrina Solid** (900) for chalk caps · **Yellowtail** for the lockup script ·
**Oswald** for small caps labels. Serif never appears.

**World** — overhead photographs of real ground: lawn, turf, dry winter grass. Top-down or near
top-down only (a side-on meadow breaks the "lettering lies on the ground" illusion).
**One different photograph per slide**; the alternate-angles panel = vary the rotation/crop.

**Anatomy (top → bottom, 1080×1350)**: handle + folio (≈y 90) → chalk lettering block
(≈y 130–620) → proof drawn on the ground (≈y 640–1130) → lockup (≈y 1170–1300).

## Mechanical rules in the template
- Type colour tokens: only `--chalk` (and its opacities). `--yellow` is used in exactly one
  place: `-webkit-text-stroke` of `.hl .accent` with `color: transparent`.
- `--red` is used in exactly one selector: `.lockup .for`.
- No UI surface is filled with a colour: proof sits straight on the grass over a soft
  shadow-green pool (a radial darkening, not a panel). Screenshots are prints lying on the
  ground (white border, contact shadow, slight rotation).
- Chalk texture = one SVG filter (`#chalk`): fractal-noise holes + a small displacement for
  rough edges, applied to the lettering, the proof and the lockup.
- Vignette: fixed, strong (edges ≈ 90% `#141E08`).
- Charts: emphasis = solid chalk vs faded chalk (dashed when a line). No hue identity.

## Per-slide fields
Standard: `headline`, `hero_word`, `kicker`, `subtitle`, `content`, `cta_pill`, `cta_soft`,
`microcopy`, `bg_file`, `logo`, `handle` / `tagline` (plan).
Chalk-specific (read from `__SLIDE_JSON__`, all optional):
| field | default | what it does |
|---|---|---|
| `lines` | split of `headline` on ` / ` | the stacked lettering lines; `hero_word` may be one of the words |
| `tilt` | alternates −8 / 6 | block rotation in degrees (vary it across the set) |
| `pitch` | 16 | perspective tilt of the ground plane (deg) |
| `head_top` | 150 | top of the lettering block (px) |
| `head_size` | auto | cap height override (px); default fits the longest line to ~900px |
| `content_top` | auto | top of the proof block; default = just under the lettering |
| `bg_focus` | `50% 50%` | object-position of the photo |
| `seed` | index | jitter seed for the hand-drawn letters |
| `lockup` | `["FROM A","Creator","FOR A","Creator"]` | footer lockup words (plan- or slide-level) |
| `logo_mode` | `chalk` | `chalk` = the logo's white shapes redrawn in chalk; `color` = full colour on a print |

## Sourcing photos ($0)
`library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_photos.py work/carousel-kit/photos/<set> "Zoysia lawn" "Agrostis lawn" ...`
Species names return real top-down turf; generic "grass" returns horses and roads. Check every
download, drop side-on shots, and put the credit (`licence · author`) in `meta3` — the template
prints it small in the bottom-right corner. Paid path: ask for "overhead photograph of a lawn,
shot straight down, natural light, no text".
