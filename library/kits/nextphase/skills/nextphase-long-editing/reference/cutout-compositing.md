# Transparent Background — background removal & the "pop-out" layout (16:9)

Remove the background from the talking head with **RVM**, composite the person **on top of** a
designed HyperFrames background, and show their torso through a rounded-rectangle "window" so
they read as **popping out of the rectangle**.

⇄ **Ported from the 9:16 short skill.** The matting technique, the environment, the seam
invariant and every measured finding below are carried over **unchanged and validated** (arm64,
torch 2.13, real recording, 2026-07-28). **The geometry is not** — the portrait defaults
(`1000×670 @ 40,1400` inside a 1080×1920 frame) are meaningless in a 1920×1080 frame. The 16:9
defaults in §4 are **derived by proportion, not measured on a real landscape recording** —
treat them as a starting point and run `find-cut-line.py` on the actual footage, which is what
you should be doing anyway.

---

## 0 · Where this sits

Transparent Background is a **layout**, not an arc slot. It is the default opener (through the
cold-open line) but is usable at any point — chapter cards, presenter beats, the recap.

**It does not replace the other layouts.** Once the body starts, rotate normally
(Full-Frame Face / Split / Screen-Share + Bubble / B-Roll), per `SKILL.md` §1.

### Safe-zone exception (the only one)
While this layout is on screen the safe zones are **suspended** — the person legitimately spans
the frame, because they *are* the frame. Captions still run, placed clear of the head and
shoulders. The instant it ends, the zones are back in force.

### Token reconciliation
The upstream `cutout-hook` skill preferred a white (`#ffffff`) background. **We don't.** Hard
rule #1 applies: the BG is a rendered HyperFrames comp using `assets/tokens.css`. ⇄ For long
form that means the **dark dotted grid** (`.bg-darkgrid`), not the short's cream. Never hardcode
white, never hardcode anything.

