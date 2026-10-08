# Style: Own images (`template-own.html`, theme `own`)

For users who bring their **own photos** (a café, a dentist, a roofer, a creator). The photo is
the world; the design is the type laid over it. There is no stock or AI imagery. There are five
layouts, one per slide, chosen with `layout`. Previews are in `library/kits/carousel-kit/carousel/assets/own-images/previews/`
(`_gallery.jpg`), and the design references behind them are described in `knowledge/own-images-layouts.md`.

```json
{ "template": "template-own.html", "theme": "own" }
```

## Per photo
1. Put the user's photos in `work/carousel-kit/my-images/<client>/`.
2. Cut the subject out: `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/cutout.py photo.jpg cutouts/photo.png` (free, local).
   Set `subject_file` to the cutout. It must be the same pixel size as the photo; `cutout.py` guarantees this.
   No subject found? Leave `subject_file` out. Every layout still works, placing type from the
   photo's busyness and brightness only.
3. Set `bg_file` (the photo) and, if the crop needs steering, `photo_pos` ("30% 50%" = the cover-crop
   anchor. The cutout follows the same crop automatically).

## Choosing a layout
| Photo | Layout |
|---|---|
| One person/object with **empty space above** the head | `orbit` (headline behind the head) |
| Subject low or centred, **calm top 40%** | `punch` |
| Subject on one side, **calm wall/space on the other** | `editorial` (also the only layout that shows `content` data) |
| Subject to one side, open space to scatter words into | `scatter` |
| Subject on one side, tall open strip beside it | `cascade` |
| No person (room, product, building) | `editorial`, `punch`, `scatter` |

Vary layouts across a set; the fonts, grade and grain keep it one piece. Use the same accent colour
across the set by setting `accent` on every slide, or let each photo choose its own.

## Fields (all per slide unless noted)
Common: `layout`, `bg_file`, `subject_file`, `photo_pos`, `accent` (hex; overrides the sampled
colour, lightness still auto-adjusted for contrast), `accent_text` (hex, used exactly as given), `side`
("left"/"right", forces the text side), `handle` (else plan `handle`), `index` (page number, shown as
`01 / 06`). Plan: `handle`, `tagline`, `brand_label`, `logo`.

| layout | fields | copy that fits |
|---|---|---|
| `scatter` | `headline` (words split on spaces, or on "/" to keep phrases together), `pill` (or `kicker`), `series` (lockup, digits set in italic; "|" splits lines), `size`, `words_top`, `words` [{x,y}] per-word override | 4–8 short words |
| `editorial` | `headline` (2 lines; "|" to split), `subtitle` (body, ≤ 45 words), `content` (chips/stats/bars/chart), `series` (footer left, else plan `tagline`), `cue` (footer right, default "Read caption"), `arrow:false`, `head_w`, `size`, `head_top`; plan `logo` or `brand_label` top-right | headline 1–3 words per line |
| `orbit` | `headline` (1 line, "|" for 2), `kicker`, `byline` (default "By @handle"), `label` (e.g. "Vol 1"), `orbit_text` (else plan `tagline`), `overlap` (share of the word the head covers, default .38), `head_top`, `head_w`, `size`, `max_hidden` (default .4), `force_behind` | 1–2 words |
| `punch` | `headline` (up to 3 lines, "|" to split), `hero_word` (one word of the headline, set in the accent), `script` (the huge italic word), `cta_pill` (default "Let me explain."), `cue` (default "save for later"), `caps_top`, `size`, `script_size`, `subject_front:false` | 6–10 words + 1 script word |
| `cascade` | `headline` (words, alternate roman/italic), `kicker` (small line above), `aside` (or `subtitle`, handwritten note, ≤ 18 words), `size`, `words_top`, `words` [{x,y}] | 4–7 words |

