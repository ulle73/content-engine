# SETUP — persa-short-editing i content-engine (Windows 11)

Anpassad vid importen (originalet var skrivet för macOS och `~/.claude/skills`). Se även
`library/kits/persa-short/IMPORT-NOTES.md`.

## 1 · Var allt ligger

```
<repo>/.claude/skills/persa-short-editing/     skillen (laddas automatiskt av Claude Code i repot)
<repo>/work/persa-short/videos/<slug>/          ett videoprojekt per klipp (gitignorerat)
    assets/recording.mp4                        kamerafilen (Rec.709, 1080x1920)
<repo>/work/persa-short/rvm_env/                RVM-miljön (torch) för frilägget
<repo>/work/persa-short/luts/                   DJI D-Log M -> Rec.709-LUT:en (om du filmar i log)
<repo>/library/.venv/                           delad Python (signerad 3.12) med numpy, pillow, playwright
```

Template-skripten hittar skillen genom att gå uppåt tills de hittar `.claude/skills/persa-short-editing`,
så `work/persa-short/videos/<slug>/` fungerar (originalet antog `videos/<slug>/` direkt under repot).

## 2 · Verktyg på maskinen

| verktyg | finns | används till |
|---|---|---|
| Node 24 + `npx hyperframes` | ja | HTML → video, `hyperframes check`, `hyperframes transcribe` |
| ffmpeg / ffprobe 9 | ja (winget) | varje ljud- och videosteg |
| Python | `library/.venv/Scripts/python.exe` (signerad 3.12) | mätskripten (numpy, pillow, playwright finns) |
| opencv-python | **saknas** i library/.venv | `find-cut-line.py`, `rvm-matte.py` — installera i RVM-miljön (nedan) |
| yt-dlp | installera vid behov: `library/.venv/Scripts/python.exe -m pip install yt-dlp` | `fetch-source.py video` |
| Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Playwright faller tillbaka på installerade Chrome (`channel="chrome"`) om Playwrights egen Chromium inte är nedladdad |

Kör Python-skript med `library/.venv/Scripts/python.exe <skript>` — **inte** `python3`
(på Windows är `python3` Microsoft Store-stubben). Bash-skripten (`*.sh`) körs i Git Bash.

## 3 · RVM-miljön (frilägg av personen)

Smart App Control blockerar DLL:er i uv-nedladdade Python-byggen, så miljön görs med den signerade 3.12:an:

```bash
"$LOCALAPPDATA/Programs/Python/Python312/python.exe" -m venv work/persa-short/rvm_env
work/persa-short/rvm_env/Scripts/python.exe -m pip install torch torchvision opencv-python numpy pillow
```

Modellvikterna (~15 MB) hämtas första gången via `torch.hub` (repo `PeterL1n/RobustVideoMatting`)
till `%USERPROFILE%\.cache\torch\hub`. Kör sedan `bash work/persa-short/videos/<slug>/matte.sh`.
`--device cuda` finns om det någon gång finns ett NVIDIA-kort; standard är CPU.

Enklare alternativ utan torch: `npx hyperframes remove-background` (sämre tidsstabilitet än RVM, men
noll installation) — se `reference/cutout-compositing.md`.

**Log-material** (DJI D-Log M): hämta DJI:s egen Rec.709-LUT och lägg den i
`work/persa-short/luts/dji-dlogm-rec709.cube`, eller ange `--lut` / `PERSA_LUT=<sökväg>` till
`scripts/camera-decode.py`.

## 4 · Det DU måste lägga in — ljud och bakgrundsmusik

Ljudpaletten och musikbädden från originalklippen är licensierat tredjepartsmaterial och följer
**inte** med. Mapparna är tomma med flit. Lägg egna licensierade filer med exakt dessa namn
(`.wav` / `.mp3` / `.aif`):

```
sfx/swell            ~0.5 s stigning som landar — VARJE layoutbyte
sfx/riser            en uppbyggnad som toppar på hookens payoff (en gång)
sfx/camera-shutter   ett produktnamn som stämplas, en per stavelse
sfx/futuristic-click ett riktigt UI som gör saken (2–3 per video)
sfx/pop              CTA-chipet
sfx/magic-reveal     valfritt — skimmer på en hero-reveal
bgm/house-bed-loop.m4a   en loop som skarvar rent, förnivåad till ca -34 LUFS
```

**Gratisvägen:** `motion-studio`-skillens `scripts/sfx/sfx_lib.py` syntetiserar `swell`, `riser`,
`shutter`, `pop`, `blip`/`tick` och `shimmer` med numpy (licensfritt, deterministiskt) — se
`library/kits/persa-short/IMPORT-NOTES.md` för ett färdigt kommando. Musikbädd kan göras lokalt med
ACE-Step (`C:\Users\rydqv\video-tools\ACE-Step-1.5`, se motion-studio `SETUP.md`).

Förbjudna i den här stilen, så du behöver dem inte: `ping`, `swoosh`, `confirm`, `beep`.

Mät varje ljuds inledande tystnad efter att du lagt in dem och uppdatera `sfx/leading-silence.json`.

## 5 · Typsnitt

`assets/tokens.css` laddar Anton, Permanent Marker, Silkscreen, Montserrat, Inter, JetBrains Mono och
Fraunces från Google Fonts (alla OFL). Instrument Serif ligger i `assets/fonts/` (OFL).

## 6 · Produktmärken

Produktmärken hämtas per video (riktiga kvadratiska app-ikonen) och ligger i den videons egen mapp.
Inga följer med. Caption-demona refererar `assets/brand/claude-coral.svg` — lägg valfritt kvadratiskt
märke där (eller byt `src`) för att förhandsvisa dem.
