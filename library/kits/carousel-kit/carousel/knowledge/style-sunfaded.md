# Style — Sun-Faded Photo Poster (`sunfaded`)

Sheet: `library/kits/carousel-kit/carousel/assets/styles/sunfaded.jpg` · template: `template-sunfaded.html` · theme: `sunfaded`
(`scripts/themes/sunfaded.json`). Mood: nostalgic, solitary, pastoral, sun-faded, still.
**$0 path:** real freely-licensed photographs + local cutouts (cutout.py: rembg or npx hyperframes remove-background), all local.

## 1. What the sheet says (the spec)
**Palette** — Sky Deep `#0E74AC` · Sky Pale `#64ADC6` · Faded Gold `#D5C377` · Meadow Lime `#8E9726` ·
Field Shadow `#5A5F19` · Weathered Ink `#292B19`.

**Rules (absolutes)**
- Every colour in the system is pulled from the photograph. Nothing is invented.
- Faded gold is the headline colour and appears nowhere else.
- Captions take their colour from whatever they sit on, darkened and dropped in opacity.
- The palette is always slightly desaturated and sun-bleached. No saturated colour survives.

**System notes**
- The headline always sits BEHIND the subject and is always partly hidden by it. Never in front.
- One gold headline per slide. Never two, never another colour.
- The photograph is full-bleed. No borders, no panels, no crops inside the slide.
- Captions are meant to be almost missed — low contrast, blended, never outlined or shadowed.
- Serif for headline and credit, light sans for captions. No third face.
- Sky occupies the top third, subject the middle, open ground the bottom third.
- Every slide carries the same grain and sun-bleached grade across the full frame.

**Type / anatomy** — small serif credit top-centre (`DESIGN BY …`), hairline, a huge wide high-contrast
gold serif headline in caps behind the subject, hairline, a light-sans uppercase caption in the lower third.

## 2. How the template enforces it
| Rule | Mechanism |
|---|---|
| Gold only for the headline | `#D5C377` exists once in the file (`.headline`); the chart theme never uses it |
| Behind the subject | stack: photo (z1) → headline (z3) → subject layer (z4). Subject layer = the local cutout (`subject_file`), else a **sky-key** made on a canvas: non-sky pixels, then cleaned — morphological close, keep only regions connected to the bottom of the frame, drop islands < 0.4% of the frame, fill small sky holes, feather 1.5px |
| **Numbers are never bitten** | for any headline containing a digit, after layout the template measures how much of each digit/`.`/`,`/`%`/`-`/`$` glyph the occluder covers; it raises the headline until digits are ≤ 15% covered and punctuation ≤ 2%. If it can't, it removes the occluder and logs `[sunfaded] …` (and `body[data-occlusion-warning]`). The value always beats the layering |
| Colours from the photo | JS samples the photo under the credit (sky) and under the caption (ground) and darkens toward weathered ink; hairlines are the sky lightened. Mono logo is painted in the sampled credit colour |
| No panels | charts, bars, dials, stats sit straight on the ground with `mix-blend-mode:multiply`; chips are words with dot separators; the CTA is a caption line, never a button |
| Readable without a panel | **ground haze**: a large soft backdrop blur (28px) + a veil in the ground's own lifted colour, under a long 290px gradient mask — edgeless, no blotches, reads as depth of field |
| Same grade everywhere | one CSS filter on photo + cutout, warm bleach, haze, seeded grain |
| Fonts | DM Serif Display (headline + credit), Jost 300/400 (captions, data). No third face |

Chart theme: emphasis by **ink density** (full weathered ink vs 36% ink), not hue — ≥3.1:1 on every ground
tested, ΔE 29–42; details in `themes/sunfaded.json` `_notes`. Sky-deep blue was tried and rejected (1.1:1 on grass).

