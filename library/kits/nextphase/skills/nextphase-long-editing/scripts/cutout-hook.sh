#!/usr/bin/env bash
# Composite a NextPhase TRANSPARENT BACKGROUND layout (16:9):
#   designed HyperFrames BG  +  source torso inside a rounded rect  +  RVM cutout on top.
#
#   usage: bash scripts/cutout-hook.sh <src.mp4> <bg.mp4> <frames_dir> <out.mp4> [seconds]
#
#   src.mp4     the TIGHTENED talking-head recording
#   bg.mp4      rendered HyperFrames background, 1920x1080, 30fps, NO audio
#   frames_dir  BGRA frames from scripts/rvm-matte.py
#   out.mp4     output (audio is muxed from src at the end)
#
# ── THE SEAM INVARIANT (read this before touching the geometry) ───────────────
#   RECT_X - CROP_X  MUST EQUAL  PERSON_X
#   RECT_Y - CROP_Y  MUST EQUAL  PERSON_Y
#
# The rect window and the cutout person are the SAME body, drawn twice. The window
# shows the source's torso; the RVM cutout is composited over it. They line up — and
# the "popping out of the rectangle" illusion only holds — if both layers are shifted
# by the same amount on BOTH axes.
#
# The 9:16 version only ever moved the person vertically, so the X half was satisfied
# by accident (40 - 40 = 0). In 16:9 you WILL move him sideways, so both are enforced
# here. Break either and the torso ghosts: a second pair of shoulders peeks out from
# behind the cutout. If you move PERSON_Y to unclip a head, move CROP_Y by the same delta.
#
# ── GEOMETRY (env vars; the defaults are PROPORTIONAL PORTS, not measurements) ─
# Always run  scripts/find-cut-line.py  on the real footage and replace RECT_Y/CROP_Y.
set -euo pipefail

SRC="${1:?source video}"; BG="${2:?background mp4}"; FRAMES="${3:?rvm frames dir}"
OUT="${4:?output mp4}";   SECS="${5:-5}"

REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Canvas
FRAME_W="${FRAME_W:-1920}"; FRAME_H="${FRAME_H:-1080}"
# Source is scaled to this before BOTH the window crop and the person overlay.
# Change it to shrink him (e.g. 1344x756 = 0.7x) — then CROP_X/Y are coordinates in
# the SCALED frame, so scale the measured cut line by the same factor.
SRC_W="${SRC_W:-1920}"; SRC_H="${SRC_H:-1080}"
# The window card
RECT_X="${RECT_X:-360}";  RECT_Y="${RECT_Y:-397}"
RECT_W="${RECT_W:-1200}"; RECT_H="${RECT_H:-803}"
# Where the window's content is taken from in the (scaled) source
CROP_X="${CROP_X:-360}";  CROP_Y="${CROP_Y:-285}"
# Where the cutout person is placed
PERSON_X="${PERSON_X:-0}"; PERSON_Y="${PERSON_Y:-112}"
# How far the rect must bleed past the frame bottom so its lower corners never show
BLEED="${BLEED:-120}"

RECT_MASK="${RECT_MASK:-$REPO/assets/rect_mask_${RECT_W}x${RECT_H}.png}"

[[ -f "$SRC" ]]    || { echo "cutout: no source: $SRC" >&2; exit 1; }
[[ -f "$BG"  ]]    || { echo "cutout: no background: $BG" >&2; exit 1; }
[[ -d "$FRAMES" ]] || { echo "cutout: no frames dir: $FRAMES" >&2; exit 1; }
compgen -G "$FRAMES/*.png" >/dev/null || { echo "cutout: no PNGs in $FRAMES — run rvm-matte.py" >&2; exit 1; }

# ── enforce the seam on BOTH axes, rather than letting it fail silently on screen ──
fail=0
if (( RECT_X - CROP_X != PERSON_X )); then
  echo "cutout: SEAM BROKEN (X) — RECT_X($RECT_X) - CROP_X($CROP_X) = $((RECT_X-CROP_X)), but PERSON_X=$PERSON_X" >&2
  fail=1
fi
if (( RECT_Y - CROP_Y != PERSON_Y )); then
  echo "cutout: SEAM BROKEN (Y) — RECT_Y($RECT_Y) - CROP_Y($CROP_Y) = $((RECT_Y-CROP_Y)), but PERSON_Y=$PERSON_Y" >&2
  fail=1
