---
name: vibecode
description: >-
  VIBECODE-stilen (16:9, NextPhase) – mättad koboltblå grund under klippt-papper-collage: rivna anteckningskort, en fejkad redigeringstidslinje på linjerat papper som byggs klipp för klipp, urklippta skärmdumpar, handritade röda X, kraftiga kondenserade affischversaler, pixelmaskot och stop-motion-churn på 2s; cream/guld- och mörk alternativgrund. Använd när användaren vill ha collage/papper-looken eller dess scener.
---

# VIBECODE — editing style

> **Importerad till content-engine — kit `nextphase` (NextPhase Skill Pack).**
> **Varumärke:** Standardlooken är kobolt/cream-papper med kodnings-/AI-exempelcopy och en pixelmaskot. Teknikerna är det värdefulla — copy, loggor och färger är utbytbara (färgerna sitter i `assets/tokens.css`). Biblioteksanvändaren är som standard **Golfkuponger** (svensk golf, svensk text; se `skills/golfkuponger-brand/`) — byt gärna till dess färger och ton, men inget här är en spärr. Kitets "hard rules" och husregler beskriver hur originalstilen ser ut; se dem som förval och tips, inte krav. "Jad/han" i texten = originalskaparen, för oss = användaren.
> **Sökvägar:** kitfilerna ligger i `library/kits/nextphase/skills/vibecode/` — `reference/…`, `components/…`, `scripts/…`, `assets/tokens.css` m.m. nedan betyder den mappen (`SK=library/kits/nextphase/skills/vibecode`). Per-video-filer (`assets/recording.mp4`, `out/…`, `PLAN.md`, `seg-NN/`, `sfx-cues.txt`) ligger i `work/nextphase/videos/<namn>/` (gitignorerat). Kör skript med full sökväg från repo-roten, t.ex. `bash library/kits/nextphase/skills/vibecode/scripts/<skript>.sh …` / `python library/kits/nextphase/skills/vibecode/scripts/<skript>.py …`; videofilerna i kommandona (`out/…`, `assets/…`) är då `work/nextphase/videos/<namn>/out/…` osv.
> **Windows:** Git Bash för `.sh`, `python` (aldrig `python3` — det är Store-stubben), Chrome i `C:\Program Files\Google\Chrome\Application\chrome.exe`, RVM-venv i `library/.venv` (signerad Python 3.12). Installation: `library/kits/nextphase/SETUP.md`.
> **Ljud (gratis som standard):** `python library/kits/nextphase/skills/nextphase-long-editing/scripts/make-free-sfx.py` (resp. `nextphase-short-editing/…`) fyller `sfx/` från HyperFrames SFX-bibliotek (Pixabay) + syntes. `scripts/gen-sfx.sh` (ElevenLabs) är betald och valfri. Originalets betalda SFX-pack, musikbädd, maskot, loggor och referensstills togs bort — se `library/kits/nextphase/IMPORT-NOTES.md`.
> **Husregler:** kitets `CLAUDE.md` finns som valfri vägledning i `library/kits/nextphase/reference/nextphase-house-rules.md`.


A talking head plus screen recordings goes in; an edit comes out where **the
frame is a workspace somebody built out of cut paper, and it is being operated
on while you watch.**

There is no grade, no lit stage, no glow. There is a flat cobalt plate, paper
cut with scissors, marker, and a machine visibly doing work.

*(Om stilen inte redan är vald kan du fråga vilken NextPhase-stil som passar — `nextphase-studio` har hela menyn. Skriv valet överst i `PLAN.md`.)*

> ### Where this look comes from
> Reverse-engineered from two edits Jade supplied on 2026-08-29. Every colour,
> size and frame count in `assets/tokens.css` is **measured**, not invented.
> - **REF-B** — `youtube.com/watch?v=Ohyo6-VO1jY` 0–45s — *the spine.* The
>   cobalt cut-paper material, the paper timeline, the red X, the churn.
> - **REF-A** — `youtube.com/watch?v=vI4RdXMSq8c` 0–1:20 — *the furniture.* The
>   idea that the frame is running software: timeline HUD, step list, meter
>   card, scrub rail. Its cream palette ships as `.vc-cream`.
>
> They are **not the same palette** — REF-B is saturated collage, REF-A is
> restrained cream-and-gold. REF-B's material won because Jade said "especially"
> that one; REF-A's widgets are rebuilt in REF-B's paper.
> `reference/reference-log.md` has the shot-by-shot evidence, the measurement
> method, and every finding mapped to where it is written up.

---

## ⛔ Seven hard rules

1. **Never hardcode a colour, font or duration.** Import `assets/tokens.css`;
   use its variables only. Never mix vibecode tokens with `nextphase`,
   `motiongraphics` or `persa` tokens in one composition.
2. **Paper is the only material** — torn edge, **hard offset shadow with zero
   blur**, hand-placed tilt, and never the same angle twice in a frame. A
   straight-edged rounded rectangle with a soft shadow is not this style.
