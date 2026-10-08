#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# zak-plate.sh — reframe and grade a source recording into the zak window.
#
#   usage:  bash zak-plate.sh <in.mp4> <out.mp4> [16x9|9x16] [crop-y] [strength]
#
#     crop-y    0.0 = crop from the top, 0.5 = centre (default), 1.0 = bottom.
#               A talking head almost always wants 0.30–0.40: the scope window
#               throws away headroom, not chin.
#     strength  plate (default) | soft | none
#
# The window is NOT the frame. In 16:9 it is a 2.35:1 letterbox, so this
# genuinely re-crops the source rather than scaling it — that is the reframe
# the style is built on, and it is why you point crop-y at the face.
#
# THE GRADE — and read this before changing it.
#
# ⚠ The first version of this script chased the reference reel's MEASURED
#   colour: B−R −53 in the mids, saturation 0.35, ceiling 151. That was wrong,
#   and it shipped an orange, muddy plate on the first real video.
#
#   Those numbers describe that creator's ROOM — a warm practical, a beige
#   door, a red cap. They are not a transform. Real footage is usually already
#   warm (the test source measured B−R −31 on its own), so applying a −53 push
#   on top DOUBLES the cast, and pulling the ceiling to 151 on a source that
#   peaked at 198 flattens the highlights into mud.
#
# What is actually transferable is EXPOSURE, not colour:
#   • pull the image down — low-key is the look (mean luma ~90)
#   • lift the black floor a little so nothing crushes into the ground
#   • roll the highlights off gently; do not crush them
#   • leave the source's own warmth alone. A tiny warm nudge, nothing more.
#
# If a source genuinely has a bad cast, fix that UPSTREAM with a balance pass
# (persa/scripts/persa-balance.py works unchanged), then grade. Do not fold a
# correction into this curve.
#
# Verify by LOOKING at a frame beside the ungraded source, then with
# scripts/check-contrast.py. The numbers alone will not catch "muddy".
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

IN="${1:?usage: zak-plate.sh <in.mp4> <out.mp4> [16x9|9x16] [crop-y] [strength]}"
OUT="${2:?missing output path}"
ASPECT="${3:-16x9}"
CROPY="${4:-0.35}"
STRENGTH="${5:-plate}"

command -v ffmpeg >/dev/null || {
  echo "zak-plate: ffmpeg not on PATH." >&2
  echo '  (Windows: node/npx ligger redan på PATH)' >&2
  exit 2; }

case "$ASPECT" in
  16x9) W=1720; H=732 ;;   # the derived 2.35:1 scope window
  9x16) W=968;  H=968 ;;   # the measured square
  *) echo "zak-plate: aspect must be 16x9 or 9x16 (got '$ASPECT')" >&2; exit 2 ;;
esac

# Cover-crop to the window aspect, biased by crop-y, then land on W×H exactly.
REFRAME="scale=${W}:${H}:force_original_aspect_ratio=increase,\
crop=${W}:${H}:(iw-${W})/2:(ih-${H})*${CROPY}"

case "$STRENGTH" in
  plate)
    # curves lifts the floor and caps the ceiling per channel; the blue curve
    # is pulled hardest, which is where the −53 B−R in the mids comes from.
    GRADE="eq=brightness=-0.065:contrast=1.03:saturation=1.02,\
curves=r='0/0.062 0.5/0.468 1/0.795':g='0/0.058 0.5/0.450 1/0.785':b='0/0.058 0.5/0.434 1/0.765'"
    ;;
  soft)   # half-strength: for a source already close to low-key
    GRADE="eq=brightness=-0.035:contrast=1.02:saturation=1.01,\
curves=r='0/0.04 0.5/0.485 1/0.86':g='0/0.038 0.5/0.474 1/0.85':b='0/0.038 0.5/0.462 1/0.835'"
    ;;
  none)   GRADE="null" ;;
  *) echo "zak-plate: strength must be plate | soft | none" >&2; exit 2 ;;
esac

echo "zak-plate: $IN -> $OUT"
echo "  window ${W}x${H} ($ASPECT)   crop-y $CROPY   grade $STRENGTH"

ffmpeg -v error -stats -i "$IN" \
  -vf "${REFRAME},${GRADE},fps=30,format=yuv420p" \
  -c:v libx264 -crf 16 -preset slow -r 30 -fps_mode cfr \
  -c:a aac -b:a 192k -y "$OUT"

echo
echo "  now verify — the caption has no shadow, so the plate is the only thing"
echo "  making it readable:"
echo "    "${PYTHON:-python}" scripts/check-contrast.py <the rendered segment>"
