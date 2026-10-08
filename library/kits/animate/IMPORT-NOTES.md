# Import: animate (cth9191/animate)

| | |
|---|---|
| Källa | <https://github.com/cth9191/animate> — Claude Code-plugin `animate` v0.4.0, commit `7e5eb56` (2026-10-05) |
| Licens | MIT, Copyright (c) 2026 cth9191 — full text i `NOTICE` här och `LICENSE` i skillmappen |
| Importerad | 2026-10-07/08 |
| Skill | `.claude/skills/animate/` (hela `plugins/animate/skills/animate/` + `LICENSE`, `NOTICE.md`, `setup.ps1`, `tools/pw.mjs`, `.gitignore`) |
| Kit | `library/kits/animate/` — `LIBRARY.json` (35 poster), `NOTICE`, `docs/` (upphovspersonens egna bilder `styles.png`, `storyboard.png` ur repots `docs/`), `.gitignore`; `styles/<namn>/` skapas här när användaren sparar en egen stil |
| Arbetsfiler | `work/animate/` (gitignorerat): `node_modules/` (Playwright), `demos/`, `pieces/`, `references/`, renderingar |
| Förhandsvisningar | `library/previews/animate.*.mp4` / `.jpg` (21 mp4 ≤ 1,9 MB, 540 px breda – history-of-ai 480 px – och 25 jpg; några poster delar fil) |

Inte kopierat: `.claude-plugin/marketplace.json` och `plugins/animate/.claude-plugin/plugin.json` (pluginmanifest – skillen
laddas direkt från `.claude/skills/`), repots README (innehållet finns i SKILL.md). Inget togs bort ur skillen: allt är kod,
dokumentation och egna exempelbilder (`styles/*/sample.png`); ingen uppladdning till tredje part, ingen bot-undanmanöver,
ingen reklam, ingen tredjepartsmedia.

## Anpassningar för content-engine / Windows

- **Playwright lokalt, systemets Chrome.** Upstream kräver `npm i -g playwright && npx playwright install chromium`. Nu laddar
  alla verktyg Playwright via nya `tools/pw.mjs` (skillens egen upplösning → `work/animate/node_modules` → `ANIMATE_PLAYWRIGHT`
  → global) och startar **systemets Chrome** (`C:\Program Files\Google\Chrome\Application\chrome.exe`, Chrome 154) med
  `executablePath`, fallback till Playwrights Chromium. `ANIMATE_CHROME`, `ANIMATE_BROWSER=bundled` styr. Installerat:
  `playwright@1.63.0` i `work/animate` med `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` (ingen nedladdning).
- **`setup.ps1`** (nytt): kontrollerar node/ffmpeg/ffprobe/Chrome och installerar Playwright lokalt; `-Whisper` lägger
  faster-whisper i `library/.venv` (signerade Python 3.12), `-BundledChromium` vid behov. Inget globalt.
- **Sökvägar:** pjäser i `work/animate/pieces/<namn>/`, verktyg körs från repo-roten som
  `node .claude/skills/animate/tools/<verktyg>.mjs`, egna stilar sparas i `library/kits/animate/styles/<namn>/`
  (`build.mjs` och `gallery.mjs` söker där), referensmedia i `work/animate/references/<look>/` (`review.mjs` default).
  Uppdaterat i `SKILL.md`, `intake.md`, `new-style.md`, `styles/README.md` och verktygens usage-texter.
- **Buggfixar:** `review.mjs` gjorde kontaktark för icke-huvudformat (`--format 16:9`) av huvudformatets `frames/` – läser nu
  `frames-<b>x<h>/` (verifierat: 16:9-arket visar 16:9-bilder). `export.mjs` brände narration-captions på `final.mp4` även för
  andra format – använder nu formatets egen fil.
- **Svenska voice-overs:** `voice.mjs --lang sv` (whisper-modellen `small` i stället för `small.en`), ordmatchningen behåller
  å/ä/ö (`\p{L}`), Python från `library/.venv` om den finns (`ANIMATE_PYTHON` överstyr). `voice_words.py` tar `--lang`.
- **Kreativ frihet:** check-ins (story/look/storyboard) är standard men användaren kan hoppa över dem (”kör direkt”); stilregler,
  frame-checklistor och craft-regler är förinställningar/tips, aldrig spärrar (nytt avsnitt ”In content-engine” i SKILL.md).
- **Kostnad:** ElevenLabs-rösten märkt **betald** i SKILL.md och intake.md; gratisvägen (egen inspelning / ingen röst) först.
- CRLF → LF i alla textfiler (git autocrlf hade konverterat klonen).

Saker som redan fungerade på Windows utan ändring: `spawnSync('ffmpeg')` (ffmpeg.exe på PATH), drawtext med
`C\:/Windows/Fonts/consolab.ttf` i review, libass-captions med Consolas, scratch-röst via PowerShell/System.Speech, och
typsnittsfallbacks (Ink Free, Segoe Print, Segoe UI, Cambria/Consolas – renderingarna matchar upphovspersonens sample.png,
som uppenbarligen gjordes på Windows).

## Verifiering (renderat med skillens egna verktyg och granskat med Read)

Maskin: Windows 11, Node 24.19, ffmpeg 9.0.2, Chrome 154, 16 trådar. Export = build + bildrendering (4 parallella sidor) +
ljud + stems + x264-mux (CRF 14 slow) + share-encode.

