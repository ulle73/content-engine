#!/usr/bin/env bash
# Bygger båda filmerna från en kopia i work/<namn>/ (aldrig i library/):
#   cp -r library/templates/golfkuponger-arsskifte work/<namn> && cd work/<namn> && ./make.sh [v1|spola|alla]
set -euo pipefail
cd "$(dirname "$0")"
PY=../../.venv/Scripts/python.exe; [ -x "$PY" ] || PY=../../.venv/bin/python
OUTRO=../../edit-renderer/outros/golfkuponger/spotlight-9x16.mp4
WHAT=${1:-alla}

mkdir -p out
"$PY" -I fetch_assets.py
assemble() { # bild ljud ut
  ffmpeg -v error -y -i "$1" -i "$2" -i "$OUTRO" -filter_complex \
    "[1:a]aresample=48000,aformat=channel_layouts=stereo[a0];[2:a]aresample=48000,aformat=channel_layouts=stereo[a1];[0:v]fps=30,format=yuv420p[v0];[2:v]fps=30,format=yuv420p,setsar=1[v1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart "$3"
  echo "klar: $3"
}
if [ "$WHAT" = v1 ] || [ "$WHAT" = alla ]; then
  node render.mjs video out/bild-9x16.mp4
  PYTHONIOENCODING=utf-8 "$PY" -I audio.py
  assemble out/bild-9x16.mp4 out/mix.wav out/gk-arsskifte-9x16.mp4
fi
if [ "$WHAT" = spola ] || [ "$WHAT" = alla ]; then
  PAGE=scene2.html node render.mjs video out/bild2-9x16.mp4
  PYTHONIOENCODING=utf-8 "$PY" -I audio2.py
  assemble out/bild2-9x16.mp4 out/mix2.wav out/gk-arsskifte-spola-9x16.mp4
fi