fi
if (( fail )); then
  echo "        The torso will ghost behind the cutout. Fix the geometry and re-run." >&2
  echo "        (Run: "${PYTHON:-python}" scripts/find-cut-line.py --frames $FRAMES --cut mid-head --person-y $PERSON_Y)" >&2
  exit 1
fi

# ── the rect must keep bleeding past the frame bottom ─────────────────────────
MIN_H=$(( FRAME_H - RECT_Y + BLEED ))
if (( RECT_H < MIN_H )); then
  echo "cutout: RECT_H=$RECT_H is too short for RECT_Y=$RECT_Y — the rect's lower rounded" >&2
  echo "        corners will come into shot and a gap opens underneath." >&2
  echo "        Need RECT_H >= FRAME_H($FRAME_H) - RECT_Y($RECT_Y) + BLEED($BLEED) = $MIN_H" >&2
  exit 1
fi
# ── the window crop must fit inside the (scaled) source ───────────────────────
if (( CROP_X + RECT_W > SRC_W || CROP_Y + RECT_H > SRC_H )); then
  echo "cutout: the window crop ${RECT_W}x${RECT_H}@(${CROP_X},${CROP_Y}) runs past the" >&2
  echo "        scaled source ${SRC_W}x${SRC_H}. ffmpeg will refuse. Lower RECT_Y/CROP_Y," >&2
  echo "        narrow RECT_W, or scale the source up via SRC_W/SRC_H." >&2
  exit 1
fi

if [[ ! -f "$RECT_MASK" ]]; then
  echo "cutout: generating rect mask -> $RECT_MASK"
  "${PYTHON:-python}" "$REPO/scripts/make-rect-mask.py" --w "$RECT_W" --h "$RECT_H" --out "$RECT_MASK"
fi

echo "cutout: ${SECS}s @ ${FRAME_W}x${FRAME_H}"
echo "        source scaled to ${SRC_W}x${SRC_H}"
echo "        rect  ${RECT_W}x${RECT_H} @ (${RECT_X},${RECT_Y})   crop @ (${CROP_X},${CROP_Y})"
echo "        person @ (${PERSON_X},${PERSON_Y})   seam ✓ on both axes"

TMPV="${OUT%.mp4}.silent.mp4"
ffmpeg -y -hide_banner -loglevel error -stats \
  -i "$BG" -i "$SRC" -loop 1 -i "$RECT_MASK" -framerate 30 -i "$FRAMES/%05d.png" \
  -filter_complex "\
    [1:v]trim=0:${SECS},setpts=PTS-STARTPTS,scale=${SRC_W}:${SRC_H},\
crop=${RECT_W}:${RECT_H}:${CROP_X}:${CROP_Y},format=yuva420p[inside_raw];\
    [2:v]format=gray[mask];\
    [inside_raw][mask]alphamerge[inside];\
    [0:v]trim=0:${SECS},setpts=PTS-STARTPTS,scale=${FRAME_W}:${FRAME_H}[bg];\
    [3:v]scale=${SRC_W}:${SRC_H}[person];\
    [bg][inside]overlay=x=${RECT_X}:y=${RECT_Y}[withrect];\
    [withrect][person]overlay=x=${PERSON_X}:y=${PERSON_Y}:shortest=1[v]" \
  -map "[v]" -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -r 30 -t "$SECS" "$TMPV" </dev/null

# The composite carries no audio — take the matching span of the source VO back.
if ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$SRC" | grep -q audio; then
  ffmpeg -y -hide_banner -loglevel error -i "$TMPV" -ss 0 -to "$SECS" -i "$SRC" \
    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest "$OUT" </dev/null
  rm -f "$TMPV"
  echo "cutout: done -> $OUT  (audio muxed from source)"
else
  mv "$TMPV" "$OUT"
  echo "cutout: done -> $OUT  (source had no audio track)"
fi

echo
echo "  Check the HAIRLINE in a still before rendering the segment — soft alpha that is"
echo "  invisible on cream fringes visibly against --dark:"
echo "    ffmpeg -ss 1 -i $OUT -frames:v 1 work/nextphase/tmp/hairline.png"
