> **PERSA SKILL NOTE.** This is a shared reference from the wider editing kit this skill was
> cut from. Where it talks about the cream plate, the house 4-frame rotation, the 3 caption
> styles / 4 caption bands, other styles (house, tierlist, vlog, yapping), `ui-blocks/`, the
> block picker, the storyboard tool or the registry shelf — those are not part of this skill.
> **`PERSA.md` overrides this doc wherever they disagree.** The rest (the clip contract, the
> matte, sourcing, rights, levels) applies as written.

# Sound Design — the SFX layer (present, on-cue, varied)

## Background music — the house bed (added 2026-08-07)

`bgm/house-bgm-34.m4a` is the channel bed for **every** short: Jad's own track, **cut from 0:20**
(the first 20s is intro he does not want), 192s long, 1.5s fade-in, AAC 128k.

**Level: -34 LUFS integrated.** A finished short of ours measures **-20.1 LUFS**, so the bed sits
**14 LU under the mix** — present, never competing. `-30` and `-38` cuts sit beside it if that reads
wrong; -38 is effectively inaudible on a phone speaker.

It runs the whole video at one level. There is **no ducking yet** — `scripts/mix-sfx.sh` only handles
the SFX layer and has no BGM stage, so the bed is currently mixed in by hand. If a beat ever buries a
word, that is the missing piece, not the level.

Do not cue `swell` over the bed repeatedly — `swell` was cut from this same track, so it doubles the
bassline. Fine once, muddy on repeat.


Sound effects are the polish pass that makes an edit feel alive. They're a **support layer that sits under the voice**: you should clearly *hear* each one, but it never competes with or steps on the narration. This is a **separate pass, done AFTER the visual edit is locked** — once the animations exist and their timings are fixed, you know exactly where sound belongs.

Source: **CreatingWithJerry's pack** — real files, peak-normalized, used as-is. The curated palette lives in `sfx/` (see `sfx/README.md`); the full library is in `sfx/library/`.


## ⭐ Fixed cues — Jad's standing rules (2026-08-08)

These are not suggestions per video. They fire every time, and `check-edit` should fail an edit
that is missing them.

| when | cue | note |
|---|---|---|
| **frame 0, the moment the video starts** | `swell` | 0.50s. The video opens on it. |
| **the hook line** | `riser` | starts BEFORE the hook word it builds to, cresting on the payoff. |
| **every syllable of a named platform / app / tool** | `camera-shutter` | one hit per syllable-group, not one per mention. |
| **whole mix** | `bgm/house-bgm-38.m4a` | the dimmest bed. |


### ⭐ Transitions use `swell` — the sound cut from Jad's own track (2026-08-08)

**Every layout change carries `swell`.** It is the 0.50s rise we cut out of
`nick_saraev_reel_background_music.mp3` at 0:00, so the transitions are scored with his own
material rather than a stock whoosh. `whoosh` / `whoosh-2` / `swoosh` stay in the palette for
graphic moves *inside* a beat, but the layout cut itself is always `swell`.

**One caveat carried over:** `swell` came from the same track as the bed, so it doubles that
bassline for half a second. With the bed at −38 that is inaudible; if the bed is ever raised,
re-check.

### The syllable rule, precisely
When Jad names a product, the shutter fires on **each spoken part** of the name, on that part's own
transcript onset:

- "OpenAI"  → `camera-shutter` on **O-pen**, `camera-shutter` on **A-I**  (2 hits)
- "GitHub"  → on **Git**, on **Hub**  (2 hits)
- "Claude"  → 1 hit
- "Claude Code" → on **Claude**, on **Code**  (2 hits)

Split on the *spoken* parts, not on dictionary syllables — "Anthropic" is said as one run, so one hit.
Read the word onsets out of `transcript.json`; never estimate. Two hits 120 ms apart is right for a
two-part name; if the parts are further apart in the audio, follow the audio.

