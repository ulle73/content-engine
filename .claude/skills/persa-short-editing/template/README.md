# template/ — the last shipped persa build (95.8s, 22 beats, no grade)

A real, finished cut — "Google just released new AI voices" — with its media stripped. Copy
the scripts into `work/persa-short/videos/<slug>/` (content-engine) and adapt; do not run them from here. Change `NAME`, `DUR`
and the output filenames (they still say `tp-0925b`).

| file | what it does |
|---|---|
| `NOTES.md` | the cut's log: fact-check, sources, gates, what sampling caught |
| `build.py` | ⭐ the persa build: BEATS table, fact fixes keyed by word onset, the display-type fitters (`emph_size`, `marker_size`, `top_for`), the card HOLE mask, `clipify()`, one-word captions at 1400, the CTA. Writes `index.html` (preview) + `layers/mid` + `layers/fg` |
| `beats.json` | the beat map it builds from |
| `geometry.json` | goes in `assets/`. The card rect, the camera solve per act, head top per beat |
| `matte.sh` | chunked RVM matte → `assets/alpha.mkv` |
| `measure-head.py` | head top per beat off the alpha, through each act's camera solve |
| `composite.py` | lays the transparent layers + his matte onto the UNTOUCHED recording in ffmpeg |
| `cut-film.sh` | cutting spans out of a vendor film, normalised to 30fps CFR |
| `rec-pages.py` | recording a live page on the video clock (Playwright, stepped clock) |
| `sfx-cues.txt` | the thin persa cue sheet: `time  sound  gain` |
| `build-audio.py` | voice + bed + SFX, and the SFX alone onto silence for measuring |
| `verify-sfx.py` | every cue measured on silence against the local voice peak |
| `check-delivery.py` | the 1080p gate: container, sharpness vs source, bitrate |

Pipeline for one video:
```bash
bash matte.sh                          # assets/alpha.mkv
# content-engine (Windows, Git Bash): PY=library/.venv/Scripts/python.exe (absolute path), never python3
$PY measure-head.py                    # head per beat -> geometry.json
$PY build.py                           # index.html + layers/
npx --yes hyperframes check layers/mid && npx --yes hyperframes check layers/fg
npx --yes hyperframes render layers/mid --format mov -o out/mid.mov
npx --yes hyperframes render layers/fg  --format mov -o out/fg.mov
$PY build-audio.py && $PY verify-sfx.py
$PY composite.py out/<slug>-FINAL.mp4 --audio out/<slug>-audio.wav
$PY check-delivery.py
```
Then sample one frame per beat of the FINAL and look at every one.
