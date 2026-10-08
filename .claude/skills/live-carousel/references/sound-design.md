# Sound design with `lc_audio` (numpy only, no samples needed)

Every slide gets its own mix, `audio/out/<slide>.wav`, which is exactly as long as the slide. Effect
tails that ring past the end are folded back onto the start (`master(..., wrap=True)`), so a slide
can loop forever with no click or gap. Because every slide is whole 120 BPM bars of the same groove,
the beat carries on across swipes.

`render_all.py` runs `audio/make_audio.py` before every build. To run it on its own:
`.claude\skills\live-carousel\scripts\py.cmd work\live-carousel\<slug>\audio\make_audio.py`.
Mixes peak at 0.6 (~-4.4 dBFS, `lc_audio.PEAK`): HyperFrames 0.8.140 refuses AAC true peaks above -1 dBTP.

## Building blocks

```python
bus = Bus(sec + 3)                    # 3 s of headroom for tails
g, _ = groove(bars, intensity=0.8)    # kick 1 & 3 (+ the and-of-3), clap 2 & 4, 16th hats, sub bass, Am9 pad
bus.add(g, 0.0)                       # add(signal, time, gain=1, pan=0)
bus.add(boop(NOTE["E5"], 0.6), 1.0, pan=0.3)   # pitched hit on a landing (A-minor pentatonic NOTE table)
place_sample(bus, "impact-bass-1", 2.0, 0.9)   # named one-shot; the transient lands exactly at t
x = master(bus, sec, wrap=True)       # wrap tails, light reverb, glue, soft clip
write_wav(OUT / "02-easing.wav", x)
```

| instrument | use |
| --- | --- |
| `kick, clap, hat(open_=), sub, pad` | the groove parts, if you want a custom pattern |
| `boop(freq, level, dec)` | marimba-ish: every bounce or landing; walk up the pentatonic for runs |
| `boing(freq, level, dur, up=)` | cartoon spring: squash and stretch, trampolines, launches |
| `thump(level)` | soft body hit under a landing |
| `whoosh(dur, level, f_lo, f_hi, shape="swell"/"in"/"out")` | movement, entrances, exits, wipes |
| `speed_whoosh(vel, level)` | noise whose loudness follows a velocity curve (sonified easing) |
| `tick(level, f)` / `clunk(level)` | UI ticks, spacing marks, robotic stops |
| `scribble(dur, level)` | a marker strike, a drawn line |
| `whistle_fall(dur, level, f0, f1)` | something dropping in from above |
| `crash(level)` | cymbal wash on a big hit |
| `tape_stop(sig, t_start, dur)` | the music winds down (the "life drains out" moment) |
| `music_bed(path, start, dur, gain)` | a bar-aligned slice of a song file |
| `match_loudness(x, rms_db=-14)` | the same level on every slide, so swiping never jumps in volume |

Named effects for `place_sample`: `impact-bass-1`, `impact-bass-2`, `riser`, `click`, `click-soft`,
`key-press`, `typing`, `pop`, `chime`, `ping`, `notification`, `sparkle`, `glitch-1`, `whoosh`.
When HyperFrames' free skills are installed, the media-use SFX pack supplies real recordings
(Pixabay licence, free for commercial use). Otherwise synthesized stand-ins are used, so it
always works. `rate=` re-pitches a sample, `cut=` trims it, and `pan=` places it.

## Timing rules

- Read the times off `render(t)`. Every visual event with weight gets a sound at the same t: a
  landing, a slam, a word flip, a letter typed, a button press. An effect even 2 frames early or late
  feels wrong.
- Put big impacts on downbeats. When a slide has a "drop", start the groove there (`bus.add(g, 2.5)`)
  and let the slide before it build: a riser, then cut 80 ms before the slam.
- Leave room: duck the groove (intensity 0.7 to 0.8) under busy effect passages.
- Pan by position on screen: the left of the frame is pan -0.6 and the right is +0.6.

## Using a song instead of the groove

Use only music the user has the rights to: their own track, a royalty-free library, or a free local
generator. In photo mode, set `carousel.json → "music": {"file": "song.mp3", "start": 8.0}`. Each
slide plays the next `dur` seconds of the song, so it carries on across swipes. Set `start` to a bar
line (a downbeat). In motion mode, call `music_bed(path, start, dur)` and add it to each slide's bus
in place of `groove`. Keep effects on top at about 0.4 to 0.6 gain.

If the platform's own music sticker is added to the post, it may replace the slides' audio. Leave
it off to keep this sound design.