## 3. Per-slide fields
Standard: `headline` (the gold word — a number works: `"0.50%"`; `"LINE ONE\nLINE TWO"` for two lines),
`subtitle` (caption), `content`, `cta_pill` + `cta_soft` + `microcopy` (said as caption lines), `kicker`
(optional small line under the top hairline), `bg_file`, `meta3` (**photo credit**, printed in the foot line).
Plan: `handle` (credit line), `tagline` (foot left), `logo` (or per slide).
`hero_word`, `topic_tag`, `brand_label`, `meta1`, `meta2` are accepted but not shown (the sheet has no slot).

Style knobs (read from the slide JSON; px, or 0–1 = fraction of 1350):
| field | default | what |
|---|---|---|
| `subject_file` | — | transparent cutout, same size as `bg_file` (see §4) |
| `subject_mode` | auto | `vision` (use cutout) · `sky` (canvas sky-key) · `none` |
| `head_top` | 300 | top of the gold headline — set it so the subject overlaps the lower part of the word |
| `head_width` | .88 | headline width as a share of the plate (auto-fitted) |
| `head_max` | 420 | cap on headline size (px) |
| `rule1` / `rule2` | 150 / 860 | the two hairlines; caption + proof stack from `rule2` down |
| `ground_blur` | 28 | haze strength (px); `0` turns it off |
| `ground_top` | rule2 − 190 | where the haze starts |
| `caption_alpha` | .84 | caption opacity |
| `attribution` | — | small line under the caption (quotes) |
| `numeric_guard` | 1 | `0` disables the number-occlusion guard (don't) |
| `max_cover` / `max_cover_punct` | .15 / .02 | allowed coverage per digit / per punctuation glyph |
| `credit_text` | `Design by <handle>` | override the credit |
| `photo_pos` | `50% 50%` | object-position if the photo isn't pre-cropped |
| `content_top`, `cta_top`, `caption_gap`, `content_gap`, `foot_clear` | auto | manual layout overrides |
The lower block auto-lifts (with its hairline and haze) if it would run into the foot line.

## 4. Photos and cutouts (the whole style depends on this)
1. **One photo per slide, never reused.** Pastoral world: a single subject (house, barn, windmill, bale,
   silo, lone tree) with sky above and open ground below. Search Commons with *simple* terms
   (`"hay bales field"`, `"windmill field"`) — queries containing "sky" return almost nothing.
2. **Composition decides everything.** Reject photos where the subject fills the frame (tractor, big oak):
   the headline disappears. Data slides need a *calm* lower third; a subject there fights the chart.
3. **Resolution:** fetch_photos gives 1920px thumbnails, which crop to ~860–1150px wide. Prefer originals
   ≥3840px wide and request the `3840px-` thumbnail (standard size; other sizes 400, and originals get
   rate-limited — back off).
4. **Pre-crop to 4:5** around the subject (full height, width = 0.8 × height) so the cutout aligns and
   Vision sees a bigger subject:
   `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/cutout.py photo.4x5.jpg photo.4x5.cutout.png` (free, local; rembg or npx hyperframes remove-background).
   Always look at the cutout. The cutout engine misses small subjects and trees — then leave `subject_file` empty
   and the template sky-keys (works when the subject stands against clear sky).
5. Credit every photo in `meta3` ("Photo · Author · Licence").

## 5. Logos
Real logo in the credit line, one colour, in the sampled sky colour: set `logo` to a **PNG**
(`assets/logos/<x>.png`). Badge logos (opaque plate + white strokes, e.g. the Instagram glyph) keep only
their white strokes; transparent logos keep their alpha. (SVG logos currently fail — the renderer embeds
non-PNG assets with a JPEG mime type.)

## 6. Known limits
- Big subjects hide the headline; the sheet's own example hides ~40% of it — stay near that. Numbers are
  guarded automatically (§2), but set `head_top` sensibly anyway: the guard only ever moves the word up.
- **Sky-key on hazy horizons:** pale distant hills can read as sky and let a letter show through a gap.
  If a sky-keyed slide shows any bite or fragment, don't ship it — use a photo with a local cutout, or
  `subject_mode: "none"` as a last resort.
- The sky-key treats pale/white subject parts as sky (use local cutouts for white subjects).
- Canvas work runs after fonts/images load; the renderer's 220ms settle has been enough in tests.
