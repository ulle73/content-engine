# SETUP — motion-studio i content-engine (Windows 11)

Ersätter originalets `INSTALL-PROMPT.md` (macOS, `~/.claude/skills`, `curl | sh`, 11 GB nedladdning).

- Skillen: `.claude/skills/motion-studio/` (`SKILL` i dokumenten). Projekt: `work/motion-studio/<namn>/`.
- Python med numpy: `bash SKILL/scripts/py …` väljer `library/.venv` (signerad Python 3.12).
- Kontroll (installerar inget): `bash SKILL/scripts/setup.sh` och `bash SKILL/scripts/setup.sh --music`.
- Självtest: `bash SKILL/scripts/selftest.sh` → `work/motion-studio/_selftest/renders/selftest.mp4`.

## Musik (nivå 2–3)

ACE-Step 1.5 finns redan i `C:\Users\rydqv\video-tools\ACE-Step-1.5` (samma revision som exemplen,
uv-venv på signerad Python 3.12, CPU, ~3.8x realtid utan LM). Skripten hittar den automatiskt
(`MOTION_STUDIO_ACESTEP=<sökväg>` för att peka om). Ladda **aldrig** ner en kopia till.

```bash
bash SKILL/scripts/music/run_music.sh work/motion-studio/<namn>      # tar i song.json -> audio/takes/seed*.wav
# snabb fristående instrumental:
cd /c/Users/rydqv/video-tools/ACE-Step-1.5 && uv run --no-sync python gen_track.py 30 out.wav "warm cinematic piano, hopeful" 100
```

- `gen_song.py` kör utan LM på CPU (`"lm": "none"`); `"lm": "acestep-5Hz-lm-1.7B"` går men är mycket långsammare.
  0.6B-LM:en finns inte i installationen.
- Låset ligger i `work/motion-studio/.acestep.lock`. Diskspärren (10 GB fritt) mäts på ACE-mappens disk.
- `stems.sh` (lyrics-timing) kräver demucs i ACE-miljön — inte installerat. Fråga användaren innan:
  `cd C:\Users\rydqv\video-tools\ACE-Step-1.5 && uv pip install demucs`. Utan demucs: tajma klipp från beat-griden.
- `acestep-mps-bf16.patch` är för Apple-GPU:er och appliceras inte här (rör aldrig den delade installationen).
- Öppna en färdig video med `start <fil>.mp4` (inte `open`).
