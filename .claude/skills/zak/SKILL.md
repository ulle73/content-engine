---
name: zak
description: >-
  ZAK-stilen (16:9 eller 9:16, NextPhase) – ett rundat fönster som svävar på helsvart med lika mycket luft ovan och under, en Didone-seriffrad i luften ovanför och täta vita 2–4-ordscaptions som hårdklipper i fönstret utan skugga. Ingen rörelse alls – lugn, seriös, minimal. Använd när användaren vill ha den stilla, minimala fönsterlooken.
---

# ZAK — editing style

> **Importerad till content-engine — kit `nextphase` (NextPhase Skill Pack).**
> **Varumärke:** Standardlooken är svart/vitt med Playfair + Inter och AI-exempelcopy. Teknikerna är det värdefulla — copy, loggor och färger är utbytbara (färgerna sitter i `assets/tokens.css`). Biblioteksanvändaren är som standard **Golfkuponger** (svensk golf, svensk text; se `skills/golfkuponger-brand/`) — byt gärna till dess färger och ton, men inget här är en spärr. Kitets "hard rules" och husregler beskriver hur originalstilen ser ut; se dem som förval och tips, inte krav. "Jad/han" i texten = originalskaparen, för oss = användaren.
> **Sökvägar:** kitfilerna ligger i `library/kits/nextphase/skills/zak/` — `reference/…`, `components/…`, `scripts/…`, `assets/tokens.css` m.m. nedan betyder den mappen (`SK=library/kits/nextphase/skills/zak`). Per-video-filer (`assets/recording.mp4`, `out/…`, `PLAN.md`, `seg-NN/`, `sfx-cues.txt`) ligger i `work/nextphase/videos/<namn>/` (gitignorerat). Kör skript med full sökväg från repo-roten, t.ex. `bash library/kits/nextphase/skills/zak/scripts/<skript>.sh …` / `python library/kits/nextphase/skills/zak/scripts/<skript>.py …`; videofilerna i kommandona (`out/…`, `assets/…`) är då `work/nextphase/videos/<namn>/out/…` osv.
> **Windows:** Git Bash för `.sh`, `python` (aldrig `python3` — det är Store-stubben), Chrome i `C:\Program Files\Google\Chrome\Application\chrome.exe`, RVM-venv i `library/.venv` (signerad Python 3.12). Installation: `library/kits/nextphase/SETUP.md`.
> **Ljud (gratis som standard):** `python library/kits/nextphase/skills/nextphase-long-editing/scripts/make-free-sfx.py` (resp. `nextphase-short-editing/…`) fyller `sfx/` från HyperFrames SFX-bibliotek (Pixabay) + syntes. `scripts/gen-sfx.sh` (ElevenLabs) är betald och valfri. Originalets betalda SFX-pack, musikbädd, maskot, loggor och referensstills togs bort — se `library/kits/nextphase/IMPORT-NOTES.md`.
> **Husregler:** kitets `CLAUDE.md` finns som valfri vägledning i `library/kits/nextphase/reference/nextphase-house-rules.md`.


A talking head goes in; an edit comes out where **the framing is the design**.
There is no grid, no stage, no collage, no accent colour and no motion. There
is a black field, one rounded window sitting in it with real air above and
below, a serif line in that air, and words that change three times a second.

*(Om stilen inte redan är vald kan du fråga vilken NextPhase-stil som passar — `nextphase-studio` har hela menyn. Skriv valet överst i `PLAN.md`.)*

> ### Where this look comes from
> Reverse-engineered frame by frame from one reel Jade supplied:
> **REF-A** — `instagram.com/p/Db2RzkxvWpz/` — 1080×1920, 30fps, 39.9s,
> creator `zacharyronusac`.
>
> Every number in `assets/tokens.css` marked MEASURED was read off it, and the
> tokens were verified by rendering them back through headless Chrome and
> diffing against the source frame — **the window, the title and the caption
> all land within 1px** (`reference/stills/09-reference-vs-tokens.png`).
>
> ⚠ **It is one reel.** Geometry and type are trustworthy to the pixel. The
> grade was measured in one room under one lamp and is a target range, not a
> calibrated curve. The scene vocabulary past the single locked frame is
> **invented**, and `reference/layouts.md` marks every scene measured or
> derived. `reference/reference-log.md` has the method, the raw readings, and
> a table mapping each finding to where it is written up.
>
> ⚠ **That reel is another creator's work.** Zak is the *technique*. Their
> words and their room are theirs — `scripts/check-zak.sh` fails the render if
> their copy resurfaces.

