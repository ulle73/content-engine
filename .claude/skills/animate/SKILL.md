---
name: animate
description: Make a short procedural animation in any style — an explainer, a history, a little story — as a single-file canvas video with a synthesized score, rendered to MP4. Ships with styles (cut paper, crosshatch ink, riso print, sketchbook, manim-style math, pixel art, isometric line art) and makes new ones from the user's references. Walks the user through intake, then three check-ins (story, look, storyboard) before animating, and proves the result with measured review checks. Use when the user asks for an animated video, short, explainer or reel made in code, or wants a look matched from references.
argument-hint: "[what the video is about] [style or reference]"
---

# Animate

You make short animated videos in code: one `<canvas>`, drawn and scored procedurally, deterministic frame by frame, rendered with a headless browser and ffmpeg. The story follows a grammar studied from strong short-form animation; the look is a **style** — a plug-in kit chosen from [styles/](styles/README.md) or made from the user's references with [new-style.md](new-style.md).

**Requirements:** Node 18+, Playwright (the npm package only), ffmpeg on PATH, and Google Chrome. Check them first: `powershell -ExecutionPolicy Bypass -File .claude/skills/animate/setup.ps1` (from the repo root) checks node, ffmpeg and Chrome and installs Playwright **locally** into `work/animate/node_modules` (gitignored) without downloading a browser — every tool launches the **system Chrome** through `tools/pw.mjs` (`ANIMATE_CHROME=<path>` to point elsewhere, `ANIMATE_BROWSER=bundled` for Playwright's own Chromium). Never `npm i -g`. If something is missing, tell the user the command and stop. For a voice-over, `faster-whisper` times every word (optional; `setup.ps1 -Whisper` puts it in `library/.venv`, built with the signed Python 3.12); without it the word times are estimated.

## In content-engine (this repo)

- **Run every tool from the repo root:** `node .claude/skills/animate/tools/<tool>.mjs …`. Relative doc links below (`styles/`, `grammar/`, `templates/`) are inside this skill folder.
- **Pieces** live in `work/animate/pieces/<name>/` (gitignored work output; create it if needed). Frames, renders and review sheets are written inside the piece.
- **Styles the user makes** are saved in `library/kits/animate/styles/<name>/` (part of the library, committed); `build.mjs` and `gallery.mjs` look there too. **Reference media** goes in `work/animate/references/<look>/` (gitignored, never committed).
- **The check-ins are the default, not a gate.** If the user says "kör direkt" / "just make it", skip the questions, use the defaults and say which you picked. Style rules, frame checklists and craft rules are presets and tips — the user can override any of them; never refuse a creative choice because a checklist says otherwise.
- **Cost:** everything here is free and local. The only paid part is the optional **ElevenLabs** voice (connector, ~1 credit per character): the free path is music only, the user's own recording, or no voice. Say the cost before any paid run.
- **Before publishing:** the crosshatch/sketchbook hero (a terracotta ball with a white asterisk), the history-of-ai 2025 era and some demo texts (`$ claude`, tool pills) evoke Anthropic/Claude branding. Mention it once and offer another hero or text for commercial pieces; don't block.
- **Swedish voice-over:** `voice.mjs … --lang sv` (uses the multilingual whisper model `small` instead of `small.en`).
- Library index: `library/kits/animate/LIBRARY.json` (every style, format, effect and tool as a catalogue entry with previews).

## Non-negotiables (technical rules; the creative ones are defaults the user can override)

1. **Storyboard before animating (default).** The check-ins exist because a wrong story or look costs a full build — unless the user waives them.
2. **Look at references before drawing anything** — the user's, or the style's `sample.png` and demo. Then check every key frame against [grammar/FRAME.md](grammar/FRAME.md) and the style's own checklist in its `STYLE.md`.
3. **Every factual claim on screen is checked with a web search** and listed with its source in the brief. Never claim "first" without a source.
4. **Single file, all code:** one `index.html`; everything is drawn and synthesized in code — no image/audio/video files, no `data:` URIs, no URLs, no web fonts in the code. `tools/build.mjs` enforces it. Two opt-in exceptions, both the user's own: **assets** (screenshots and logos in `<piece>/assets/`, embedded by the build) and **a music track** (joined at export). See Assets and Music below.
5. **Deterministic:** seeded randomness only (`RNG(...)`), the boil index `B` for per-step variation. Never `Math.random()` or wall-clock time.
6. **Reference media stays local.** Never commit it, copy its code, or name its artist in published output unless the user asks to credit them.
7. **"Done" is measured:** `tools/review.mjs` passes and you have looked at the contact sheets. Report the numbers, not "looks good".
8. **Ask with options.** Use AskUserQuestion with a recommended default first, so the user can answer in one click.

## The flow

### 0. Intake
Ask the questions in [intake.md](intake.md) — only the ones you can't infer. For the look, build the gallery (`node .claude/skills/animate/tools/gallery.mjs work/animate/styles.png`, ~3s; it includes the user's saved styles from `library/kits/animate/styles/`), show it and ask: **which of these, or show me a reference?** Then study the references yourself against FRAME.md and the style's checklist.

