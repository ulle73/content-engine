# Workflow

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```
node/npx come from nvm; `ffmpeg`, `ffprobe`, `yt-dlp` live in `~/.local/bin`. Neither is
on the default non-interactive PATH — every "command not found" in this workflow is this.

Per-video work lives **only** in `work/nextphase/videos/<name>/`. The skill never changes as a side
effect of editing a video.

---

## 0 · Ask which style

Before anything else: **`motiongraphics` or `nextphase`?** Never assume. Record the
answer at the top of `PLAN.md`.

Then locate `work/nextphase/videos/<name>/`, read `VIDEO.md`, put the recording at
`assets/recording.mp4` (and the screen capture at `assets/screen.mp4` if there is one).

## 1 · Transcribe, and gap-check

```bash
npx --yes hyperframes transcribe assets/recording.mp4 -e parakeet -o assets/transcript.json
```

**Parakeet silently drops audio.** It has lost 77s of a 164s take with no silence to
show for it, and a 10s non-English span that looked like trailing dead air. Chunk
anything over ~90s, and compare the transcript span against the file duration **minute
by minute** — a dropped chunk in the middle desyncs everything after it, and checking
only the ends will not catch it. Before trimming anything that looks like dead air,
measure it with `volumedetect`.

Fix obvious ASR errors (brand names, the CTA keyword, verbal number slips) while
keeping sync.

## 2 · Tighten — before timing a single graphic

```bash
python ../../.claude/skills/nextphase-long-editing/scripts/tighten-cuts.py \
  --src assets/recording.mp4 --transcript assets/transcript.json \
  --max-gap 0.55 --pad 0.12 --out assets/recording-tight.mp4
```

Writes `recording-tight.mp4`, `assets/transcript-tight.json` (**onsets remapped**) and
`assets/cuts.json`. From this moment **`transcript-tight.json` is the only timing
source.** Timing against the original transcript after a tighten shows up as "the
graphics are all slightly early" — never as an error.

Frame-align every segment boundary: Parakeet reports fake `0.000s` sentence gaps, so
find real cut points with `silencedetect` and round to whole frames.

## 3 · `PLAN.md` — and get a "go"

Record, per beat: **in/out word onsets**, the **scene** (`layouts.md`), the **device**
(`motion-library.md`), the **exact copy that will appear on screen**, the **media** it
needs, and whether it is a **re-hook**. Plus, for the whole video:

- the **style** (answer from step 0)
- the **temperature** — violet (REF-A) or magenta (REF-B); pick one and hold it
- the **caption switch** — `on` (accumulating) or `off`
- the chapter list and the media shopping list

**Show it and get a go before authoring.** On a 15-minute video, building before the
structure is agreed wastes hours — and writing the real copy at plan stage is where a
factual error gets caught cheaply, on a plan line rather than in a render.

## 4 · Source real media

Into `assets/broll/`. **≥1 per 25s of finished video, minimum 10.**

- GitHub OG cards via `curl opengraph.githubassets.com/<anything>/<owner>/<repo>`;
  READMEs via `raw.githubusercontent.com`.
- Site screenshots via **Chrome headless in a 16:9 window** (background it with a
  kill-after-25s safety):
  ```bash
  "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new \
    --disable-gpu --hide-scrollbars --window-size=1600,900 \
    --virtual-time-budget=9000 --screenshot=out.png "URL"
  ```
  **Check every screenshot actually rendered content.** Login-walled and JS-heavy pages
  come back blank and ship as empty panels. Consent modals dim the page — crop above
  them or brighten with `eq=brightness=0.30:contrast=1.35`. Cloudflare walls → find
  another source. The browser MCP extension is flaky here; prefer curl / headless / yt-dlp.
- Clips via `yt-dlp --download-sections`, trimmed to **6–12s**.
- **Normalise every sourced clip to 30fps CFR**, then verify — they come back at
  24/25/50/60fps or VFR and will judder or drift in a 30fps composition:
  ```bash
  ffmpeg -i in.mp4 -r 30 -fps_mode cfr -an -c:v libx264 -crf 21 out.mp4
  ffprobe -show_entries stream=r_frame_rate,avg_frame_rate,nb_frames -of default=nw=1 out.mp4
  ```
- Give any image reused across two beats **its own copy** (dodges the duplicate-media lint).
- **Verify facts while sourcing.** Caption live numbers, not stale ones. Flag debunked
  stats, dead or renamed products, and any third-party clip whose rights are unclear —
  **before** it reaches a render.
- **Windows-skärmdumpar:** Win+Shift+S lägger bilden i urklipp; be användaren spara den (t.ex. `Bilder\Skärmbilder\…png`) och ge sökvägen, eller använd den inklistrade filen direkt. Kopiera filer med glob om namnet innehåller specialtecken.

## 5 · Author per-chapter compositions

`seg-01-<name>/`, `seg-02-<name>/`, … one per chapter — **not one giant `index.html`**.

- **Each segment folder is its own project root.** HyperFrames rejects `../assets/`:
  symlink assets into each `seg-NN/` and vendor fonts + GSAP locally.
- Import `../assets/tokens.css` **through the symlink**. Tokens only, transforms only,
  word-synced to `transcript-tight.json`.
- **Clips create stacking contexts that hide captions.** Keep the caption layer out of
  any `class="clip"` subtree.
- **Derive segment durations from frame indices, never from subtracted seconds.**
- Install catalog blocks with `hyperframes add`, then **retoken them immediately**
  (`catalog-map.md`).

## 6 · Gates, per segment

```bash
npx --yes hyperframes lint                       # 0 errors
bash ../../.claude/skills/motiongraphics/scripts/check-placeholders.sh .   # MUST exit 0
npx --yes hyperframes snapshot --at <times> -o snaps
npx --yes hyperframes render -q high -f 30 -o out/seg-NN.mp4
```

**The placeholder gate is not optional.** The bricks ship with realistic copy so they
render in a browser; it is the easiest thing in this whole pipeline to leave behind,
because it does not *look* wrong at a glance. The script fails on kit strings and, more
seriously, on proper nouns lifted from the reference edits — another creator's name in a
monetized video is not a cosmetic mistake. See **COPY IS DERIVED, NEVER INHERITED** in
`SKILL.md`.

**Read the contact sheet and fix** before rendering — that is the step that catches
blank screenshots, clipped text and elements outside title-safe. Read it for *content*
as well as layout: a panel still labelled with a brick's words is a failed shot even
though nothing errored.

## 7 · Concat + chapters

```bash
bash ../../.claude/skills/nextphase-long-editing/scripts/concat-segments.sh \
  out/final-visual.mp4 out/seg-*.mp4
```
It also writes `out/chapters.txt` from **real rendered durations**. Never hand-count
chapter timestamps and never copy them from `PLAN.md` — plan times are pre-render
estimates and always drift.

**Per-chapter renders accumulate ~38ms of AAC priming per join.** After concat, relay
the source audio onto the joined video rather than letting the segment audio stack, or
the whole video drifts progressively out of sync.

Lock the visual edit here.

## 8 · Sound

Pass A (SFX), then Pass B (the ducked bed) — `sound-design.md`. Gut-check the levels:
SFX present but under the voice, bed under both, no clipping.

## 9 · Deliver

`out/final.mp4` · `out/chapters.txt` · `out/<name>.srt` · a thumbnail frame if asked.

Report **rendered + scored**, open it for review, and stop there.
**Nothing publishes, posts or uploads without explicit approval** — these are monetized
client-facing videos, an unapproved post is not retractable, and it can carry unverified
facts or clip-rights problems. Never chain into a publish step, even when the toolchain
offers one.
