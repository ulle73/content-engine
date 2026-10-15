#!/usr/bin/env bash
# Bygger filmen från en kopia i work/<namn>/ (aldrig i library/):
#   cp -r library/templates/golfkuponger-chefen-betalar work/<namn> && cd work/<namn> && ./make.sh
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv/Scripts/python.exe; [ -x "$PY" ] || PY=../../.venv/bin/python
OUTRO=../../edit-renderer/outros/golfkuponger/spotlight-9x16.mp4
mkdir -p out
"$PY" -I fetch_assets.py
PAGE=chef-film.html node render.mjs video out/bild-9x16.mp4
PYTHONIOENCODING=utf-8 "$PY" -I audio_chef.py
ffmpeg -v error -y -i out/bild-9x16.mp4 -i out/mix.wav -i "$OUTRO" -filter_complex \
  "[1:a]aresample=48000,aformat=channel_layouts=stereo[a0];[2:a]aresample=48000,aformat=channel_layouts=stereo[a1];[0:v]fps=30,format=yuv420p[v0];[2:v]fps=30,format=yuv420p,setsar=1[v1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart out/gk-chefen-betalar-9x16.mp4
echo "klar: out/gk-chefen-betalar-9x16.mp4"
