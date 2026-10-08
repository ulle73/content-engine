# The PERSA build

```
work/nextphase/videos/<name>/
  VIDEO.md              the brief
  PLAN.md               style: persa  ← first line. Then the approved structure.
  assets/  recording.mp4 · plate.mp4 · recording-tight.mp4 · transcript-tight.json
           cuts.json · matte/ · broll/ · music/
  seg-NN-<name>/        one composition per chapter
  out/                  seg renders · visual · final · chapters.txt · .srt
  sfx-cues.txt
```

Per-video work lives **only** in `work/nextphase/videos/<name>/`. The skill never changes as a
side effect of editing a video.

---

## 0 · Ask which style
`persa` · `nextphase` · `motiongraphics`. Never assume, never infer it from the
footage. Record the answer at the top of `PLAN.md`.

## 1 · Transcribe
```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```
⚠ **Parakeet silently drops audio.** It lost 77s of a 164s take once, and 13s
another time, with no silence to show for it. **Chunk anything over ~90s**, and
compare the transcript span against the file duration **minute by minute** — a
dropped chunk mid-file desyncs everything after it and checking only the ends
will not catch it. It also drops other-language spans; measure with
`volumedetect` before trimming anything that looks like dead air.

## 2 · Tighten
```bash
python library/kits/nextphase/skills/nextphase-long-editing/scripts/tighten-cuts.py ...
```
⚠ After this, **`assets/transcript-tight.json` is the only timing source.** The
tighten pass moves every word onset. Timing against the original transcript shows
up as "the graphics are all slightly early", never as an error.

⚠ Frame-align every segment boundary. Parakeet reports fake 0.000s sentence gaps;
use `silencedetect` and whole-frame cut times.

## 3 · Grade the plate
```bash
bash scripts/persa-grade.sh assets/recording-tight.mp4 assets/plate.mp4 plate
python scripts/grade-check.py assets/plate.mp4
```
`plate` strength only — bloom, vignette and grain go on **once, at the end**, over
the finished comp. See `grade.md` §4.

## 4 · Matte
```bash
source library/.venv/Scripts/activate
python library/kits/nextphase/skills/nextphase-long-editing/scripts/rvm-matte.py --src assets/plate.mp4 --out assets/matte --frames <n>
```
Matte the **graded** plate, so the cutout and the background are the same colour.
Keep the rim (`layouts.md` §5); kill the flicker.

## 5 · PLAN.md — get a "go" before authoring
Chapters with word onsets · the scene assigned to each beat · **the actual
on-screen copy for every caption and emphasis word** · the media shopping list ·
the re-hook marks. A beat whose copy is still a placeholder is not ready to build.
This is also where a factual error gets caught cheaply — on a plan line, not in a
render.

⚠ **Verify facts while sourcing.** Caption live numbers, not stale ones. Flag
debunked stats, dead or renamed products, and any third-party clip whose rights
are unclear — **before** it reaches a render.

## 6 · Source real media
≥1 per 20s, minimum 8. Normalise every sourced clip to **30fps CFR** and verify
with `ffprobe`. Check every screenshot actually rendered content.

⚠ The browser MCP extension is flaky here — use `curl`, Chrome headless and
`yt-dlp` for sourcing.

**Windows-skärmdumpar:** Win+Shift+S lägger bilden i urklipp; be användaren spara den (t.ex. `Bilder\Skärmbilder\…png`) och ge sökvägen, eller använd den inklistrade filen direkt. Kopiera filer med glob om namnet innehåller specialtecken.

## 7 · Author
One composition per chapter, `seg-NN-<name>/`.

⚠ A segment folder is its own project root — HyperFrames rejects `../assets/`.
**Symlink assets into each `seg-NN/`** and vendor fonts + gsap.

⚠ Clips create stacking contexts that hide captions. Derive segment durations from
**frame indices**, never from subtracted seconds.

```bash
python scripts/build-captions.py assets/transcript-tight.json \
    --out seg-01-x/captions.html --emphasis WORD,WORD
```

## 8 · Per segment
```bash
npx --yes hyperframes lint          # 0 errors
bash scripts/check-persa.sh .       # MUST exit 0
npx --yes hyperframes snapshot --at <times>
#   -> read the contact sheet and fix before rendering
npx --yes hyperframes render -q high -f 30
```

## 9 · Concat
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh
```
⚠ Chapter timestamps come from **real rendered durations** — never hand-counted,
never copied from `PLAN.md`.

⚠ Per-chapter renders accumulate ~38ms AAC priming per join. **Relay the source
audio after the concat** rather than letting the joins drift.

## 10 · Finish the look
```bash
bash scripts/persa-grade.sh out/visual.mp4 out/visual-look.mp4 soft
python scripts/grade-check.py out/visual-look.mp4
```

## 11 · Sound
SFX pass, then the ducked bed. `sound-design.md`.

## 12 · Deliver
`out/final.mp4` · `out/chapters.txt` · `out/<name>.srt`.

Report rendered + scored, open it for review, **stop there**. Nothing publishes,
posts or uploads without explicit approval — these are monetized client-facing
videos and an unapproved post is not retractable.
