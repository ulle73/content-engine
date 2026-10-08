# Render, QA, troubleshooting, posting

## QA checklist (look at the images; don't assume)

- [ ] `renders/contact-sheet.jpg` top row: every slide's frame 0 is a finished, readable design.
      In photo mode it is identical to the original slides.
- [ ] The bottom row (mid-slide): the big moment is visible, nothing is clipped or off-canvas, and no
      text collides with anything by accident.
- [ ] `renders/seams/*.jpg` (last frame | first frame): they look like consecutive frames. No pop,
      and no element that appears or vanishes at the loop.
- [ ] Every MP4 has `audio`, and its duration is exactly the slide's `dur` (render_all prints both).
- [ ] Sound lines up with picture. Open `preview.html`, tap "play with sound", and watch the hits land.
- [ ] Top-right and bottom-right corners are clear of important content (Instagram's own overlays).
- [ ] Copy check: spelling, the counters (`01 / 04`), the CTA keyword is the same in caption and slide.
- [ ] Continuity: the protagonist leaves slide N on the right and enters slide N+1 from the left.

To check a moment: run `npx hyperframes snapshot --at 1.5,2.5 --no-end` inside
`slides/<name>/`, then look at `snapshots/`.

## Troubleshooting

| symptom | fix |
| --- | --- |
| `check` reports layout overlap or occlusion | If it is intentional (a ball over text, word swaps), add `data-layout-allow-overlap` / `data-layout-allow-occlusion` to that element. Otherwise move it. |
| `check` reports contrast | Raise the text size or weight, or put it on a darker or lighter backing. Never use accent-coloured text under 90 px. |
| the timeline never registered, or the render is blank | `render(t)` threw an error before `window.__timelines["main"]` was set. Run `npx hyperframes check` in `slides/<name>` and read the JS error. Usually it is a missing element id or a font measured before it loaded. |
| wrong font in the render | Add `document.fonts.load("…")` for that face before `fonts.ready`, and check the @font-face family name in `shared/fonts.css`. |
| something moves differently in the render than in the browser | Something isn't a pure function of `t` (Math.random, Date, an autoplaying tween, CSS transitions). |
| WebGL (sky) is black or frozen in the render | Run the render with `--browser-gpu`, or set `sky` to 0. Check `flow.png` exists in `assets/NN/`. |
| the loop pops | An effect is still mid-way at `DUR`. Make it end 0.5 s earlier, or make it periodic in `DUR`. |
| audio missing or silent | `audio/out/<name>.wav` wasn't made (an error in make_audio.py), or the slide's `<audio>` tag is missing. |
| render is slow or runs out of memory | Use `--workers 1`, close other apps, or render with `--only` one slide at a time. |
| "Chrome not found" | `npx hyperframes browser ensure --force` |
| disk full | Delete `renders/.frames` and old `slides/*/renders`. Each render needs a few hundred MB of temporary space. |
| `npx` asks to install, or hangs | The first run downloads the CLI. It needs internet once, then the CLI is cached. |

## Posting

- Post the MP4s in order, as **one carousel** post. Each video loops on its own while it is on screen.
- 1080x1350 (4:5) is the tallest feed size. H.264 + AAC MP4 is what the renderer outputs, and it
  uploads as is. You can mix in still images too.
- Leave the platform's music sticker off, or it may replace your sound design.
- Use the cover (slide 1) frame 0 as the thumbnail. It was designed for that.
- The same MP4s work on any platform that accepts multi-video posts. Check its current limits on
  slide count and duration.
