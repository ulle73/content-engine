---
name: persa
description: >-
  PERSA-stilen (16:9 eller 9:16, NextPhase) – varm, avmättad film-grade med grain och bloom, hårdklippta enordscaptions, motivet matte:at tillbaka ovanpå så att huvudet skymmer de stora emfasorden, riktiga skärminspelningar som rundade paneler, tre accenter och en handtextad not-nivå. Använd när användaren vill ha persa-looken, persa-graden eller text-bakom-huvudet-tekniken.
---

# PERSA — editing style

> **Importerad till content-engine — kit `nextphase` (NextPhase Skill Pack).**
> **Varumärke:** Standardlooken är en varm film-grade med röd/lime/amber-accenter och AI-exempelcopy. Teknikerna är det värdefulla — copy, loggor och färger är utbytbara (färgerna sitter i `assets/tokens.css`). Biblioteksanvändaren är som standard **Golfkuponger** (svensk golf, svensk text; se `skills/golfkuponger-brand/`) — byt gärna till dess färger och ton, men inget här är en spärr. Kitets "hard rules" och husregler beskriver hur originalstilen ser ut; se dem som förval och tips, inte krav. "Jad/han" i texten = originalskaparen, för oss = användaren.
> **Sökvägar:** kitfilerna ligger i `library/kits/nextphase/skills/persa/` — `reference/…`, `components/…`, `scripts/…`, `assets/tokens.css` m.m. nedan betyder den mappen (`SK=library/kits/nextphase/skills/persa`). Per-video-filer (`assets/recording.mp4`, `out/…`, `PLAN.md`, `seg-NN/`, `sfx-cues.txt`) ligger i `work/nextphase/videos/<namn>/` (gitignorerat). Kör skript med full sökväg från repo-roten, t.ex. `bash library/kits/nextphase/skills/persa/scripts/<skript>.sh …` / `python library/kits/nextphase/skills/persa/scripts/<skript>.py …`; videofilerna i kommandona (`out/…`, `assets/…`) är då `work/nextphase/videos/<namn>/out/…` osv.
> **Windows:** Git Bash för `.sh`, `python` (aldrig `python3` — det är Store-stubben), Chrome i `C:\Program Files\Google\Chrome\Application\chrome.exe`, RVM-venv i `library/.venv` (signerad Python 3.12). Installation: `library/kits/nextphase/SETUP.md`.
> **Ljud (gratis som standard):** `python library/kits/nextphase/skills/nextphase-long-editing/scripts/make-free-sfx.py` (resp. `nextphase-short-editing/…`) fyller `sfx/` från HyperFrames SFX-bibliotek (Pixabay) + syntes. `scripts/gen-sfx.sh` (ElevenLabs) är betald och valfri. Originalets betalda SFX-pack, musikbädd, maskot, loggor och referensstills togs bort — se `library/kits/nextphase/IMPORT-NOTES.md`.
> **Husregler:** kitets `CLAUDE.md` finns som valfri vägledning i `library/kits/nextphase/reference/nextphase-house-rules.md`.


A talking head plus screen recordings goes in; an edit comes out where **the
footage itself is the design**. There is no dark grid and no lit stage. There is a
graded plate, a cut-out person, and type that lives *in the room with them*.

*(Om stilen inte redan är vald kan du fråga vilken NextPhase-stil som passar — `nextphase-studio` har hela menyn. Skriv valet överst i `PLAN.md`.)*

> ### Where this look comes from
> Reverse-engineered frame-by-frame from three reels Jade supplied. Every colour,
> size and duration in `assets/tokens.css` is **measured**, not invented:
> - **REF-A** — `instagram.com/p/DcgMgW6yahM/` — 38.7s, the primary reference.
> - **REF-B** — `instagram.com/p/DcOJfx0SXyN/` — 67.6s, same creator, cleaner density.
> - **REF-C** — `instagram.com/p/DcBwAjvoEqI/` — **a different creator**. Used for
>   its font recommendations only (`reference/typography.md` §4). Its own look is
>   NOT persa; do not mix it in.
>
> `reference/reference-log.md` has the shot-by-shot breakdown, the measurement
> method, and a table mapping every finding to where it is written up.