### Everything DIM
Jad's word. These cues punctuate, they never announce. Mix the fixed cues **below** the SFX level
you would normally use — the shutter especially, because it fires in pairs and doubles up fast.
If you can hear the cue as a separate event rather than as emphasis on the word, it is too loud.

### Emphasis captions
`camera-shutter` also lands on a caption that carries real emphasis — not on every caption. Same
rule: it marks the word, it does not perform.

## Order of operations (don't plan SFX upfront)
1. Build the video exactly as always — timing table (**graphics only**), author the scenes, render to `out/`. **Lock the visual edit.**
2. **Then** do the sound pass on the locked render: watch it, note every motion / appearance / transition with its real timecode, choose a sound for each, write `sfx-cues.txt`, mix, gut-check.

Planning sound before the animation exists is guesswork; placing it after is just reading what's on screen. Timing is accurate because the render is final.

## Level — present, not loud (and not subliminal)
- You should **clearly hear** each effect on a normal watch. It sits **under** the voice — supporting it, never masking a word.
- Calibrate to the video's voice. For a voice around **−25 dB mean / −6 dB peak** (typical here) with the 0 dB-normalized pack:
  - **Transient hits** (pop, click, whoosh, swoosh, shutter, ping, beep, futuristic-click…): **gain ≈ 0.12** → ~−18 dBFS peak.
  - **Sustained beds** (riser, magic-reveal): **gain ≈ 0.09** → ~−21 dBFS peak.
  - **A hero moment** may go to **≈ 0.16** (~−16 dBFS). Rarely louder.
- The gate: watch once. If an effect **buries a word or makes you flinch**, it's too loud — pull it down. If you have to **strain to hear it**, it's too quiet — bring it up. It should make the edit feel *crisper*, and you should notice it.
- Different voice level? Measure it (`ffmpeg -i render.mp4 -af volumedetect -f null -`) and scale the gains to keep SFX roughly **15 dB under the voice peaks**.

## Density & variety (use the opportunities; don't lean on three sounds)
> **HOUSE ONLY.** `persa` runs a much thinner pass and bans four of these sounds —
> see the persa section below before applying any of this to a full-bleed cut.
- **Be generous.** Most moves — an entrance, a number landing, a card flip, a checkmark, a zoom, a cut, a highlight — earn a sound. Silence is a deliberate breath, not the default.
- **Vary it.** Match the sound to the *specific* element, and rotate so it doesn't feel copy-pasted. Reusing a sound is fine; reusing the *same* one for everything is what feels cheap. A code chip is a `futuristic-click`, a checkmark is a `confirm`, a countdown is a `beep` — not all "pop."
- **One foreground hit at a time** (space hits ≥ ~0.3s). A sustained bed (riser / reveal) MAY underlie hits — that's a layer, not a clash.


## ⛔ PERSA: FOUR SOUNDS ARE BANNED, AND THE PASS IS THIN (added 2026-08-28)

Jad, on tp-0828c: *"there are too many sound effects chill out on them blacklist: ping,
swoosh, confirm, beep"*.

