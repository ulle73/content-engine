---
name: persa-short-editing
description: >-
  Edit a talking-head SHORT (9:16, 1080x1920) in the PERSA style: the camera is the
  frame (full bleed), a real product demo holds the screen for 15s+ while the camera
  drops to a rounded card with the head matted out over its top edge, one white word
  caption pinned at 72.9%, and a full display-type pass (coral payoff word, hollow
  outline emphasis, title stack, marker lines, lime claims typed into the UI's empty
  space). HyperFrames (HTML to MP4) layers composited onto the untouched camera, a thin
  SFX pass, 1080p delivery. Invoke whenever someone drops a recording and asks for a
  persa / full-bleed / Instagram-style edit.
---

# PERSA — the full-bleed short (9:16)

> **content-engine (Windows):** the skill is `.claude/skills/persa-short-editing/` (paths below
> marked `scripts/…`, `template/…`, `components/…` are relative to it). Each video lives in
> `work/persa-short/videos/<slug>/` with the camera file at `assets/recording.mp4`. Run Python with
> `library/.venv/Scripts/python.exe` (never `python3`, the Windows Store stub) and `*.sh` in Git Bash.
> Install notes, the RVM env and the sounds you must supply: `SETUP.md`. Library entries and
> previews: `library/kits/persa-short/LIBRARY.json`. Free SFX stand-ins: motion-studio's `sfx_lib.py`.

You edit **one** talking-head recording into a 9:16 short in one style: **persa**.
The camera **is** the frame. The frame barely changes — **the graphics change over a
continuous take.** A real product UI owns the screen for long stretches (the "demo spine"),
the camera shrinks to a rounded card under it with the head popping out over the card's top
edge, and a full pass of display type does half the work.

In the reference docs "he" / "Jad" means **the creator on camera**. Everything in them was
learned by shipping something broken; the numbers are measured, not guessed.

