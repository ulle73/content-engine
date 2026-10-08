# Sound

*"Sounds are super important, man."* Every layout change carries a transition **and** a
sound. No silent cuts, ever.

The palette and the mixers are **shared with `nextphase-long-editing`**. Call the
scripts by their path inside that skill folder — `mix-sfx.sh` resolves the palette as
`$(dirname $0)/../sfx/`, so a copy placed in a video folder fails every cue with
`unknown sound`.

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/final-visual.mp4 out/final-sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh  out/final-sfx.mp4   out/final.mp4     assets/music/bed.mp3
```

Both passes run **on the locked visual render**, in this order.

---

## Pass A — SFX

**Density ~12–20 cues per minute.** Nearly every move earns a sound; silence is a
deliberate breath, not a default.

### Cue map for this style

| Moment | Sound |
|---|---|
| **Light leak** | `swoosh` on the bloom **+ a `riser` tail cresting on the white-out**. Start the riser ~1.2s early so it peaks on the blowout frame. This is the loudest transition in the style — treat it as an event. |
| Whip between scenes | `whoosh-2` / `swoosh` |
| Bar wipe opening | `swoosh`, short and dry |
| Word build (per word) | `click` at low level on each word onset — or one `futuristic-click` on the first word only, if per-word reads as busy |
| Glass tile pops in | `pop` per tile, following the stagger |
| Node pill lands | `click` |
| Connector draws | nothing — the pill landing already sounded it |
| Panel outlines in | `futuristic-click` |
| Camera pull-back | nothing on its own — it runs the whole scene. Sound the elements arriving on it, not the move. |
| Media card rises in | `camera-shutter` |
| Count-up ticking | `beep` per tick, or one `confirm` on the final value |
| Conic ring draw | a `riser` under the sweep, resolving on completion |
| Dive-through | `whoosh` in, `swoosh` out |
| Screen-stage punch-in | `whoosh`, quiet |
| Typing on screen | `keyboard` |
| Checkmark / land / confirm | `confirm` |
| Brand lockup | `magic-reveal` |
| Chapter payoff / slam reveal | `magic-reveal` + `riser` |
| CTA | `ping` |

### The payoff spike
**Always a `riser`**, started ~1.5s before the reveal so it crests on the beat. Also
use one into each chapter card. Reserve the coral/magenta flash + riser combination for
the real payoff and the turn — no more than ~3 per video, or it stops meaning anything.

### Levels
Calibrate against the voice, don't guess:
```bash
ffmpeg -i out/final-visual.mp4 -af volumedetect -f null - 2>&1 | grep max_volume
```
SFX sit **~13–15 dB under voice peaks**. Hot VO → transients around 0.11–0.12; quiet VO
→ 0.07–0.09. A cue you *notice as a sound effect* is too loud.

---

## Pass B — the music bed

A long-form video without a bed sounds like a webcam recording. The bed is **ducked
under the voice by a sidechain compressor**, not just turned down.

- Sits **~22–26 dB under voice peaks**. You should notice it *leave*, not arrive.
- Instrumental only. No vocals, no melody that competes with speech. Rights-cleared only.
- **Change the bed at the turn**, and **drop it entirely for ~3s before the payoff
  spike** — the return of music is itself a retention device.
- This style's beds want a dark synth / arp texture rather than lo-fi. It should sit
  with the violet glow, not against it.

Source through `media-use` (`resolve` BGM), which freezes the file locally and records
the licence in the ledger.

---

## Writing `sfx-cues.txt`

One cue per line, timed against the **final visual render** — which is the concatenated
timeline, not a segment. Get the times from the rendered file, never from `PLAN.md`.
Segment boundaries move during render; plan times are pre-render estimates and always
drift.

If a cue fails with `unknown sound`, you copied the script instead of calling it by its
path in the skill folder.
