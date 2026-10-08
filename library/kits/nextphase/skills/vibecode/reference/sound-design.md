# Sound

*"sounds are super important, man."* Every layout change carries a transition
**and** a sound. No silent cuts, ever.

vibecode is a **paper and machine** style, so the palette leans mechanical and
physical rather than cinematic. Roughly **12–18 cues/min** — denser than persa,
because more things move.

Reuse the shared palette and **call the mixer by its path inside the sibling
skill folder** — never copy it into a video folder, or every cue fails with
`unknown sound`:

```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh \
     out/final-visual.mp4 out/final-sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh \
     out/final-sfx.mp4 out/final.mp4 assets/music/bed.mp3
```

## What gets a cue

| Event | Cue | Note |
|---|---|---|
| Paper card arrives | paper/whoosh-short | one per card, so a row of 3 gets 3 |
| Sticker lands | click + paper | the 2-frame punch reads as an impact |
| Clip block appears on timeline | tick | short, dry; pitch up across the row |
| Playhead sweep | soft rise | under the sweep, out on the last clip |
| **Red X stroke** | marker/scratch | ⭐ the loudest cue in the style |
| Strike-through | same, softer | |
| Step row activates | click | |
| Meter fill | rising tick bed | ends on a soft chime at full |
| Caption change | **nothing** | captions are silent — they hard-cut |
| Scene transition | whoosh | matched to the transition type |
| Ground swap (chapter) | big whoosh + impact | the biggest cue in the video |
| Churn / sparkle | nothing | it would machine-gun; the churn is silent |
| Cursor press in a screen recording | click | match every real one |

## The two that matter most

1. **The red X.** It is the punchline of Scene 3. Give it a real marker-scratch
   with body, and let it sit slightly above the bed.
2. **The chapter ground swap.** Cobalt→cream is the biggest visual event in the
   video and it needs a cue with weight, or the new act starts limply.

## The bed

Ducked under the VO throughout. Something with a pulse — the style is
mechanical, and a floaty ambient bed fights it. Drop the bed entirely for the
2s teaser interstitial and bring it back with the new chapter; that silence is
what makes the swap land.

## Where cues come from

Write `sfx-cues.txt` against **`assets/transcript-tight.json` timings**, and
only after the concat, from real rendered durations. Timing cues against the
original transcript puts every one of them slightly early.