| pjäs | bilder | bildrendering | export totalt | review | resultat |
|---|---|---|---|---|---|
| cut-paper demo | 192 | 10,3 s | 24 s | 4 s | PASS (morph, arc 2/2, text, −14,5 LUFS) |
| crosshatch demo | 144 | 7,7 s | 17 s | 3 s | PASS; högsta ljudet i akt 1 (demots score) |
| riso demo | 144 | 15,7 s | 35 s | 11 s | PASS; 1 WARN text i UI-zonen |
| sketchbook demo | 144 | 10,9 s | 22 s | 3 s | PASS |
| math demo | 144 | 2,1 s | 9 s | 2 s | PASS; 2 WARN text i UI-zonen under morfen |
| pixel demo | 144 | 5,8 s | 13 s | 2 s | bild/text PASS; story arc FAIL (demots score, −16,4 LUFS) |
| isometric demo | 144 | 2,1 s | 9 s | 2 s | PASS; högsta ljudet i akt 1 |
| isometric demo-dark | 144 | 1,6 s | 11 s | 3 s | PASS |
| templates/piece i 9:16+1:1+4:5+16:9 | 4×192 | 6,9–9,9 s/format | 72 s | 3 s/format | PASS i alla format |
| templates/beat-cut | 144 | 7,7 s | 18 s | 8 s | 8/8 klipp på griden, arc 4/4 |
| examples/history-of-ai (60 s) | 1440 | 94,9 s | 253 s | 53 s | 13 morfer, arc 4/4, ankare 100 %, text PASS, −15,0 LUFS |
| math demo `--blur 4` | 144 | 13,8 s | 19 s | 2 s | fungerar (4 delbilder syns som trappsteg i mycket snabba kanter) |
| product-test (capture + drawAsset + springs + push) | 192 | 12,9 s | 26 s | 4 s | PASS, deterministic true |
| music-test (egen låt + beats.mjs) | 192 | 10,8 s | 24 s | 4 s | låten mixad, morf på låtens grid |
| voice-test (scratch-röst) | 192 | 9,0 s | 21 s | 3 s | röst + duckning, −15,0 LUFS |

Även körda: `gallery.mjs`, `storyboard.mjs` (history-of-ai 15 paneler 1,2 s), `still.mjs`, `tile.mjs` (deterministic true),
`textcheck.mjs`, `framehash.mjs` (5/5 identiska), `capture.mjs` (lokal `file://`-testsida), `measure/refs.mjs` och
`compare.mjs` (isometric-samplet som ”referens”), `beats.mjs`, `voice.mjs --scratch [--lang sv]`, `setup.ps1`.
Contact sheets/mobilark (`review/phone.jpg`, `shotNN-sheet.jpg`) tittade på för alla pjäser ovan.

**LIBRARY.json: 35 poster – 26 verified, 9 unverified, 0 broken.** Unverified: berättelseformaten F1, F3, F4, F5, F6, F7, F8
(ingen pjäs i formatet renderad här; F5:s ankarkontroll är dock körd i history-of-ai), story-grammar-prompten (ren text) och
ElevenLabs-rösten (betald, ej testad). Flerformat är renderat för startmallen (klippt papper); stilarnas kit ritar med W/H och
klarar alla format, men deras demos är skrivna för 9:16 – en annan stil i 16:9 kräver det formatmedvetna huvudet ur
`templates/piece/src/head.html` och LX/LY-layout i scenerna.

## Kända problem / att veta

- **Claude-liknande figurer och varumärken.** Hjälten i crosshatch och sketchbook är en terrakottaboll (`#d97757`) med vit
  asterisk, gnistan blir ”Claudes asterisk” i history-of-ai:s 2025-era, crosshatch-demot visar verktygsbubblor (`Read(notes.md)`)
  och isometric-demot `$ claude`; history-of-ai nämner ChatGPT, Claude Code, Deep Blue, AlphaGo. Allt är procedurell kod under
  MIT (inga logofiler), men byt hjälte/texter innan något publiceras kommersiellt (intake fråga 5 har ”eget figur / ingen hjälte”).
- **Demos tonsättning:** pixel (story arc FAIL), crosshatch och isometric (högsta ljudet utanför payoff-akten) – upstream-innehåll,
  inte Windows. Ingen har lyssnat; ljudet är bara mätt.
- **beats.mjs** kan låsa fasen på offbeats när hi-hats dominerar spektralflödet (hände med ett första syntetiskt testspår) och
  tempot blev 126,8 i st. f. 128 utan `--bpm`. Ange `--bpm` när tempot är känt och kontrollera gridden.
- **faster-whisper** är inte installerat (`setup.ps1 -Whisper`); utan den uppskattas ordtider ur bokstäverna. Startmallens huvud
  saknar `VL()`/`VW()` – ordsynkade klipp kräver att huvudet skrivs enligt SKILL.md → Voice-over.
- `measure/shotlog.py` kräver numpy (finns i `library/.venv`), inte testad mot en riktig referensvideo.
- `--blur 4` ger synliga trappsteg vid mycket snabba kanter; använd `--blur 8` vid behov.
- Systemets Chrome uppdateras automatiskt; sätt `ANIMATE_BROWSER=bundled` (efter `setup.ps1 -BundledChromium`) om en
  framtida Chrome-version skulle ändra rendering eller inte fungera med Playwright 1.63.
- WebGL/GPU-vägen (`TIMELINE.gpu`, `--gpu`) finns i verktygen men ingen stil använder den; inte testad.

## Köra

```powershell
powershell -ExecutionPolicy Bypass -File .claude/skills/animate/setup.ps1
node .claude/skills/animate/tools/gallery.mjs work/animate/styles.png
cp -r .claude/skills/animate/styles/riso/demo work/animate/pieces/min-pjas   # eller templates/piece
node .claude/skills/animate/tools/build.mjs work/animate/pieces/min-pjas
node .claude/skills/animate/tools/export.mjs work/animate/pieces/min-pjas --share
node .claude/skills/animate/tools/review.mjs work/animate/pieces/min-pjas
```

Eller i Claude Code: `/animate en 30 s förklarare om … i riso-stil, 9:16`.
