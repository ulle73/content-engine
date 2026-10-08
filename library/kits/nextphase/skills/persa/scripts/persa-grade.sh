#!/usr/bin/env bash
# persa-grade.sh — apply the PERSA look to a clip.
#
#   bash scripts/persa-grade.sh in.mp4 out.mp4 [strength]
#       strength: full (default) | soft | plate
#         full  — curves + bloom + vignette + grain. The deliverable look.
#         soft  — curves + bloom only. For footage that is already contrasty.
#         plate — curves only. Use when compositing: grade the PLATE, then
#                 add bloom/vignette/grain ONCE over the finished comp, so the
#                 graphics sit inside the look instead of on top of it.
#
# The curve anchors are measured, not eyeballed — see reference/grade.md.
# Verify any output with:  "${PYTHON:-python}" scripts/grade-check.py out.mp4
set -euo pipefail
# (macOS nvm PATH-export borttagen vid Windows-importen — node/npx/ffmpeg ligger på PATH)

IN="${1:?usage: persa-grade.sh in.mp4 out.mp4 [full|soft|plate]}"
OUT="${2:?usage: persa-grade.sh in.mp4 out.mp4 [full|soft|plate]}"
MODE="${3:-full}"

# ── The transfer function. The two reference reels are the SAME look at two
#    densities (A hazier, B cleaner — see reference/grade.md §3), so these
#    anchors sit at their MIDPOINT and grade-check.py passes on both.
#    Verified on a neutral ramp: black 3/5/3 · shadows G-R +2 B-R +2
#    mids G-R +0 B-R -24 · highs G-R +6 B-R -20 · white 224/209/196
CURVES="curves=\
r='0/0.012 0.25/0.200 0.5/0.440 0.75/0.643 1/0.882':\
g='0/0.020 0.25/0.206 0.5/0.440 0.75/0.663 1/0.820':\
b='0/0.012 0.25/0.194 0.5/0.349 0.75/0.561 1/0.769'"

SAT="eq=saturation=0.88"                       # measured mean sat 0.22-0.29
# Import fix (Windows/ffmpeg 9): blend in RGB (gbrp). Screen-blending yuv420p also blends
# the chroma planes and pushes the whole frame magenta.
BLOOM="format=gbrp,split[a][b];[b]gblur=sigma=26,curves=all='0/0 0.55/0.10 1/0.80'[bl];\
[a][bl]blend=all_mode=screen:all_opacity=0.22,format=yuv420p"  # the milky halation
VIG="vignette=angle=PI/4.6"                    # measured corner/centre = 0.57
GRAIN="noise=alls=7:allf=t+u"                  # measured temporal sigma 8.3

case "$MODE" in
  plate) VF="$CURVES,$SAT" ;;
  soft)  VF="$CURVES,$SAT,$BLOOM" ;;
  full)  VF="$CURVES,$SAT,$BLOOM,$VIG,$GRAIN" ;;
  *) echo "unknown strength '$MODE' (full|soft|plate)" >&2; exit 2 ;;
esac

echo "persa-grade [$MODE]  $IN -> $OUT"
ffmpeg -hide_banner -v warning -stats -i "$IN" \
  -vf "$VF" -r 30 -fps_mode cfr \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -c:a copy "$OUT" -y

echo
echo "verifying against the measured persa targets:"
"${PYTHON:-python}" "$(dirname "$0")/grade-check.py" "$OUT" || true
