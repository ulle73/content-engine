---
name: live-carousel
description: Make "live carousels" for Instagram (also LinkedIn, TikTok photo mode, Threads), where every slide is a looping 4:5 motion-graphics video with sound, so the post moves as people swipe. Two modes. (1) Design a new carousel from a topic in an editorial big-word house style (cobalt/orange/cream, plus tomato, forest and noir palettes). (2) Bring someone's finished carousel images (PNG/JPG) to life without changing the design, with a drifting sky, 3D type pops, light sweeps, music and sound effects. Everything is free and runs locally (open-source HyperFrames, GSAP, numpy, ffmpeg), with no paid APIs, credits or sign-ups. Use this skill whenever someone wants an animated, moving, motion, video or "live" carousel, wants to animate their carousel slides, add motion, music or sound effects to carousel images, turn a carousel into videos, or make carousel posts that move, even if they only say "make my carousel move" or "animate these slides".
---

# Live Carousel

A live carousel is a normal carousel post where each slide is a short MP4 instead of a still image.
Each slide is 1080x1350, 30 fps, and has its own sound. It is also a **seamless loop** whose length
is a whole number of 120 BPM bars (4, 6 or 8 s). People swipe, every slide moves, and the music
carries on from one slide to the next.

`SKILL` below means this folder, `.claude/skills/live-carousel/` (Claude Code runs from the content-engine repo root).
Run every Python script with the wrapper `.claude\skills\live-carousel\scripts\py.cmd` (PowerShell/cmd) or `.claude/skills/live-carousel/scripts/py` (Git Bash).
It uses the skill's private venv (signed Python 3.12 + numpy/opencv) and forces UTF-8.
This is the Windows port imported into content-engine; see `library/kits/live-carousel/IMPORT-NOTES.md`.

## Cost: $0

Everything is local and free. HyperFrames (an open-source HTML-to-video renderer) runs through `npx`,
along with GSAP, Node.js, ffmpeg, Python with numpy and opencv, free SIL OFL fonts (bundled), and
synthesized music and sound effects. Never route the work through paid image, video or music
generators, API keys or credit-based tools. If the user asks for AI-generated imagery, say that this
skill animates designs and images they already have, and keep going for free.

## 0. First use on a machine