---

## ⛔ Six hard rules

1. **Never hardcode a colour, font or duration.** Import `assets/tokens.css`; use
   its variables only. Never mix persa tokens with `nextphase` or `motiongraphics`
   tokens in one composition.
2. **The word caption HARD-CUTS.** Zero frames of transition. No fade, no scale,
   no pop, ever. This is the single most-broken rule in the style — see
   `reference/captions.md` §1.
3. **The emphasis word lives BEHIND the subject matte.** The head must occlude it.
   In front, it is a lower-third graphic; behind, it is in the room. That
   difference is the style.
4. **Animate transforms only** — `opacity, x, y, scale, scaleX/Y, rotation` plus
   `filter: blur()`. Never `top/left/width/height`.
5. **Every word on screen is derived from THIS video.** Kit copy in `components/`
   is placeholder, and some reference copy belongs to **other creators**. Run
   `bash library/kits/nextphase/skills/persa/scripts/check-persa.sh work/nextphase/videos/<name>` before every render; it exits
   non-zero on kit copy, borrowed names, and persa-specific style violations.
6. **Nothing publishes without explicit approval.** Deliver rendered + scored, open
   it for review, stop there.

**Read `reference/` before building** — `grade.md` (the measured colour science) ·
`captions.md` (**the core of the style — read this first**) · `layouts.md` (the
five scenes and the matte) · `typography.md` · `motion-grammar.md` ·
`sound-design.md` · `workflow.md` · `reference-log.md`.

---

## 1 · The look in one paragraph

**Blue is pulled down hard everywhere; green is lifted in the shadows and
highlights; everything is desaturated, bloomed, vignetted and grained; nothing
reaches pure black or pure white.** The footage is warm, hazy and slightly old.
Over it: one white word at chest height that replaces itself on every syllable,
and occasionally one huge outlined word behind the speaker's head. Media arrives
as rounded panels the person's shoulders break through. Three accent colours,
one per frame. No transitions except a panel fading in place.

Full numbers: `reference/grade.md`.

---

## 2 · The frame

**1920×1080 @30fps is the default** for this studio. The style was *measured* at
1080×1920, so that is what `:root` in `tokens.css` carries; `.pa-16x9` overrides
the six tokens that do not transfer.

```html
<div class="pa-frame pa-16x9"> … </div>     <!-- long-form -->
<div class="pa-frame">          … </div>     <!-- vertical  -->
```

**Read `reference/layouts.md` §16:9 before building wide.** Three scene rules
change, they were derived on real 16:9 footage, and the first one fails silently:

1. **A short emphasis word centred behind a centred head disappears.** Long words
   run frame-wide and the head cuts their middle; short words get `--pa-emph-x`
   so the head cuts one edge instead.
2. **The caption centres on the SUBJECT, not the frame** — set `--pa-cap-x`
   whenever the speaker sits in a corner card.
3. **Media becomes a row of three panels**, not one panel stacked above the head.

| Zone | Value | Rule |
|---|---|---|
| Safe | inset `--pa-safe-x` 6.5% × `--pa-safe-y` 4.5% | Nothing outside. Suspended for the subject only. |
| Caption | centred, **73% height** | Fixed. Never moves. Nothing else lives there. |
| Emphasis | centred, **25% height** | Behind the matte. Top two-thirds must stay readable. |
| Panel | 9:16 **86% wide**, top 8% · 16:9 a **row of 3** | Scene 2. |
| Head card | 9:16 **80%** centred · 16:9 **34%** corner card | Scene 3/4. Bleeds off the bottom. |
| 9:16 bottom | lowest **12%** | Keep readable content out — platform UI. |

### ⭐ The z-order — get this wrong and it is not persa
```
50  .pa-caption   one word, in front of everything
40  .pa-subject   the matted talking head
20  .pa-emph      the huge word the head cuts into
10  .pa-panel     real screen recordings
 0  the graded plate
```

