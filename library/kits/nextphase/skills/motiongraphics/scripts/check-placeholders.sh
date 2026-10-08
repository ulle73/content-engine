#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# check-placeholders.sh — refuse to render a segment that still carries kit copy.
#
# Every string in components/*.html is PLACEHOLDER. It exists so the bricks look
# like something in a browser. None of it describes the video being edited, and
# some of it was lifted from the reference edits and belongs to other people.
# Shipping any of it into a monetized client-facing video is a real failure.
#
#   usage:  bash check-placeholders.sh work/nextphase/videos/<name>
#           bash check-placeholders.sh work/nextphase/videos/<name> --quiet   # exit code only
#
# Exit 0 = clean. Exit 1 = placeholder copy found; do not render.
# ═══════════════════════════════════════════════════════════════════════════
set -uo pipefail

DIR="${1:-.}"
QUIET="${2:-}"

if [ ! -d "$DIR" ]; then
  echo "check-placeholders: no such directory: $DIR" >&2
  exit 2
fi

# 1 · Copy that ships with the kit. Realistic on purpose, which is exactly why
#     it is dangerous — it does not look wrong at a glance.
KIT=(
  "Your subject" "@yourhandle" "Brand one" "Brand two" "Owner name"
  "Field one: replace me" "Field two: replace me"
  "Replace this with a real quote"
  "The tool is just guessing" "It has no context on you"
  "It doesn't know what videos are working" "It doesn't know how the competitors post"
  "Content Strategy & Positioning" "Video Workflow" "The Learning Loop" "The Content Coach"
  "Niche Interviewer" "Positioning Builder" "Bullseye Builder" "Topic Scanner" "Format Finder"
  "CONTENT GROWTH SYSTEM" "THE FINAL RESULT" "NEXT SCENE"
  "Photographer" "The lighting" "Shooting"
  "Business owner" "New Product" "Store Management"
  "2026 Goals" "Replace your 9-to-5 income" "Start an online business" "Discover new places"
  "Nothing changes" "What would happen?" "3rd place" "Leaderboard"
  "New payment" "You've received a payment from a client"
  "You want to work with me?"
  "Main character" "Real > Perfect" "Visual continuity" "Light & colour"
  "Photo dump" "Week in the life" "Get ready with me" "Faceless" "Hot takes"
  "Editors" "Judges" "Freelance freedom"
  "hero media" "screen recording" "screenshot" "camera —" "replace me"
  "Lorem" "lorem" "TODO" "FIXME" "XXX"
)

# 2 · Proper nouns from the reference edits. These belong to other creators and
#     must never appear anywhere — not in a render, not in a comment.
BORROWED=(
  "Visual adam" "kallaway" "Kallaway" "Sandcastles" "Al-sagh"
  "plastic surgeon" "SCC Leaderboard"
)

FILES=$(find "$DIR" -type f \( -name '*.html' -o -name '*.md' -o -name '*.txt' -o -name '*.json' \) \
        -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null)

if [ -z "$FILES" ]; then
  [ "$QUIET" = "--quiet" ] || echo "check-placeholders: nothing to scan in $DIR"
  exit 0
fi

HITS=0
report () { # severity pattern
  local sev="$1" pat="$2" out
  out=$(grep -rInF -- "$pat" $FILES 2>/dev/null) || return 0
  HITS=$((HITS+1))
  if [ "$QUIET" != "--quiet" ]; then
    printf '\n  [%s] %s\n' "$sev" "$pat"
    printf '%s\n' "$out" | sed 's/^/      /' | head -6
  fi
}

for p in "${BORROWED[@]}"; do report "BORROWED" "$p"; done
for p in "${KIT[@]}";      do report "KIT COPY" "$p"; done

if [ "$HITS" -eq 0 ]; then
  [ "$QUIET" = "--quiet" ] || echo "check-placeholders: clean — no kit copy in $DIR"
  exit 0
fi

if [ "$QUIET" != "--quiet" ]; then
  cat <<'EOF'

──────────────────────────────────────────────────────────────────────────────
  DO NOT RENDER.

  Every string above came from the brick kit, not from this video. Replace it
  with copy derived from THIS recording:

    • a caption or headline  -> the speaker's own words, from transcript-tight.json
    • a label on a diagram   -> the thing actually being described in that beat
    • a stat, name or handle -> the real, verified figure or the real person
    • a media placeholder    -> the real screenshot or clip from assets/broll/

  Anything marked BORROWED is another creator's name lifted from a reference
  edit. That must never ship under any circumstances.
──────────────────────────────────────────────────────────────────────────────
EOF
fi
exit 1
