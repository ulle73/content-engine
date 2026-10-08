---
name: nextphase-long-editing
description: >-
  NextPhase LONG (16:9) – redigera en lång talking-head/skärminspelning i NextPhase-husstilen: coral på mörkt prickrutnät, kapitelkort och chapter wipe, whip-pan, lower thirds, article-highlight, logga-blur-reveal, tystnadstrimning (tighten-cuts), layoutrotation, RVM-pop-out, SFX-pass + duckad musikbädd och segmentvis rendering. Delar skript (tighten, mix-sfx, mix-bgm, concat, RVM) med motiongraphics/persa/vibecode/zak.
---

# NextPhase — LONG-FORM editing skill (16:9)

> **Importerad till content-engine — kit `nextphase` (NextPhase Skill Pack).**
> **Varumärke:** Standardlooken är Claude-tema (coral på mörkt prickrutnät, AI-nyhetsexempel). Teknikerna är det värdefulla — copy, loggor och färger är utbytbara (färgerna sitter i `assets/tokens.css`). Biblioteksanvändaren är som standard **Golfkuponger** (svensk golf, svensk text; se `skills/golfkuponger-brand/`) — byt gärna till dess färger och ton, men inget här är en spärr. Kitets "hard rules" och husregler beskriver hur originalstilen ser ut; se dem som förval och tips, inte krav. "Jad/han" i texten = originalskaparen, för oss = användaren.
> **Sökvägar:** kitfilerna ligger i `library/kits/nextphase/skills/nextphase-long-editing/` — `reference/…`, `components/…`, `scripts/…`, `assets/tokens.css` m.m. nedan betyder den mappen (`SK=library/kits/nextphase/skills/nextphase-long-editing`). Per-video-filer (`assets/recording.mp4`, `out/…`, `PLAN.md`, `seg-NN/`, `sfx-cues.txt`) ligger i `work/nextphase/videos/<namn>/` (gitignorerat). Kör skript med full sökväg från repo-roten, t.ex. `bash library/kits/nextphase/skills/nextphase-long-editing/scripts/<skript>.sh …` / `python library/kits/nextphase/skills/nextphase-long-editing/scripts/<skript>.py …`; videofilerna i kommandona (`out/…`, `assets/…`) är då `work/nextphase/videos/<namn>/out/…` osv.
> **Windows:** Git Bash för `.sh`, `python` (aldrig `python3` — det är Store-stubben), Chrome i `C:\Program Files\Google\Chrome\Application\chrome.exe`, RVM-venv i `library/.venv` (signerad Python 3.12). Installation: `library/kits/nextphase/SETUP.md`.
> **Ljud (gratis som standard):** `python library/kits/nextphase/skills/nextphase-long-editing/scripts/make-free-sfx.py` (resp. `nextphase-short-editing/…`) fyller `sfx/` från HyperFrames SFX-bibliotek (Pixabay) + syntes. `scripts/gen-sfx.sh` (ElevenLabs) är betald och valfri. Originalets betalda SFX-pack, musikbädd, maskot, loggor och referensstills togs bort — se `library/kits/nextphase/IMPORT-NOTES.md`.
> **Husregler:** kitets `CLAUDE.md` finns som valfri vägledning i `library/kits/nextphase/reference/nextphase-house-rules.md`.


You are the motion-graphics editor for a monetized AI-news / how-to **long-form** video
(typically 5–20 minutes). A talking-head + screen recording goes in, and you build a
structured, chaptered edit with HyperFrames graphics over it. The look is the **dark
dotted-grid** house style. Everything below is the bar — an edit that misses **structure,
timing, media, or sound** is not done.

> **This is the long-form sibling of `nextphase-short-editing`.** Same design system,
> same motion grammar, same sound palette, same sourcing tricks, same background remover.
> What changes: the canvas, the safe zones, the arc (chapters instead of one 45-second
> ramp), retention pacing, the silence-tightening pass, the music bed, and segment-based
> assembly. Where a rule is inherited unchanged it says so; where it is **deliberately
> different for long form**, it is marked ⇄.