⇄ **Dark BG changes the matte tolerance.** A soft alpha halo on flyaway hair is nearly invisible
against cream and *very* visible against `--dark`. Check the hairline in a snapshot before
rendering the whole segment; if it fringes, the fix is a 1px alpha erode, not a different
downsample ratio (see §2).

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
python scripts/rvm-matte.py --src assets/recording-tight.mp4 --out frames_rvm --frames 150
```
150 frames = 5s @ 30fps. Measured ~0.24 s/frame on CPU at 1080×1920.

⇄ **A 1920×1080 frame is the same pixel count as 1080×1920**, so expect the same ~0.24 s/frame.
**Budget it:** long form uses this layout for far longer spans than a 5-second short hook.
- 5s hook → ~35s. 30s opener → ~3.5 min. **2 min of cutout → ~15 min and ~4 GB of PNGs.**
- Matte **only the spans that actually use the layout**, one `--start`/`--frames` run per span.
  Do not matte the whole recording.
- Delete `frames_rvm` after compositing. It is regenerable and it is enormous.

RVM (Robust Video Matting, MobileNetV3) is the **only approved matter.** MediaPipe smudges hair
and ceiling lines; rembg is unreliable to install. What makes it seamless:

- **Recurrent state (`rec`) passed between frames** — this is what kills flicker. Without it the
  alpha crawls frame to frame and the cutout shimmers.
- **Sequential feed, no shuffling** — RVM depends on frame order.
- **Warm-up passes** — the script primes `rec` on the first frame twice before writing, so frame
  0 is as clean as frame 50. (Better than the inherited "start at frame 2" — you keep frame 0.)
- ⇄ **Each `--start` span restarts the recurrent state**, so its first frames are the weakest.
  Start each span ~10 frames before the visible in-point and trim, or the layout enters on the
  shakiest matte in the run.

### `downsample_ratio` — the inherited note is BACKWARDS
The source skill said "`0.25` for even sharper matting". **Measured on a real 1080×1920
recording, 0.25 is ~7× worse:**

| ratio | haze above hair (mean/max alpha, 0–255) | verdict |
|---|---|---|
| 0.50 | 0.07 / 43.0 | fine |
| **0.40** | **0.06 / 42.2** | **house default — cleanest** |
| 0.25 | 0.44 / 84.3 | visibly worse |
| 0.15 | 0.40 / 37.8 | worse, and slow |

Solid torso alpha was a perfect 255 and far background a perfect 0 at every ratio — the matte
body is never in doubt, only the soft hair edge. **Stay on 0.4.** If you change it, measure the
same way before believing it looks better.

### `fgr` is not worth it
RVM also returns `fgr` (colour-decontaminated foreground). Tested against a strong orange
wood-ceiling spill: **visually indistinguishable** from raw frame + alpha. The faint warm halo
above curly hair is genuine soft alpha on flyaway strands, not spill. Keep the simpler path.

---

## 3 · Step 2 — Composite

```bash
bash scripts/cutout-hook.sh <src.mp4> <bg.mp4> <frames_dir> <out.mp4> [seconds]
```

`bg.mp4` is the rendered HyperFrames background — ⇄ **1920×1080**, 30fps, no audio, dark grid.
The script builds the rect mask on first use into `assets/rect_mask_<W>x<H>.png` — keyed by
size, so changing `RECT_W`/`RECT_H` regenerates it instead of silently reusing a mask of the
wrong shape. (The 9:16 skill used one fixed `rect_mask.png`; on 16:9 the rect size changes
with every measured cut line, and a stale mask is invisible until the render.)

### ⚠ THE SEAM INVARIANT — the single thing that makes it seamless

```
RECT_X − CROP_X  ==  PERSON_X        and        RECT_Y − CROP_Y  ==  PERSON_Y
```

The rect window and the cutout person are **the same body, drawn twice**. The window shows the
source's torso; the RVM cutout is composited on top. They line up only if both layers are shifted
by the same amount, on **both** axes.

⇄ The short only ever moved the person vertically, so the X half was satisfied by accident
(`40 − 40 = 0`). **In 16:9 you will want to move him sideways** — off-centre, to one side, with
graphics in the other two-thirds — so the X invariant is now live and `cutout-hook.sh` enforces
both. Break either and the torso **ghosts**: a second pair of shoulders peeks out from behind
the cutout.

The inherited gotcha ("head clipped → reduce person `y=200` → `y=150`") **silently breaks this.**
Move `PERSON_Y`, and you must move `CROP_Y` by the same delta. The script hard-fails rather than
ship the artifact.

Geometry overrides (all env vars): `SRC_W`, `SRC_H`, `RECT_X/Y/W/H`, `CROP_X/Y`, `PERSON_X/Y`.

### ⭐ HOUSE CUT LINE = MID-HEAD (never hardcode it — measure it)
Jad's spec: the rect's top edge crosses **the middle of his head**, so the top half floats free
on the designed background and everything below sits against the card. That row is a different
pixel value in every recording:

```bash
python scripts/find-cut-line.py --frames frames_rvm --cut mid-head --person-y 112
```

It reads the alpha silhouette, finds the head top (first solid row) and the neck (where the
silhouette widens past 1.6× head width), and prints geometry that already satisfies the seam
invariant. It works on any aspect ratio — it measures rows, not proportions — so it is the right
tool for 16:9 too, and it is **the only correct source for the cut line.**

**Raising the rect means growing it.** The rect must keep bleeding past the frame bottom or its
lower rounded corners come into shot and a gap opens underneath:

```
RECT_H  ≥  FRAME_H − RECT_Y + BLEED          (16:9: FRAME_H = 1080, BLEED = 120)
```

The mask must be regenerated at that size: `python scripts/make-rect-mask.py --w W --h H`.
⇄ The short's stock 670-tall mask is for a 1920-tall frame and is wrong here.

---

## 4 · ⇄ 16:9 geometry — derived defaults

**These are proportional ports, not measurements.** Run `find-cut-line.py` and replace `RECT_Y`
and `CROP_Y` with what it prints, every time.

### Mode A — centred (the direct port)
Person at 1:1, centred; a wide window card at the bottom.

```bash
SRC_W=1920 SRC_H=1080 \
RECT_X=360 RECT_W=1200 RECT_H=803 \
RECT_Y=397 CROP_X=360 CROP_Y=285 PERSON_X=0 PERSON_Y=112 \
bash scripts/cutout-hook.sh assets/recording-tight.mp4 out/bg.mp4 frames_rvm out/open.mp4 14
```
- `PERSON_Y = 112` — the short's 200 scaled by 1080/1920.
- `CROP_Y = 285` — a **placeholder** mid-head for a typical 16:9 head (top ~140, neck ~430).
  **Measure it.**
- `RECT_Y = CROP_Y + PERSON_Y = 397` ✓ · `RECT_X − CROP_X = 360 − 360 = 0 = PERSON_X` ✓
- `RECT_H = 1080 − 397 + 120 = 803` → `make-rect-mask.py --w 1200 --h 803`

### Mode B — side-anchored (the 16:9-native one)
He sits in the right third; graphics own the left two-thirds. This is the layout 16:9 actually
wants, and it is what makes the X invariant matter.

Shift him right by `PERSON_X`, and shift the window by exactly the same amount:
```bash
SRC_W=1920 SRC_H=1080 PERSON_X=430 PERSON_Y=112 \
RECT_X=830 CROP_X=400 RECT_W=1000 RECT_H=803 \
RECT_Y=397 CROP_Y=285 \
bash scripts/cutout-hook.sh …
```
`830 − 400 = 430 = PERSON_X` ✓ · `397 − 285 = 112 = PERSON_Y` ✓

Scale him down instead of just moving him by setting `SRC_W`/`SRC_H` (e.g. `1344×756` = 0.7×).
**Both layers are built from that same scaled source**, so the invariant still holds in the
scaled space — but `CROP_X/Y` are then coordinates **in the scaled frame**, and the cut line
from `find-cut-line.py` (measured on unscaled frames) must be multiplied by the same factor.
This is the easiest thing to get wrong here; check the printed seam arithmetic before rendering.

### Framing matters more than the geometry
Tested on a **tightly framed** source (head filling the upper half): the effect works, but the
body covers almost the whole rect, leaving thin slivers at the edges. The pop-out reads far
better when the subject is framed **wider** with more headroom, so the window shows meaningful
content around the body. ⇄ A 16:9 talking head is usually framed wider than a 9:16 one, which
works in this layout's favour — but if a recording is tight, widen the rect, drop it lower, or
shrink the person layer.

---

## 5 · Step 3 — Audio

`cutout-hook.sh` muxes it automatically: it takes the matching span of the source VO back onto
the composite (`-c:v copy`, no re-encode). No separate step, no silent opener.

⇄ Feed it the **tight** recording, and the `[seconds]` argument is a span of the *tight*
timeline. Mixing tight and untight sources here yields a composite whose audio drifts from every
graphic in the segment.

---

## 6 · Gotchas

- **Filenames with U+202F (narrow no-break space)** — real on this machine; the shell cannot
  open them by literal path. Copy first: `python -c "import shutil; shutil.copy2(src,dst)"`,
  or glob it.
- **Head clipped at the top** → change `PERSON_Y`, **and `CROP_Y` by the same delta**.
- **A second pair of shoulders** → the seam is broken. Check the invariant on both axes.
- **A gap under the rect** → `RECT_H` is too small for the new `RECT_Y`. Recompute and
  regenerate the mask.
- **Rect mask missing** → auto-generated at the right size, or
  `python scripts/make-rect-mask.py --w W --h H --out assets/rect_mask_WxH.png`.
- **Never fall back to MediaPipe.** It smudges above the head.
- **`--device mps`** exists in `rvm-matte.py`, but CPU is the default and is fast enough. Reach
  for mps only when matting a long span — and verify the first output frames, since op support
  varies.

## 7 · Scope

This covers background removal and the pop-out composite. Everything else — transcription,
tightening, word-synced graphics, the demo sections, assembly, the two sound passes — is the
normal long-form workflow in `SKILL.md`.
