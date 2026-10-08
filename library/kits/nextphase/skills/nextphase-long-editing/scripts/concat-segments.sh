#!/usr/bin/env bash
# Join per-segment renders into the final visual cut and emit YouTube chapter timestamps.
# See reference/assembly.md.
#
#   usage: bash scripts/concat-segments.sh <out.mp4> <seg1.mp4> <seg2.mp4> ...
#          bash scripts/concat-segments.sh out/final-visual.mp4 out/seg-*.mp4
#
#   --titles <file>   one chapter title per line, in segment order. Without it, titles
#                     are derived from the filenames (seg-02-what-it-does -> "What It Does").
#   --no-chapters     skip chapters.txt
#
# Tries the concat DEMUXER with -c copy first: instant and lossless. Falls back to a
# re-encode only if the streams genuinely differ, and says WHICH segment differs — so
# you fix the real problem (a segment rendered at the wrong fps/size) instead of
# silently accepting a re-encode.
#
# Writes <out-dir>/chapters.txt from the REAL measured durations. Never hand-count
# chapter timestamps and never copy them from PLAN.md — plan times are pre-render
# estimates and always drift.
set -euo pipefail

OUT="${1:?output mp4}"; shift
TITLES=""; WRITE_CHAPTERS=1; SEGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --titles)      TITLES="$2"; shift 2 ;;
    --no-chapters) WRITE_CHAPTERS=0; shift ;;
    *)             SEGS+=("$1"); shift ;;
  esac
done

[[ ${#SEGS[@]} -ge 1 ]] || { echo "concat: no segments given" >&2; exit 1; }
for s in "${SEGS[@]}"; do
  [[ -f "$s" ]] || { echo "concat: missing segment: $s" >&2; exit 1; }
done

OUTDIR="$(cd "$(dirname "$OUT")" && pwd)"

probe () { ffprobe -v error -select_streams "$1" -show_entries "$2" -of default=nw=1:nk=1 "$3" 2>/dev/null | head -1; }

# ── verify every segment matches the first, and collect durations ────────────
REF_V="$(probe v:0 stream=width,height,r_frame_rate,pix_fmt "${SEGS[0]}" | tr '\n' '/')"
REF_A="$(probe a:0 stream=sample_rate,channels "${SEGS[0]}" | tr '\n' '/')"
MISMATCH=0
MANIFEST="$(mktemp)"; trap 'rm -f "$MANIFEST" "${LIST:-}"' EXIT

echo "concat: ${#SEGS[@]} segment(s)"
i=0
for s in "${SEGS[@]}"; do
  i=$((i+1))
  v="$(probe v:0 stream=width,height,r_frame_rate,pix_fmt "$s" | tr '\n' '/')"
  a="$(probe a:0 stream=sample_rate,channels "$s" | tr '\n' '/')"
  d="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$s")"
  flag=""
  if [[ "$v" != "$REF_V" ]]; then flag=" <- VIDEO MISMATCH ($v vs $REF_V)"; MISMATCH=1; fi
  if [[ "$a" != "$REF_A" ]]; then flag="$flag <- AUDIO MISMATCH ($a vs $REF_A)"; MISMATCH=1; fi
  printf '  %-38s %8.2fs%s\n' "$(basename "$s")" "$d" "$flag"

  # title: --titles line i, else derived from the filename
  #   seg-02-what-it-does.mp4 -> "What It Does"
  if [[ -n "$TITLES" ]]; then
    title="$(sed -n "${i}p" "$TITLES")"
  else
    title="$(basename "$s" .mp4 \
      | sed -E 's/^seg-?[0-9]+-?//; s/[-_]+/ /g' \
      | awk '{for(j=1;j<=NF;j++) $j=toupper(substr($j,1,1)) substr($j,2)}1')"
  fi
  [[ -n "$title" ]] || title="Chapter $i"
  printf '%s\t%s\n' "$d" "$title" >> "$MANIFEST"
done

TOTAL="$(awk -F'\t' '{t+=$1} END{printf "%.3f", t}' "$MANIFEST")"
awk -v t="$TOTAL" 'BEGIN{
  m=int(t/60); s=int(t%60);
  printf "  %-38s %8.2fs  (%dm %02ds)\n", "TOTAL", t, m, s
}'

# ── join ─────────────────────────────────────────────────────────────────────
LIST="$(mktemp)"
for s in "${SEGS[@]}"; do
  # Windows/Git Bash (import fix): the list file is read by native ffmpeg, which cannot
  # resolve MSYS paths like /c/Users/… — `pwd -W` gives C:/Users/…; plain pwd elsewhere.
  printf "file '%s'\n" "$(cd "$(dirname "$s")" && (pwd -W 2>/dev/null || pwd))/$(basename "$s")" >> "$LIST"
done

if [[ $MISMATCH -eq 0 ]] && \
   ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$LIST" -c copy "$OUT" </dev/null; then
  echo "concat: stream-copied (lossless) -> $OUT"
else
  if [[ $MISMATCH -eq 1 ]]; then
    echo "concat: segments differ (see the MISMATCH lines above)." >&2
    echo "        Re-render the odd segment at 1920x1080 / 30fps rather than living with" >&2
    echo "        a re-encode — but proceeding with one now so you have a file." >&2
  fi
  ffmpeg -hide_banner -loglevel error -stats -y -f concat -safe 0 -i "$LIST" \
    -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 256k "$OUT" </dev/null
  echo "concat: re-encoded -> $OUT"
fi

# ── chapters ─────────────────────────────────────────────────────────────────
[[ $WRITE_CHAPTERS -eq 1 ]] || exit 0

CH="$OUTDIR/chapters.txt"

# One awk pass over the manifest (duration<TAB>title) — cumulative timestamps from the
# REAL measured durations. YouTube wants the first chapter at exactly 0:00, M:SS under an
# hour, H:MM:SS over, and every chapter >= 10s.
awk -F'\t' -v out="$CH" -v total="$TOTAL" '
  function hms(t,   h,m,s) {
    h = int(t/3600); m = int((t%3600)/60); s = int(t%60)
    return (total >= 3600) ? sprintf("%d:%02d:%02d", h, m, s) : sprintf("%d:%02d", int(t/60), s)
  }
  BEGIN { t = 0; warned = 0 }
  {
    printf "%s %s\n", hms(t), $2 > out
    if ($1 + 0 < 10) { printf "  ! \x27%s\x27 is %.0fs — YouTube requires every chapter >= 10s; merge it.\n", $2, $1 | "cat 1>&2"; warned = 1 }
    t += $1
  }
  END { close(out); if (warned) print "  (fix the short-chapter warnings before publishing chapters)" | "cat 1>&2" }
' "$MANIFEST"

echo "concat: wrote $CH"
cat "$CH"
echo
echo "  Segment durations changed? Every SFX cue after the changed segment has moved."
echo "  Diff this chapters.txt against the previous one before re-mixing sound."
exit 0