**⛔ Three hard rules**
1. **Never hardcode a color or font.** Import `assets/tokens.css` into every scene; use its
   CSS variables only.
2. **Animate transforms only** (`opacity, x, y, scale, scaleX/Y, rotation`) — plus
   `filter: blur()`, the one sanctioned exception. Never animate `top/left/width/height/
   borderWidth` for motion; it stutters and fails lint (`gsap_non_transform_motion`).
   Bars, highlighters and progress grow with `scaleX` + `transform-origin`, never `width`.
3. **Nothing publishes without explicit approval.** Deliver rendered + scored, open it for
   review, stop there.

**Read `reference/` before building** — `structure.md` (the long-form arc, read first) ·
`edit-standard.md` (the mandatory bar) · `design-system.md` (the look + 16:9 layouts) ·
`editing-rules.md` (timing, safe zones, the timing table) · `motion-grammar.md` (how things
move) · `screen-recording.md` (demo sections) · `sound-design.md` (SFX + the music bed) ·
`assembly.md` (segment rendering, concat, chapters) · `cutout-compositing.md` (background
removal) · `logo-reveal.md` (the blurred-logo name reveal).

---

## 0 · The frame (16:9 safe zones — never violate)

- **Canvas:** 1920×1080, 30fps. Margin/pad **96px** (5% title-safe) on every side.
- **Baseline grid:** 12 columns of 128px with 32px gutters inside the 96px margins.

| Zone | Box | Rule |
|---|---|---|
| **Title-safe** | inset 96 × 54 | No text or logo outside this, ever. |
| **Camera bubble** (screen-share layouts) | `1364,738 → 1864,1020` (500×282, `--r-card`) | Reserved. No graphic enters it. |
| **Bubble exclusion** | `x > 1300, y > 700` | Keep all graphics out while the bubble is up. |
| **Lower third** | `96,830 → 1000,1000` | Names, terms, sources, chapter labels. |
| **Caption band** (when captions are on) | centred `y 890–990`; when the bubble is up, centre it in `x 96–1300` instead | Nothing else lives here. |
| **Callout layer** | anywhere over the screen-share | Small labels + arrows only. Never a full card that hides the screen. |

⇄ **Long form has no fixed three-lane split.** The short's `top zone / caption / camera card`
is a 9:16 invention. In 16:9 the frame is divided by **layout** (below), and the safe zones
above are what each layout must respect.

---

## 1 · The ARC — every long-form video follows this

Full detail in `reference/structure.md`. The skeleton:

| # | Beat | Typical | What it is |
|---|---|---|---|
| 1 | **COLD OPEN** | 0:00–0:15 | The payoff **first**: the result, the number, the thing working. Never "hey guys, in today's video". Real media + motion from second one. |
| 2 | **PAYOFF SPIKE** | on the punch word | Reveal + coral flash + the `riser` cresting. ← the fixed signature, inherited from the short. |
| 3 | **PROMISE** | 0:15–0:45 | What they get and why now. Title card. One open loop planted ("and one of these is a trap"). |
| 4 | **CHAPTER 1…N** | 60–180s each | 3–6 chapters. Each opens on a **chapter card** (~2s) and runs its own mini-arc: claim → real proof → demo → takeaway. |
| 5 | **RE-HOOK** | every 45–90s | An open loop, a pattern interrupt (layout change + sound), or a tease of what's next. **Mark these on the timeline before you build.** |
| 6 | **THE TURN** | ~65–75% in | The catch / caveat / "here's what nobody tells you". Full-frame face, **Face Punch** zoom, graphics cleared. |
| 7 | **RECAP** | last 60–90s | The numbered payoff, staggered in, one line per chapter. |
| 8 | **CTA / OUTRO** | last 15–25s | The ask + the next-video card. |

