#!/usr/bin/env bash
# Mix faint SFX onto a rendered video, on cue — the NextPhase sound layer.
# See system/sound-design.md for when to use each sound and the volume rule.
#
#   usage:  bash scripts/mix-sfx.sh <in.mp4> <out.mp4> <cues.txt>
#
# cues.txt — one cue per line:   <time_sec>  <sound>  [gain]
#   time_sec : when the sound STARTS, in seconds (for a riser, that's a few
#              seconds BEFORE the payoff so it crests on the beat).
#   sound    : a canonical name (whoosh, pop, click, magic-reveal, riser,
#              swoosh, camera-shutter) or a path under sfx/
#              (e.g. library/trending/PopUp/pop 2.mp3).
#   gain     : linear volume, optional. Default 0.12 (~ -18 dBFS) = present,
#              under the voice. Transients ~0.12, sustained riser/reveal ~0.09,
#              a hero moment ~0.16. See system/sound-design.md for the level gate.
# '#' comment lines and blank lines are ignored.
#
# Video is stream-copied (no re-encode, no quality loss); only audio is rebuilt.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
IN="${1:?input video}"; OUT="${2:?output video}"; CUES="${3:?cues file}"
DEFAULT_GAIN="0.12"

[[ -f "$IN" ]]   || { echo "mix-sfx: no input video: $IN"  >&2; exit 1; }
[[ -f "$CUES" ]] || { echo "mix-sfx: no cues file: $CUES" >&2; exit 1; }

resolve () { # sound token -> absolute file path (or non-zero if not found)
  local s="$1"
  for cand in "sfx/$s" "sfx/$s.mp3" "sfx/$s.wav" "sfx/$s.aif" "sfx/$s.aiff"; do
    [[ -f "$REPO/$cand" ]] && { echo "$REPO/$cand"; return 0; }
  done
  return 1
}

inputs=(); filters=(); labels=""; k=0
while read -r t sound gain _; do
  [[ -z "${t:-}" ]] && continue
  [[ "${t:0:1}" == "#" ]] && continue
  [[ -z "${sound:-}" ]] && { echo "mix-sfx: cue missing sound: '$t'" >&2; exit 1; }
  path="$(resolve "$sound")" || { echo "mix-sfx: unknown sound '$sound' (looked in sfx/)" >&2; exit 1; }
  gain="${gain:-$DEFAULT_GAIN}"
  ms="$(awk "BEGIN{printf \"%d\", $t*1000}")"
  k=$((k+1))
  inputs+=( -i "$path" )
  # per-cue: unify format -> tiny fade-in (de-click) -> faint gain -> delay to the beat
  filters+=( "[${k}:a]aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:st=0:d=0.006,volume=${gain},adelay=${ms}:all=1[s${k}]" )
  labels+="[s${k}]"
done < "$CUES"

[[ $k -gt 0 ]] || { echo "mix-sfx: no cues found in $CUES" >&2; exit 1; }

sfx_chain="$(IFS=';'; echo "${filters[*]}")"
fc="[0:a]aformat=sample_rates=48000:channel_layouts=stereo[vox];${sfx_chain};[vox]${labels}amix=inputs=$((k+1)):normalize=0:duration=first,alimiter=limit=0.95[aout]"

echo "mix-sfx: $k cue(s)  $IN -> $OUT"
ffmpeg -hide_banner -loglevel error -y -i "$IN" "${inputs[@]}" \
  -filter_complex "$fc" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 256k "$OUT" </dev/null
echo "mix-sfx: done -> $OUT"