**In the `persa` style these four never go in a cut: `ping` · `swoosh` · `confirm` · `beep`.**
Not "use them sparingly" — out. They were the second, sixth, eighth and thirteenth most-used
sounds across the six persa cuts before this (12 of tp-0828c's 41 cues), so this is a real
change to the palette, not a trim. `ping` in particular was persa's signature cue on the
outline emphasis word: **that beat is now silent and lands on the type alone.** Do not
substitute another sound for a banned one — the answer to a banned cue is no cue.

**And the whole pass is much thinner than house.** tp-0828c went 41 cues → **17** in 40s.
What earns a cue in persa:

| keep | why |
|---|---|
| `swell` on **every** layout change | BLACKLIST #8 — a silent layout change is still banned. These are the bed, not events. |
| `riser`, **once**, in the hook | — |
| `camera-shutter` on a product NAME | one per syllable, at the one place the name is stamped |
| `futuristic-click`, **two or three in a whole video** | only where a real UI does the thing he is describing |
| `pop` on the CTA chip | — |

Everything else is decoration. The ten `futuristic-click`s cut from tp-0828c were each
audible, on a real word onset, and correctly gained — they were cut because there were **too
many of them**, which is a judgement the level gate cannot make for you.

⚠ This puts persa **below the 25–40 range** in *Density & variety* above. That section is
**house**. Do not "fix" a persa pass back up to 25 cues.

## The palette (`sfx/`) — reach for these
| sound | ~dur | use it when… |
|---|---|---|
| `whoosh` / `whoosh-2` | 1.1 / 0.5s | a zoom in/out; a big element flies in — rotate the two |
| `swoosh` ⛔ **house only** | 0.9s | a fast slide / whip between scenes |
| `pop` | 0.1s | something small appears (soft) |
| `click` | 0.35s | something appears / a UI tap (crisp) |
| `futuristic-click` | 0.7s | a *techy* element — settings row, code chip, toggle |
| `confirm` ⛔ **house only** | 1.9s | a success — checkmark, "it works", a positive result |
| `ping` ⛔ **house only** | 1.1s | a notification, a highlight, a single alert |
| `beep` ⛔ **house only** | 0.7s | a countdown, a timer, a numeric / warning beat |
| `keyboard` | 1.3s | typing, code, a terminal moment |
| `magic-reveal` | 3.1s | you UNVEIL something (the big reveal shimmer) |
| `riser` | 3.2s | building tension — starts BEFORE the payoff, crests on it |
| `swell` | 0.5s | a fast rise that lands on the beat — riser at one-sixth the length |
| `highlighter` | 0.46s | the marker stroke — cue it ON the sweep, and match its length to the phrase. **Gain ≈0.34, target only +1 to +3 dB** (2026-08-11) |
| `camera-shutter` | 0.1s | a crisp clean cut / snapshot |

Want another voice? Pull any variant from `sfx/library/` (PopUp ×6, Click ×10, Futuristic Click ×10, Woosh ×6, Beep ×7, Confirmation, Riser ×4, Extras — ring slice, turn-it-up, radio…). Trim it to a clean hit; copy it into `sfx/` with a clear name if you'll reuse it.

## A cue that REPEATS is texture, not an event

Added 2026-08-11, from Jad on halo-3-ai: *"we need to reduce the highlighter sound more."*

The +2 to +5 dB delta target below is for cues that fire **once or twice**. Applied to a sound
that recurs — `highlighter` fires on every marker sweep, six times in a 48s cut — it becomes the
loudest recurring thing in the video and reads as an announcement. `highlighter` at gain 0.72
measured +3.5 to +6.0 dB and was rejected; **0.34, measuring +1 to +3 dB**, was accepted.

Rule of thumb: **three or more firings in one video → target +1 to +3 dB, not +2 to +5.**
Transitions and one-off reveals (`swell`, `magic-reveal`, `riser`, `ping`) keep the higher band.

## Applying it (the sound pass, per video)
1. On the **locked render**, write `videos/<folder>/sfx-cues.txt` — one line per cue: `<time_sec> <sound> [gain]` (`#` comments ok; see `scripts/mix-sfx.sh`).
   - **Time to the animation, not the plan.** Read the composition's real timeline (GSAP `.to(…, t)` positions, CSS `animation-delay`) or extract frames (`ffmpeg -ss T -i render.mp4 -frames:v 1 f.jpg`) to pin the exact instant each event fires. Word/plan times drift from the animation by up to a second — that drift is the #1 cause of sloppy sound. Align swelling sounds (whoosh, riser) to *crest* on the event; put transients (pop, click, shutter) *on* the frame.
2. Mix:
   ```
   bash scripts/mix-sfx.sh out/<render>.mp4 out/<render>-sfx.mp4 videos/<folder>/sfx-cues.txt
   ```
   Video is stream-copied (no quality loss); each cue is faded-in, leveled, and delayed to its beat.
3. Gut-check with the level gate above. Tune any line, re-mix (seconds).

## Reproducibility
Same palette + same `sfx-cues.txt` + `mix-sfx.sh` → identical result every time. Levels live in the cue file and the script default; the palette is fixed; so the sound is consistent across every video.

---

## ⚠ Leading silence — four sounds fire LATE unless you pre-roll them

Measured 2026-08-09 on the shipped palette. These files begin with digital silence, so a cue
placed on the word lands after it:

| sound | silence at head | place the cue at |
|---|---|---|
| `magic-reveal` | **0.85 s** | word − 0.85 |
| `whoosh` | **0.50 s** | word − 0.50 |
| `ping` | **0.25 s** | word − 0.25 |
| `swoosh` | **0.15 s** | word − 0.15 |

Everything else starts within 0.10 s and needs no offset.

## ⚠ Gain is per SOUND, not per cue type

Source peaks across the palette span 12 dB, so one flat gain leaves half the pass inaudible:

```
camera-shutter  0.0    futuristic-click -0.1   riser  0.0    swell -2.0
highlighter    -2.0    confirm          -2.1   beep  -3.3    pop   -4.7
keyboard       -4.5    ping             -7.7   whoosh -9.4   click -11.4
magic-reveal  -12.2
```

A `magic-reveal` at 0.30 measures **+0.4 dB** at the cue — inaudible. It needs ~0.95.
`click` and `whoosh` need 0.45–0.55. Always verify by measuring the delta at each cue against
the visual-only render:

```bash
ffmpeg -ss <cue> -t 0.45 -i out/<slug>-visual.mp4 -af volumedetect -f null /dev/null
ffmpeg -ss <cue> -t 0.45 -i out/<slug>-sfx.mp4    -af volumedetect -f null /dev/null
```
Under +1.0 dB is thin. Target +2 to +5 dB.

## The bed — a 36-SECOND LOOP, levelled by LUFS (replaced 2026-08-10)

**bed = `broll-library/bgm/house-bed-loop.m4a`** — *Baba* (Daniel Deuschle), cut **0:09 → 0:45**
and looped. Jad:

> "start recording it from the second nine and then when you reach the second 45 you stop there
> ... if sometimes my videos are 2 minutes or 3 minutes or 4 minutes it just loops back in to
> the second nine ... we don't need the entire song because then in the song it starts singing
> lyrics and I don't want that in the video"

So the bed never reaches the vocal section, and length is no longer a constraint — a 4-minute
video plays the loop ~7 times. Lay it with:

```bash
bash scripts/lay-bed.sh out/<slug>-sfx.mp4 out/<slug>-FINAL.mp4
```

**The seam.** Built with an equal-power crossfade from the material that FOLLOWS 0:45, sliced
**sample-accurately off a decoded WAV**. `-ss` on the compressed m4a is not sample accurate and
leaves an audible click (measured: 18x the local material). Verified seamless — the boundary
step sits *below* the median sample-to-sample difference of its own neighbourhood.

## ⚠ LEVEL THE BED BY LOUDNESS, NOT BY PEAK

The loop is pre-levelled to **-34 LUFS** and mixes at `volume=1.0`. Do not re-level it.

The old rule — "peak-normalise to -38 dB" — is what made the music inaudible. Peak and loudness
are not interchangeable for sparse music: Baba's mean sits 10-17 dB below its peaks, so a -38 dB
PEAK put the bed at **-49.8 LUFS** against a **-20.4 LUFS** mix. That is 29 LU down, versus the
14 LU this document actually targets. It contributed **+0.1 dB** and Jad asked where the song
was, on a render that already contained it.

The method, whenever the bed or the track changes:

```bash
ffmpeg -i out/<slug>-FINAL.mp4 -af ebur128 -f null -    # measure the MIX
# bed target = mix - 14 LU ; gain the bed to hit it, then verify it adds ~+1 dB or more
# in the quietest windows of the sfx-only render
```

