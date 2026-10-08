#!/usr/bin/env bash
# Lay a DUCKED music bed under a long-form render — NextPhase sound Pass B.
# Run this AFTER mix-sfx.sh, on the SFX'd file. See reference/sound-design.md.
#
#   usage: bash scripts/mix-bgm.sh <in.mp4> <out.mp4> <bed.mp3> [options]
#
#   --bed   <gain>   linear bed level before ducking. Default 0.10.
#                    Target ~22-26 dB under voice peaks. You should notice the bed
#                    LEAVE, not arrive. If you can hum along, it is too loud.
#   --drops "a:b,c:d"  spans (seconds) where the bed is silenced, 300ms fades.
#                    Use for: ~3s before the payoff spike, and the whole "turn" beat.
#                    The RETURN of music is the retention device, not the music.
#   --fade-in <s>    default 1.5   --fade-out <s>  default 2.5
#
# The bed is DUCKED by a sidechain compressor keyed off the voice, not merely turned
# down: under speech it drops, in the gaps it comes back. A bed at a fixed low level
# either masks words or is inaudible — there is no single gain that does both.
#
#   Target duck depth: 5-9 dB between "under speech" and "in the gap". Measure it:
#     ffmpeg -ss <t> -t 0.8 -i out.mp4 -af volumedetect -f null -     # over a spoken word
#     ffmpeg -ss <t> -t 0.8 -i out.mp4 -af volumedetect -f null -     # over a pause
#   Too shallow -> lower --threshold (0.02) or raise --ratio (12).
#   Pumping / audible breathing -> raise --release (500) or lower --ratio (5).
#
# The bed is looped to cover the whole video. Video is stream-copied (no quality loss).
set -euo pipefail

IN="${1:?input video (the mix-sfx.sh output)}"; shift
OUT="${1:?output video}"; shift
BED="${1:?music bed audio file}"; shift

BED_GAIN="0.10"; DROPS=""; FADE_IN="1.5"; FADE_OUT="2.5"
# sidechain: how hard the voice pushes the bed down
THRESH="0.03"; RATIO="8"; ATTACK="20"; RELEASE="350"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bed)      BED_GAIN="$2"; shift 2 ;;
    --drops)    DROPS="$2";    shift 2 ;;
    --fade-in)  FADE_IN="$2";  shift 2 ;;
    --fade-out) FADE_OUT="$2"; shift 2 ;;
    --threshold) THRESH="$2";  shift 2 ;;
    --ratio)    RATIO="$2";    shift 2 ;;
    *) echo "mix-bgm: unknown option '$1'" >&2; exit 1 ;;
  esac
done

[[ -f "$IN"  ]] || { echo "mix-bgm: no input video: $IN" >&2; exit 1; }
[[ -f "$BED" ]] || { echo "mix-bgm: no bed file: $BED" >&2; exit 1; }

if ! ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$IN" \
     | grep -q audio; then
  echo "mix-bgm: input has no audio track — run mix-sfx.sh first (or check the render)." >&2
  exit 1
fi

DUR="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$IN")"
FADE_OUT_AT="$(awk "BEGIN{printf \"%.3f\", ($DUR)-($FADE_OUT)}")"

# --- build the drop envelope -------------------------------------------------
# ONE volume expression, not a stack of afades. Chaining afade=t=out / afade=t=in
# per drop looks right and is silently wrong: afade=t=in outputs ZERO for all t
# before its start time, so a drop at 25s mutes the bed for the first 25 seconds.
#
# Per drop [a,b] with a fade f, the envelope is
#     g(t) = max( max( min(1,(a-t)/f), min(1,(t-b)/f) ), 0 )
#  -> 1 before a-f · ramp down to 0 at a · 0 across [a,b] · ramp back to 1 by b+f.
# Drops multiply, so overlapping spans behave sensibly.
# (max()/min() in ffmpeg's evaluator take exactly TWO arguments — hence the nesting.
#  Commas are escaped because filter_complex splits filters on them.)
DROP_F="0.3"
envelope="${BED_GAIN}"
n_drops=0
if [[ -n "$DROPS" ]]; then
  IFS=',' read -ra SPANS <<< "$DROPS"
  for span in "${SPANS[@]}"; do
    [[ "$span" =~ ^[0-9]+(\.[0-9]+)?:[0-9]+(\.[0-9]+)?$ ]] || {
      echo "mix-bgm: bad drop span '$span' — want start:end in seconds, e.g. 12.4:15.9" >&2; exit 1; }
    a="${span%%:*}"; b="${span##*:}"
    awk -v a="$a" -v b="$b" 'BEGIN{exit !(a < b)}' || {
      echo "mix-bgm: drop span '$span' does not advance (start must be < end)" >&2; exit 1; }
    envelope+="*max(max(min(1\,(${a}-t)/${DROP_F})\,min(1\,(t-${b})/${DROP_F}))\,0)"
    n_drops=$((n_drops+1))
  done
fi

# --- build the bed chain -----------------------------------------------------
# loop -> trim to length -> level + drop envelope -> global in/out fades
bed_chain="[1:a]aformat=sample_rates=48000:channel_layouts=stereo"
bed_chain+=",atrim=0:${DUR},asetpts=PTS-STARTPTS"
bed_chain+=",volume='${envelope}':eval=frame"
bed_chain+=",afade=t=in:st=0:d=${FADE_IN}"
bed_chain+=",afade=t=out:st=${FADE_OUT_AT}:d=${FADE_OUT}"
bed_chain+="[bedraw]"

# --- voice: one copy to the mix, one as the sidechain key --------------------
fc="[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[vox][key];"
fc+="${bed_chain};"
fc+="[bedraw][key]sidechaincompress=threshold=${THRESH}:ratio=${RATIO}"
fc+=":attack=${ATTACK}:release=${RELEASE}[bed];"
fc+="[vox][bed]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[aout]"

echo "mix-bgm: bed=${BED_GAIN}  drops=${n_drops}  duck=${RATIO}:1@${THRESH}  ${DUR%.*}s"
echo "         $IN + $(basename "$BED") -> $OUT"

ffmpeg -hide_banner -loglevel error -y \
  -i "$IN" -stream_loop -1 -i "$BED" \
  -filter_complex "$fc" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 256k -shortest "$OUT" </dev/null

echo "mix-bgm: done -> $OUT"
echo
echo "  Now WATCH IT END TO END with headphones. Levels that measure right can still"
echo "  feel wrong; the watch is the real gate. If the bed masks a word, drop --bed."
