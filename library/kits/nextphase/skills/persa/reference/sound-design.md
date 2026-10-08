# Sound

*"sounds are super important, man."* Every layout change carries a transition
**and** a sound. No silent cuts, ever.

Persa has no visual transitions to speak of — panels fade, cuts are hard. That
puts **more** load on sound than in the other two styles, not less: the sound is
what makes a hard cut feel intentional instead of like a dropped frame.

## The palette

Shared with the sibling skills. **Call the mixer by its path inside that skill
folder** — never copy it into a video folder, or every cue fails with
`unknown sound`:

```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/visual.mp4 out/sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh  out/sfx.mp4    out/final.mp4 assets/music/bed.mp3
```

## What gets a cue

| Event | Sound |
|---|---|
| Panel in | `whoosh` — short, low |
| Panel out | nothing. It fades; silence is correct. |
| Scene change (1↔2/3/4) | `swoosh` on the cut frame |
| Emphasis word | `pop` or `futuristic-click` on the onset frame |
| Slam headline | `confirm` with a `riser` tail into it |
| Screen-recording cursor click | `click`, on the actual click frame |
| Punch-in | `camera-shutter`, quiet |
| Hand note | `magic-reveal`, soft |

**Cursor clicks are worth the effort.** The reference is mostly screen recordings;
matching a `click` to each real cursor press is what makes them feel live rather
than like footage playing in a box.

## Levels

- Density **~10–16 cues per minute**. Persa is slightly sparser than
  motiongraphics because it has fewer graphic events.
- SFX sit **13–15 dB under voice peaks**; the music bed **22–26 dB under**.
- Calibrate with `ffmpeg -af volumedetect`. Do not guess.

## The bed

One bed for the whole runtime, ducked under voice. It should be almost
subliminal — if you notice the music on a first watch it is too loud.
