# Import: persa-short (skill `persa-short-editing`)

**Källa:** `Downloads/hyperframes-remotion/persa-short-editing.zip` (NextPhase/Jad, ingen licens angiven — endast egen användning).
**Importerad:** 2026-10-08. Skillen ligger komplett i `.claude/skills/persa-short-editing/` (självständig, relativa sökvägar
intakta). Det här kitet innehåller `LIBRARY.json` (54 poster) och denna fil. Förhandsbilder: `library/previews/persa-short.*.jpg`.
Skillnamnet behölls som `persa-short-editing` (NextPhase-kitet har en separat skill `persa`).

## Borttaget / ändrat
- `components/persa-captions/sample/all.png` och `rowA.png`: Claude/Anthropic-märket i panel 6 (titelstacken) pixlat.
  Bilderna är kitets egna demorenderingar (kitets skapare i bild) och behölls i övrigt.
- `scripts/fetch-source.py`: förfalskad macOS-Chrome user-agent borttagen → ärlig beskrivande UA.
- `sfx/` och `bgm/` var redan tomma (kommersiella ljud/musik följde inte med); README-filerna kvar.
- `SETUP.md` omskriven för Windows/content-engine (svenska).

## Windows-anpassningar
- All fil-I/O i Python-skripten explicit UTF-8 (Windows cp1252 kraschade `persa-captions/build.py` på box-tecken).
- Videoprojekt: `work/persa-short/videos/<slug>/`; template-skripten (`build-audio.py`, `verify-sfx.py`, `matte.sh`) hittar
  skillen genom att gå uppåt i stället för en fast `../../.claude/...`.
- `template/matte.sh`: ingen macOS-nvm-PATH / `source ~/.cache/...`; RVM-miljö `work/persa-short/rvm_env` (signerad Python 3.12).
- `camera-decode.py`: LUT-standardsökväg `work/persa-short/luts/` eller `PERSA_LUT` (inte `~/.cache`).
- `check-delivery.py`: `/tmp/hf.png` → systemets temp-mapp. `lay-bed.sh`: `python3` (Store-stubben) → awk.
- `source-scout.py`: `python3` → `sys.executable`. `shoot-page-9x16.py`, `rec-pages.py`: faller tillbaka på installerade Chrome.
- `rvm-matte.py`: `--device cuda` tillagt. `composite.py`: concat-listan med framåtsnedstreck.
- `components/type-roles-demo/tokens.css` saknades → kopierad från `persa-captions/`.
- Dokumentation (SKILL.md, template/README.md, SOURCING.md, cutout-compositing.md) uppdaterad med Windows-kommandon.

## Verifiering
- 0 verifierade. De 13 typbehandlingarna + caption-boken har förhandsbilder beskurna ur kitets egna sample-renderingar
  (granskade), men inget renderades här (budget) — därför `unverified`.
- Inget RVM-, render- eller ljudpass kördes. RVM-miljön (torch) är inte skapad.

## Kända problem / att göra
- Kompositionerna kräver egna `assets/recording.mp4`, `person-alpha.webm`, UI-bild och kvadratiskt märke.
- Ljud saknas. Gratis ersättare från motion-studio (kör i Git Bash från repo-roten):
  ```bash
  library/.venv/Scripts/python.exe -I -c "import sys,wave,numpy as np;sys.path.insert(0,'.claude/skills/motion-studio/scripts/sfx');import sfx_lib as L
  for n,x in {'swell':L.reverse_swell(0.6),'riser':L.riser(3.0),'camera-shutter':L.shutter(),'futuristic-click':L.blip(),'pop':L.ui_pop(),'magic-reveal':L.shimmer(1.5)}.items():
   w=wave.open(f'.claude/skills/persa-short-editing/sfx/{n}.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(L.SR);w.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes());w.close()"
  ```
  Uppdatera sedan `sfx/leading-silence.json` (lead ≈ 0 för alla utom `swell`/`riser` som stiger in).
- `find-cut-line.py` behöver opencv (finns inte i `library/.venv`).