### ⭐ THE ROTATION — the retention rule, outranks beat-by-beat taste
⇄ Inherited from the short, re-cast for 16:9 and **relaxed to long-form cadence**:

**Never the same layout twice in a row. Never hold one past ~25s.** (The short's limit is 8s;
long form can breathe, but not more than this.) **Every layout change carries a transition
AND a sound.** No silent cuts, ever.

The six 16:9 layouts:

| Layout | Frame | You visible? | Use it for |
|---|---|---|---|
| **Full-Frame Face** | camera edge to edge | yes | cold open, the turn, emphatic lines, CTA |
| **Transparent Background** | you cut out (RVM) on the designed BG, torso through a rounded-rect window | yes, floating | the opener, chapter cards, any "presenter" beat |
| **Split — Media Left / Face Right** | media `0–1150`, you `1150–1920` | yes, right | showing a thing while talking about it |
| **Split — Face Left / Media Right** | the mirror | yes, left | the alternate, so the split never repeats identically |
| **Screen-Share + Bubble** | recording full-frame, you in the bottom-right bubble | yes, small | demos and walkthroughs (`screen-recording.md`) |
| **B-Roll takeover** | full frame, edge to edge | **no** | the real web thing, or a designed explainer |

Default opener: **Transparent Background** through the cold-open line → cut to **B-Roll** of
something real pulled from the internet → **Split** → then keep rotating.

### ⭐ REAL MEDIA, NOT TEXT — every supporting beat
Typeset text graphics are **banned as support**. Every beat that backs a point shows a **real
resource**: a screenshot, a real product UI, a repo card, real footage, a pricing page, a
tweet, a docs page. Captions and the lower third are the only text; the CTA card is the one
exception.
- When he names a tool, show **that tool's real UI**, on the word.
- **Check every screenshot actually rendered content.** Login-walled and JS-heavy pages come
  back blank and ship as empty panels.
- ⇄ **Quota scales with length: ≥1 real media per 25s of finished video, minimum 10.** A
  10-minute video needs ~24. The short's "≥4" is a 45-second number and does not transfer.
- **No stock/podcast humans as b-roll** unless that person IS the subject of the line. If no
  relevant human footage exists, use the real UI, repo card, docs page, or the project's own
  diagram — never a generic cutaway to fill a slot.

### CAPTIONS — ⇄ selective, not wall-to-wall
Burned-in karaoke captions everywhere are a **shorts** convention; on a 16:9 timeline they
fight the graphics and read as cheap. The long-form rule:

- **ON** for the cold open, the payoff spike, the turn, any quoted stat or claim, and the CTA.
- **OFF** during screen-share/demo sections and whenever the picture already says it.
- **Word by word** when on: one word, popping in on its own transcript onset, out, next.
- Styles (`design-system.md`): **Parallax** (Instrument Serif, coral, vertical stretch) for the
  lines that matter · **Weight Shift** (Montserrat 300→900 as the word lands) for narration ·
  **Highlighted** (white on a `--coral` marker) for split layouts, matching the coral half.
- Position per the safe-zone table. Never over the camera bubble, never over the b-roll media.
- Ship a **separate `.srt`** for the whole video regardless — that's the accessibility layer,
  and it is not the same thing as burned captions.

### ⇄ SILENCE-TIGHTENING — do this FIRST, before anything else
Long-form recordings are full of half-second dead air and filler that a 45-second short never
accumulates. **Tighten before you time a single graphic**, because every word onset moves.

```bash
python library/kits/nextphase/skills/nextphase-long-editing/scripts/tighten-cuts.py --src assets/recording.mp4 --transcript assets/transcript.json \
  --max-gap 0.55 --pad 0.12 --out assets/recording-tight.mp4
```
It writes `recording-tight.mp4`, `assets/transcript-tight.json` (**onsets remapped to the new
timeline**) and `assets/cuts.json`. From that moment **the tight transcript is the only
timing source.** Timing anything against the original transcript after a tighten is the single
most common way this edit goes wrong.

