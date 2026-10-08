# Import: motion-studio

**Källa:** `Downloads/hyperframes-remotion/motion-studio-skill/motion-studio/` (ingen licens för skillen angiven — endast egen
användning; tredjepart enligt `LICENSES.md`). **Importerad:** 2026-10-08. Skillen ligger komplett i `.claude/skills/motion-studio/`.
Kitet: `LIBRARY.json` (79 poster). Förhandsbilder: `library/previews/motion-studio.sound.*.jpg`.

## Borttaget / ändrat
- `INSTALL-PROMPT.md` (macOS, global install i `~/.claude/skills`, `~/motion-studio-tools`) borttagen → `SETUP.md` (svenska, Windows).
- `scripts/setup.sh` omskriven till ren kontroll: ingen `curl … | sh` (uv), ingen klon/11 GB-nedladdning av ACE-Step, ingen
  `git apply` av Apple-patchen på den delade installationen, ingen global `npx hyperframes skills`, ingen numpy-install.
  `--music-test` borttagen. `acestep-mps-bf16.patch` ligger kvar som referens men används inte.
- Exempelprompterna nämner "Claude" som ordmärke i text — behållna (ingen logotypfil ingår).

## Windows-anpassningar
- **Musik återanvänder `C:\Users\rydqv\video-tools\ACE-Step-1.5`** (samma ACE-revision ca1e85f som exemplen). `run_music.sh` och
  `stems.sh` hittar den automatiskt (eller `MOTION_STUDIO_ACESTEP`), kör `uv run --no-sync`.
- `gen_song.py`: LM av på CPU (`"lm": "none"`, thinking off — som installationens `gen_track.py`); vald LM som saknas
  (0.6B finns inte) faller tillbaka; `ACESTEP_DEVICE` kan sättas.
- `run_music.sh`: låset i `work/motion-studio/.acestep.lock` (inte hemkatalogen); diskspärren mäts på ACE-disken; Git Bash
  saknar `ps -o` → `kill -0` för inaktuella lås.
- `scripts/py` använder `library/.venv` (signerad 3.12, numpy) och aldrig Store-stubben `python3`.
- `selftest.sh` skriver till `work/motion-studio/_selftest`. Projekt: `work/motion-studio/<namn>/`.
- `contact_sheet.sh`: typsnittssökvägen escapad för native ffmpeg (`C\:/Windows/Fonts/arial.ttf`).
- All JSON/MD/JS-I/O i Python explicit UTF-8 (svenska lyrics och etiketter).
- SKILL.md / music.md / critique-loop.md / README.md: Windows-sökvägar, `start` i stället för `open`.

## Verifiering
- `bash .claude/skills/motion-studio/scripts/setup.sh --music` → "All set" (demucs saknas, 0.6B-LM saknas).
- **19 ljud verifierade:** alla 18 effekter i `sfx_lib.py` + rumston syntetiserade med `library/.venv` numpy, längd/topp mätt
  (t.ex. whoosh 0,60 s −1,9 dBFS, boom 8,31 s −3,2 dBFS, riser 4,0 s −2,5 dBFS), vågform+spektrum renderad och granskad.
  WAV-filerna ligger i `work/motion-studio/sfx-preview/`.
- HyperFrames-självtestet och musikgenereringen kördes **inte** (budget) — `selftest`, `run-music` m.fl. är `unverified`.
- Art directions, övergångar och showreel-tekniker är bara beskrivningar i kitet (ingen kod) → `unverified`.

## Kända problem
- `stems.sh` (lyric-timing för nivå 2) kräver demucs i ACE-miljön: `cd C:\Users\rydqv\video-tools\ACE-Step-1.5 && uv pip install demucs`
  — fråga användaren först (ändrar den delade miljön).
- CPU-generering: ~3,8x realtid; en 40 s tagning ≈ 2,5 min + modelladdning; 4 tagningar per runda ≈ 12+ min.
