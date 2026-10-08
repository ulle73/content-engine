# PERSA LESSONS — the bugs every gate passes

Each of these shipped into a render with `hyperframes check` at 0 errors and the density gate
happy. Every one was caught the same way: **one sampled frame per beat of the rendered mp4,
looked at.** A snapshot or a preview is not evidence — the preview path and the render path
disagree.

---

## Framing and layout

1. **The card hides the bottom 40%.** On a card beat, y ≥ 1143 (59.5%) is behind him. A marker,
   a star count, an "Add" button placed there renders invisible. Compose every UI surface to the
   59.5% line — what must be read sits in the top ~55%. Fix the SHOT (shoot taller, scroll the
   panel), not the crop.
2. **A 1080×1918 capture in a 1143px band shows only its top 60%.** Scroll the panel inside the
   recording so the action is high, and assert the label actually moved. Cut the band where the
   page is blank; 1143 is odd, libx264 refuses it — use 1144.
3. **`object-fit:contain` on a full-frame surface** shrinks it into a small floating screenshot.
   Use `cover` and the box it deserves.
4. **Give every media element explicit `left/top/width/height`.** A flex wrapper sizing it renders
   at intrinsic size in the render path only.
5. **Entrance tween lands on `y:0`**, never on the same number as the CSS `top` — or it renders
   twice as low.
6. **Transform carries its own clip.** Put `overflow:hidden` on the thing you translate.
7. **An animated `transform` REPLACES an inline one** — a `rotate()` set inline is discarded the
   moment a keyframe touches `transform`. Carry the static part inside the keyframe via a custom
   property (`rotate(var(--ang)) scaleX(0)`).
8. **A hand-set font size is a ceiling, never an override** — `min(size, fitted)`. A centred
   nowrap word that runs off both edges passes the layout gate.
9. **Head top varies per beat.** Measure it off the alpha per beat; an act average (or the
   whole-take minimum) puts a display word through his cap.
10. **A push that scales below 1.0 off-centre uncovers black edges.** Put a div in the surface's
    own ground colour (median of a 6px border ring) under every pushed still, on its own track.
11. **Your naming pill lands on the app's own wordmark** at `left:40 top:40`. Drop the pill
    wherever the real logo is already in frame.

## Timing and the clip contract

12. **`class="clip"` must be the FIRST class.** `class="shot clip"` is invisible to
    `check-density.py`, which then invents holes.
13. **CSS `animation-delay` inside a clip is on the composition clock.** A 1.2s delay in a clip
    starting at 14s is long over — the build renders fully built at frame 1. Every animated child
    gets its own `data-start` (= parent start), `class="clip"`, `data-duration` and a unique
    `data-track-index` (the template's `clipify()` post-pass does this).
14. **An entrance's FROM state paints early.** With `both` fill, a child starting at the group
    start shows its from-state until its delay — a blurred logo for 3 seconds. Every entrance
    keyframe starts at `opacity:0`. Never "cover" something with a rectangle to remove it.
15. **A SECOND animation with an explicit `from` paints early too.** Out-animations are
    `to`-only (`@keyframes outq{to{opacity:0}}`) and come LAST in the shorthand.
16. **One highlight/marker at a time.** A mark's clip ends where the next mark starts.
17. **A clip asked for more media than it has** renders a frozen/blank tail. Assert
    `media_start + duration ≤ clip length` in the build.

## Rendering

18. **Never send the camera through the browser.** Chrome's decode tints it (measured G +4 with
    identical colour tags). Render the designed layers transparent (`--format mov`) and
    composite onto the untouched recording in ffmpeg (`template/composite.py`). Check per-channel
    means, render vs source, in an uncovered region.
19. **A CSS mask on a `<video>` renders nothing.** Put the mask on an untimed wrapper `<div>`.
20. **A `<video data-start>` nested inside a timed element renders frozen.** Its wrapper is
    untimed.
21. **The transcode cache is stale.** Rebuild a clip in place and the render uses the OLD
    footage. `rm -rf .transcode-cache` after changing any source video.
22. **`mix-blend-mode` can produce a broken one-packet MP4** at >1 worker. Render
    `--format png-sequence -w 1` and encode with ffmpeg.
23. **`font-size:%d px`** (a space before `px`) is invalid CSS; the word silently never paints.
24. **Recolouring an SVG by string replace can duplicate `fill`** = invalid XML = an empty box.
    Rasterise marks to PNG.
25. **Never `pkill -f "hyperframes render"`** — it kills every render on the machine. Kill your
    own PID.
26. **Under ~1 GB free disk the render silently refuses.** Delete matte frames once
    `alpha.mkv` exists.
27. **Comparison frames lie on untagged video:** ffmpeg decodes untagged YUV as BT.601. Extract
    with `-vf scale=in_color_matrix=bt709:in_range=tv:out_color_matrix=bt709:out_range=pc,format=rgb24`.

## Sound

28. **Measure cues on SILENCE.** Mix the cue sheet onto digital silence (`out/sfx-only.wav`) —
    a delta against the voice mix is invalid under a loud word, and AAC subtraction does not
    cancel (the control reads −0.5 dB where it should read −90).
29. **Open each window at cue + that sound's leading silence** (`sfx/leading-silence.json`), and
    end it at the next cue's onset (cap 0.9s). A late-firing sound reads dead at any gain
    otherwise.
30. **Level the bed by loudness (LUFS), never by peak.**
31. **Gain is per SOUND, not per cue type** — source peaks span 12 dB.
32. **Clicks land ON word peaks** — carrying a gain from a quieter take clipped at +3 dBFS.

## Sourcing

33. **Some sites serve an empty document to headless browsers** (and some to headful Playwright
    too). The shooter correctly refuses; use a real browser or their CDN.
34. **Playwright's fake clock does not drive CSS animations** — they have already finished by the
    time capture starts. Pause and step `document.getAnimations()` per frame. rAF loops cannot be
    stretched this way; cut the beat to the longest blank-free run.
35. **Smooth scrolling drifts a stepped-clock recording** — inject `scroll-behavior:auto` and
    assert `scrollY` per frame.
36. **A vendor film cuts mid-beat.** Template-match the stable span; slow it, never run past its
    cut.
37. **Recording filenames are not keys** — the same name and length can be a different take.
    Transcribe first.

## Delivery

38. **1080p is a standing requirement, verified**: container 1080×1920@30, bitrate, and actual
    sharpness against the source (a 1080-shaped upscale passes every header check). Measure
    sharpness where no graphic lives — a strip holding the caption measures the caption's edges.
39. **Nothing darkens the photograph** — no scrim, vignette, radial or grade used to rescue type,
    and no compensating drop shadow either. Prove it: background luma render vs source in an
    uncovered region, every delta codec noise.
