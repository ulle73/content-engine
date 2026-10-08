# Source study

One link, one creator, one 39.9-second reel. Everything in `assets/tokens.css`
marked MEASURED was read off it; everything marked DERIVED was reasoned from it
and is flagged as such wherever it appears.

| | Link | Role |
|---|---|---|
| **REF-A** | `instagram.com/p/Db2RzkxvWpz/` | the only style reference |

Spec: 1080×1920, **30fps**, 39.937s, 1198 frames, H.264 + AAC 44.1k stereo.
Creator: `zacharyronusac`.

> ⚠ **This is another creator's work.** Zak is the *technique* — the window
> geometry, the caption system, the stillness, the type pairing. Their words,
> their room and their delivery are theirs. `scripts/check-zak.sh` flags
> `work-life balance`, `sunshine and rainbows` and the handle as `BORROWED`
> if any of it resurfaces in a segment.

> ⚠ **One reel is a thin base, and the skill says so where it matters.**
> Geometry and type were measurable to the pixel and are trustworthy. The
> GRADE was measured in one room under one lamp, so `look.md` separates what
> is the style from what is that creator's window light. The SCENE VOCABULARY
> beyond the single locked frame is invented — `layouts.md` marks each scene
> measured or derived. A second reel from this creator would firm up the grade
> and settle whether the window ever changes; if one turns up, start there.

---

## Method

```bash
yt-dlp -o 'refA.%(ext)s' <url>
ffmpeg -i refA.mp4 -vf "cropdetect=limit=24:round=2" -t 20 -f null -    # the window
ffmpeg -i refA.mp4 -vf "fps=1,scale=190:-1,tile=8x5" -frames:v 1 sheet.jpg
ffmpeg -ss 9 -i refA.mp4 -frames:v 1 -vf "crop=W:H:X:Y,scale=3x" crop.png
```
Then, in numpy over raw `rgb24` frames:
- **Geometry** — row and column luminance profiles over the full 1198 frames.
  Rows above a luma-3 threshold separate the title band from the window band
  cleanly, because the ground is literally 0,0,0.
- **Corner radius** — first-lit column per row down the corner, arc-fitted.
  `inset = R − √(R² − (R−dy)²)` matched R=70 at every one of 23 sampled rows.
- **Type** — near-white bounding boxes for size and position; then candidate
  faces rendered at matched x-height and fitted for width.
- **Cadence** — XOR of the thresholded caption band between consecutive
  frames, over all 1198.
- **Verification** — the tokens rendered back through headless Chrome at
  1080×1920 and diffed against the source frame. `stills/09`.

---

## The findings, and where each is written down

| Finding | Evidence | Written up in |
|---|---|---|
| Ground is pure `#000000`, not near-black | 7 points × 120 frames | `look.md` §1 |
| Window 968×968 **square**, x=56, y=476 | row/col profile, 240 frames | `layouts.md` §1 |
| Air above = air below = 476px, **exactly** | 476+968+476 = 1920 | `layouts.md` §1 |
| Corner radius **70px** | arc fit over 23 rows | `layouts.md` §1 |
| Window never moves or scales, 0px over 40s | static-edge correlation | `motion-grammar.md` §1 |
| No push-in, no drift, no parallax | bright-span width, 5 samples | `motion-grammar.md` §1 |
| Title line **Playfair Display 400 ≈56px** | width fit 872 vs 878 measured | `typography.md` §1 |
| Title is set once and **never changes** | 80 frames diffed, max Δ 1.8/255 | `layouts.md` §2 |
| Caption **Helvetica-family bold ≈63px** | x-height 36, baseline 1042 | `typography.md` §2 |
| Caption tracking **−0.065em** | in-browser fit to a 624px string | `typography.md` §2 |
| Caption has **NO shadow and no stroke** | ring sampling at 2-3px vs 8px | `captions.md` §2 |
| Caption **hard-cuts, 0 frames** | XOR: 7000+ on the cut frame, ~30 either side | `captions.md` §1 |
| Captions are **2-4 word phrases** | 53 changes read off the sheet | `captions.md` §1 |
| Hold mean 22f, floor 7f, ceiling 44f | 53 changes over 39.9s | `captions.md` §3 |
| Plate mids **B−R = −53**, mean luma 90 | 120 frames, band-split | `look.md` §2 |
| Plate floor 24, ceiling 151 — neither clips | percentiles, 120 frames | `look.md` §2 |
| **Caption band luma 126** (min 121, max 129) | 120 frames | `look.md` §3 |
| One continuous take, no cuts | scene-score, whole file | `layouts.md` §3 |
| No silence ≥0.35s at −35dB in 40s | silencedetect | `sound-design.md` |
| Tokens reproduce the frame to ±1px | headless Chrome round-trip | `stills/09` |

---

## Shot log — REF-A (39.9s)

There is only one shot. That is the finding.

| t | What changes |
|---|---|
| 0.00 | Title line up, window up, first caption up. No fade-in, no intro card. |
| 0.23–39.37 | **53 caption changes.** Nothing else changes at all. |
| 39.94 | Ends. No outro card, no logo, no CTA. |

The camera does not move. The window does not move. The title does not move.
The subject is the only thing in motion in the entire frame for 40 seconds, and
the caption changing every ~22 frames is the only edit. Whatever else you take
from this reel, that restraint is the style.

---

## Stills

| File | What it shows |
|---|---|
| `01-full-frame.jpg` · `02-full-frame-alt.jpg` | the whole thing, two moments |
| `03-contact-sheet-1fps.jpg` | 40 frames — the layout never varies |
| `04-header-type-3x.png` | the Didone ball terminals that identify Playfair |
| `05-caption-type-3x.png` | the tracking, and the absence of any halo |
| `06-corner-radius-4x.png` | the 70px arc at 4× nearest-neighbour |
| `07-caption-hardcut-8f.png` | 8 consecutive frames across one caption change |
| `08-frame-half.jpg` | the frame at 1/2 for judging the air |
| `09-reference-vs-tokens.png` | **the round-trip** — source beside the tokens |
| `10-derived-16x9.png` | the derived 16:9 window on a real plate |