3. **Red means no.** `--vc-red` is for the X and the strike-through and nothing
   else. Never fill a card red, never colour type red.
4. **The caption HARD-CUTS.** Zero frames in, zero frames out. No fade, no
   scale, no pop. See `reference/motion-grammar.md` §4.
5. **The ground never moves.** No camera drift, no push-in, no parallax on the
   plate. This is the opposite of `motiongraphics` — do not carry that habit
   over.
6. **Animate transforms only** — `opacity, x, y, scale, scaleX/Y, rotation` plus
   `filter: blur()`. Bars and rails grow with `scaleX` + `transform-origin`.
7. **Nothing publishes without explicit approval.** Deliver rendered + scored,
   open it for review, stop there.

**Read `reference/` before building** — `look.md` (the material) ·
`motion-grammar.md` (**the core — read this first**) · `layouts.md` (the seven
scenes) · `typography.md` · `sound-design.md` · `workflow.md` ·
`reference-log.md`.

---

## 1 · The look in one paragraph

**A flat saturated cobalt plate under a halftone dot grid, with a radial lift in
the middle and a vignette at the corners. Everything on it is cut from the same
cream paper — torn edges, hard offset shadows, hand-placed tilts, a magenta/cyan
print misregistration on the hero pieces.** A fake editing timeline drawn on
ruled notebook paper builds clip by clip. Real screenshots and app icons are
scissored out with a white paper border. Heavy condensed cream caps sit on the
ground with a hard navy shadow. A red hand-drawn X kills things. A pixel agent
character stands in for the AI. And it all **churns on 2s** — icons shuffling,
cards jittering, sparkles blinking — which is what makes it read as vibe coded
rather than designed.

Full numbers: `reference/look.md`.

## 2 · The frame

1920×1080 @30fps. The composition root carries **`.vc-frame`**:

```html
<div class="vc-frame">           <!-- cobalt, the default -->
<div class="vc-frame vc-cream">  <!-- calm chapters, money beats -->
<div class="vc-frame vc-dark">   <!-- the teaser interstitial, the CTA -->
```

### ⭐ `.vc-frame` on the composition root
Type is sized in `cqh`, which resolves against a **size container** —
`.vc-frame` sets `container-type: size`. Without it every string renders at a
fraction of its size and the layout still "looks fine", which is exactly why it
is worth checking first when a scene looks subtly wrong.

| Zone | Value | Rule |
|---|---|---|
| Safe | inset `--vc-safe-x` 6% × `--vc-safe-y` 5% | Nothing readable outside. Paper may bleed; a label may not. |
| Caption | centred, bottom 11% | Fixed. Never moves. Hard-cuts. |
| Rail | bottom 2.6%, 4% inset | Workspace scenes only. |

**One ground per chapter.** Switching mid-chapter reads as a mistake; switching
*at* a chapter boundary is a strong beat — give it a transition and the biggest
sound in the video.

## 3 · The seven scenes and the rotation

Full spec in `reference/layouts.md`.

| # | Scene | For |
|---|---|---|
| 1 | **Clean Face** | the rest beat — roughly a third of the runtime |
| 2 | **Paper Timeline** ⭐ | the signature: ruled paper, clips building left→right |
| 3 | **Tile Row** ⭐ | three paper tiles with navy pictograms, then the red X lands on each |
| 4 | **Poster** | two lines of display caps, second 1.7–1.8× the first, yellow arrow |
| 5 | **Workspace** | REF-A's step list + media card + head card + scrub rail, in paper |
| 6 | **Sticker Wall** | 3–5 real assets, scissored, churning as they land |
| 7 | **Agent Beat** | the pixel mascot doing one thing — punctuation, 1.5–3s |

Plus the `.vc-dark` **Teaser** between chapters and the CTA card at the end.

**Never the same scene twice in a row. Never hold one past ~20s.** But do not run
wall-to-wall graphics either — REF-B sits on a plain talking head for 8+ seconds
at a stretch. Wall-to-wall media is the amateur read.

### ⭐ REAL MEDIA, NOT TYPESET TEXT
Every beat that supports a point shows a real resource — a screenshot, a real
product UI, a repo card, a docs or pricing page, real footage. **≥1 per 20s,
minimum 8.**
- **Check every screenshot actually rendered content.** Login-walled and
  JS-heavy pages come back blank and ship as empty panels.
- **No random humans as b-roll.** Cut to a person only when that person *is* the
  subject of the line — otherwise the real UI, the repo card, or the agent
  character. That is what the mascot is for.
- **Never use emojis.** Build a navy pictogram on a paper tile instead. REF-A
  uses an emoji on its strike slide; we do not — see `reference-log.md`.
- Re-encode every sourced clip to **30fps CFR** and verify with `ffprobe`.

