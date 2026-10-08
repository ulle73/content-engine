# Workflow

Prefix **every** bash step with:

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```

node/npx come from nvm; `ffmpeg`, `ffprobe` and `yt-dlp` live in `~/.local/bin`.
Neither is on the default non-interactive PATH, and every "command not found"
in this workflow is this.

---

### 0 · Ask which style
`zak` · `persa` · `nextphase` · `motiongraphics` · `vibecode`. Never assume,
never infer it from the footage. Record the answer at the top of `PLAN.md`.
Then locate `work/nextphase/videos/<name>/`, `VIDEO.md`, `assets/recording.mp4`.

### 1 · Transcribe
Chunk anything over ~90s. ⚠ Parakeet silently drops audio — it has lost 77s of
a 164s take, and a 10s non-English span that looked like trailing dead air.
Compare the transcript span against the file duration **minute by minute**;
checking only the ends will not catch a dropped chunk in the middle.

### 2 · Tighten
`library/kits/nextphase/skills/nextphase-long-editing/scripts/tighten-cuts.py`. From here on,
`assets/transcript-tight.json` is the **only** timing source. Timing against
the original shows up as "the captions are all slightly early", never as an
error.

### 3 · Reframe and grade the plate
```bash
bash scripts/zak-plate.sh assets/recording-tight.mp4 assets/plate.mp4 16x9 0.35 plate
```
The 16:9 window is a 2.35:1 crop, so this genuinely re-crops — point `crop-y`
at the face (0.30–0.40 for a talking head). Details and the caveat on the
curve: `look.md` §2.

**There is no matte step.** Zak does not cut the subject out; the plate goes in
the window whole. Reaching for `rvm-matte.py` here is `persa` habit.

### 4 · PLAN.md
Scenes per beat, the **actual on-screen copy** for every title line, the media
list, the chapter boundaries, the re-hooks. Write the real strings — that is
where a factual error gets caught cheaply. **Get a "go" before authoring.**

⚠ Split segments **mid-scene, never on a transition** — a transition cannot
cross a segment boundary. Use `silencedetect` and whole-frame cut times;
Parakeet reports fake 0.000s sentence gaps that are not real silence.

### 5 · Source real media
Verify facts while sourcing — caption live numbers, not stale ones. Flag
debunked stats, dead or renamed products, and any third-party clip whose rights
are unclear, **before** it reaches a render. Check every screenshot actually
rendered content. Re-encode everything to 30fps CFR and verify with `ffprobe`.

### 6 · Author, one composition per chapter
- Root carries `class="zk-frame zk-16x9"` — without it every `cqh` collapses.
- Import `assets/tokens.css`. Never mix in another style's tokens.
- Build captions:
  ```bash
  python scripts/build-captions.py assets/transcript-tight.json \
      --out seg-01-cold-open/captions.html --offset <segment start>
  ```
- ⚠ Symlink assets into each `seg-NN/` — HyperFrames rejects `../assets/`, and
  each segment folder is its own project root. Vendor fonts and gsap per
  segment too.
- ⚠ Derive segment durations from **frame indices**, never subtracted seconds.
- ⚠ A `clip` creates a stacking context that can hide captions — keep
  `.zk-caption` out of one.

### 7 · Per segment: gate, snapshot, render
```bash
npx hyperframes lint seg-01-cold-open
bash scripts/check-zak.sh work/nextphase/videos/<name>                 # must exit 0
npx hyperframes snapshot seg-01-cold-open --at 0,2,5,9  # READ the contact sheet
npx hyperframes render seg-01-cold-open -q high -f 30
python scripts/check-contrast.py out/seg-01.mp4        # must exit 0
```
`check-zak.sh` is static and cannot see the plate; `check-contrast.py` runs on
the render and is the one that catches an invisible caption. Run both.

### 8 · Concat
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh
```
⚠ Chapter timestamps come from **real rendered durations** — never hand-count
them and never copy them from `PLAN.md`. And relay the source audio after the
concat: AAC priming drifts ~38ms per join and accumulates.

### 9 · Sound
SFX pass, then the ducked bed. `sound-design.md`. ~6–10 cues/min, transitions
only, and **never cue a caption change**.

### 10 · Deliver
`out/final.mp4` · `out/chapters.txt` · `out/<name>.srt`. Report rendered +
scored, open it for review, **stop there**.

**Nothing publishes, posts or uploads without explicit approval.**

---

## The five things that go wrong

| Symptom | Cause |
|---|---|
| Type is tiny but the layout looks fine | the root is missing `.zk-frame`, or a `%` font-size |
| Captions all slightly early | timed against the original transcript, not the tight one |
| Captions invisible in the final | bright plate; `check-contrast.py` was skipped |
| It looks like a subtitle track | one-word captions, or the caption tracking is not negative |
| It feels floaty and generic | something is drifting. Nothing drifts in zak. |
