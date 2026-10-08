# live-carousel: importanteckningar

**Källa:** `Downloads\hyperframes-remotion\live-carousel-skill\live-carousel\` (Claude Code-skill "live-carousel",
HyperFrames + GSAP + numpy + ffmpeg). Ingen kodlicens angiven → endast egen användning. Typsnitt (Anybody, Fraunces,
JetBrains Mono, Anton) SIL OFL 1.1, licenstexter ligger bredvid typsnitten. Importerad 2026-10-07/08.

## Var allt ligger

| Vad | Var |
|---|---|
| Skillen (SKILL.md, references, scripts, templates, typsnitt) – enda källan | `.claude/skills/live-carousel/` |
| Privat venv (signerad Python 3.12 + numpy 2.5 + opencv 5.0, gitignorerad via `.venv/`) | `.claude/skills/live-carousel/.venv/` |
| Index | `library/kits/live-carousel/LIBRARY.json` (51 poster) |
| Exempel: photo-läge golfdemo (design-HTML, källbilder, cues) | `library/kits/live-carousel/examples/golf-photo-demo/` |
| Projekt/utdata | `work/live-carousel/<slug>/` (gitignorerat) |
| Förhandsvisningar | `library/previews/live-carousel.*.(mp4|jpg)` |

Kitet är en enda skill, så mallar och scripts ligger kvar i skillmappen (ingen dubblering i `library/kits/`).
LIBRARY.json-posternas `path` pekar dit.

## Borttaget
- `scripts/setup.sh` (bash/macOS, `brew install`, `chmod`) → ersatt av `scripts/setup.ps1`.
- `INSTALL-PROMPT.md` (installerar till `~/.claude/skills`, `~/live-carousels`) och `README.md` (Skool-nedladdning, installinstruktioner).
- Inget uppladdnings-, bot- eller reklaminnehåll fanns. Inga ljudfiler medföljde (ljud syntas; media-use-SFX-paketet
  i `~/.claude/skills/media-use/audio/assets/sfx` används om det finns, Pixabay-licens).

## Windows-anpassningar
- `scripts/setup.ps1`: kollar Node 22+, ffmpeg/ffprobe, HyperFrames CLI + headless Chrome, skapar venv med
  `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (inte uv – Smart App Control) och installerar numpy/opencv. Körtid 19 s.
- `scripts/py.cmd` (ny) + `scripts/py` (Git Bash) väljer venv:en och sätter `PYTHONUTF8=1`.
- All filläsning/skrivning i `new_carousel.py`, `render_all.py`, `build.py`, `prep_photo.py`, `make_audio.py` är UTF-8
  (mallarna innehåller `·`, `—`, `●` som kraschar med cp1252); JSON läses som `utf-8-sig` (PowerShell 5.1 skriver BOM).
- `npx` körs via `shutil.which("npx")` (npx.cmd). HyperFrames är den redan installerade `npx hyperframes` (0.8.140)
  i stället för pinnade `hyperframes@0.8.121`; pinna med env `LIVE_CAROUSEL_HF=hyperframes@<version>`.
- `prep_photo.py`: imread/imwrite via `np.fromfile`/`imencode` (klarar å/ä/ö i sökvägar).
- Ett bart projektnamn (`demo`) → `work/live-carousel/demo`; `render_all.py --open` öppnar preview.html (`os.startfile`),
  och skriver rendertider.
- SKILL.md och references skrivna om till repo-relativa sökvägar.

## Buggfixar under verifieringen
- **Ljud:** HyperFrames 0.8.140 avbryter renderingen när AAC true peak > −1 dBTP ("audioPadTrim"). Kitets mixar toppade
  på 0.89/0.95 (AAC lägger till upp till 1.8 dB överskjut). `lc_audio.PEAK = 0.6` (~−4.4 dBFS) i `master()`,
  `match_loudness()` (nu −17 dB RMS) och ett tak i `write_wav()`.
- **prep_photo-rubrikdetektion:** mättad natur som rör vid text (fairway, solbelyst lövverk) togs som "accent"-penselord
  och blev en jätterubrik. Nu ignoreras accentblobbar > 60 % bredd / > 35 % höjd, ny flagga `--no-accent`, och stora
  rubrikord som delas av ordmellanrum grupperas till samma rubrik.

## Verifiering (renderat och tittat på)
- Motion-demo (`work/live-carousel/demo`, cobalt): build + `hyperframes check` OK på alla 4; rendertid 22/32/33/31 s
  (totalt 125 s, 2 workers, AMD Ryzen AI 7 350). Contact sheet, sömbilder och impact-frames granskade.
- Photo-demo (`work/live-carousel/golf-photo`): prep 19 s, rendertid 25/25/22/22 s (153 s). Frame 0 = original,
  extrusion, shine, flare/ringar/gnistor, kamera-push, motes och sömlös loop granskade.
- 33 av 51 poster `verified`, 18 `unverified`, 0 `broken`.

## Kända problem / ej verifierat
- Teman tomato/forest/noir är inte renderade (bara cobalt). Byt med `--theme`.
- PH.lift, brush, pills, counter, cursor, echo och `--cutout`-parallax är inte körda (kräver slide-specifik kod;
  cutout laddar ner ~170 MB modell). Light leak kördes men syns för svagt i stillbilder för att bekräftas.
- Rubrikdetektionen kan fortfarande missa på mörka foton med ljus lövverk (golfdemons slide 04): sätt `extrude: false`
  eller rätta `assets/NN/geo.json`. Falska "textlinjer" i träd kan få glansvep – titta alltid på `prep/NN_maskvis.jpg`.
- Linjalens keyframe-romber nollställs vid loopen tillsammans med playheaden (avsiktlig "tidslinje börjar om").
- GSAP hämtas från jsDelivr vid render (HyperFrames inlinar den) – kräver nät första gången.
- Receptposterna hook-contradiction, number-slam, split-screen, before-after-wipe och cta-save är bara beskrivningar.
