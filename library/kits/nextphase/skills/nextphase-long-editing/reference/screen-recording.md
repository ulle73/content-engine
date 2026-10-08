# Screen-share & demo sections (16:9 only)

The long-form beat the short has no room for. A demo is where the viewer either believes you or
leaves, and a raw unedited screen recording is the fastest way to lose them.

---

## 0 · The layout

**Screen-Share + Bubble.** The screen recording fills the frame; the camera sits in a bubble at
`1364,738 → 1864,1020` (500×282, `--r-card`, `--shadow-cam`, 2px `--hairline` border).

- **Graphics stay out of `x>1300, y>700`** while the bubble is up.
- **Never a full-screen card over the screen recording.** Callouts and labels only — the whole
  point of the layout is that the screen is visible.
- Captions, if on, centre within `x 96–1300` so they clear the bubble.
- The bubble does **not** get a zoom. Zooms are for full-frame face only.

**Bubble-off variant:** for a dense demo where every pixel matters, drop the bubble entirely and
run the screen full-frame. Bring the bubble back at the takeaway. Treat bubble-on and bubble-off
as two distinct layouts for the rotation rule.

---

## 1 · Prepare the recording BEFORE compositing

A raw capture is almost never usable as-is.

```bash
# 1. Normalise to the canvas and 30fps CFR (captures are frequently 60fps or VFR)
ffmpeg -i assets/screen-raw.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,\
pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x201512" \
  -r 30 -fps_mode cfr -an -c:v libx264 -crf 18 -preset slow assets/screen.mp4

# 2. Verify
ffprobe -v error -show_entries stream=width,height,r_frame_rate,avg_frame_rate \
  -of default=nw=1 assets/screen.mp4
```

**Retina captures are 2× (2880×1800 or 3456×2234).** Scaling those to 1920 makes UI text tiny
and unreadable after YouTube's compression. Do **not** fit the whole desktop into the frame —
crop to the region that matters (see §2) and let the rest go.

**Pre-flight the capture itself, before recording if you can:**
- Editor / browser zoom pushed up so body text is ≥ 22px **in the final 1920-wide frame**.
- Notifications off, tabs cleaned, no personal data, no visible API keys, no email address in
  the corner. **Scan every frame you ship for credentials and private info** — this is the beat
  where secrets leak.
- Dark theme, so the capture sits on the dark house background instead of flashing white.
- Cursor visible and moving deliberately.

---

## 2 · The punch-in — the core demo move

A full desktop is unreadable. When he refers to a specific element, **punch into it.**

- Animate the screen layer `scale 1 → 2.2` with `transform-origin` set to the target point as a
  percentage of the frame, `--ease-out`, over ~700ms. Hold, then release back to 1.0.
- Transforms only. **Never** animate `width`/`height` to zoom.
- `transform-origin: 34% 61%` means "the thing at x=653, y=659". Work the percentage out from
  the actual pixel; do not eyeball it.
- Punch in **on the word** that names the element, release when he moves on.
- `whoosh` in, `whoosh-2` out.
- 2.2× is the useful default. Past ~3× a 1920-wide capture goes soft; if you need more, re-record
  at a higher zoom instead of scaling further.

## 3 · Callouts

A coral leader line draws from a label to the exact pixel, with a ring pulsing at the target.

- The ring: 44px circle, 3px `--coral`, `scale .6→1` + fade, then a slow `glow-pulse`.
- The line: SVG path, `draw-on` via `stroke-dashoffset`, 3px `--coral`, 260ms.
- The label: `--font-ui` 700 30px on a `--panel` pill, `--r-pill`, entering `clip-reveal` from
  the line's end.
- Sound: `futuristic-click` on the ring, `pop` on the label.
- **Max two callouts on screen at once.** More reads as a diagram, not a demo.

## 4 · Cursor and typing

- **The real cursor is often too small and too fast.** If it matters, add a designed cursor
  layer: a 28px arrow or a soft coral halo tracking the real one, so the eye can follow it.
- **Typing is a sound beat.** Any visible typing gets `keyboard`, gain ~0.10, for the duration of
  the typing — not a single hit at the start.
- **Never show real typing at real speed for more than ~4s.** Speed-ramp the boring middle
  (`setpts=0.5*PTS` on that span) and let the result land at full speed. Say nothing about it —
  it reads as competence, not deception, as long as the *outcome* shown is genuine.
- **A wait is not content.** Any spinner, install, or build over ~2s gets cut or speed-ramped
  with a small "3 min later" mono label, never left to play out.

## 5 · What the demo must actually prove

- The result on screen has to be **real and reproducible**. Never stage a fake output, never
  re-typeset a terminal result, never edit a number in a screenshot. If a demo did not work,
  that is the story — say so, or cut the section.
- If something is sped up, cut, or run off-camera, the claim on screen still has to be true of
  the unedited run.
- Credit and show the version/date on screen for anything that changes fast (model names,
  pricing, free tiers). A demo of a free tier that ended last month is a correction you will be
  making in the comments.

## 6 · The takeaway

Every demo section ends by leaving the bubble layout: cut to Full-Frame Face or a Split for the
one-line takeaway. **Do not end a chapter on a screen recording** — the viewer needs the face
back to reset before the next chapter card.
