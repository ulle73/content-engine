# Style — Sky-Blue Tech Poster (`skyblue`)

Sheet: `library/kits/carousel-kit/carousel/assets/styles/skyblue.jpg` · template: `scripts/template-skyblue.html` ·
chart theme: `scripts/themes/skyblue.json` · plan: `"template":"template-skyblue.html","theme":"skyblue"`

## 1. What the sheet says (read as a spec)
| Panel | Finding |
|---|---|
| Palette (sampled — the sheet prints no hex) | Gradient magenta `#CE3FC3` → pink `#F4428C` → orange `#FC7E41` · white `#FFFFFF` · navy field `#2C4E72` · sky pale `#95BCDD` · tan/skin `#DD956D` · silver `#E5E6EA → #F9F9F9 → #D5D6DC` |
| Type specimen | Two-line headline in a heavy **condensed sans, all caps** (Anton), the **last line larger** ("THE ART OF VIRAL / CAROUSELS"). **One word** is re-written over itself in a **brush script in the gradient** (the white word stays visible underneath). Top line `**Category** │ @handle` (bold + regular sans). A centred sans paragraph (Inter). |
| Hero image | Sky + clouds photo, full-bleed. The **subject stands in front of the headline**: its top covers the lower part of the last line. On the sheet the subject wears a headset whose screen shows the real Instagram logo on a silver bezel. |
| Thumbnails | Same subject, different crops — framed by thin white rules. |

## 2. Rules the template enforces
- **All type is white.** Hierarchy is size / weight / condensed-vs-sans only. Secondary text is white at lower opacity or `#C3DAEE` (a lightened sky) — never another hue.
- **The gradient exists in exactly one element per slide:** the brush re-write of `hero_word`. Real brand logos keep their own colours. The gradient never touches charts, frames, buttons or body text.
- **Navy `#2C4E72` is the field; sky photography is the world.** `layout:"field"` = navy (lightly toothed); `layout:"photo"` (default when `bg_file` is set) = full-bleed sky with a navy scrim that deepens the top and extends just past the last line of type, so white never sits on a bright cloud.
- **The headline is condensed caps, last line biggest** — last line auto-fitted to `head_w` × plate width, earlier lines to 93% of that but never above `head_ratio` (0.64) × the last line's size.
- **Put the accent word on a SMALL line (line 1).** On the huge last line the brush doubles up and reads as noise (tested). The brush is capped at ~1.12× the word's width (squeezed, then shrunk) and clamped inside the frame.
- **Subject in front of the headline** on hero slides: `photo → headline → cutout → logo`.
- **Frames are thin white rules, square corners.** Cards = deep navy `#1F3A57` + 3px white border. No filled buttons: the CTA is a white-outlined frame. **Silver is only for devices/bezels** (the logo "screen").
- Proof still sits mid/low on data slides (field: centred under the subtitle; photo: anchored low so the sky stays open).

## 3. Per-slide fields (plan.json)
Standard: `headline` (lines split by `|`), `hero_word` (the brushed word — pick one from line 1), `subtitle`, `content`, `kicker` (optional small line above the headline), `topic_tag` (the bold category in the top line; falls back to plan `brand_label`), `cta_pill` + `cta_soft` + `microcopy`, `bg_file`.
Style knobs (read from `__SLIDE_JSON__`):
| field | meaning |
|---|---|
| `layout` | `"photo"` (default if `bg_file`) or `"field"` (navy) |
| `bg_pos` | CSS object-position of the sky photo, e.g. `"50% 40%"` |
| `subject_file` | transparent cutout PNG. Same size as `bg_file` → **aligned** over the photo; or a trimmed cutout + `subject_box` |
| `subject_box` | `{x (centre px), w, y or bottom, rot, flip}` to place a trimmed cutout from another photo |
| `logo` (slide or plan) + `logo_box` | real logo file + `{x (centre), y (top), w, rot, ry (3D tilt), frame:true}` — `frame` draws the silver bezel + sky screen |
| `credit` | photo credit line (centre of the bottom rail) — required for every photo |
| `head_top`, `head_w` (0.86), `head_ratio` (0.64), `head_max` (300) | headline geometry |
| `brush_scale` (1.0), `brush_w` (1.12), `brush_rot` (−6), `brush_dx`, `brush_dy` | brush re-write tuning |
| `sub_top` / `sub_gap` | subtitle position (default: 34px under the headline) |
| `content_place` (`bottom`/`center`), `content_bottom`, `cta_bottom` | proof / CTA position |
| `scrim`, `scrim_mid`, `scrim_bottom` | override the automatic navy wash |
| `cue:false` | hide "SWIPE →" (auto-hidden on the last slide) |

## 4. Sourcing photos + cutouts ($0)
1. Skies: `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_photos.py work/carousel-kit/photos/<set> "cumulus clouds blue sky" "blue sky white clouds" ...` — **one different photo per slide**; check each (reject sunsets/storms — the world is clear daytime blue).
2. **Resolution:** the 1800px previews are soft when cropped to 4:5 and rendered at 2×. For the hero (and any subject), fetch a larger rendition from the Commons API (`iiurlwidth=3200`) — the hook's first version was visibly smeared until this was done.
3. Subjects: pick photos whose subject separates cleanly (a headset on a display head, a balloon, a person on a plain backdrop). `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/cutout.py <photo> <out.png>` (free, local: rembg or npx hyperframes remove-background). **Look at every cutout on a magenta background** before using it.
4. To place a subject on a *different* sky, trim it: `PIL: c = Image.open(cut); c.crop(c.getbbox()).save(...)`, then set `subject_box`. A subject cut from its own photo can stay full-size (aligned) — but check it doesn't cover more than the lower part of the last line.
5. Logos: `library/kits/carousel-kit/carousel/scripts/fetch_logo.py` (see `logos.md`), placed with `logo_box` — never redrawn.
6. Credit every photo in `credit`.

## 5. Chart theme
Emphasis white `#FFFFFF` vs muted darkened-sky `#7F9DBC` on plate `#1F3A57`: CVD ΔE 30.5, normal 32.1, both ≥ 3:1 (band/chroma checks are categorical-only and fail by design for an emphasis pair; every mark is directly labelled). Ordinal ramp `#5A7FA6 → #E6F0F9` passes all ordinal checks. Details in `themes/skyblue.json` `_notes`.

## Known limits
- Brush font is Permanent Marker (closest free match); the sheet's brush is more italic — the template skews/rotates it.
- A very tall `content` block on a field slide can reach the rail — keep cards to ~480px (charts `h_scale` 0.84 helps).
- The subject-in-front effect needs a clean cutout; busy photos give ragged edges.
