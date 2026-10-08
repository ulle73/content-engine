#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# check-persa.sh — the render gate for the PERSA style.
#
#   usage:  bash check-persa.sh work/nextphase/videos/<name>
#
# Three classes of failure, all of which have shipped before in other styles:
#   1 · KIT COPY   — placeholder strings from components/ surviving into a segment.
#   2 · BORROWED   — copy lifted from the reference reels. Those words belong to
#                    another creator; they must not appear in a client video.
#   3 · STYLE      — the mistakes specific to persa: an animated caption, a
#                    hardcoded colour, a caption that is not one word.
#
# Exit 0 = clean. Exit 1 = do not render.
# ═══════════════════════════════════════════════════════════════════════════
set -uo pipefail
DIR="${1:-.}"
[ -d "$DIR" ] || { echo "check-persa: no such directory: $DIR" >&2; exit 2; }

FAIL=0
hit(){ printf '  %-9s %s\n' "$1" "$2"; FAIL=1; }

FILES=$(find "$DIR" -name '*.html' -not -path '*/node_modules/*' 2>/dev/null)
[ -n "$FILES" ] || { echo "check-persa: no .html found under $DIR"; exit 0; }

echo "check-persa: $DIR"

# 1 · kit placeholder copy ---------------------------------------------------
KIT=("Replace this word" "SUBJECT WORD" "your headline here" "HEADLINE"
     "Real product name" "App Name 2026" "the thing being said"
     "hand note goes here" "placeholder" "Lorem" "lorem ipsum" "TODO")
for s in "${KIT[@]}"; do
  while IFS= read -r f; do [ -n "$f" ] && hit "KIT" "$f  <- \"$s\""
  done < <(grep -rlF "$s" $FILES 2>/dev/null)
done

# 2 · copy that belongs to the reference creators ---------------------------
BORROWED=("OpenCurve" "Artzen" "artzenmedia" "FINALLY GOOD KEY FRAME"
          "Grok Bot" "Rocktown" "Snell Roundhand" "KALYL")
for s in "${BORROWED[@]}"; do
  while IFS= read -r f; do [ -n "$f" ] && hit "BORROWED" "$f  <- \"$s\" belongs to another creator"
  done < <(grep -rliF "$s" $FILES 2>/dev/null)
done

# 3 · persa-specific style violations ---------------------------------------
# 3a — a transition or animation on the word caption. It hard-cuts. Always.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- .pa-caption must not carry a transition/animation (it HARD-CUTS)"
done < <(grep -rlE '\.pa-caption[^{]*\{[^}]*(transition|animation)' $FILES 2>/dev/null)
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- do not tween .pa-caption in GSAP; it hard-cuts"
done < <(grep -rlE '(to|from|fromTo)\([^)]*\.pa-caption' $FILES 2>/dev/null)

# 3b — hardcoded colour instead of a token
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- hardcoded hex; import assets/tokens.css and use --pa-*"
done < <(grep -rlE '#[0-9a-fA-F]{6}\b' $FILES 2>/dev/null | grep -v tokens.css)

# 3c — animating layout properties instead of transforms
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- animate transforms only, never top/left/width/height"
done < <(grep -rlE '(transition|animation)[^;]*:[^;]*\b(width|height|top|left)\b' $FILES 2>/dev/null)

# 3d — the subject matte must sit above the emphasis word, or the whole style breaks
if grep -rqF 'pa-emph' $FILES 2>/dev/null && ! grep -rqF 'pa-subject' $FILES 2>/dev/null; then
  hit "STYLE" "uses .pa-emph but no .pa-subject matte layer — the emphasis word MUST be occluded by the head"
fi

# 3e — multi-word captions
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- a .pa-caption holds ONE word; split it"
done < <(grep -rlE 'class="[^"]*pa-caption[^"]*"[^>]*>[^<]*[A-Za-z] +[A-Za-z][^<]*<' $FILES 2>/dev/null)

echo
if [ "$FAIL" -eq 0 ]; then echo "clean — ok to render."; exit 0; fi
echo "check-persa FAILED. Fix the above before rendering."; exit 1