> ## ⭐ READ THESE FIRST, IN THIS ORDER
> 1. `reference/PERSA.md` — the style: precondition, demo spine, camera card, caption line,
>    the treatments, the asset rule, the layer order, what BLACKLIST rules it suspends.
> 2. `reference/TYPE-ROLES.md` — the display type (13 treatments). **Half the style.** A cut
>    with great media and only white captions gets rejected.
> 3. `reference/PERSA-LESSONS.md` — the silent bugs. Every one passed every gate and only
>    showed up in a sampled frame of the render.
> 4. `reference/BLACKLIST.md` — what never goes in a short. Walk it before rendering.
>    (Persa suspends #2b, #7, #11, #12 — see PERSA.md §9.)
> 5. `reference/HOW-WE-EDIT.md` — the HyperFrames clip contract (§1) and density (§6).
>    Its camera/caption sections describe the *house* cream-plate style — PERSA.md wins.
> 6. `reference/SOURCING.md` — before fetching anything from the web.
> 7. `reference/sound-design.md` — read the **PERSA** section; the rest is the house pass.
> 8. `template/README.md` — the last shipped persa build, as a starting point.

## ⛔ THE ORDER OF WORK — do not reorder these

```
 0 PRECONDITION  Does the video have a REAL product demo worth 15s+ of screen time?
                 If not, persa is the wrong style — say so in one line before building.
 1 DECODE        Probe the camera file. Log footage (e.g. DJI D-Log M) is decoded to Rec.709
                 FIRST: scripts/camera-decode.py --src <file> --probe, then --out
                 assets/recording.mp4. A 4K export is downscaled (lanczos) to 1080x1920.
                 Nothing downstream ever reads the log/4K file.
 2 TRANSCRIBE    npx --yes hyperframes transcribe assets/recording.mp4 -e parakeet
                 -> assets/transcript.json (word-level). Gap-check: the ASR drops whole
                 sentences; any silent-looking gap >0.7s is level-checked and re-transcribed.
 3 FACT-CHECK    every claim in the VO against the vendor's own announcement page. A wrong
                 claim is fixed in the caption/annotation (or scoped by the picture), not by
                 asking for a re-record. Ask the creator which way.
 4 SOURCE FIRST  find real MOVING media for every support beat and get it APPROVED before
                 building (scripts/source-scout.py). Vendor film > live product recording >
                 designed animation carrying real copy. No page screenshots with highlighter.
 5 FRAMING       probe for framing cuts in the take; RVM matte ONCE (template/matte.sh ->
                 assets/alpha.mkv); solve the card per ACT; measure head top per BEAT
                 (template/measure-head.py). Write assets/geometry.json.
 6 BUILD         build.py -> index.html + transparent layers (mid = picture + type behind
                 him, fg = captions + everything in front). Tokens only, transforms only.
 7 GATES         npx hyperframes check (0 errors) · scripts/check-density.py · BLACKLIST walk
 8 RENDER        layers --format mov, then template/composite.py onto the UNTOUCHED camera.
                 Then SAMPLE ONE FRAME PER BEAT OF THE RENDERED MP4 AND LOOK AT IT.
 9 SOUND         thin pass (~1 cue per 2-3s, mostly swell on layout changes). ping, swoosh,
                 confirm, beep are BANNED. Measure every cue on silence (template/verify-sfx.py).
10 BED           the bed loop under everything, levelled by LUFS, never by peak.
11 DELIVER       template/check-delivery.py: 1080x1920@30, sharpness vs source, bitrate.
                 Open it for review (`start <file>` on Windows). Publish NOTHING without explicit approval.
```

## The five that get persa cuts rejected

1. **Type is half the style.** Every cut runs the full display pass — coral filled payoff in
   the hook, the title stack on the product name, stacked repetition on a repeated phrase,
   marker lines, lime claims typed into dark UI negative space, pill labels. Roughly one
   display treatment every 3–4s. `components/persa-captions/` has all 13, built and rendered.
2. **The display type goes BEHIND his head.** Layer order: raw camera → the type → the matte
   at 1:1 → captions. Type he occludes reads painted on the wall; type floating clear reads
   pasted on. A slight overlap at the cap is the depth cue — a word over his eyes is crowding.
   `top = head_top_on_screen + 22 - font_size`, per beat.
3. **When a real UI is the beat, it owns the whole frame** and he drops to the card. Never a
   screenshot in a partial box; never `object-fit:contain` on a full-frame surface. And
   everything that must be read sits **above 59.5%** (y 1143) — below that line is behind him.
4. **Media is moving.** Vendor films, live product recordings driven on the video clock,
   replayed page entrances, animated marks. A page of text with a highlighter — even a
   scrolling one — was rejected. Facts come from pages; pictures do not.
5. **Never darken the picture, never tint it.** No scrim, no vignette, no band behind text,
   no compensating drop shadow. If type does not read, change the *type* (filled coral or
   solid white instead of a hollow outline on a bright wall). The camera never goes through
   the browser — layers are composited onto the untouched recording in ffmpeg.

## Two hard rules for the HTML
1. **Never hardcode a colour or font.** Import `assets/tokens.css`; use its variables.
2. **Animate transforms only** (`opacity, x, y, scale, rotation`). Never `top/left/width/height`.
   Every timed element carries `class="clip"` **first** + `data-start` + `data-duration` +
   `data-track-index`, and every concurrent element owns its own track (HOW-WE-EDIT §1).

## Files
```
SKILL.md                    this file
SETUP.md                    install, machine dependencies, what YOU must drop in (sounds, bed)
styles/persa.json           the preset, machine-readable: geometry, palette, rules
reference/
  PERSA.md                  ⭐ the operative style doc
  TYPE-ROLES.md             ⭐ the 13 display-type treatments, measured
  PERSA-LESSONS.md          ⭐ the silent bugs and how each was caught
  BLACKLIST.md              never-list + the pre-render test (persa deltas in PERSA.md §9)
  HOW-WE-EDIT.md            clip contract, density, working rules (house camera parts: skip)
  SOURCING.md               where to fetch, in what order, rights
  sound-design.md           the SFX pass — read the PERSA section
  cutout-compositing.md     the RVM matte environment, downsample ratio, seam invariant
  motion-grammar.md         how things move
components/
  persa-captions/           all 13 type treatments in one composition (build.py -> index.html)
                            sample/all.png shows every one rendered
  type-roles-demo/          the four core roles + the camera card with the matted pop-out
  grade-persa.svg           the optional colour grade (feComponentTransfer)
  cta-old.html              the CTA — copy it, never re-type it
assets/tokens.css           design tokens (fonts load from Google Fonts)
assets/fonts/               Instrument Serif (OFL)
library/concepts.json       what to SHOW for what the creator SAYS
scripts/                    the toolchain (see SETUP.md for what each needs)
template/                   the last shipped persa build (95.8s) — build, composite, audio,
                            gates. Copy into work/persa-short/videos/<slug>/ and adapt. See template/README.md
sfx/  bgm/                  EMPTY — drop your own licensed sounds and bed here (SETUP.md)
```
