# Transparent Background — background removal & the seamless "pop-out" layout

Merged in from the `cutout-hook` skill and reconciled with the NextPhase standards.
Validated end-to-end on this machine 2026-07-28 (arm64, torch 2.13, real recording).

The technique: remove the background from the talking head with RVM, composite the
person **on top of** a designed HyperFrames background, and show their torso through a
rounded-rectangle "window" so they read as **popping out of the rectangle**.

---

## 0 · Where this sits in the ARC

TRANSPARENT BACKGROUND is a **layout**, not an arc slot. As the house opener it **replaces arc
steps 1–2** (hook + payoff), but it can be used at any point in the reel. The rest of the arc is unchanged: after it you
still cut to the **full-screen face hold (~2s, Slow Push)**, then the body.

**It does not replace the bottom camera card.** Once the body starts, the camera returns
to the normal `960–1920` card and the three-lane safe zones resume.

### Safe-zone exception (the only one)
While this layout is on screen the three-lane rule is **suspended** — the person legitimately spans
the top zone, the caption band, and the camera card, because they are the whole frame.
Captions still run, but place them clear of the head and shoulders. The instant it ends, the lanes are back in force.

### Token reconciliation — the inherited default was WRONG for us
The source skill preferred a white (`#ffffff`) background. **We don't.** Hard rule #1
still applies: the BG is a rendered HyperFrames comp using `assets/tokens.css`, and for a
SHORT that means `--cream` (`#F0EDE4`). Never hardcode white, never hardcode anything.

### The four LAYOUTS (how the frame is divided)
Renamed and fixed 2026-07-29. These are layouts, not arc slots — any of them can serve any beat.

| Layout | Frame | You visible? |
|---|---|---|
| **Transparent Background** | cut out on the designed BG, card crossing mid-head | yes, floating |
| **B-Roll** | FULL takeover — animation or the real web thing, edge to edge | **no** |
| **Half & Half — Animation Up** | animation top, you bottom (the house standard three lanes) | yes, bottom |
| **Half & Half — Face Up** | you top, animation bottom (the reverse) | yes, top |

`Half & Half — Face Up` moves the caption band to the seam (~960–1080), just under the face,
so captions keep the same reading position relative to the head.

---

## 1 · The environment (persistent — Windows, importerad)

RVM körs i repots gemensamma venv `library/.venv` (gitignorerad). Skapa den med den
**signerade Python 3.12** — Smart App Control blockerar DLL:er i uv-nedladdade Python-byggen,
så använd inte `uv venv --python …`:

```bash
# Git Bash, från repo-roten — en gång (~5 min, torch CPU ~200 MB)
"$LOCALAPPDATA/Programs/Python/Python312/python.exe" -m venv library/.venv
library/.venv/Scripts/python.exe -m pip install --upgrade pip
library/.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
library/.venv/Scripts/python.exe -m pip install opencv-python numpy pillow av tqdm
```