### TRANSITIONS
- **PUSH** (inherited) on graphic swaps inside a layout: outgoing `x:0→-540` + fade, incoming
  `x:540→0` + fade, `power3.out`, ~0.44s.
- **⇄ WHIP-PAN** between layouts — a fast directional slide with a motion-blur streak, ~0.28s,
  on a `swoosh`. This is the long-form workhorse; the short's hard cut is too abrupt at this
  cadence.
- **⇄ CHAPTER WIPE** at every chapter boundary — the dot-grid BG sweeps across on a coral edge,
  ~0.6s, under the chapter card. Always paired with a `riser` tail or a `magic-reveal`.
- **DISSOLVE** 300ms for calm topic shifts inside a chapter. **FLASH** (1–2 frames coral) only
  on the payoff spike and the turn — it loses its meaning if used more than ~3× per video.

### Full-frame face ZOOMS (only when the face is full-frame — never in the bubble or a split)
- **Slow Push** (default): origin `50% 44%`, scale `1.00→1.06`, `ease:"none"`. ⇄ Gentler than
  the short's 1.10 — a 16:9 face is already large, and long holds make a big push seasick.
- **Face Punch** (the turn / a warning): origin `50% 38%`, scale `1.00→1.14`, `power2.inOut`.
- **Handheld Drift** (cinematic line): scale `1.04→1.08` + a small sine x/y sway.
Zoom the camera element only; captions and the lower third do **not** zoom.

---

## 2 · Timing — RETENTION FIRST

⇄ Long-form pacing, recalibrated from the short's numbers:

- **A new visual beat every ≤8s.** Nothing static holds longer. Screenshots get a slow
  Ken-Burns, stats a **count-up**, lists a stagger.
- **Never more than ~12s of uninterrupted talking head** without a cut, a zoom change, a
  graphic, or b-roll.
- **A layout change at least every 25s**, and always at a chapter boundary.
- **A re-hook every 45–90s.** Plan them on the timeline before building.
- **Anchor every graphic to the tight-transcript word onset** — it enters ON, or a hair after,
  the exact word it illustrates, never before. Round-number / eyeballed timings are **banned**.
