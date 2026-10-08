# Sound design

## Sound is not optional, and here it carries more than usual

Zak has no visual transitions at all. Nothing fades, nothing wipes, nothing
eases. The sound is what makes a hard cut read as intentional rather than as a
dropped frame — it is doing the job that a transition does in the other four
styles.

## Density

**~6–10 cues per minute.** That is the studio's relaxed density, roughly half
what the skills' own defaults suggest, and it is what Jade asked for:
transitions only, quiet transients, nothing decorative.

Because zak's layout changes are rarer than `nextphase`'s or
`motiongraphics`', the count lands naturally near the bottom of that range.
Do not pad it back up with texture cues.

| Event | Cue | Note |
|---|---|---|
| Scene change | `swoosh` or `whoosh` | the main workhorse |
| Chapter card in | `riser` into the cut | the only cue that builds |
| Chapter card out | `confirm` | |
| Window → full bleed | `whoosh-2` | the one move gets the one big cue |
| Cursor press in a screen recording | `click` | match every real press |
| Caption changes | **nothing** | 80/min. Cueing them is unlistenable. |

**Never cue a caption change.** It is the most tempting mistake in this style
and it ruins the piece within ten seconds.

## The mixer

Reuse the sibling palette and **call the scripts by their path inside that
skill folder** — never copy them into a video folder, or every cue fails with
`unknown sound`:

```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-sfx.sh out/visual.mp4 out/sfx.mp4 sfx-cues.txt
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/mix-bgm.sh  out/sfx.mp4    out/final.mp4 assets/music/bed.mp3
```

⚠ `mix-bgm`'s `-shortest` eats the last frame — pad the bed, and check the
final duration against the visual. And the SFX palette's peaks span ~11dB, so
per-cue gains have to be solved against the bed, not guessed.

## The bed

The reference has no music bed at all — 40 seconds of wall-to-wall speech with
no silence over 0.35s at −35dB. For a long-form piece a bed is still right, but
keep it **low and ducked**; this is a quiet, still style and a loud bed fights
it directly.
