#!/bin/sh
# usage: tools/render.sh <9x16|4x5|1x1> <draft|looks|delivery> <out.mp4>
# Renders picture with HyperFrames, then muxes the mastered soundtrack (-14 LUFS, <= -1 dBTP) ourselves:
# the renderer re-measures true peak on its own mix and pulled the level down 4 dB in draft 1.
cd "$(dirname "$0")/.." || exit 1
(cd film && ../../../library/.venv/Scripts/python.exe build_index.py >/dev/null)
case "$1" in 9x16) P=film;; 4x5) P=film-4x5;; 1x1) P=film-1x1;; esac
T0=$(date +%s)
(cd $P && npx hyperframes render --quality "$2" -o ../renders/_pic.mp4 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "rendered in|capture ·|error|Error" )
ffmpeg -v error -y -i renders/_pic.mp4 -i film/assets/soundtrack.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$3"
rm -f renders/_pic.mp4
T1=$(date +%s); echo "total $((T1-T0)) s -> $3"
ffmpeg -hide_banner -i "$3" -af ebur128=peak=true -f null - 2>&1 | grep -A20 Summary | grep -E "I:|Peak:" | tr -s ' '
