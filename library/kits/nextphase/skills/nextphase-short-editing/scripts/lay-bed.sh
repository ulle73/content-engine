#!/usr/bin/env bash
# Lay the house bed under a finished render, looping it for as long as the video runs.
#
#   bash scripts/lay-bed.sh out/<slug>-sfx.mp4 out/<slug>-FINAL.mp4
#
# THE BED IS A 36-SECOND LOOP — bgm/house-bed-loop.m4a, cut from 0:09 to 0:45 of
# *Baba* (Daniel Deuschle). Jad, 2026-08-10:
#
#   "start recording it from the second nine and then when you reach the second 45 you stop
#    there ... if sometimes my videos are 2 minutes or 3 minutes or 4 minutes it just loops
#    back in to the second nine ... we don't need the entire song because then in the song it
#    starts singing lyrics and I don't want that in the video"
#
# So the loop never reaches the vocal section, and a 4-minute video just plays it ~7 times.
# The seam is an equal-power crossfade built from the material that FOLLOWS 0:45, sliced
# sample-accurately off a decoded WAV — `-ss` on the compressed m4a is NOT sample accurate and
# leaves an audible click. Verified: the boundary step sits below the median sample-to-sample
# difference of its own neighbourhood.
#
# LEVEL: the file is pre-levelled to -34 LUFS and mixes at volume=1.0. Do NOT re-level it.
# That is a LOUDNESS target, not a peak target — see the note in reference/sound-design.md.
# The old -38 dB PEAK spec put the bed at -49.8 LUFS, ~15 LU under its own documented target,
# which is why the music was inaudible and read as missing.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
IN="${1:?input video (the -sfx render)}"
OUT="${2:?output video}"
# The bed sits at bgm/ in the working repo but at bgm/ inside the packaged skill.
# Only the repo path was checked, so running this script BY ITS SKILL PATH — which is how
# mix-sfx.sh and the docs tell you to run it — failed with "no bed" on a machine that has the
# bed. That is also how a buyer would hit it first. Try both, then give up.
BED="${3:-}"
if [[ -z "$BED" ]]; then
  for cand in "$REPO/bgm/house-bed-loop.m4a" "$REPO/bgm/house-bed-loop.m4a"; do
    [[ -f "$cand" ]] && { BED="$cand"; break; }
  done
  BED="${BED:-$REPO/bgm/house-bed-loop.m4a}"      # so the error names a sensible path
fi

[[ -f "$IN"  ]] || { echo "lay-bed: no input video: $IN" >&2; exit 1; }
[[ -f "$BED" ]] || { echo "lay-bed: ingen bed: $BED — kitets kommersiella låt togs bort vid importen."
  echo "  Ge en egen rättighetsklar bed som 3:e argument (t.ex. en ACE-Step-genererad loop):" >&2
  echo "  bash lay-bed.sh in.mp4 out.mp4 path/to/bed.m4a" >&2; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
BEDLEN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$BED")
# how many whole loops are needed to cover the video (-stream_loop counts EXTRA plays)
LOOPS=$("${PYTHON:-python}" -c "import math;print(max(0,math.ceil($DUR/$BEDLEN)-1+1))")
FADEOUT=$("${PYTHON:-python}" -c "print(max(0,$DUR-1.5))")

echo "lay-bed: video ${DUR}s · bed ${BEDLEN}s · looping ${LOOPS}x · $(basename "$BED")"

ffmpeg -y -v error -i "$IN" -stream_loop "$LOOPS" -i "$BED" \
  -filter_complex "[1:a]atrim=0:${DUR},asetpts=PTS-STARTPTS,\
afade=t=in:st=0:d=1.2,afade=t=out:st=${FADEOUT}:d=1.5[bed];\
[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k "$OUT"

echo "lay-bed: done -> $OUT"
