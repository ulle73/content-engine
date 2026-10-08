#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# check-zak.sh — the render gate for the ZAK style.
#
#   usage:  bash check-zak.sh work/nextphase/videos/<name>
#
# Four classes of failure:
#   1 · KIT COPY   — placeholder strings from components/ surviving into a segment.
#   2 · BORROWED   — copy lifted from the reference reel. Those words belong to
#                    another creator; they must not appear in a client video.
#   3 · STYLE      — the mistakes specific to zak: an animated caption, a caption
#                    with a shadow, a moving window, a hardcoded colour.
#   4 · IMPORTS    — another style's tokens mixed into a zak composition.
#
# Exit 0 = clean. Exit 1 = do not render.
#
# This gate is static. It cannot see whether the plate is dark enough behind
# the caption — that is scripts/check-contrast.py, on the RENDER. Run both.
# ═══════════════════════════════════════════════════════════════════════════
set -uo pipefail
DIR="${1:-.}"
[ -d "$DIR" ] || { echo "check-zak: no such directory: $DIR" >&2; exit 2; }

FAIL=0
hit(){ printf '  %-9s %s\n' "$1" "$2"; FAIL=1; }

FILES=$(find "$DIR" -name '*.html' -not -path '*/node_modules/*' 2>/dev/null)
[ -n "$FILES" ] || { echo "check-zak: no .html found under $DIR"; exit 0; }

echo "check-zak: $DIR"

# 1 · kit placeholder copy ---------------------------------------------------
KIT=("the definition of" "your title line here" "TITLE LINE" "caption goes here"
     "two to four words" "Real product name" "placeholder" "Lorem" "lorem ipsum" "TODO")
for s in "${KIT[@]}"; do
  while IFS= read -r f; do [ -n "$f" ] && hit "KIT" "$f  <- \"$s\""
  done < <(grep -rlF "$s" $FILES 2>/dev/null)
done

# 2 · copy that belongs to the reference creator ----------------------------
BORROWED=("work-life balance" "sunshine and rainbows" "zacharyron" "Zachary Ron")
for s in "${BORROWED[@]}"; do
  while IFS= read -r f; do [ -n "$f" ] && hit "BORROWED" "$f  <- \"$s\" belongs to the reference creator"
  done < <(grep -rliF "$s" $FILES 2>/dev/null)
done

# 3 · zak-specific style violations ------------------------------------------
# 3a — a transition or animation on the caption. It hard-cuts. Always.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- .zk-caption must not carry a transition/animation (it HARD-CUTS)"
done < <(grep -rlE '\.zk-caption[^{]*\{[^}]*(transition|animation)' $FILES 2>/dev/null)
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- do not tween .zk-caption in GSAP; it hard-cuts"
done < <(grep -rlE '(to|from|fromTo)\([^)]*\.zk-caption' $FILES 2>/dev/null)

# 3b — a shadow, stroke or box on the caption. Measured: there is none.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- .zk-caption carries a shadow/stroke. It has NONE — fix the plate instead"
done < <(grep -rlE '\.zk-caption[^{]*\{[^}]*(text-shadow|-webkit-text-stroke|background)' $FILES 2>/dev/null)

# 3c — a moving window. The ground and the window never move in this style.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- .zk-window is being tweened; the window NEVER moves (the one exception is .zk-window--bleed)"
done < <(grep -rlE '(to|from|fromTo)\([^;]*\.zk-window[^;]*(scale|x:|y:|rotation)' $FILES 2>/dev/null)

# 3d — a drift / push-in on the plate. Measured at 0px over 40s.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- .zk-plate is being drifted or pushed in; zak is locked off"
done < <(grep -rlE '(to|from|fromTo)\([^)]*\.zk-plate' $FILES 2>/dev/null)

# 3e — hardcoded colour instead of a token
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- hardcoded hex; import assets/tokens.css and use --zk-*"
done < <(grep -rlE '#[0-9a-fA-F]{6}\b' $FILES 2>/dev/null | grep -v tokens.css)

# 3f — animating layout properties instead of transforms
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- animate transforms only, never top/left/width/height"
done < <(grep -rlE '(transition|animation)[^;]*:[^;]*\b(width|height|top|left)\b' $FILES 2>/dev/null)

# 3g — the frame root must carry .zk-frame or every cqh token collapses
for f in $FILES; do
  if grep -qE 'zk-(window|caption|title)' "$f" && ! grep -q 'zk-frame' "$f"; then
    hit "STYLE" "$f  <- uses zak classes but no .zk-frame root; all cqh type will render tiny"
  fi
done

# 3h — a one-word caption is persa, not zak.
#      A real one exists now and then: a coined term that IS one word, or the
#      payoff number. Mark those `data-zk-allow="one-word"` on the caption so
#      the exception is visible in the source; they are reported, never hidden.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- a one-word .zk-caption is persa; zak captions are 2-4 words (mark a deliberate one data-zk-allow=\"one-word\")"
done < <(grep -rhoE '<[^<>]*class="[^"]*zk-caption[^"]*"[^<>]*> *[A-Za-z0-9,'"'"'-]+ *<' $FILES 2>/dev/null \
           | grep -v 'data-zk-allow' | grep -q . && grep -rlE 'class="[^"]*zk-caption[^"]*"[^<>]*> *[A-Za-z0-9,'"'"'-]+ *<' $FILES 2>/dev/null)

ALLOWED=$(grep -rhoE '<[^<>]*data-zk-allow="one-word"[^<>]*> *[^< ][^<]*' $FILES 2>/dev/null | sed 's/.*> *//' | sort -u)
if [ -n "$ALLOWED" ]; then
  echo "  note      deliberate one-word caption(s): $(echo $ALLOWED | tr '\n' ' ')"
fi

# 3i — punctuation in a caption. The reference has none in 53 captions; the cut
#      does the punctuating. A comma inside a number is fine (120,000).
#      Entities are stripped first: &#x27; for an apostrophe contains a ';' and
#      would otherwise trip this on every caption that has a contraction.
while IFS= read -r f; do [ -n "$f" ] && hit "STYLE" "$f  <- a .zk-caption carries punctuation; strip it (a comma inside a number is fine)"
done < <(for f in $FILES; do
           grep -ohE 'class="[^"]*zk-caption[^"]*"[^>]*>[^<]*' "$f" 2>/dev/null \
             | sed -e 's/&[a-zA-Z0-9#]*;//g' -e 's/^[^>]*>//' \
             | grep -qE '[.!?]|[^0-9],|,[^0-9]' && echo "$f"
         done)

# 4 · another style's tokens mixed in ---------------------------------------
for pre in pa- mg- np- vc-; do
  while IFS= read -r f; do [ -n "$f" ] && hit "IMPORTS" "$f  <- uses --${pre}* tokens; never mix two style token sets"
  done < <(grep -rlE -- "--${pre}[a-z]" $FILES 2>/dev/null)
done

echo
if [ "$FAIL" -eq 0 ]; then
  echo "clean — ok to render."
  echo "then, on the render:  "${PYTHON:-python}" scripts/check-contrast.py out/seg-NN.mp4"
  exit 0
fi
echo "check-zak FAILED. Fix the above before rendering."; exit 1