---

## ⛔ Seven hard rules

1. **Never hardcode a colour, font or duration.** Import `assets/tokens.css`;
   use its variables only. Never mix zak tokens with another style's.
2. **The caption HARD-CUTS.** Zero frames. No fade, no scale, no pop, no
   per-word reveal. 53 out of 53 measured changes landed on a single frame.
3. **The caption has NO shadow, NO stroke and NO box.** That is measured, not
   an omission — see `reference/captions.md` §2. It reads only because the
   plate under it is dark, so **when it is hard to read, fix the plate.**
   `python library/kits/nextphase/skills/zak/scripts/check-contrast.py` gates this on every render.
4. **Nothing moves.** No drift, no push-in, no parallax, no eased anything.
   Measured at 0px over 40 seconds. The one exception is the 6-frame full
   bleed, used once or twice in a whole video.
5. **A caption is 2–4 words.** A one-word caption is `persa`, not zak.
6. **Every word on screen is derived from THIS video.** Kit copy in
   `components/` is placeholder and the reference copy belongs to another
   creator. Run `bash library/kits/nextphase/skills/zak/scripts/check-zak.sh work/nextphase/videos/<name>` before every render.
7. **Nothing publishes without explicit approval.** Deliver rendered + scored,
   open it for review, stop there.

**Read `reference/` before building** — `captions.md` (**the core of the style
— read this first**) · `layouts.md` (the frame, the scenes, and the 16:9
derivation) · `look.md` · `typography.md` · `motion-grammar.md` ·
`sound-design.md` · `workflow.md` · `reference-log.md`.

---

## 1 · The look in one paragraph

**A pure-black field with one rounded window in it, equal air above and below,
and a single serif line in the upper air that is set once and never changes.**
Inside the window: warm, low-key footage that never touches white, and two to
four white words in a brutally tight grotesque that replace themselves every
twenty-odd frames. Two colours — black and white. Two typefaces. One move in
the entire video. Everything else is a hard cut carried by a sound.

---

## 2 · The frame

**1920×1080 @30fps is the default** for this studio. The style was *measured*
at 1080×1920, so `:root` in `tokens.css` carries those numbers and `.zk-16x9`
overrides the five that do not transfer.

```html
<div class="zk-frame zk-16x9"> … </div>   <!-- long-form  -->
<div class="zk-frame">         … </div>   <!-- vertical   -->
```

| | 9:16 — measured | 16:9 — derived |
|---|---|---|
| Window | **968 × 968**, a square | **1720 × 732**, a 2.35:1 scope letterbox |
| Side margin | 56px (5.19%) | 100px (5.19%) — the same |
| Air above / below | **476 / 476**, equal to the pixel | **174 / 174**, equal |
| Corner radius | 70px | 70px — the same *absolute* size |
| Title line | Playfair 56px, 66px above the window | Playfair 46px, 21px above |
| Caption | Inter 700, 63px, −0.065em | Inter 700, **80px**, −0.065em |

**Read `reference/layouts.md` §5 before building wide.** The 16:9 window is a
genuine re-crop of the source, not a scale — `zak-plate.sh` takes a `crop-y`
because a talking head wants headroom thrown away, not chin. And the 16:9
caption size is **the one token in the style that was chosen by eye rather than
derived**; the reasoning, and why arithmetic gives two answers 3× apart, is
written up there and in the tokens file.