- **Exit at the OUT word + 0.3s.** ⇄ **Cap 10s** per support graphic (the short's cap is 6s) —
  beyond that, evolve it (add a layer, advance a step) rather than let it sit.
- **One idea on screen at a time.**
- **Gap-check the transcript before editing:** Parakeet silently drops audio. Compare the
  transcript span against the file duration; re-transcribe any window with a >0.7s gap and
  merge. ⇄ On a 15-minute file, check **every** minute, not just the ends — a dropped chunk in
  the middle desyncs everything after it.
- Fix obvious ASR errors (brand names, the CTA keyword, verbal number slips) while keeping sync.

---

## 3 · Media — sourcing from the internet

- `curl` GitHub OG cards: `opengraph.githubassets.com/<anything>/<owner>/<repo>` · READMEs via
  `raw.githubusercontent.com` · og:images.
- **Chrome headless** for site screenshots (background it with a kill-after-25s safety).
  ⇄ Use a **16:9-shaped window** so the crop matches the canvas:
  ```
  "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu \
    --hide-scrollbars --window-size=1600,900 --virtual-time-budget=9000 \
    --screenshot=out.png "URL"
  ```
  Cookie/consent modals dim the page — crop above them, or brighten the crop with
  `ffmpeg -vf "eq=brightness=0.30:contrast=1.35"`. Cloudflare bot walls → pick another source.
- `yt-dlp` for real X / TikTok / YouTube clips (`--download-sections`). ⇄ Trim to **6–12s** for
  long form (the short's 4–6s reads as a flicker on a 16:9 timeline).
- **⭐ NORMALISE EVERY SOURCED CLIP TO 30fps CFR.** `yt-dlp --download-sections` and GIF→MP4
  conversions come back at 24/25/50/60fps or VFR; dropped into a 30fps composition they judder
  or drift. Always re-encode and then verify:
  ```
  ffmpeg -i in.mp4 -r 30 -fps_mode cfr -an -c:v libx264 -crf 21 out.mp4
  ffprobe -show_entries stream=r_frame_rate,avg_frame_rate,nb_frames -of default=nw=1 out.mp4
  ```
- Crop tight with `ffmpeg -vf "crop=W:H:X:Y"`. Downscale huge PNGs with `ffmpeg -i in.png -vf "scale=1920:-2" out.png` (eller Pillow).
  ⇄ A vertical screenshot in a 16:9 frame must be **framed inside a device or browser chrome**,
  not letterboxed with empty bars.
- Give any image reused across two beats **its own copy** (dodges the duplicate-media lint).
- **ARTICLE-HIGHLIGHT** (`components/article-highlight.html`): when a real headline/stat/quote/
  claim is referenced, screenshot the **REAL article body**, present it as a browser page, and
  sweep a **yellow highlighter** (`mix-blend-mode:multiply`, `scaleX` from the word onset)
  across the actual words. Real screenshot + real words only — never re-typeset or invent.
  ⇄ In 16:9 the page fills the frame as a **two-column browser page or a centred 1100px reading
  column** on the dark BG, not a full-bleed vertical scroll.
- **NEVER use emojis** anywhere on screen. Build designed marks (coral-circle monograms, CSS
  icons, arrows, checks, X). Emojis read as amateur.
- **Verify facts while sourcing.** Caption live numbers, not stale ones. Flag debunked stats,
  dead products, or clips whose rights are unclear — never amplify a myth on screen.
- **Windows-skärmdumpar:** Win+Shift+S lägger bilden i urklipp; be användaren spara den (t.ex. `Bilder\Skärmbilder\…png`) och ge sökvägen, eller använd den inklistrade filen direkt. Kopiera filer med glob om namnet innehåller specialtecken.

---

## 4 · Sound — ⇄ two passes, on the locked render

Full detail in `reference/sound-design.md`.

**Pass A — SFX** (inherited, rescaled):
- **⭐ The payoff spike = `riser`, ALWAYS** — start it ~1.5s before the reveal so it crests on
  the beat. Also use a `riser` into each chapter card.
- ⇄ **Density: ~12–20 cues per minute** (the short's "25–40 per short" is a per-45s figure).
  Nearly every move earns a sound; silence is a deliberate breath.
- **Varied palette — match the sound to the element:** `whoosh`=zoom/in · `swoosh`/`whoosh-2`=
  out/air/whip-pan · `pop`/`click`/`futuristic-click`=appears · `confirm`=✓/land ·
  `beep`=count tick · `magic-reveal`=hero reveal/highlight · `camera-shutter`=real media
  cut-in · `keyboard`=code/typing/terminal · `vinyl-rewind`=a swap/rewind · `ping`=CTA.
- **Calibrate to the VO** (`ffmpeg -af volumedetect`): SFX sit ~13–15 dB under voice peaks.
  Hot VO → ~0.11–0.12 transients; quiet VO → ~0.07–0.09.
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/<name>-visual.mp4 out/<name>-sfx.mp4 sfx-cues.txt
```

**⇄ Pass B — MUSIC BED (long form only).** A 15-minute video without a bed sounds like a
webcam recording; a short does not need one. The bed is **ducked under the voice** by a
sidechain compressor, not just turned down.
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh out/<name>-sfx.mp4 out/<name>-final.mp4 assets/music/bed.mp3
```
- Bed sits **~22–26 dB under voice peaks**; you should notice it leave, not arrive.
- **Change the bed at the turn** and drop it entirely for ~3s before the payoff spike — the
  return of music IS a retention device.
- Instrumental only, no vocals, no melody that competes with speech. Rights-cleared only.

---

## 5 · The workflow (every long-form video)

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```

0. **Locate the video folder + `VIDEO.md`.** Place the recording at `assets/recording.mp4`
   (and the screen capture at `assets/screen.mp4` if there is one).
1. **Transcribe** → `assets/transcript.json` (word-level):
   `npx --yes hyperframes transcribe assets/recording.mp4 -e parakeet -o assets/transcript.json`
   **Gap-check** against the file duration, minute by minute.
2. **⇄ TIGHTEN** → `scripts/tighten-cuts.py`. From here on, `transcript-tight.json` is the only
   timing source.
3. **⇄ STRUCTURE PASS — do this before authoring anything.** Write `PLAN.md`: the chapter list
   with in/out word onsets, the re-hook marks, the layout assigned to each beat, and the media
   shopping list. **Show it and get a go.** On a 15-minute video, building before the structure
   is agreed wastes hours.
4. **Source real media** into `assets/broll/` (≥1 per 25s, min 10); verify facts; normalise
   every clip to 30fps CFR.
5. **⇄ Author per-CHAPTER compositions**, not one giant `index.html` — `seg-01-cold-open/`,
   `seg-02-<chapter>/`, … See `reference/assembly.md`. Tokens only, transforms only, word-synced.
6. **Gates, per segment:** `npx --yes hyperframes lint` (0 errors) →
   `snapshot --at <times> -o snaps` → **read the contact sheet and fix** →
   `render -q high -f 30 -o out/seg-NN.mp4`.
7. **Concat + chapters:**
   `bash library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh out/final-visual.mp4 out/seg-*.mp4` — it also writes
   `out/chapters.txt` (YouTube timestamps) from the real segment durations. **Lock the visual edit.**
8. **Sound:** Pass A (`sfx-cues.txt` → `mix-sfx.sh`), then Pass B (`mix-bgm.sh`). Gut-check
   levels: SFX present but under the voice, bed under both, no clipping.
9. **Deliverables:** `out/<name>-final.mp4` · `out/chapters.txt` · `out/<name>.srt` ·
   a thumbnail frame if asked.
10. **Done:** report rendered + scored, open it for review. **Publish nothing without explicit
    approval.**

---

## Files in this skill

- `reference/` — the standards. Read `structure.md` first, then the rest.
- `assets/tokens.css` — the design tokens, 16:9 type scale. **Import into every composition.**
- `components/long-blocks.html` — the 16:9 brick kit (open it in a browser).
  `article-highlight.html` · `logo-blur-reveal.html` · `lower-third.html` · `chapter-card.html`.
- `scripts/tighten-cuts.py` — silence/filler tightening **+ transcript remap**.
- `scripts/mix-sfx.sh` — mixes `sfx-cues.txt` onto a render. `scripts/mix-bgm.sh` — ducked
  music bed. `scripts/gen-sfx.sh` — (re)generates the palette.
- `scripts/concat-segments.sh` — joins segment renders, emits `chapters.txt`.
- `scripts/rvm-matte.py` · `scripts/cutout-hook.sh` · `scripts/make-rect-mask.py` ·
  `scripts/find-cut-line.py` — background removal + the pop-out layout
  (`reference/cutout-compositing.md`). Env: `source library/.venv/Scripts/activate`.
- `sfx/` — the sound palette the cues resolve against.

> `mix-sfx.sh` resolves the palette as `$(dirname $0)/../sfx/`. **Invoke it by its path inside
> the skill folder** — never copy it into a video folder, or every cue fails with
> "unknown sound".

Bricks are starting points, not a cage. Invent bespoke, story-specific scenes freely — but
everything obeys tokens + motion grammar + the arc + the safe zones.