### ⭐ COPY IS DERIVED, NEVER INHERITED
Every string comes from the speaker's own words at their onset in
`transcript-tight.json`, the real thing named in that beat, or a verified figure.
**Write the actual copy into `PLAN.md`, per beat, before authoring.**

## 4 · The two things that make it vibecode

### The churn
REF-B's cards do not ease into place — their contents **shuffle between them
every 2–3 frames** while the group assembles, the cards jitter ±1.2° at the same
cadence, and yellow sparkles blink on 2 / off 2. Step the values; never tween
them. A smooth interpolation between the same two states reads as a glitch, not
as stop-motion.

Churn is **texture around the message, never the message**. The ground, the
talking head, and anything the viewer is being asked to read all hold still.

### The negation
Two red strokes with rounded caps, drawn on with a stroke-dash reveal, 5 frames
each with a 3-frame lag, **overshooting the card on both ends**. It is the
punchline of Scene 3 and it gets the loudest sound in the style.

A red X contained neatly inside its tile looks drawn by a computer, which is
exactly the opposite of the intent.

## 5 · Motion

`reference/motion-grammar.md`. Measured at 30fps (REF-B was 23.976 and every
count was converted — do not copy its raw numbers):

| Move | Frames |
|---|---|
| **Churn hold** | **2 — the whole style lives here** |
| **Caption in / out** | **0 — it hard-cuts** |
| Paper card in | 7 (+25 settle) |
| Stagger between siblings | 3 |
| Timeline clip in | 5, staggered 4 |
| Red X stroke | 5, second lags 3 |
| Anything out | 4 |
| Paper wipe transition | 9 |

## 6 · Sound

`reference/sound-design.md`. **~12–18 cues/min** — denser than persa, because
more things move. Every layout change gets a transition **and** a sound.

The two that matter most: **the red X** (marker scratch, loudest cue in the
style) and **the chapter ground swap** (cobalt→cream, the biggest visual event
in the video). Captions and churn are **silent** — a cue on either machine-guns.

Reuse the shared palette and **call the mixer by its path inside the sibling
skill folder** — never copy it into a video folder, or every cue fails with
`unknown sound`:
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/final-visual.mp4 out/final-sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh out/final-sfx.mp4 out/final.mp4 assets/music/bed.mp3
```

## 7 · The workflow

Full detail in `reference/workflow.md`. Prefix **every** bash step with:
```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```

0. **Ask which style.** Locate `work/nextphase/videos/<name>/`, `VIDEO.md`, `assets/recording.mp4`.
1. **Transcribe** → chunk anything over ~90s and gap-check minute by minute.
2. **Tighten** → `transcript-tight.json` is now the only timing source.
3. **Build the ground plate** with `scripts/make-paper.py`. **No colour grade** —
   vibecode does not touch the footage.
4. **Matte** the head with RVM (only for Scene 7 and card-less beats).
5. **`PLAN.md`** — scenes per beat, the actual copy, the media list, the chapter
   grounds. **Get a "go" before authoring.**
6. **Source real media**, verify facts, normalise to 30fps CFR.
7. **Author** per-chapter compositions. Symlink assets into each `seg-NN/`;
   HyperFrames rejects `../assets/`. Vendor fonts and gsap.
8. **Per segment:** `lint` (0 errors) → **`check-vibecode.sh` (must exit 0)** →
   `snapshot --at <times>` → **read the contact sheet and fix** →
   `render -q high -f 30`.
9. **Concat** via `library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh` —
   chapter timestamps come from real rendered durations, never from `PLAN.md`.
   Relay the source audio after the concat (~38ms AAC priming per join).
10. **Sound:** SFX pass, then the ducked bed.
11. **Deliver:** `out/final.mp4` · `out/chapters.txt` · `out/<name>.srt`. Report
    rendered + scored, open for review. **Publish nothing without approval.**

---

## Files in this skill

- `assets/tokens.css` — the measured tokens and every `vc-` class.
  **Import into every composition.** (CSS comments do not nest — never write a
  closing marker inside one of its header blocks, or the whole sheet silently
  stops applying.)
- `components/vibecode-system.html` — **the whole style on one page**: all seven
  scenes, both alternate grounds, the palette, the churn and the cadence, live
  in a browser. Open this first; it is the fastest way to see what the style
  *is*. Open it beside `reference/stills/`.
- `reference/` — `look.md` · `motion-grammar.md` · `layouts.md` ·
  `typography.md` · `sound-design.md` · `workflow.md` · `reference-log.md`.
- `reference/stills/` — the source evidence: 15 frames including 1fps/2fps
  contact sheets of both reels and full-res captures of every signature layout.
- `scripts/make-paper.py` — render the halftone ground plate; generate
  deterministic torn-edge polygons so no two cards share a silhouette.
- `scripts/check-vibecode.sh` — **the render gate.** Run before every render.
- Everything else is **shared with `nextphase-long-editing`** — tighten,
  rvm-matte, mix-sfx, mix-bgm, concat-segments. Call them by their path in that
  folder; never copy them into a video folder.