### ⭐ Three things follow from the ground being literally `#000000`
- **No drop shadow on the window.** There is nothing behind it to catch one.
- **No border, no rim, no glow.** The radius is the only edge treatment.
- **Nothing lives in the bottom air.** It is empty for all 40 seconds of the
  reference. No bar, no handle, no logo. The air *is* the design.

### ⭐ `.zk-frame` on the composition root
Type is sized in `cqh` so one scale serves both aspects, and `cqh` resolves
against a size container. Without `.zk-frame` every string renders at a
fraction of its size and the layout still looks plausible — which is why it is
the first thing to check when a scene looks subtly wrong. Never size type in
`%`: that resolves against the parent's font-size and fails the same way.

---

## 3 · The scenes

Scene 1 is measured. **Scenes 2–5 are derived** — invented so long-form has a
rotation, keeping everything that was measured intact. Full spec in
`reference/layouts.md` §3.

| # | Scene | For |
|---|---|---|
| 1 | **Locked Window** | the rest beat — and it is most of the runtime |
| 2 | **Media Window** | the window holds the real resource instead of the face |
| 3 | **Split Window** | the face and the thing, at once, one outer radius |
| 4 | **Title Card** | the chapter break — empty window, serif line carries it |
| 5 | **Full Bleed** | **the one move.** 6 frames. Once or twice per video. |

**Never the same scene twice in a row. Never hold one past ~20s.** But note
what the reference does: it holds *one* shot for 39.9 seconds. This style is
supposed to sit still, and cutting every three seconds is the amateur read of
it. Hold 6–15s at a stretch.

### ⭐ REAL MEDIA, NOT TYPESET TEXT
Every beat that supports a point shows a real resource — a screen recording,
real product UI, a docs or pricing page, a repo card. **≥1 per 20s, minimum 8.**
- **Check every screenshot actually rendered content.** Login-walled and
  JS-heavy pages come back blank and ship as empty windows.
- **No random humans as b-roll.** Cut to a person only when that person *is*
  the subject of the line.
- **Never use emojis.** There is no accent colour here to build a mark from —
  a designed mark is white type, a white rule, or nothing.
- Re-encode every sourced clip to **30fps CFR** and verify with `ffprobe`.

### ⭐ COPY IS DERIVED, NEVER INHERITED
Every string comes from the speaker's own words at their onset in
`transcript-tight.json`, the real thing named in that beat, or a verified
figure. **Write the actual copy into `PLAN.md`, per beat, before authoring.**

---

## 4 · The two things that make it zak

### The caption system
2–4 words, white, Inter 700 at **−0.065em**, hard-cutting on a single frame
every ~22 frames, in a fixed position, with **no shadow of any kind**.

```bash
python library/kits/nextphase/skills/zak/scripts/build-captions.py assets/transcript-tight.json \
    --out seg-01-cold-open/captions.html --offset <segment start>
python library/kits/nextphase/skills/zak/scripts/check-contrast.py out/seg-01.mp4
```

The builder derives its hold target from the transcript's own speech rate — the
measured 22 frames is what 2–4 words *cost* at the reference speaker's ~240
wpm, not a metronome. It reports rate, holds and words-per-caption against the
reference and warns on anything out of range.

The checker is the one that matters. The caption has no shadow, so the plate is
the only thing making it readable; a bright plate kills it **silently**, and
the render still succeeds. It is calibrated: the reference reads 125.1 against
a ceiling of 150, and a brightened copy of the same reel fails on every frame.
`reference/captions.md` §2.

### The stillness
Nothing drifts. Nothing pushes in. Nothing eases. Measured at 0px of drift and
0% of scale change across 40 seconds, with the title line static to within JPEG
noise. **This is the exact opposite of `motiongraphics`, and carrying that
skill's continuous-drift habit over is the most common way a zak comp goes
wrong.** `check-zak.sh` fails a tween on `.zk-plate` or a transform on
`.zk-window`.

---

## 5 · Motion

`reference/motion-grammar.md`. The whole table:

| Move | Frames @30fps |
|---|---|
| **Caption change** | **0 — it hard-cuts** |
| Window contents change | 0 |
| Scene change | 0 |
| Camera drift / push-in | **0 — there is none** |
| Window → full bleed | **6** — the only animation in the style |