## How placement works
- The photo and cutout are drawn into a 216×270 analysis canvas with the same cover crop. That
  gives a 27×34 grid (40px cells) of **subject occupancy**, **busyness** (luminance std-dev) and
  **relative luminance**, plus the subject's bounding box and its top edge per column.
- **Free side:** left vs right half, scored by occupancy×4 + busyness. `side` overrides it.
- **scatter / cascade:** each word tries x positions across its band and keeps the lowest cost.
  Subject cover is weighted heavily; scatter adds a zig-zag term (no two consecutive words
  aligned) and cascade adds a pull toward a diagonal from the inner edge to the outer edge.
- **orbit:** the headline is fitted to 92% of the width, and its top is set so the subject's top edge
  (in the central 60% of the word) covers the lower `overlap` share. If the subject would hide
  more than `max_hidden` (e.g. the head is at the very top of the frame), the headline comes
  **in front** instead and a warning is logged. The ring is an ellipse around the body whose top
  never rises into the **face zone** (the top 35% of the subject box) or above the byline. The ring
  text repeats at its natural width and only its spacing is eased to close the loop.
- **punch:** caps are fitted to 960px, and the script word overlaps the last caps line by 26% of its
  size. The subject is placed in front of the script unless it would hide more than 45% of it.
- **editorial:** the text block sits on the calm side under a side gradient scaled to that area's
  brightness and busyness, plus a soft pool behind the body when it's busy. The doodle arrow runs
  from the body to the subject (or the opposite side when there is no subject).
- **Accent:** the dominant saturated hue of the photo (warm hues weighted ×1.35), else the photo's
  brightest tone, always used as a **light tint** (hue kept). **All type in this template is light;
  the ground is darkened to fit it, never the reverse, so it never produces dark text on a dark scrim.**
- **Contrast pass (every layout):** after layout, each visible text element gets a blurred darkening
  pool whose strength is *solved* from its colour and the brightest ground cell under its box.
  Targets: 3.5:1 for large type (≥40px, or ≥30px bold), 5:1 for body, 6.5:1 for type under 20px.
  Front text over a shown cutout puts its pool above the cutout; text behind the subject puts it
  below. `contrast_pass:false` turns it off.
- **Editorial column:** stops 40px before the subject. The headline and body keep the width free at
  the top and are shrunk to fit above the first row where the subject reaches further in (hands, a
  cup). Content below gets the width free at its own rows. The doodle arrow ends just outside the
  subject's edge.
- Every slide gets the same film grade, grain and vignette.

## Checks
`library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/check_own.py <run_dir>` renders each slide and flags:
- text outside the frame (24px margin) or overlapping other text (punch caps + script may overlap);
- **pixel contrast**: the slide is re-shot with all text hidden (the final backdrop: photo, grade,
  scrims, pools, grain), and each text colour is compared with the 90th-percentile luminance
  behind its box (10th if the text is darker). It fails below 3:1 for large type and 4.5:1 otherwise.
  Text behind the subject is measured without the cutout.
It also prints the template's own warnings. Add `--save-backdrops` to keep the text-free shots.

## Limits
- Placement is grid-based: it avoids the subject and busy texture, but it can't tell a calm wall from a
  calm but important object. Use `side` / `words` / `head_top` when a photo needs a nudge.
- Orbit needs space above the subject; otherwise it falls back to headline-in-front (logged).
- The cutout must have the same ASPECT as the photo (it may be smaller). `cutout.py` output always
  lines up. Prefer WebP cutouts (`.webp`, alpha kept): the renderer embeds assets inline, and a
  full-size PNG cutout (10MB+) can decode too slowly. The renderer screenshots about 220ms after
  load, and a slide shot before the template finishes has NO text. The template sets
  `window.__ownReady = true` when done; the renderer should wait for it.
- Charts (`content`) render only in `editorial`. The chart theme is neutral grey/white (emphasis by
  brightness) because the accent changes per photo.
- Signage or other brands visible in a user's photo stay visible. Check photos before using them.
