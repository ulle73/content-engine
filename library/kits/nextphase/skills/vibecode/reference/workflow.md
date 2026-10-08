# Workflow

Prefix **every** bash step with:

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
```

node/npx come from nvm; `ffmpeg`, `ffprobe` and `yt-dlp` live in `~/.local/bin`.
Every "command not found" in this workflow is this.

---

### 0 · Ask which style
`vibecode` · `persa` · `nextphase` · `motiongraphics`. Never assume, never infer
it from the footage. Record the answer at the top of `PLAN.md`.

Locate `work/nextphase/videos/<name>/`, `VIDEO.md`, `assets/recording.mp4`.

### 1 · Transcribe
Chunk anything over ~90s — Parakeet silently drops audio on long files, and it
drops other-language spans entirely. **Gap-check minute by minute** against the
file duration; checking only the ends will not catch a dropped middle chunk.

### 2 · Tighten
```bash
python ../../.claude/skills/nextphase-long-editing/scripts/tighten-cuts.py …
```
After this, **`assets/transcript-tight.json` is the only timing source.** Timing
graphics against the original transcript shows up as "the graphics are all
slightly early", never as an error.

Frame-align segment boundaries with `silencedetect` and whole-frame cut times —
Parakeet reports fake 0.000s sentence gaps.

### 3 · Build the ground plate
```bash
python scripts/make-paper.py ground --out assets/ground.png
python scripts/make-paper.py edges  --out assets/edges.json --count 24
```
`ground` renders the halftone plate once as a PNG (cheaper and steadier than
re-rasterising the dot grid every frame). `edges` writes deterministic torn-edge
polygons so no two paper cards share a silhouette.

**No colour grade.** Unlike persa, vibecode does not touch the footage — the
plate is flat, the head is a cut-out card on top of it. If the recording is
badly lit, fix exposure, nothing more.

### 4 · Matte the head
```bash
source library/.venv/Scripts/activate
python library/kits/nextphase/skills/nextphase-long-editing/scripts/rvm-matte.py \
       --src assets/recording-tight.mp4 --out assets/matte --frames <n>
```
Needed for Scene 7 and any beat where the head sits on the ground without a
card. Scenes 1–6 use the footage in a `.vc-head` card and do not need a matte.

### 5 · `PLAN.md` — get a "go" before authoring
Scenes per beat, **the actual on-screen copy**, the media list, the chapter
grounds (cobalt/cream), the re-hooks. This is where a factual error gets caught
cheaply.

### 6 · Source real media
≥1 real resource per 20s, minimum 8. Verify facts while sourcing — caption live
numbers, not stale ones. Flag debunked stats, dead products and any third-party
clip whose rights are unclear **before** it reaches a render.

Check every screenshot actually rendered content. Re-encode every clip to 30fps
CFR and verify with `ffprobe`.

### 7 · Author
One composition per chapter in `seg-NN-<name>/`.

- **The segment folder is its own project root.** HyperFrames rejects
  `../assets/` — symlink assets into each `seg-NN/`, and vendor the fonts and
  gsap.
- Root element carries **`.vc-frame`** (plus `.vc-cream` / `.vc-dark`).
- Import `assets/tokens.css`. Never hardcode a colour or font. Never mix in
  another style's tokens.
- Derive segment durations from **frame indices**, never subtracted seconds.
- Clips create stacking contexts that hide captions — keep `.vc-caption` out of
  any element that carries a `clip` or `clip-path`.

### 8 · Per segment
```bash
npx hyperframes lint seg-NN-<name>            # 0 errors
bash scripts/check-vibecode.sh work/nextphase/videos/<name>  # MUST exit 0
npx hyperframes snapshot seg-NN-<name> --at <times>
#   → read the contact sheet and fix before rendering
npx hyperframes render seg-NN-<name> -q high -f 30
```

### 9 · Concat
```bash
bash library/kits/nextphase/skills/nextphase-long-editing/scripts/concat-segments.sh
```
**Chapter timestamps come from here**, computed from real rendered durations —
never hand-counted, never copied from `PLAN.md`.

Relay the source audio after the concat: per-chapter renders accumulate ~38ms of
AAC priming per join.

### 10 · Sound
SFX pass, then the ducked bed. `reference/sound-design.md`.

### 11 · Deliver
`out/final.mp4` · `out/chapters.txt` · `out/<name>.srt`.

Report rendered + scored, open it for review, **stop there. Nothing publishes,
posts or uploads without explicit approval** — never chain into a publish step
even when the toolchain offers one.

---

## Gotchas that have bitten before

- **Windows-skärmdumpar:** Win+Shift+S lägger bilden i urklipp; be användaren spara den (t.ex. `Bilder\Skärmbilder\…png`) och ge sökvägen, eller använd den inklistrade filen direkt. Kopiera filer med glob om namnet innehåller specialtecken.
- **The browser MCP extension is flaky here.** Use `curl`, Chrome headless and
  `yt-dlp` for sourcing.
- **CSS comments do not nest.** Never write a closing marker inside one of
  `tokens.css`'s header blocks, or the whole sheet silently stops applying.
- **A percentage `font-size` resolves against the parent's font-size.** Size
  type in `cqh` and keep `.vc-frame` on the root.