**The cut is the transition. If a cut needs help, the help is a sound.**

⚠ GSAP `fromTo` defaults to `immediateRender:true` and will apply a later
beat's `from` state at frame 0. Always pass `immediateRender:false` — with a
single tween in the whole piece, a failure here is total.

---

## 6 · Sound

`reference/sound-design.md`. Zak has **no visual transitions at all**, so sound
is doing the job a transition does elsewhere — it is what makes a hard cut read
as intentional. **~6–10 cues/min: transitions only, quiet transients.**

**Never cue a caption change.** At 80 changes a minute it is unlistenable, and
it is the most tempting mistake in the style.

Reuse the sibling palette and **call the mixer by its path inside that skill
folder** — never copy it into a video folder:
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/visual.mp4 out/sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh  out/sfx.mp4    out/final.mp4 assets/music/bed.mp3
```

---

## 7 · The workflow

Full detail in `reference/workflow.md`. Prefix **every** bash step with:
```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```

0. **Ask which style.** Locate `work/nextphase/videos/<name>/`, `VIDEO.md`, `assets/recording.mp4`.
1. **Transcribe** → chunk anything over ~90s, gap-check minute by minute.
2. **Tighten** → `transcript-tight.json` is now the only timing source.
3. **Reframe + grade** the plate (`zak-plate.sh`). **No matte step** — zak does
   not cut the subject out; reaching for `rvm-matte.py` here is persa habit.
4. **`PLAN.md`** — scenes per beat, the real on-screen copy, the media list.
   **Get a "go" before authoring.**
5. **Source real media**, verify facts, normalise to 30fps CFR.
6. **Author** per chapter. Symlink assets into each `seg-NN/`; HyperFrames
   rejects `../assets/`. Build captions with `build-captions.py`.
7. **Per segment:** `lint` (0 errors) → **`check-zak.sh` (exit 0)** →
   `snapshot` → **read the contact sheet and fix** → `render -q high -f 30` →
   **`check-contrast.py` (exit 0)**.
8. **Concat** via `library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh` —
   chapter timestamps come from real rendered durations, never from `PLAN.md`.
   Relay the source audio after the concat (AAC priming drifts ~38ms per join).
9. **Sound:** SFX pass, then the ducked bed.
10. **Deliver:** `out/final.mp4` · `out/chapters.txt` · `out/<name>.srt`.
    Report rendered + scored, open for review. **Publish nothing without approval.**

---

## Files in this skill

- `assets/tokens.css` — the measured design tokens and every zak class.
  **Import into every composition.** (CSS comments do not nest — never write a
  closing marker inside one of its header blocks, or the whole sheet silently
  stops applying.)
- `components/zak-system.html` — **the whole style on one page**: all five
  scenes at real proportions in both aspects, the type table, the cadence
  table, and a list of what breaks it. Open this first; it is the fastest way
  to see what the style *is*. Open it beside `reference/stills/`.
- `reference/` — `captions.md` · `layouts.md` · `look.md` · `typography.md` ·
  `motion-grammar.md` · `sound-design.md` · `workflow.md` · `reference-log.md`.
- `reference/stills/` — the source evidence: full frames, a 1fps contact sheet,
  3× type crops, a 4× corner crop, an 8-frame strip across a caption hard cut,
  **the tokens-vs-reference round-trip**, and the derived 16:9 form.
- `scripts/zak-plate.sh` — reframe a source into the window and grade it.
- `scripts/build-captions.py` — transcript → hard-cut 2–4 word phrase captions.
- `scripts/check-contrast.py` — **the gate that matters.** Run on every render;
  the caption has no shadow and dies silently on a bright plate.
- `scripts/check-zak.sh` — the static render gate. Run before every render.
- Everything else is **shared with `nextphase-long-editing`** — tighten,
  mix-sfx, mix-bgm, concat-segments. Call them by their path in that folder;
  never copy them into a video folder.
