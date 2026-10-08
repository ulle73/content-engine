# Sound Design — the SFX layer + the music bed (long form)

Sound is the polish pass that makes an edit feel alive. It is a **support layer that sits under
the voice**: you should clearly *hear* each effect, but it must never compete with or step on
the narration.

⇄ **Long form has two passes, in this order:**
- **Pass A — SFX**, on the locked visual render (`mix-sfx.sh`).
- **Pass B — MUSIC BED**, on the SFX'd render (`mix-bgm.sh`). Long form only. A 15-minute video
  with no bed sounds like a webcam recording; a 45-second short does not need one.

Source palette: **CreatingWithJerry's pack** — real files, peak-normalized, used as-is. The
curated palette is in `sfx/` (see `sfx/README.md`).

---

## Order of operations (don't plan sound upfront)

1. Build the video as always — `PLAN.md`, timing tables (**graphics only**), author the segment
   compositions, render, concat. **Lock the visual edit.**
2. **Then** Pass A: watch it, note every motion / appearance / transition with its real
   timecode, choose a sound for each, write `sfx-cues.txt`, mix, gut-check.
3. **Then** Pass B: the bed, with its own duck/drop map.

Planning sound before the animation exists is guesswork; placing it after is just reading what
is on screen. Timing is accurate because the render is final.

---

# PASS A — SFX

## Level — present, not loud (and not subliminal)
- You should **clearly hear** each effect on a normal watch. It sits **under** the voice.
- Calibrate to this video's voice. For a voice around **−25 dB mean / −6 dB peak** with the
  0 dB-normalized pack:
  - **Transient hits** (pop, click, whoosh, swoosh, shutter, ping, beep, futuristic-click):
    **gain ≈ 0.12** → ~−18 dBFS peak.
  - **Sustained beds** (riser, magic-reveal): **gain ≈ 0.09** → ~−21 dBFS.
  - **A hero moment** may reach **≈ 0.16** (~−16 dBFS). Rarely louder.
- Different voice level? Measure it and scale to keep SFX roughly **15 dB under voice peaks**:
  ```
  ffmpeg -i render.mp4 -af volumedetect -f null -
  ```
- The gate: watch once. If an effect **buries a word or makes you flinch**, it is too loud. If
  you have to **strain to hear it**, too quiet. It should make the edit feel *crisper*.

## Density & variety
- ⇄ **~12–20 cues per minute.** (The short's "25–40 per short" is a per-45s figure — reading it
  as a whole-video number on a 12-minute edit produces a nearly silent video.) A 12-minute video
  lands around 150–240 cues. That is normal; write them per segment, not in one sitting.
- **Be generous.** Most moves — an entrance, a number landing, a checkmark, a zoom, a cut, a
  highlight, a layout change — earn a sound. Silence is a deliberate breath, not the default.
- **Vary it.** Match the sound to the *specific* element and rotate. Reusing a sound is fine;
  reusing the *same* one for everything is what feels cheap. A code chip is a `futuristic-click`,
  a checkmark is a `confirm`, a countdown is a `beep` — not all "pop".
- **One foreground hit at a time** (space hits ≥ ~0.3s). A sustained bed may underlie hits —
  that is a layer, not a clash.

## Fixed signatures (never skip these)
- **⭐ Payoff spike = `riser`**, starting ~1.5s before the reveal so it **crests on** it.
- **Every chapter card** = a short `riser` tail into a `magic-reveal` or `confirm` on the title.
- **Every layout change** = a `swoosh` (whip-pan) or `whoosh` (zoom-driven). **No silent cuts.**
- **Every card exits on soft air** (`whoosh-2`/`swoosh`, ~0.07–0.09) so it breathes out instead
  of clicking off.
- **Real media cut-in** = `camera-shutter` in / `swoosh` out.
- **The turn** = the bed drops out, one `vinyl-rewind` or a bare `beep`, then the bed returns.

## The palette (`sfx/`)

