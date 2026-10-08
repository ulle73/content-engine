#!/usr/bin/env bash
# motion-studio setup CHECK for content-engine (Windows 11, Git Bash). Safe to re-run. Installs nothing.
#
#   setup.sh                          core: Node 22+, ffmpeg, Python + numpy (library/.venv), HyperFrames CLI
#   setup.sh --music [--acestep-dir <path>]   + the local music studio: the EXISTING ACE-Step 1.5 install
#
# Rewritten at import (see library/kits/motion-studio/IMPORT-NOTES.md): the original installed uv with
# `curl … | sh`, cloned ACE-Step and downloaded ~11 GB of models into ~/motion-studio-tools, patched it,
# and installed the HyperFrames skills globally. Here ACE-Step is reused from
# C:\Users\rydqv\video-tools\ACE-Step-1.5 and every missing piece is only REPORTED with the command to run.
set -u
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"
MUSIC=0
ACE_DIR="${MOTION_STUDIO_ACESTEP:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --music) MUSIC=1 ;;
    --acestep-dir) ACE_DIR="$2"; shift ;;
  esac
  shift
done
problems=0
ok()   { printf '  ok  %s\n' "$1"; }
bad()  { printf '  !!  %s\n' "$1"; problems=$((problems + 1)); }
note() { printf '      %s\n' "$1"; }

echo "motion-studio setup check  ($SKILL_DIR)"
if command -v node >/dev/null 2>&1; then
  major="$(node -p 'process.versions.node.split(".")[0]')"
  [ "$major" -ge 22 ] && ok "Node.js $(node -v)" || bad "Node.js $(node -v) is too old (need 22+)"
else bad "Node.js not found"; note "winget install OpenJS.NodeJS.LTS"; fi
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then ok "ffmpeg"
else bad "ffmpeg not found"; note "winget install Gyan.FFmpeg"; fi
if "$SKILL_DIR/scripts/py" -c 'import numpy' >/dev/null 2>&1; then ok "Python with numpy ($("$SKILL_DIR/scripts/py" -c 'import sys; print(sys.executable)'))"
else bad "no Python with numpy"; note "\"\$LOCALAPPDATA/Programs/Python/Python312/python.exe\" -m venv library/.venv && library/.venv/Scripts/python.exe -m pip install numpy"; fi
if npx --yes hyperframes --version >/dev/null 2>&1; then ok "HyperFrames CLI $(npx --yes hyperframes --version 2>/dev/null | tail -1)"
else bad "HyperFrames CLI not runnable through npx"; fi
if [ -f "$HOME/.claude/skills/hyperframes/SKILL.md" ] || [ -f "$HOME/.agents/skills/hyperframes/SKILL.md" ]; then ok "HyperFrames skills"
else note "HyperFrames skills not found globally (optional; ask before running: npx hyperframes skills)"; fi

if [ "$MUSIC" = 1 ]; then
  echo; echo "music studio (existing ACE-Step 1.5, CPU)"
  [ -z "$ACE_DIR" ] && [ -f "$SKILL_DIR/.acestep" ] && ACE_DIR="$(cat "$SKILL_DIR/.acestep")"
  [ -z "$ACE_DIR" ] && ACE_DIR="/c/Users/rydqv/video-tools/ACE-Step-1.5"
  if [ -f "$ACE_DIR/pyproject.toml" ]; then
    ok "ACE-Step checkout: $ACE_DIR"
    command -v uv >/dev/null 2>&1 && ok "uv $(uv --version | awk '{print $2}')" || bad "uv not found (winget install astral-sh.uv)"
    for m in acestep-v15-turbo vae Qwen3-Embedding-0.6B; do
      [ -d "$ACE_DIR/checkpoints/$m" ] && ok "checkpoint $m" || bad "checkpoint $m missing"
    done
    for m in acestep-5Hz-lm-0.6B acestep-5Hz-lm-1.7B; do
      [ -d "$ACE_DIR/checkpoints/$m" ] && ok "LM $m" || note "LM $m not downloaded (fine: gen_song.py runs without the LM on CPU)"
    done
    if (cd "$ACE_DIR" && uv run --no-sync python -c "import demucs" >/dev/null 2>&1); then ok "demucs"
    else note "demucs missing (needed by stems.sh for lyric videos). With the user's OK: cd \"$ACE_DIR\" && uv pip install demucs"; fi
  else
    bad "ACE-Step not found at $ACE_DIR"; note "pass --acestep-dir <path> or set MOTION_STUDIO_ACESTEP"
  fi
fi
echo
[ "$problems" -eq 0 ] && echo "All set." || { echo "$problems thing(s) to fix above."; exit 1; }
