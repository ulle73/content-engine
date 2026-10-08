# Assembly — segment rendering, concat, chapters

⇄ **The single biggest structural difference from the short.** A 45-second short is one
`index.html`. A 12-minute video **must not** be. Build one composition per segment.

---

## 1 · Why segments

A monolithic long-form composition fails in four ways, all of them expensive:

1. **Render time is serial and total.** One bad frame at 11:40 means re-rendering 12 minutes.
   With segments you re-render 90 seconds.
2. **Browser memory.** A single timeline holding hundreds of media elements and thousands of
   GSAP tweens gets slow to seek and eventually unstable — snapshots and preview become useless
   exactly when you need them.
3. **Lint and snapshot stop being usable.** A contact sheet of a 12-minute comp is unreadable;
   per-segment sheets are the actual review instrument.
4. **You cannot iterate on one chapter.** In practice this is what kills the edit — feedback
   always arrives per chapter.

## 2 · The layout on disk

```
work/nextphase/videos/<name>/
  VIDEO.md               the brief
  PLAN.md                the approved structure (structure.md §4)
  assets/
    recording.mp4        original camera
    recording-tight.mp4  post-tighten  ← everything times against this
    screen.mp4           normalised screen capture (if any)
    transcript.json      original (dead after the tighten)
    transcript-tight.json  ← the only timing source
    cuts.json            the tighten's kept spans
    broll/               sourced media, all 30fps CFR
    music/bed.mp3
  seg-01-cold-open/
    index.html
    build.py             (optional generator)
    snaps/
  seg-02-what-it-does/
  …
  out/
    seg-01.mp4 … seg-NN.mp4
    final-visual.mp4
    chapters.txt
    final-sfx.mp4
    final.mp4            ← the deliverable
    <name>.srt
  sfx-cues.txt
```

## 3 · Segment rules

- **One segment per chapter**, plus one each for the cold open, the turn, the recap, and the
  outro. Target 60–180s per segment.
- **Cut segments on a real silence** in the tight transcript — at least a 0.25s gap — never
  mid-word and never mid-breath. A boundary inside a phrase is audible at the join.
- **Each segment owns its slice of the recording.** In the composition, the camera/screen video
  element is the tight recording with the segment's in-point:
  ```html
  <video src="../assets/recording-tight.mp4" data-media-start="184.62"></video>
  ```
  Every time inside that segment's timeline is then **relative to the segment**, starting at 0.
  Convert once, at the top of the file, and never mix the two clocks:
  ```js
  const SEG_START = 184.62;              // from PLAN.md, a real word onset
  const at = t => t - SEG_START;         // transcript time -> segment time
  tl.to("#card", {opacity:1}, at(191.24));
  ```
  Mixing absolute and relative times in one composition is the most common bug here, and it
  looks like "the graphics are all slightly early" rather than like a bug.
- **A layout never spans a segment boundary.** End each segment on a completed beat.
- **Each segment lints and snapshots independently** and must pass on its own.

## 4 · Render each segment

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
cd work/nextphase/videos/<name>/seg-02-what-it-does
npx --yes hyperframes lint                                  # 0 errors
npx --yes hyperframes snapshot --at 0,4.2,11.8,26.0 -o snaps
#   ^ read the contact sheet. Fix. Repeat.
npx --yes hyperframes render -q high -f 30 -o ../out/seg-02.mp4
```

**Identical encode settings across every segment**, or the concat either refuses or re-encodes.
Same resolution (1920×1080), same fps (30), same codec, same audio sample rate.

## 5 · Concat + chapters

```bash
bash scripts/concat-segments.sh out/final-visual.mp4 out/seg-*.mp4
```
- Tries the **concat demuxer with `-c copy`** first — instant, lossless, no re-encode.
- Falls back automatically to a re-encode if the streams differ, and tells you which segment
  differs so you can fix the real problem instead of accepting a silent quality loss.
- Writes **`out/chapters.txt`** from the real measured durations of each segment — YouTube
  format, `0:00` first, one line per segment.

**Never hand-count chapter timestamps, and never copy them from `PLAN.md`** — the plan's times
are pre-render estimates and always drift by a few seconds.

Chapter titles come from the segment folder names (`seg-02-what-it-does` → "What It Does"), or
pass `--titles titles.txt` with one title per line to control them exactly. YouTube requires the
first chapter at `0:00` and every chapter ≥10s — the script warns if a segment is shorter.

## 6 · Then, and only then, sound

Concat first, **lock the visual cut**, then Pass A (SFX) and Pass B (music bed) on the whole
file (`sound-design.md`). Mixing sound per segment and concatenating afterwards produces audible
seams at every join — the amix tail and the limiter state do not survive a cut.

Write the **cues** per segment (timing against the short file is far easier), then offset each
cue by that segment's start from `chapters.txt` into one `sfx-cues.txt` for the full mix.

## 7 · Re-rendering one segment after feedback

```bash
cd work/nextphase/videos/<name>/seg-04-the-catch && npx --yes hyperframes render -q high -f 30 -o ../out/seg-04.mp4
cd ../ && bash scripts/concat-segments.sh out/final-visual.mp4 out/seg-*.mp4
```
Then **re-run the sound passes** — if the segment's duration changed at all, every cue after it
has moved. `concat-segments.sh` rewrites `chapters.txt`, so diff it against the old one to see
exactly how much later everything downstream now sits.

## 8 · Deliverables

| File | What |
|---|---|
| `out/final.mp4` | the video — 1920×1080, 30fps, SFX + bed |
| `out/chapters.txt` | YouTube chapter timestamps |
| `out/<name>.srt` | full subtitles from the tight transcript |
| `out/thumb-*.png` | thumbnail candidate frames, if asked |

Report rendered + scored and open it for review. **Publish nothing without explicit approval.**
