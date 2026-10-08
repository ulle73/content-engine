#!/usr/bin/env bash
# Composite a NextPhase CUTOUT HOOK:
#   designed HyperFrames BG  +  source torso inside a rounded rect  +  RVM cutout person on top.
#
#   usage: bash scripts/cutout-hook.sh <src.mp4> <bg.mp4> <frames_dir> <out.mp4> [seconds]
#
#   src.mp4     the talking-head recording (1080x1920, 30fps)
#   bg.mp4      rendered HyperFrames motion-graphics BG, same length, NO audio
#   frames_dir  BGRA frames from scripts/rvm-matte.py
#   out.mp4     output (video only; audio is muxed at the end from src)
#
# ── THE SEAM INVARIANT (read this before touching the geometry) ──────────────
#   RECT_Y - CROP_Y  MUST EQUAL  PERSON_Y
#
# The rect window and the cutout person are the SAME body, drawn twice. The window
# shows the source's torso; the RVM cutout is composited over it. They only line up
# — and the "popping out of the rectangle" illusion only holds — if both layers are
# shifted down by the same amount. Defaults: 1400 - 1200 = 200. ✓
# Break it and the torso ghosts: a second pair of shoulders peeks out from behind
# the cutout. If you move PERSON_Y to unclip a head, move CROP_Y by the same delta.
set -euo pipefail

SRC="${1:?source video}"; BG="${2:?background mp4}"; FRAMES="${3:?rvm frames dir}"
OUT="${4:?output mp4}";   SECS="${5:-5}"

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RECT_MASK="${RECT_MASK:-$REPO/assets/rect_mask.png}"

# Geometry (override via env to retune per recording)
RECT_X="${RECT_X:-40}";   RECT_Y="${RECT_Y:-1400}"
RECT_W="${RECT_W:-1000}"; RECT_H="${RECT_H:-670}"
CROP_X="${CROP_X:-40}";   CROP_Y="${CROP_Y:-1200}"
PERSON_X="${PERSON_X:-0}"; PERSON_Y="${PERSON_Y:-200}"

[[ -f "$SRC" ]] || { echo "cutout-hook: no source: $SRC" >&2; exit 1; }
[[ -f "$BG"  ]] || { echo "cutout-hook: no background: $BG" >&2; exit 1; }
[[ -d "$FRAMES" ]] || { echo "cutout-hook: no frames dir: $FRAMES" >&2; exit 1; }

if [[ ! -f "$RECT_MASK" ]]; then
  echo "cutout-hook: generating rect mask -> $RECT_MASK"
  "${PYTHON:-python}" "$REPO/scripts/make-rect-mask.py" --w "$RECT_W" --h "$RECT_H" --out "$RECT_MASK"
fi

# Enforce the seam invariant rather than letting it fail silently on screen.
if (( RECT_Y - CROP_Y != PERSON_Y )); then
  echo "cutout-hook: SEAM BROKEN — RECT_Y($RECT_Y) - CROP_Y($CROP_Y) = $((RECT_Y-CROP_Y)), but PERSON_Y=$PERSON_Y." >&2
  echo "             The torso will ghost behind the cutout. Fix the geometry and re-run." >&2
  exit 1
fi

echo "cutout-hook: ${SECS}s  rect ${RECT_W}x${RECT_H}@(${RECT_X},${RECT_Y})  person@(${PERSON_X},${PERSON_Y})"
TMPV="${OUT%.mp4}.silent.mp4"
ffmpeg -y -hide_banner -loglevel error \
  -i "$BG" -i "$SRC" -loop 1 -i "$RECT_MASK" -framerate 30 -i "$FRAMES/%05d.png" \
  -filter_complex "\
    [1:v]trim=0:${SECS},setpts=PTS-STARTPTS,scale=1080:1920,crop=${RECT_W}:${RECT_H}:${CROP_X}:${CROP_Y},format=yuva420p[inside_raw];\
    [2:v]format=gray[mask];\
    [inside_raw][mask]alphamerge[inside];\
    [0:v]trim=0:${SECS},setpts=PTS-STARTPTS[bg];\
    [bg][inside]overlay=x=${RECT_X}:y=${RECT_Y}[withrect];\
    [withrect][3:v]overlay=x=${PERSON_X}:y=${PERSON_Y}:shortest=1[v]" \
  -map "[v]" -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -r 30 -t "$SECS" "$TMPV" </dev/null

# The composite carries no audio — take the matching span of the source VO back.
if ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$SRC" | grep -q audio; then
  ffmpeg -y -hide_banner -loglevel error -i "$TMPV" -ss 0 -to "$SECS" -i "$SRC" \
    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest "$OUT" </dev/null
  rm -f "$TMPV"
  echo "cutout-hook: done -> $OUT  (audio muxed from source)"
else
  mv "$TMPV" "$OUT"
  echo "cutout-hook: done -> $OUT  (source had no audio track)"
fi