### 1. Story check (text, fast)
Pick the **format** from [grammar/FORMATS.md](grammar/FORMATS.md) — the plot engine decides it (a history is a chronology joined by morphs; a mission cuts on the beat; a list is a catalogue). Read [grammar/STORY.md](grammar/STORY.md). Web-check the facts. Then show the user:
- the one-line idea and the sayable device ("the spark gains a ray each era and ends as the answer")
- the format and why, the style, length, BPM
- a numbered beat table: time, what happens, the bridge into the next beat, the sound's role (where the silence is, where the loudest hit is)

Ask: **approve / change beats / different angle.** Revise until approved. This is where "I meant X, not Y" gets caught cheaply.

### 2. Look check (2–4 style frames)
Start the piece at `work/animate/pieces/<name>/`: copy `piece.json` and `src/` from the style's demo (`styles/<name>/demo/`) — it already speaks the style's kit and joins eras with a morph — or from [templates/beat-cut/](templates/beat-cut/) for a piece that cuts hard on the beat (8ths, a 16th-note rush on odd frames, one era per shot, framings from cameras), or [templates/piece/](templates/piece/) for the plainest cut-paper morph. Set `"style"` in `piece.json`, then write `brief.md` and `LOG.md` fresh (the template's are placeholders).
- **A shipped style:** read its `STYLE.md` and demo and draw with its kit.
- **The user's references:** follow [new-style.md](new-style.md). Measure the references first (`tools/measure/refs.mjs`); the piece's own style frames *are* the matched frames, so this is **one** check-in: the compare sheets and the frames together. Save the style folder after the piece is approved (the piece becomes its "proven on").

Draw 2–4 of the most different beats as full-size frames. Each must pass FRAME.md and the style's checklist. Render them side by side with `node .claude/skills/animate/tools/still.mjs work/animate/pieces/<name> 2.25,9.75,16.5 look.png --scale 0.5` (or `tools/storyboard.mjs` with `TIMELINE.board` set to those beats), and show the image. Ask: **thumbs up per frame / change the look / try another style.**

### 3. Storyboard check (every beat)
Draw every beat in the approved look. Fill `TIMELINE.board` with one key time per beat (`{ t, title, sound, next }`) and render the board. Ask for **thumbs up/down by panel number** and notes; redraw what's down; repeat. The panels are the video's own scene functions, so nothing is redrawn later.

### 4. Build
1. Write `work/animate/pieces/<name>/brief.md` (spec, style, beats, bridges, sound plan, claims + sources). Keep a `LOG.md`.
2. Animate the scenes: timed actions with `TT`, `ev(t, d)`, `popS(t)`, write-ons (see [craft.md](craft.md) → Motion). Wire eras, cameras and bridges in `src/bridges.js` (morph-joined formats) or leave `BRIDGES = []` for hard cuts.
3. `node .claude/skills/animate/tools/build.mjs work/animate/pieces/<name>` → `index.html` (the style's kit is pulled in from `piece.json` `"style"`).
4. Test tiles while building: `node .claude/skills/animate/tools/tile.mjs work/animate/pieces/<name> tile.png <frames...>` — look at them; tile across every morph and cut.
5. Score in `src/score.js` (see craft.md → Sound).
6. `node .claude/skills/animate/tools/export.mjs work/animate/pieces/<name> --share` → frames, `audio.wav`, stems, `renders/final.mp4`, `renders/share.mp4` (`--formats 9:16,1:1,16:9` for every format; `--blur 4` for motion blur on 1s styles). Iterate the mix with `--only-audio` (re-renders the score and remuxes it, ~4× faster).
7. `node .claude/skills/animate/tools/review.mjs work/animate/pieces/<name>` → contact sheets per shot, cut grid, morph grid, story arc, anchor, **text** (cut off / overlapping / under the phone UI) and **sound** (the loudest moment, the silence before it, LUFS). Fix until it passes, view the sheets, write a per-shot PASS table in `LOG.md`. Trust the text check over your eye: a cropped label looks fine on a contact sheet.

### 5. Deliver
Send `renders/share.mp4`. Say in a few lines: what it is, the checks' numbers, what the review caught and fixed, the weakest shot, and what you haven't verified (e.g. you can't listen to the score). Ask what should change: story, look, transitions, pacing, sound.

### 6. Learn
After each run append to the piece's `LOG.md`. If something new went wrong or worked, propose a one-line rule for [craft.md](craft.md), the style's `STYLE.md` or a kit change, and add it when the user agrees.

## Voice-over (optional)

Ask at intake (question 3). With a voice, **the voice is the clock**: each beat starts ~0.3s after the previous sentence ends, and the big moments land on spoken words. The script is the storyboard: one line per beat.
1. Write the script to `work/animate/pieces/<name>/voice/script.json`: `{ "lead": 1.2, "tail": 1.8, "lines": [{ "id": "open", "text": "As it is spoken.", "after": 0.45 }, ...] }`. Write numbers and names the way they should be said. Keep it ≤ 3.5 words/s; give a line a longer `after` where the picture needs time to land (a count, a caption, the silence before the payoff).
2. **Build before the voice exists:** `node .claude/skills/animate/tools/voice.mjs work/animate/pieces/<name> --scratch` makes a timing voice with the OS's own speech (never ship it), so the whole piece can be animated and reviewed.
3. **The takes:** one file per line, saved as `voice/<id>.mp3` with `"file"` set on the line. **Free first:** the user's own recording (below) or no voice at all; ElevenLabs is the paid option.
   - **PAID — the ElevenLabs connector** (only if the user has it and accepts the cost: Claude's Settings → Connectors → ElevenLabs, signed in with OAuth, no API key): find 2–3 narrators that fit with its voice search, generate *one* line in each (one variation each, not four), let the user pick, then generate every line once with that voice and model. The generation result gives a short-lived download link per take: save each into `voice/`. It costs about one credit per character; say the total before the full run. If the connector was added during the session, its tools may only appear after the app restarts.
   - **The user's own recording,** one file per line (or cut from one take).
   - Never fetch a voice from a site the user didn't point to, and never clone a voice without its owner's consent.
4. `node .claude/skills/animate/tools/voice.mjs work/animate/pieces/<name> [--lang sv]` → `voice/voice.wav` (the lines with their pauses) and `voice.json` (every line's and word's start and end, heard in the audio by faster-whisper, locally — it runs with `library/.venv` when that has faster-whisper, else `python`; `ANIMATE_PYTHON` overrides). The build injects it as `VOICE`.
5. In the head: `VL(id)` is a line, `VW(id, word, n)` when its n-th `word` starts; beats start at the previous line's `t1 + 0.3`; `TIMELINE.narration` comes from `VOICE.lines` and `DURATION` from `VOICE.duration`. Cue Writes and flashes on the words that name them. **Put the payoff hit in a pause before the line that names it**: a hit under speech is ducked away.
6. `piece.json`: `"voice": { "file": "voice/voice.wav", "music": -12 }`. Export mixes the voice over the score (the score at `music` dB, ducked further while the voice speaks) to −14 LUFS. Review judges the story arc and the payoff window on the score alone (`renders/audio-score.wav`; a voice is louder than any hit) and the voice with its NARRATION check.
7. **Re-takes and script edits:** replace a line's file (or edit its text), rerun `voice.mjs`, rebuild: scenes cued from `VOICE` move with it. A changed word can orphan a cue that points at it; check those beats.

## Music: the user's own track (optional)

Ask at intake (question 6). Without a track the score is composed in code on a 120 BPM grid. With one:
1. Put it in the piece: `work/animate/pieces/<name>/audio/track.wav` (WAV, MP3 or M4A), and in `piece.json`: `"music": { "file": "audio/track.wav", "start": 12.0, "gain": 0, "fade": 0.5 }` (`start` = where in the song the piece begins).
2. `node .claude/skills/animate/tools/beats.mjs work/animate/pieces/<name>/audio/track.wav work/animate/pieces/<name> --start 12 --dur <piece length>` → `beats.json`: the tempo, the first beat, every beat and bar, the strongest hits, the loudest moment and the drops. Pass `--bpm 128` if the user knows the tempo; check its "other tempos" line otherwise (double / half / two-thirds time is the usual miss).
3. The build injects it as `BEATS`; the starter head reads `BPM` and `GRID0` from it, and `onBeat(t)` snaps a time to the song's 8th grid. Put cuts, morphs and cues on `onBeat(...)`. **The song decides the arc:** put the turn on a drop (`BEATS.quiet`) and the payoff on its loudest hit (`BEATS.loudest`, `BEATS.hits`), not where a composed score would have put them.
4. The score (`src/score.js`) keeps only sound effects (`to = 's'`): export replaces the music bus with the track, mixes the sfx stem on top and normalises to −14 LUFS. Review's grid uses `TIMELINE.gridOffset`; its SOUND section says whether the loudest moment lands in the payoff act.
5. The browser preview still plays the composed score (no audio files in the page); the export has the track.

## Assets: real screenshots and logos (optional)

Ask at intake (question 7) when the subject is a product. Then:
- `node .claude/skills/animate/tools/capture.mjs <url> work/animate/pieces/<name>/assets/home.png [--selector "css"] [--full] [--dark] [--hide "css"]` screenshots the user's own site (a page, a section, the logo). Ask before capturing anything they don't own. Logo files they give you go in `assets/` too (PNG, SVG, JPG, WEBP).
- `tools/build.mjs` embeds everything in `assets/` into `index.html` (the piece stays one file, and the canvas stays readable by the checks); `window.renderFrame` appears once the images are decoded, and every tool waits for it.
- Draw them with `drawAsset('home.png', x, y, w, h, { fit: 'cover' | 'contain', r })` inside the style's own framing (a torn-paper photo, an inked frame, a printed card) so they belong to the look. `asset(name)` returns the image.
- **Real product UI only:** animate the real screens (crop, push in, reveal, point at them with the hero); never draw a fake screen as if it were the product. Sample brand colours from the screenshots.

## Formats: one piece, several shapes (optional)

Ask at intake (question 2, multi-select). List them in `piece.json` `"formats": ["9:16", "1:1", "16:9"]` (the first is the main one). The starter's head reads `?format=` and sets `W`, `H`, `SAFE` and `CX`; scenes place things with `LX(fraction)`, `LY(fraction)` and size them with `UNIT`, and choose a different arrangement with `PORTRAIT` / `WIDE` where a shape needs it (a column of three on 9:16, a row of three on 16:9). Never crop a 9:16 render to 16:9.
- `node .claude/skills/animate/tools/export.mjs work/animate/pieces/<name> --formats 9:16,1:1,16:9 --share` → `renders/final.mp4` (main) and `final-<w>x<h>.mp4` for the others.
- Review each: `node .claude/skills/animate/tools/review.mjs work/animate/pieces/<name> --format 16:9` (and `tile` / `still` / `textcheck` / `storyboard` take `--format` too). The text check matters most here: a wide caption that fits 16:9 can run off 9:16.

## Motion: springs and blur

- **Springs** (`kit/core.js`): `springMove(t0, a, b, SPRING.snappy)` moves a value with a little overshoot and a settle; `springTrack([[t, v], ...])` follows a value through many targets without a jump. Presets: `snappy` (UI), `smooth` (cards, camera), `heavy` (big type, logos), `playful` (mascots). Closed-form, so frames stay deterministic. On-2s styles step them every 2 frames, as they should.
- **Motion blur:** `export.mjs --blur 4` averages 4 sub-frames per frame — only for styles on 1s (`STYLE.ones`: math, isometric); hand-drawn looks on 2s are crisp on purpose (export warns).

## Parallel agents (long pieces)

A 45–60s piece has 10–15 scenes; split the drawing across agents once the storyboard is approved:
- **One `src/` file per section or era, owned by one agent** (`src/era-01.js`, `src/era-02.js`, …). List them in `piece.json` `"scenes": [...]`; they take the place of `src/scenes.js` in the build order.
- **The shared parts stay with you:** `src/head.html` (TIMELINE, eras, shots, cues), `src/bridges.js`, the score, and the kit. Agents read them but never edit them; if a scene needs a kit helper, they write it in their own file under a prefixed name.
- **Brief each agent** with the approved board panel(s), the style's `STYLE.md`, the era's time range and cue names, its bridge objects (what must be in frame at the boundary), and the rules: deterministic, no new globals without the era prefix, tile its frames and look at them.
- **`build.mjs` joins them**; you build, tile across every boundary, and run the review.

## Files

| path | what | read when |
|---|---|---|
| [intake.md](intake.md) | the questions and defaults | step 0 |
| [craft.md](craft.md) | the distilled rules: story, frame, motion, timing, sound, code, review | before step 1, and when building |
| [grammar/FORMATS.md](grammar/FORMATS.md) | 8 story formats (engine × stage × clock), invariants, which are proven | step 1 |
| [grammar/STORY.md](grammar/STORY.md) | beat-level story rules with evidence | step 1 |
| [grammar/FRAME.md](grammar/FRAME.md) | what a single key frame must hold, in any style | steps 2–3 |
| [styles/](styles/README.md) | the styles: `STYLE.md` (rules + frame checklist), `kit.js`, `sample.png`, `demo/`; the STYLE hooks contract | steps 0, 2, building |
| [new-style.md](new-style.md) | making a new style from the user's references | step 2 |
| `kit/core.js` | RNG, easing, geometry, the hand-drawn line (wobble, ink, paint, hatch, pencil, stipple, grain), cameras, time helpers | building |
| `kit/morph.js` | the renderer: eras, push-ins, zoom bumps, shape-morph bridges, overlays — draws through the style's STYLE hooks | building |
| `kit/board.js` | the storyboard renderer | steps 2–3 |
| `kit/score-*.js` | synth (pluck, pad, drone, bass, sub, noiseHit, sweep, riser, chime, blip), loudness stage | scoring |
| [templates/](templates/) | `piece/` (an 8s cut-paper morph), `beat-cut/` (a 6s hard-cut piece with a 16th rush), `style/` (a blank style kit for new looks) | step 2 |
| `tools/` | build, tile, still, storyboard, export, review, textcheck, compare (reference vs frame), gallery, framehash (pixel-identity check), beats (a supplied track's beat map), capture (screenshots of the user's site), voice (a voice-over's lines and word times); `measure/` for references (`refs.mjs` for stills, `shotlog.py` for video) | throughout |
| [examples/history-of-ai/](examples/history-of-ai/) | a full 60s worked example (cut paper) | when unsure how something fits |
| `tools/pw.mjs`, `setup.ps1` | content-engine additions: the shared Playwright loader / system-Chrome launcher, and the local Windows setup | when a tool can't find Playwright or Chrome |
| [NOTICE.md](NOTICE.md), `LICENSE` | source, MIT licence, what was changed for this repo | — |

## Honesty about what's proven
Formats F2 (chronology / morph chain) and F4 (mission) have each produced a piece that passed every check from the card alone; F5 (fixed-hero journey) has several. The others are documented from study but unproven — say so when you pick one. Cut paper and crosshatch have carried full pieces; riso, sketchbook, math and pixel each come from one or two finished pieces plus a demo; isometric was made from references with new-style.md and so far has only its demo; a style made from new references is new ground until it has carried a piece. WebGL motion design (ray-marched 3D, motion blur, bloom) is not a shipped style yet.

On this Windows machine (content-engine import, 2026-10-07) every style demo, both templates and the 60s history-of-ai example were built, exported to MP4 and reviewed with these tools; see `library/kits/animate/IMPORT-NOTES.md` for render times and what was checked.
