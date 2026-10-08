# Source study

The three links Jade supplied, what was taken from each, and how.

| | Link | Role |
|---|---|---|
| **Reel A** | `instagram.com/p/DcgMgW6yahM/` | primary style reference |
| **Reel B** | `instagram.com/p/DcOJfx0SXyN/` | primary style reference (same creator) |
| **Reel C** | `instagram.com/p/DcBwAjvoEqI/` | **font shelf only** — different creator, different look |

Specs: A 1080×1920 30fps 38.7s · B 1080×1920 30fps 67.6s · C 1080×1920 **24fps** 52.8s.

⚠ **Reels A and B are another creator's work.** Persa is the *technique* — the
grade, the caption system, the matte compositing, the scene rotation. Their copy,
their product names, their brand marks and their pixel-art characters are theirs.
`scripts/check-persa.sh` flags "OpenCurve", "Artzen", "Grok Bot" and the reel C
font names as `BORROWED` if any of them resurface in a segment.

---

## Method

```bash
yt-dlp -o "%(id)s.%(ext)s" <url>
ffmpeg -i reel.mp4 -vf "fps=1,scale=260:-1,tile=7x6" -frames:v 1 sheet.jpg   # structure
ffmpeg -ss <t> -t 1.2 -i reel.mp4 -vf "crop=...,scale=..." anim/%02d.png     # 30fps steps
ffmpeg -ss <t> -i reel.mp4 -frames:v 1 -vf "crop=W:H:X:Y,scale=..." crop.png # 2-4x type
```
Then per-band channel statistics in numpy for the grade, near-white pixel
bounding boxes for the type geometry, and rendered font candidates at matched
cap-height for the face identification.

---

## The findings, and where each is written down

| Finding | Evidence | Written up in |
|---|---|---|
| Blue crushed −18 to −28 in the mids | 98 sampled frames | `grade.md` §2 |
| Green lifted in shadows + highlights | same | `grade.md` §2 |
| Two densities, one look (A hazy / B clean) | A vs B endpoint spread | `grade.md` §3 |
| Vignette corner/centre = 0.57 | 39 frames | `grade.md` §2 |
| Grain temporal σ = 8.3 on a static wall | 15 consecutive frames | `grade.md` §2 |
| **Captions hard-cut, 0 frames** | `stills/10`, 36 frames @30fps | `captions.md` §1 |
| Caption fixed at 73.0–73.7% height | 3 frames, near-white bbox | `captions.md` §1 |
| Caption cap-height 38px @1920h | same | `typography.md` §2 |
| **Emphasis word sits BEHIND the matte** | `stills/01`, `05`, `06` | `captions.md` §3 |
| Emphasis cap-height 153px = 4× caption | `stills/05` | `typography.md` §2 |
| Matte has a light rim fringe — keep it | `stills/06` at 3× | `layouts.md` §5 |
| Panel 86% wide, top 8%, r≈30px | `stills/02`, edge scan | `layouts.md` §2 |
| Head card 80% wide, top 58–60% | `stills/03`, `04` | `layouts.md` §3 |
| **Panel exits by fading in place, 8f** | `stills/11`, 24 frames @30fps | `motion-grammar.md` |
| Red #DE2B2A · lime #BEE24B · amber #D48D33 | bright-core means | `assets/tokens.css` |

---

## Shot log — Reel A (38.7s)

| t | Scene | Note |
|---|---|---|
| 0.0–0.5 | 5 Hand-Note | hand line begins mid-word, already on screen |
| 0.5–4.5 | Slam | hand line + red display word, **both behind the head** |
| 1.0–4.5 | — | app chip pill top-centre, dark translucent |
| 5.5–12.5 | 2 Panel Over Face | screen recording, cap breaks the bottom edge |
| 12.9–13.7 | — | **panel fades out in place over 8f**; wordmark holds longest |
| 13.5–17.0 | 3 Media Full / Head Card | UI punched in, head card bleeds off bottom |
| 20.0–24.0 | 4 Split | head breaks out through the top of its own card |
| 24.5–26.0 | 5 Hand-Note | lime approval note |
| 26.5–31.0 | 1 Clean Face | ~5s rest beat |
| 31.5–35.5 | 5 Hand-Note | lime, one word |
| 36.0–38.7 | CTA | hand line + red word + drawn pointing hand (not an emoji) |

## Shot log — Reel B (67.6s)

Same vocabulary at a faster rate. Notable additions:
- **Curved-baseline hand note** following the ceiling seam (~9.2s) — text set on a
  path that matches a real line in the room. Written up in `layouts.md` §5.
- **Outlined emphasis words** in amber and white behind the head — "MANUALLY"
  (~7.3s), "THING" (~11.0s), "AGAIN" stacked (~13s), "TIRED" (~60s).
- A long chat-thread sequence (25–55s) run entirely as scene 3, the head card
  holding steady while the media above changes every 1–2s. Worth studying as the
  answer to "how do I keep a long screen-recording section alive".
- Pixel-art character sprites with name labels. **Content-specific to that video,
  not a style element** — do not carry them over.

## Reel C — what was taken

Three font names only: **Impact**, **Snell Roundhand**, **Rocktown**
(`typography.md` §4). Its own layout and grade are not persa and must not be mixed
in. Rocktown is commercial and must be licensed before it ships.