### ⭐ `.pa-frame` on the composition root
Type is sized in `cqh` so one scale serves both aspects. That resolves against a
size container — **the root must carry `.pa-frame`**. Without it every string
renders at a fraction of its size and the layout still "looks fine", which is
exactly why it is worth checking first when a scene looks wrong.

---

## 3 · The five scenes and the rotation

Full spec in `reference/layouts.md`.

| # | Scene | For |
|---|---|---|
| 1 | **Clean Face** | the rest beat — and it is ~40% of the runtime |
| 2 | **Panel Over Face** ⭐ | the signature: media panel, head breaks its bottom edge |
| 3 | **Media Full / Head Card** | the screen content IS the point; punched in, head card bleeds off the bottom |
| 4 | **Split / Break the Box** | media above, head card below, head crosses the seam |
| 5 | **Hand-Note Beat** | a lettered line, often curved to follow a real edge in the room |

**Never the same scene twice in a row. Never hold one past ~20s.** Every scene
change carries a sound. But note what the reference does: it **alternates** clean
face and media beat, and it returns to a clean face constantly, holding 6–10s at
a stretch. Wall-to-wall media is the amateur read.

### ⭐ REAL MEDIA, NOT TYPESET TEXT
Every beat that supports a point shows a real resource — a screen recording, a
real product UI, a docs page, a repo card, a real thread. **≥1 per 20s, minimum 8.**
- **Check every screenshot actually rendered content.** Login-walled and JS-heavy
  pages come back blank and ship as empty panels.
- **No random humans as b-roll.** Cut to a person only when that person *is* the
  subject of the line.
- **Never use emojis.** Build designed marks — a CSS glyph, a small SVG, a monogram.
- Re-encode every sourced clip to **30fps CFR** and verify with `ffprobe`.

### ⭐ COPY IS DERIVED, NEVER INHERITED
Every string comes from the speaker's own words at their onset in
`transcript-tight.json`, the real thing named in that beat, or a verified figure.
**Write the actual copy into `PLAN.md`, per beat, before authoring** — that is
where a factual error gets caught cheaply.

---

## 4 · The two things that make it persa

### The grade
```bash
python library/kits/nextphase/skills/persa/scripts/persa-balance.py assets/recording.mp4 --out assets/bal.mp4  # neutralise first
bash library/kits/nextphase/skills/persa/scripts/persa-grade.sh assets/bal.mp4 assets/plate.mp4 plate          # then grade
bash library/kits/nextphase/skills/persa/scripts/persa-grade.sh out/visual.mp4 out/visual-look.mp4 soft       # once, at the end
python  scripts/grade-check.py out/visual-look.mp4                        # verify
```
Grade the **plate**, composite, then bloom/vignette/grain the **finished comp**
once. Grading footage at `full` and laying ungraded graphics on top is the most
common way this look fails — the graphics sit *on* the image instead of *in* it.

**Balance before you grade.** The persa curve is calibrated against a *neutral*
source; a real plate's own cast rides straight through it, so grading a cool-lit
recording directly leaves it failing `grade-check.py` no matter how warm it looks.
`persa-balance.py` measures the source's cast per luma band and writes the
cancelling curve — one command, no hand-tuning. Verified on real footage: four
readings out of tolerance before, a clean pass after.

`grade-check.py` gates on the channel relationships (`B-R` in the mids is the
number that matters — **−18 to −28**) and passes on both reference reels while
failing a third reel by a different creator.

### The matte
```bash
source library/.venv/Scripts/activate
python library/kits/nextphase/skills/nextphase-long-editing/scripts/rvm-matte.py --src assets/plate.mp4 --out assets/matte --frames <n>
```
Matte the **graded** plate. **Keep the rim** — the light fringe on the matte edge
is visible in the reference at 3× and is what separates the subject from a busy
recording behind them; `--pa-rim` makes it deliberate instead of leaving it to
luck. What you still fix is *flicker*. Detail:
`library/kits/nextphase/skills/nextphase-long-editing/reference/cutout-compositing.md`.

---

## 5 · Motion

`reference/motion-grammar.md`. The whole cadence, measured at 30fps:

