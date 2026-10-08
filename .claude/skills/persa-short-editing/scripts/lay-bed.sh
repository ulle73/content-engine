#!/usr/bin/env bash
# Lay the house bed under a finished render, looping it for as long as the video runs.
#
#   bash scripts/lay-bed.sh out/<slug>-sfx.mp4 out/<slug>-FINAL.mp4
#
# THE BED IS A 36-SECOND LOOP — broll-library/bgm/house-bed-loop.m4a, cut from 0:09 to 0:45 of
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
# The bed sits at broll-library/bgm/ in the working repo but at bgm/ inside the packaged skill.
# Only the repo path was checked, so running this script BY ITS SKILL PATH — which is how
# mix-sfx.sh and the docs tell you to run it — failed with "no bed" on a machine that has the
# bed. That is also how a buyer would hit it first. Try both, then give up.
BED="${3:-}"
if [[ -z "$BED" ]]; then
  for cand in "$REPO/broll-library/bgm/house-bed-loop.m4a" "$REPO/bgm/house-bed-loop.m4a"; do
    [[ -f "$cand" ]] && { BED="$cand"; break; }
  done
  BED="${BED:-$REPO/bgm/house-bed-loop.m4a}"      # so the error names a sensible path
fi

[[ -f "$IN"  ]] || { echo "lay-bed: no input video: $IN" >&2; exit 1; }
[[ -f "$BED" ]] || { echo "lay-bed: no bed: $BED" >&2; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
BEDLEN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$BED")
FADEOUT=$(awk -v d="$DUR" 'BEGIN { x = d - 1.5; if (x < 0) x = 0; print x }')

# ── THE SEAM, and why this is NOT -stream_loop ────────────────────────────────────────────
# FIXED 2026-08-30 on tp-0830c. This script used to do `-stream_loop N -i "$BED"`, which butts
# the bed's last sample straight against its first. house-bed-loop.m4a does NOT join cleanly:
# measured at its own loop point the single-sample step is 658 against a neighbourhood median
# of 9 — a 73x click, audible, and present in every shipped cut longer than 36s. Decoding to
# WAV first does not help (65.7x): the discontinuity is in the file's content, not the codec.
# The header above has always described an equal-power crossfade; it just was not being done.
# So: load the bed as N separate inputs and chain acrossfade (esin = equal power) between
# them. Verified after the change — the join measures 2.2x, i.e. below its own neighbourhood.
# Each join consumes XF seconds, so N is computed against the EFFECTIVE loop length.
XF=0.5
N=$(awk -v d="$DUR" -v b="$BEDLEN" -v x="$XF" 'BEGIN { n = d / (b - x); c = int(n); if (c < n) c++; if (c < 1) c = 1; print c }')

echo "lay-bed: video ${DUR}s · bed ${BEDLEN}s · ${N} copy(ies), ${XF}s equal-power joins · $(basename "$BED")"

BEDIN=(); FC=""
for ((i=0;i<N;i++)); do BEDIN+=(-i "$BED"); done
if (( N == 1 )); then
  FC="[1:a]anull[bedsrc];"
else
  FC="[1:a][2:a]acrossfade=d=${XF}:c1=esin:c2=esin[x1];"
  for ((i=2;i<N;i++)); do
    FC+="[x$((i-1))][$((i+1)):a]acrossfade=d=${XF}:c1=esin:c2=esin[x${i}];"
  done
  FC+="[x$((N-1))]anull[bedsrc];"
fi

ffmpeg -y -v error -i "$IN" "${BEDIN[@]}" \
  -filter_complex "${FC}[bedsrc]atrim=0:${DUR},asetpts=PTS-STARTPTS,\
afade=t=in:st=0:d=1.2,afade=t=out:st=${FADEOUT}:d=1.5[bed];\
[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k "$OUT"

echo "lay-bed: done -> $OUT"
