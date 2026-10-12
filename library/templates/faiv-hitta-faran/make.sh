#!/usr/bin/env bash
# Hela kedjan: (hämta Mixkit-ljud) -> bild -> ljud (effekter + musik, loudnorm -14 LUFS) -> out/faiv-hitta-faran-9x16.mp4
# Körs i en kopia under work/, inte i library/ (se README.md).
# Effekter och musik ligger också separat (out/*-sfx.wav, out/*-musik.wav) så musiken kan bytas.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$PWD; while [ ! -f "$ROOT/manage.py" ] && [ "$ROOT" != / ]; do ROOT=$(dirname "$ROOT"); done
PY="$ROOT/.venv/Scripts/python.exe"
mkdir -p build out
$PY -I fetch_assets.py
[ -f build/dark.png ] || $PY -I prep.py
[ "${SKIP_VIDEO:-}" ] || $PY -I render.py
$PY -I audio.py
cp build/sfx.wav out/faiv-hitta-faran-sfx.wav
cp build/music.wav out/faiv-hitta-faran-musik.wav
# två-pass loudnorm: hela mixen (effekter + musik) lika mycket upp till -14 LUFS, balansen orörd
J=$(ffmpeg -hide_banner -nostats -i build/mix.wav -af loudnorm=I=-14:TP=-1.0:LRA=20:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
v() { echo "$J" | grep "\"$1\"" | grep -o -- '-\?[0-9.]*' | head -1; }
ffmpeg -y -loglevel error -i out/video_noaudio.mp4 -i build/mix.wav   -filter:a "loudnorm=I=-14:TP=-1.0:LRA=20:measured_I=$(v input_i):measured_TP=$(v input_tp):measured_LRA=$(v input_lra):measured_thresh=$(v input_thresh):offset=$(v target_offset):linear=true"   -ar 48000 -c:v libx264 -preset slow -crf 18 -tune grain -pix_fmt yuv420p -movflags +faststart   -c:a aac -b:a 256k -shortest out/faiv-hitta-faran-9x16.mp4
ffmpeg -hide_banner -nostats -i out/faiv-hitta-faran-9x16.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E " I:|Peak:" | tail -2