| Move | Frames |
|---|---|
| **Word caption** | **0 — it hard-cuts** |
| Emphasis in | 5 |
| Slam | 4 |
| Panel in | 9 |
| Panel out | 8, **fading in place — it never slides** |
| Plate drift | continuous, scale 1.00→1.03 over 6s, **linear** |

Persa moves less than either sibling style. There is no whip pan, no zoom blur, no
light leak, no glitch. **If a cut needs help, the help is a sound.**

---

## 6 · Sound

`reference/sound-design.md`. Because persa has almost no visual transitions,
sound carries more here, not less — it is what makes a hard cut read as
intentional. **~10–16 cues/min.** Every layout change gets one. Reuse the sibling
palette and **call the mixer by its path inside that skill folder** — never copy
it into a video folder:
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/visual-look.mp4 out/sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh out/sfx.mp4 out/final.mp4 assets/music/bed.mp3
```
Match a `click` to every real cursor press in a screen recording — that is what
makes the panels feel live.

---

## 7 · The workflow

Full detail in `reference/workflow.md`. Prefix **every** bash step with:
```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```

0. **Ask which style.** Locate `work/nextphase/videos/<name>/`, `VIDEO.md`, `assets/recording.mp4`.
1. **Transcribe** → chunk anything over ~90s and gap-check minute by minute.
2. **Tighten** → `transcript-tight.json` is now the only timing source.
3. **Balance** (`persa-balance.py`) → **grade the plate** (`plate` strength) →
   `grade-check.py`.
4. **Matte** the graded plate with RVM.
5. **`PLAN.md`** — scenes per beat, the actual on-screen copy, the media list,
   the re-hooks. **Get a "go" before authoring.**
6. **Source real media**, verify facts, normalise to 30fps CFR.
7. **Author** per-chapter compositions. Symlink assets into each `seg-NN/`;
   HyperFrames rejects `../assets/`. Build captions with
   `scripts/build-captions.py`.
8. **Per segment:** `lint` (0 errors) → **`check-persa.sh` (must exit 0)** →
   `snapshot --at <times>` → **read the contact sheet and fix** → `render -q high -f 30`.
9. **Concat** via `library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh` — chapter
   timestamps come from real rendered durations, never from `PLAN.md`. Relay the
   source audio after the concat (AAC priming drifts ~38ms per join).
10. **Finish the look** (`soft` strength over the concat) → `grade-check.py`.
11. **Sound:** SFX pass, then the ducked bed.
12. **Deliver:** `out/final.mp4` · `out/chapters.txt` · `out/<name>.srt`. Report
    rendered + scored, open for review. **Publish nothing without approval.**

---

## Files in this skill

- `assets/tokens.css` — the measured design tokens and every persa class.
  **Import into every composition.** (CSS comments do not nest — never write a
  closing marker inside one of its header blocks, or the whole sheet silently
  stops applying.)
- `components/persa-system.html` — **the whole style on one page**: all five
  scenes, both caption tiers, the z-order table, the palette and the cadence,
  live in a browser. Open this first; it is the fastest way to see what the style
  *is*. Open it beside `reference/stills/`.
- `reference/` — `grade.md` · `captions.md` · `layouts.md` · `typography.md` ·
  `motion-grammar.md` · `sound-design.md` · `workflow.md` · `reference-log.md`.
- `reference/stills/` — the source evidence: 14 frames including two 30fps
  transition strips (the caption hard-cut and the panel exit), 2–4× type crops,
  a 3× crop of the matte edge, and 1fps contact sheets of all three reels.
- `scripts/persa-balance.py` — measure a source's cast and cancel it. **Run this
  before grading real footage**, or the plate will not land in the colour space.
- `scripts/persa-grade.sh` — apply the look (`plate` | `soft` | `full`).
- `scripts/grade-check.py` — **verify** a clip is in the persa colour space.
- `scripts/build-captions.py` — transcript → hard-cut word captions.
- `scripts/check-persa.sh` — **the render gate.** Run before every render.
- Everything else is **shared with `nextphase-long-editing`** — tighten,
  rvm-matte, mix-sfx, mix-bgm, concat-segments. Call them by their path in that
  folder; never copy them into a video folder.