Aktivera i Git Bash med `source library/.venv/Scripts/activate` (PowerShell:
`library\.venv\Scripts\Activate.ps1`), eller anropa `library/.venv/Scripts/python.exe` direkt.
Maskinen saknar NVIDIA — kör `--device cpu` (standard). Vikterna hämtas via `torch.hub` från
GitHub (PeterL1n/RobustVideoMatting) första gången (~15 MB) och cachas i
`%USERPROFILE%\.cache\torch\hub\`. Alternativ utan torch: `npx hyperframes remove-background`.

---

## 2 · Step 1 — RVM matte

```bash
python scripts/rvm-matte.py --src src.mp4 --out frames_rvm --frames 150
```
150 frames = 5s @ 30fps. Measured ~0.24 s/frame on CPU → **~35s for a 5s hook.**

RVM (Robust Video Matting, MobileNetV3) is the only approved matter. MediaPipe smudges
hair and the ceiling line; rembg is unreliable to install. What makes it seamless:

- **Recurrent state (`rec`) passed between frames** — this is what kills flicker. Without
  it the alpha crawls frame to frame and the cutout shimmers.
- **Sequential feed, no shuffling** — RVM depends on frame order.
- **Warm-up passes** — the script primes `rec` on the first frame twice before writing, so
  frame 0 is as clean as frame 50. (Inherited fix: "start at frame 2." Priming is better —
  you keep frame 0.)

### `downsample_ratio` — the inherited note is BACKWARDS for our format
The source skill said "`0.25` for even sharper matting." **Measured on a real portrait
1080×1920 recording, 0.25 is ~7× worse**, not sharper:

| ratio | haze above hair (mean/max alpha, 0–255) | verdict |
|---|---|---|
| 0.50 | 0.07 / 43.0 | fine |
| **0.40** | **0.06 / 42.2** | **house default — cleanest** |
| 0.25 | 0.44 / 84.3 | visibly worse |
| 0.15 | 0.40 / 37.8 | worse, and slow |

Solid torso alpha was a perfect 255 and far background a perfect 0 at every ratio — the
matte body is never in doubt, only the soft hair edge is. **Stay on 0.4.** If you change
it, measure the same way before believing it looks better.

### `fgr` is not worth it
RVM also returns `fgr` (colour-decontaminated foreground). Tested against a strong orange
wood-ceiling spill: **visually indistinguishable** from using the raw frame + alpha. The
faint warm halo above curly hair is genuine soft alpha on flyaway strands, not spill.
Keep the simpler raw-frame path.

---

## 3 · Step 2 — Composite

```bash
bash scripts/cutout-hook.sh <src.mp4> <bg.mp4> <frames_dir> <out.mp4> [seconds]
```

`bg.mp4` is the rendered HyperFrames motion-graphics background (1080×1920, 30fps, no
audio, cream). The script builds the rect mask on first use into `assets/rect_mask.png`.

### ⚠ THE SEAM INVARIANT — the single thing that makes it seamless

```
RECT_Y − CROP_Y  ==  PERSON_Y
```

The rect window and the cutout person are **the same body, drawn twice**. The window
shows the source's torso; the RVM cutout is composited on top. They only line up if both
layers are shifted down by the same amount. Defaults: `1400 − 1200 = 200` ✓

Break it and the torso **ghosts** — a second pair of shoulders peeks out from behind the
cutout. The inherited gotcha ("head clipped → reduce person `y=200` → `y=150`") **silently
breaks this**: move `PERSON_Y` and you must move `CROP_Y` by the same delta.
`cutout-hook.sh` now hard-fails on a broken invariant instead of shipping the artifact.

Geometry overrides (all env vars): `RECT_X/Y/W/H`, `CROP_X/Y`, `PERSON_X/Y`.

### ⭐ HOUSE CUT LINE = MID-HEAD (never hardcode it — measure it)
Jad's spec: the rect's top edge crosses **the middle of his head**, so the top half of the
head floats free on the designed background and everything below sits against the card.
That row is a different pixel value in every recording, so measure it from the matte:

```bash
python scripts/find-cut-line.py --frames frames_rvm --cut mid-head
```

It reads the alpha silhouette, finds the head top (first solid row) and the neck (where the
silhouette widens past 1.6× head width), and prints geometry that already satisfies the seam
invariant. Measured on the reference recording: head top 513 · **mid-head 856** · neck 1199 →
`RECT_Y=1056 CROP_Y=856 PERSON_Y=200`.

**Raising the rect means you must grow it too.** The rect has to keep bleeding past the frame
bottom or its lower rounded corners come into shot and a gap opens under it:
`RECT_H ≥ 1920 − RECT_Y + 150`. At `RECT_Y=1056` that means `RECT_H=1014`, and the mask has to
be regenerated at that size (`make-rect-mask.py --h 1014`) — the default 670 mask is only
right for the old low rect.

Notes on the defaults:
- The rect is `1000×670` at `(40,1400)` → its bottom edge lands at 2070, **150px past the
  1920 frame bottom**. That bleed is intentional; the bottom two corner radii are never
  seen. Don't "fix" it.
- `crop=1000:670:40:1200` pulls the torso window from the source's own x=40, so the window
  content is horizontally aligned with the person.

### Framing matters more than the geometry
Tested on a **tightly framed** source (head filling the upper half): the effect works, but
the person's body covers almost the whole rect, leaving only thin slivers visible at the
left and right edges. The pop-out reads far better when the subject is framed **wider**
with more headroom, so the window shows meaningful content around the body. If a recording
is framed tight, either widen the rect, drop it lower, or shrink the person layer.

---

## 4 · Step 3 — Audio

`cutout-hook.sh` now muxes it automatically: it takes the matching span of the source VO
back onto the composite (`-c:v copy`, no re-encode). No separate step, no silent hook.

---

## 5 · Gotchas

- **Filenames with U+202F (narrow no-break space)** — real on this machine; the Downloads
  folder has such files and the shell cannot open them by literal path. Copy to a clean
  path first: `python -c "import shutil; shutil.copy2(src,dst)"`, or glob it.
- **Head clipped at the top** → change `PERSON_Y`, **and `CROP_Y` by the same delta** (see
  the invariant). Head floating too high → increase both.
- **Rect mask missing** → auto-generated; or `python scripts/make-rect-mask.py --out …`.
- **Never fall back to MediaPipe.** It smudges above the head.
- **`--device mps`** exists in `rvm-matte.py` but CPU is the default and is fast enough
  (35s for a 5s hook). Only reach for mps if you're matting a long span.

## 6 · Scope

This covers background removal and the pop-out hook composite. The rest of the short —
transcription, word-synced graphics, the full-screen beats, the SFX pass — is the normal
NextPhase workflow in `SKILL.md`.
