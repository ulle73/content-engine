# Photo mode: bring finished slides to life

The promise is that **frame 0 looks identical to the user's original image**. Only a fine film grain is added. Every effect sits on
top of the image, or re-paints pixels that match it, and everything returns to rest before the loop
point. Nothing is regenerated and the design never breaks.

## Layers (made by `prep_photo.py`, per slide in `assets/NN/`)

| file | what | used by |
| --- | --- | --- |
| `bg.jpg` | the original at 2160x2700 (crisp under camera push) | base layer, `PH.lift` |
| `clean.jpg` | text inpainted away | the sky shader's displaced lookups next to text |
| `flow.png` | R,G = wind direction, B = how much each pixel may move | `PH.cinemagraph` |
| `text.png` | matte of all detected text and graphics | `PH.shine` sweeps |
| `head.png` | the headline letters only, in their own tone | `PH.extrusion` + the flat re-paint on top |
| `accent.png` | saturated shapes over the headline (brush words, stickers) | re-painted above headline effects |
| `subject.png` | (`--cutout`) the person or product, defringed | parallax pop |
| `geo.json` | boxes in canvas px: `text`, `headline`, `subject`, plus `palette.accent/accent2`, `headline_color` | the slide script, as `GEO` |

### Fixing the masks (always look at `prep/NN_maskvis.jpg`)

- **Sky or background frozen (too much red):** raise `--busy` (for example 0.09). Busy textures stop
  counting as detail.
- **Text, faces or logos drifting (not red enough):** lower `--busy` (0.04).
- **Headline missing or partly missing:** lower `--edge` (50) for soft or low-contrast type. If junk
  is picked up as text, raise it (90).
- **Headline box wrong:** edit `"headline": [x0, y0, x1, y1]` in `assets/NN/geo.json` by hand. The
  slide reads the box from there. (head.png still comes from detection: re-run with other flags if
  the letters themselves are wrong.)
- Re-run only one slide: `prep_photo.py --only 03`.

## Cues (`carousel.json → cues.NN`), shared by the slide and the audio

```json
"02": { "dur": 6, "hits": [2.0], "shine": [0.6, 3.6], "extrude": true,
        "sky": 0.012, "motes": 16, "push": 0.022, "hitAt": [540, 640] }
```
- `dur`: 4, 6 or 8 (whole bars). `hits`: the big moments. Each one fires a camera kick, a flare,
  rings, sparks and a sub boom with a crash. The first hit is the main one, and extrusion pops on it.
  Keep hits on the 0.5 s grid and at least 0.8 s before `dur`.
- `shine`: start times of the light sweeps across the text (each one 0.5 s, with a sparkle sound).
- `extrude`: a 3D extrusion behind the headline, in the slide's own accent colours. It is safe on
  pure white or near-black type. Turn it off if the headline sits on a busy photo or the matte looks rough.
- `sky`: cinemagraph drift (0.008 is subtle, 0.02 is strong, 0 turns it off). `motes`: floating dust
  and sparkles (0 turns them off). `push`: slow camera push-in (0.02 to 0.03). `hitAt`: where rings
  and sparks burst (default: just under the headline).
- The cover (slide 01) defaults to a hit at 0.5 s, because people decide in half a second.

## The `PH` toolkit (window.PH, in `shared/photo.js`)

| call | effect |
| --- | --- |
| `cinemagraph(canvas, {bg, clean, flow}, {period, amp})` → `sky(t)` | WebGL flow-map drift on the movable areas (seamless over `period`) |
| `camera(stage, DUR, [[t, amp]...], {push})` → `cam(t)` | slow push-in plus decaying shakes on hits |
| `extrusion(parent, mask, n, {front, back})` → `ext(depth)` | stacked offset copies behind a matte, so a flat headline turns 3D |
| `masked(parent, mask, background)` | any fill through a matte (re-paint the face flat, tint, glow) |
| `lift(parent, imgUrl, mask, box)` → `set(scale, dy, depth, rot)` | the photo's own pixels under a matte as a movable layer. **Keep scale ≥ 1** so it always covers the baked copy |
| `shine(parent, mask)` → `sweep(p)` | a light band across a matte; p in 0..1, hidden outside |
| `brush(parent, url, box)` → `set(pop, rot, shineP, lift)` | pop + wet-paint shine for a keyed-out brush word |
| `flare(fx, x, y)` → `f(t, t0)` · `ring(fx, cls)` → `r(t, t0, x, y, maxS, life)` | impact light and shockwave rings |
| `motes(fx, n, seed, opts)` → `m(t, gain)` | dust, sparkles, fireflies; periodic, so loops are seamless |
| `leak(parent, color, DUR)` → `l(t, gain)` | a soft coloured light drifting across |
| `pills(parent, pills, onTimes, offTimes)` → `p(t)` | pills or tags that light up in sequence, with a spark running between them |
| `counter(parent, box, {to, prefix, suffix, decimals, style})` → `c(p)` | count-up text that covers a baked number |
| `cursor(parent)` | a pointer SVG; move it with `style.transform` |
| `echo(parent, mask)` → `e(d)` | two-colour offset echo of a matte |
| `pop(t, t0, rise, fall)` | 0 → fast rise → slow settle envelope (never negative) |

`LC` (engine.js) is loaded too: `settle`, `kick`, `prog`, easing, `makeBurst`, `hash`.

## Moment recipes (pick one per slide, matched to what the slide says)

- **Stat or number slide → count-up.** Inpaint the baked digits out of a card crop first. Use
  `cv2.inpaint` on a small box in a prep step, like the template's `clean.jpg`, and save it as
  `assets/NN/card.png`. Then show the card crop over the original and run `PH.counter` on top from
  0 to the value, with a tick sound per step. Frame 0 must match the original, so the counter shows
  the final value at t=0. On a beat it blinks or resets to 0, counts back up, and lands on the final
  value before the loop point.
- **List or tags → pills light up** one by one on eighths (`PH.pills`), a `pop` sound each.
- **Chart → bars grow.** Lift each bar (`lift` with a rectangular mask), scale Y from the baseline
  from 1.0 to 1.12 and back on the beat, or sweep a `shine` across the bars.
- **Person or product → parallax pop.** Use `--cutout`, then scale `subject.png` 1.00 → 1.03 on the
  hit with `pop`. The background drifts behind it.
- **CTA → a cursor presses the button.** `PH.cursor`, a press (scale 0.92) on the beat, a ring and a
  `click` sound, and a `shine` across the button.
- **Brush or script word → wet-paint shine** and a small pop (`PH.brush` with a keyed matte).
- **Cover → hit at 0.5 s**: extrusion pops, the camera kicks, sparks fly, and the sky starts moving.

## Pitfalls

- An effect that moves baked pixels must cover the originals. Scale ≥ 1, or put a clean plate under it.
- A re-paint matte must be the same tone as the original pixels. Use `head.png` for white or black
  type, and `accent.png` with the original pixels for coloured strokes.
- When text sits on a busy photo, prefer `shine` and camera over `extrude`.
- Leave fine print (credits, captions) untouched. It is held still on purpose.