| sound | ~dur | use it when… |
|---|---|---|
| `whoosh` / `whoosh-2` | 1.1 / 0.5s | a zoom in/out; a big element flies in — rotate the two |
| `swoosh` | 0.9s | a fast slide / whip-pan between layouts |
| `pop` | 0.1s | something small appears (soft) |
| `click` | 0.35s | something appears / a UI tap (crisp) |
| `futuristic-click` | 0.7s | a *techy* element — settings row, code chip, toggle |
| `confirm` | 1.9s | a success — checkmark, "it works", a positive result |
| `ping` | 1.1s | a notification, a highlight, a single alert, the CTA keyword |
| `beep` | 0.7s | a countdown, a timer, a numeric or warning beat |
| `keyboard` | 1.3s | typing, code, a terminal moment |
| `vinyl-rewind` | 1.0s | a rewind / "wait — back up" / a reset |
| `magic-reveal` | 3.1s | you UNVEIL something (the big reveal shimmer) |
| `riser` | 3.2s | building tension — starts BEFORE the payoff, crests on it |
| `camera-shutter` | 0.1s | a crisp clean cut / snapshot / real media cut-in |

## Applying it
1. On the **locked render**, write `work/nextphase/videos/<folder>/sfx-cues.txt` — one line per cue:
   `<time_sec> <sound> [gain]  # note` (`#` comments and blank lines are ignored).
   - **Time to the animation, not the plan.** Read the composition's real timeline (GSAP
     `.to(…, t)` positions, CSS `animation-delay`) or extract frames
     (`ffmpeg -ss T -i render.mp4 -frames:v 1 f.jpg`) to pin the exact instant each event fires.
     Word and plan times drift from the animation by up to a second — that drift is the #1 cause
     of sloppy sound. Align swelling sounds (whoosh, riser) to **crest** on the event; put
     transients (pop, click, shutter) **on** the frame.
   - ⇄ On a long edit, write cues **per segment against the segment render**, then offset them by
     the segment's start time from `out/chapters.txt` before mixing onto the full cut. Timing
     against the concatenated 12-minute file is slow and error-prone.
2. Mix:
   ```
   bash scripts/mix-sfx.sh out/final-visual.mp4 out/final-sfx.mp4 sfx-cues.txt
   ```
   Video is stream-copied (no quality loss); each cue is faded in, leveled, and delayed to its beat.
3. Gut-check with the level gate. Tune any line, re-mix (seconds).

---

# ⇄ PASS B — THE MUSIC BED (long form only)

## What it is for
The bed is **continuity**, not energy. It holds the space between beats so a 12-minute video
does not feel like 40 disconnected clips. If the bed is doing the emotional work, the edit is
underbuilt.

## Choosing it
- **Instrumental only.** No vocals, no lyrics, nothing with a melody in the speech range
  competing for attention.
- Low-mid focused, minimal transients, no big drops. Anything with its own dynamics fights the
  sidechain and pumps audibly.
- **Rights-cleared only.** Flag anything whose licence is unclear *before* it reaches a render —
  a claim on a monetized long-form video is not a cheap mistake.
- One bed for the video, or two: one for the body, one darker for the turn onward.

## Level and ducking
- Bed sits **~22–26 dB under voice peaks** — noticeably quieter than the SFX layer.
- It is **ducked by a sidechain compressor keyed off the voice**, not just turned down. Under
  speech it drops; in the gaps it comes back up. `mix-bgm.sh` does this
  (`sidechaincompress`, threshold .03 / ratio 8 / attack 20ms / release 350ms).
- The gate: you should notice the bed **leave**, not arrive. If you can hum along, it is too loud.

## The drop map (this is where the retention lives)
| Where | What the bed does |
|---|---|
| Cold open | in from `0`, full |
| **~3s before the payoff spike** | **drops to silence** — the return on the spike is the hit |
| Chapters | steady, under everything |
| Chapter boundaries | a 400ms dip under the wipe, then back |
| **The turn** | **out entirely** for the whole beat. Bare voice. This is the most powerful move in the pass. |
| Recap | back in, slightly brighter |
| Outro | full, fading out over the last 2s |

Passing `--drops "t1:t2,t3:t4"` to `mix-bgm.sh` cuts the bed over those spans with 300ms fades.

## Applying it
```bash
bash scripts/mix-bgm.sh out/final-sfx.mp4 out/final.mp4 assets/music/bed.mp3 \
  --bed 0.10 --drops "12.4:15.9,440.0:462.0"
```
Then watch the whole thing once, end to end, with headphones. Levels that measure right can
still feel wrong; the watch is the real gate.

---

## Reproducibility
Same palette + same `sfx-cues.txt` + same bed + the two scripts → an identical result every
time. Levels live in the cue file and the script defaults; the palette is fixed; so the sound is
consistent across every video.
