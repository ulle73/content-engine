# Where vibecode comes from

Reverse-engineered from two edits Jade supplied on 2026-08-29. Every colour,
size and frame count in `../assets/tokens.css` is **measured off these two
files**, not chosen. This page is the audit trail: if a token looks wrong,
check it here before changing it.

## The two references

| | REF-B — **the spine** | REF-A — **the furniture** |
|---|---|---|
| URL | `youtube.com/watch?v=Ohyo6-VO1jY` | `youtube.com/watch?v=vI4RdXMSq8c` |
| Title | *I taught Claude how to use Premiere Pro and it's INSANE.* | *How I Fully Automated Video Editing (Claude Code)* |
| Creator | Jason Cooperson | Sandy Lee AI |
| Range Jade cited | **0–45s** ("especially this one") | 0–1:20 |
| Captured | first 70s | first 200s |
| Native | 1920×1080 **@23.976fps** | 1920×1080 @30fps |

> ⚠ **REF-B is 23.976fps.** Every frame count taken off it was converted to
> 30fps (×1.2513) before it entered `tokens.css`. If you re-measure it, convert
> again — a count copied raw runs ~20% fast.

## Why REF-B is the spine

They are not the same palette. REF-B is saturated cobalt cut-paper collage;
REF-A is restrained cream-and-gold app chrome. Jade said "especially" REF-B, and
REF-B is the more distinctive instance, so **its material is the style**: paper,
marker, sticker, halftone, stop-motion churn.

REF-A is not discarded. Its contribution is **structural, not visual** — the
idea that the frame is a piece of software being operated. Its widgets (timeline
HUD, numbered step list, meter card, scrub rail) are rebuilt in REF-B's paper
material. Its cream palette survives as the `.vc-cream` ground for calm chapters.

**What they share — this is the actual DNA:**

1. The frame is a **workspace being operated on**. Both draw a fake editing
   timeline that builds block by block (REF-B on notebook paper, REF-A as a
   sleek HUD).
2. A **red hand-drawn negation** kills the old way — REF-A strikes a line
   through text at 14.6s, REF-B lands a big red X on each tile at 30–36s.
3. **Sequential build.** Things arrive one at a time in a list or row with a
   label, like an agent working a task list.
4. **Real app iconography as first-class art** — the Premiere icon is a hero
   shot at REF-B 11.2s.
5. **A non-human character stands in for the AI** — REF-B's pixel blob, REF-A's
   wooden robot b-roll. Neither ever cuts to a random human.
6. **One saturated accent on a flat ground**, heavy caps, near-black ink.
7. **Captions hard-cut.** Verified on REF-A at 27.9–28.3s: the lozenge is
   present for 3 frames and gone on the 4th, no fade.

## Measurements → where they are written up

| Finding | Evidence | Written up in |
|---|---|---|
| Ground `#226DE5`, halftone dots, radial lift + vignette | `stills/09-refB-ground-plate.png` (empty plate) | `look.md` §1 |
| Paper `#FEFEF5`, torn edge, hard offset shadow, no blur | `stills/05-refB-paper-timeline.png` | `look.md` §2 |
| Chromatic fringe — magenta leading, cyan trailing edge | `stills/06-refB-redX-tiles.png` (visible on tiles **and** type) | `look.md` §3 |
| Clip blocks `#3DDEFE` / `#FF9EC0` / `#2F68E0`, navy outline | `stills/05-refB-paper-timeline.png` | `layouts.md` §2 |
| Ink `#162949` | gear pictogram, `stills/06-refB-redX-tiles.png` | tokens |
| Red `#E54926` — negation only | `stills/06-refB-redX-tiles.png` | `look.md` §4 |
| Yellow `#FFDD36` — arrows, sparkles | `stills/07-refB-title-arrow.png` | tokens |
| Display type: heavy condensed caps, cream `#FFF9EB`, hard navy offset shadow | `stills/07-refB-title-arrow.png` | `typography.md` |
| Real assets get a scissor-cut white paper border | `stills/08-refB-sticker-appicon.png` | `look.md` §2 |
| **Stop-motion churn** — icons shuffle between cards every 2–3 frames, cards jitter in rotation, sparkles blink | `strip-B-cardin` (native fps, 4.0–4.85s) | `motion-grammar.md` §1 |
| Elements arrive with rotational overshoot and settle (~20f @24 → 25f @30) | `strip-B-title` (26.2–27.05s) | `motion-grammar.md` §2 |
| Red X: two strokes, second lags the first | `stills/06-refB-redX-tiles.png` + sheet 04 | `motion-grammar.md` §3 |
| Caption hard-cuts out, zero frames | `strip-A-caption` (27.9–28.6s, 30fps) | `motion-grammar.md` §4 |
| Timeline HUD, step list, meter card, scrub rail | stills 10, 11, 13 | `layouts.md` §3–5 |
| Cream ground `#F7F1DD`→`#F4E8CC`, gold `#D3A74B`, ink `#11140C` | `stills/12-refA-question-slide.png` | `.vc-cream` in tokens |
| Dark teaser ground `#19140A` | `stills/15-refA-comingup-dark.png` | `.vc-dark` in tokens |

## Deliberate divergences from the references

Both reels do things this studio does not. These are **decisions, not misses**:

- **REF-A puts an emoji on the strike slide** (14.6s, 😩). The house rule bans
  emoji on screen. vibecode replaces it with a designed mark — a navy pictogram
  on a paper tile, exactly as REF-B does at 34s. Jade confirmed this on
  2026-08-29.
- **REF-B cuts to a full-frame talking head with no treatment.** Fine there;
  here the head is a cut-out card on the ground (`.vc-head`) in every scene
  except the clean-face rest beat, because our long-form runtime needs the
  layout rotation.
- **Neither reel labels its sources.** Our fact-verification rule still applies:
  every figure on screen is checked while sourcing.

## Re-capturing the references

The clips are not committed (rights). To pull them again:

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]" \
  --download-sections "*0-70" -o refB.mp4 \
  "https://www.youtube.com/watch?v=Ohyo6-VO1jY"
```

`yt-dlp` warns about a missing JS runtime and still works. Measure colour with
dominant-count over a crop, never a single pixel — anti-aliasing on this style's
hard edges will hand you a blend of two tokens and you will write it down as a
third.