If `SKILL/.venv` does not exist, run `powershell -ExecutionPolicy Bypass -File .claude\skills\live-carousel\scripts\setup.ps1`
first. It checks Node 22+, ffmpeg and the installed HyperFrames CLI (`npx hyperframes`) + its headless Chrome, and creates
`SKILL/.venv` with the signed `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (never a uv-downloaded Python:
Smart App Control blocks its DLLs) with numpy + opencv. Re-running it is safe. If it reports a problem, fix that before
building anything, because nothing renders without these tools.

## 1. Pick the mode

| The user gives you…                                              | Mode       |
| ---------------------------------------------------------------- | ---------- |
| a topic, an idea, a message, notes, a niche ("a carousel about…") | **motion** |
| images: slide PNG/JPGs, a folder of slides, an exported carousel   | **photo**  |

Ask at most one question, and only when the answer would change the whole piece. Otherwise
choose sensible defaults and state them: 4 slides (hook, two value slides, CTA), the `cobalt` theme,
the user's language, and a "comment KEYWORD" CTA. People who use this usually want you to cook.

Projects go in `work/live-carousel/<short-slug>/` (gitignored). Pass just the slug to the scripts and they resolve it there.

## 2a. Motion mode: a new carousel from a topic

1. **Scaffold** from the working reference carousel:
   `.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\new_carousel.py <slug> --theme cobalt --title "<series name>" --caption "<post caption>"`
   The template is a complete 4-slide carousel called "Motion Design 101". One orange ball travels
   through every slide and teaches with its motion. Render it unchanged first if you want to see the
   target quality (`render_all.py <dir> --only 01-hook`).
2. **Concept.** Read `references/house-style.md` and `references/slide-recipes.md`. Then rewrite
   `BRIEF.md`, `STORYBOARD.md` and the copy in `frame.md` for the new topic. The strongest concepts
   have **one protagonist object** that belongs to the topic and proves every point by moving: a coin
   for money, a cursor for UX, a dumbbell for fitness. Write the storyboard beats as times on the
   0.5 s beat grid.
3. **Build the slides.** Edit `src/*.html` and `shared/*`, never `slides/`, because `build.py`
   regenerates that folder. Keep each slide's chrome: the top bar, the small line / BIG WORD /
   small line stack, the bottom triplet and the timeline ruler. Replace the words, the demo and the
   choreography. Read `references/engine-api.md` before you touch `render(t)`. If you rename,
   add or remove slides, update `"slides"` in `carousel.json`, the `0N / 0M` counters, the ruler's
   `frameStart`, and the slide list at the bottom of `audio/make_audio.py`.
4. **Sound.** Retime `audio/make_audio.py` so every effect lands on the frame its visual event
   happens. Take the times from `render(t)`. See `references/sound-design.md`.
5. **Render and QA** (section 3).

## 2b. Photo mode: bring finished slides to life

1. **Collect the images in slide order.** In a folder, sort by filename and skip contact sheets and
   files that start with `_`. Non-4:5 images are centre-cropped to 4:5.
2. **Scaffold:** `.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\new_carousel.py <slug> --mode photo --images 01.png 02.png …`
3. **Split into layers:** `.claude\skills\live-carousel\scripts\py.cmd work\live-carousel\<slug>\prep_photo.py` (no cd needed). On busy photos where saturated
   scenery touches the text, add `--no-accent`. Add `--cutout` when a person
   or product should pop forward. That uses HyperFrames' free local background remover, which
   downloads about 170 MB once.
4. **Look at every `prep/NN_maskvis.jpg`.** Red is held still, green boxes are text lines, and the
   blue box is the headline. Sky, gradients and plain backgrounds should be clear. Text, faces,
   objects and UI should be red. If the result is wrong, re-run with `--edge` or `--busy` (see
   `references/photo-mode.md`), or edit the boxes in `assets/NN/geo.json`.
5. **Direct the motion** in `carousel.json → cues.NN`. Each cue sets `dur`, the `hits` (the one big
   moment, on the beat), the `shine` sweeps, the `sky` drift, `motes`, `extrude` (a 3D pop behind the
   headline), `hitAt` and `push`. The defaults already work. Make each slide's moment fit what that
   slide says: a count-up on a stat slide, pills lighting in sequence, or a cursor pressing the CTA.
   The recipes are in `references/photo-mode.md`. Add custom moments in `src/NN.html` and matching
   sounds in `extra()` in `audio/make_audio.py`.
6. **Render and QA** (section 3). The first-frame row of the contact sheet must look identical to the
   user's originals.

## 3. Render, check, deliver

```
.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\render_all.py <slug>          # audio → build → check → render → verify
.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\render_all.py <slug> --check-only
.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\render_all.py <slug> --only 02-easing --no-check
.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\render_all.py <slug> --open     # also opens preview.html (Windows start)
```

When `check` fails, read its messages, fix `src/`, and run it again. Errors are layout overlap,
off-canvas content, contrast, missing assets, or a timeline that never registered. Then **look at**
`renders/contact-sheet.jpg`. Its top row is frame 0 of every slide, which is what people see right
after a swipe. Its bottom row is mid-slide. Also look at `renders/seams/*.jpg` (last frame | first
frame) and confirm the loop is invisible. Work through the checklist in `references/render-qa.md`
before you call the carousel done. To spot-check one moment, run
`npx hyperframes snapshot --at 2.5 --no-end` inside `slides/<name>/`.

Deliver:
- the MP4 paths, in order (`renders/slide-*.mp4`), ready to post together as one carousel
- `preview.html`, a local Instagram-style swipe preview. Open it for the user (`start work\live-carousel\<slug>\preview.html`).
- a caption and the CTA keyword, if the carousel uses one

## Rules that keep renders correct (and why)

- **Make everything a pure function of `t`.** The renderer seeks frames out of order and in parallel
  workers. Draw each frame from `render(t)` alone. Don't use `Math.random`, `Date`, timers or
  `requestAnimationFrame` loops. Use `LC.hash(n)` for deterministic randomness.
- **Make every loop seamless.** The last frame has to flow into frame 0. Use whole bars (2 s each),
  have every effect finish or come back to rest before `DUR`, keep periodic motion periodic in `DUR`,
  and keep hits at least 0.8 s before the end. The audio wraps its tails to the start for the same
  reason.
- **Make frame 0 a finished, readable design.** It is the thumbnail and the first frame after a swipe.
- **Keep the platform's overlays clear.** Instagram puts a "1/4" counter at the top right and a sound
  icon at the bottom right. Keep a 72 px margin.
- **Give each slide its own HyperFrames project** (`slides/<name>/`). That way each slide checks
  and renders on its own, and one broken slide never blocks the rest.
- **Render with `--workers 2`** (the default here). Each worker is a Chrome process.

## References (read when the step calls for it)

| File                          | Read it for                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------- |
| `references/house-style.md`   | the design system: palettes and themes, type, layout grammar, motion rules, copy |
| `references/slide-recipes.md` | hook, value and CTA patterns, continuity tricks, finding the protagonist object |
| `references/engine-api.md`    | slide file anatomy, the `LC` engine (ball physics, springs, bursts, ruler, word fitting) |
| `references/sound-design.md`  | `lc_audio`: groove, instruments, named effects, timing, loudness, using a song |
| `references/photo-mode.md`    | layers, cues, the `PH` toolkit, per-slide moment recipes, fixing masks |
| `references/render-qa.md`     | the QA checklist, troubleshooting, and posting tips                          |
