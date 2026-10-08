#!/usr/bin/env bash
# vibecode render gate.  Usage:  bash scripts/check-vibecode.sh work/nextphase/videos/<name>
# Exits non-zero on kit copy, borrowed names, and vibecode style violations.
# Portable to macOS bash 3.2 / BSD grep — no mapfile, no grep -P.
set -uo pipefail

DIR="${1:-}"
[ -n "$DIR" ] || { echo "usage: check-vibecode.sh work/nextphase/videos/<name>"; exit 2; }
[ -d "$DIR" ] || { echo "no such directory: $DIR"; exit 2; }

FAIL=0
say()  { printf '  %s\n' "$*"; }
bad()  { printf '\033[31m  FAIL\033[0m  %s\n' "$*"; FAIL=1; }
warn() { printf '\033[33m  WARN\033[0m  %s\n' "$*"; }
ok()   { printf '\033[32m  ok\033[0m    %s\n' "$*"; }

# Only the authored compositions — never assets/, out/, snaps/ or node_modules.
HTML=()
while IFS= read -r f; do HTML+=("$f"); done < <(
  find "$DIR" -name '*.html' \
    -not -path '*/node_modules/*' -not -path '*/out/*' -not -path '*/snaps/*' 2>/dev/null
)

if [ ${#HTML[@]} -eq 0 ]; then
  echo "no compositions found under $DIR"; exit 2
fi

echo "vibecode gate — ${#HTML[@]} composition(s) under $DIR"
echo

# ---------------------------------------------------------------- 1. kit copy
echo "1 · placeholder copy"
KIT='CLAUDE EDIT STUDIO|FUTURE OF VIDEO EDITING|YOU BE THE JUDGE|THE PART NOBODY TALKS ABOUT|A TON of credits|ADJUSTMENT LAYERS|Lorem ipsum|REPLACE ME|Your headline here|THE PIPELINE'
if grep -nEi "$KIT" "${HTML[@]}" 2>/dev/null; then
  bad "kit / reference copy survived — every string must come from THIS video"
else
  ok "no placeholder copy"
fi

KIT2=$(grep -n 'data-kit' "${HTML[@]}" 2>/dev/null)
if [ -n "$KIT2" ]; then
  printf '%s\n' "$KIT2"
  bad "data-kit placeholder strings survived from components/vibecode-system.html"
else
  ok "no data-kit placeholders"
fi

# ------------------------------------------------------- 2. borrowed identity
echo
echo "2 · borrowed names"
if grep -nEi 'Sandy Lee|Jason Cooperson|Claude Edit Studio' "${HTML[@]}" 2>/dev/null; then
  bad "a reference creator's name or product is on screen"
else
  ok "no borrowed names"
fi

# --------------------------------------------------------------- 3. no emoji
echo
echo "3 · emoji"
EMOJI=$("${PYTHON:-python}" - "${HTML[@]}" <<'PY' 2>/dev/null
import re, sys
pat = re.compile('[\U0001F300-\U0001FAFF☀-➿️←-⇿⬀-⯿]')
hits = []
for p in sys.argv[1:]:
    try: txt = open(p, encoding='utf-8', errors='replace').read().splitlines()
    except OSError: continue
    for i, line in enumerate(txt, 1):
        if pat.search(line):
            hits.append(f"{p}:{i}: {line.strip()[:90]}")
print("\n".join(hits))
PY
)
if [ -n "$EMOJI" ]; then
  printf '%s\n' "$EMOJI"
  bad "emoji on screen — build a navy pictogram on a paper tile instead"
else
  ok "no emoji"
fi

# ------------------------------------------------------ 4. token discipline
echo
echo "4 · hardcoded colour / font"
HEX=$(grep -nE '(#[0-9a-fA-F]{3,8}\b|rgba?\()' "${HTML[@]}" 2>/dev/null \
      | grep -vE 'tokens\.css|--vc-|currentColor|transparent')
if [ -n "$HEX" ]; then
  printf '%s\n' "$HEX"
  bad "hardcoded colour — import tokens.css and use --vc-* only"
else
  ok "no hardcoded colours"
fi
FONT=$(grep -nE 'font-family[[:space:]]*:' "${HTML[@]}" 2>/dev/null | grep -v 'var(--vc-')
if [ -n "$FONT" ]; then
  printf '%s\n' "$FONT"
  bad "hardcoded font-family — use var(--vc-display) / var(--vc-body)"
else
  ok "no hardcoded fonts"
fi

# ------------------------------------------------- 5. no foreign token sets
echo
echo "5 · token cross-contamination"
if grep -nE '\-\-(np|mg|pa)-' "${HTML[@]}" 2>/dev/null; then
  bad "another style's tokens are present — never mix token sets"
else
  ok "vibecode tokens only"
fi

# ------------------------------------------------------- 6. .vc-frame root
echo
echo "6 · .vc-frame on the composition root"
MISSING=0
for f in "${HTML[@]}"; do
  if ! grep -q 'vc-frame' "$f"; then
    bad "$f — no .vc-frame; cqh type will silently render tiny"
    MISSING=1
  fi
done
[ $MISSING -eq 0 ] && ok ".vc-frame present in every composition"

# -------------------------------------------------- 7. captions must hard-cut
echo
echo "7 · caption hard-cut"
CAP=$(grep -nE '\.vc-caption[^{]*\{[^}]*(transition|animation)' "${HTML[@]}" 2>/dev/null)
if [ -n "$CAP" ]; then
  printf '%s\n' "$CAP"
  bad ".vc-caption carries a transition — captions hard-cut, 0 frames, always"
else
  ok "captions hard-cut"
fi

# --------------------------------------- 8. transforms only (no layout anim)
echo
echo "8 · animated properties"
ANIM=$(grep -nE '(transition|animation)[^;]*[^-a-z](top|left|width|height)\b' "${HTML[@]}" 2>/dev/null)
if [ -n "$ANIM" ]; then
  printf '%s\n' "$ANIM"
  bad "animating top/left/width/height — transforms only; bars grow with scaleX"
else
  ok "transforms only"
fi

# ------------------------------------------------------------ 9. red is no
echo
echo "9 · red is reserved for negation"
RED=$(grep -nE '(background|background-color|fill|[^-]color)[[:space:]]*:[[:space:]]*var\(--vc-red\)' "${HTML[@]}" 2>/dev/null)
if [ -n "$RED" ]; then
  printf '%s\n' "$RED"
  bad "--vc-red used as a fill or type colour — it marks negation only (X, strike)"
else
  ok "red reserved for the X and the strike"
fi

# ------------------------------------------------------ 10. hard shadows
echo
echo "10 · paper shadows are hard"
SOFT=$(grep -nE 'box-shadow:[^;]*[0-9.]+(px|cqh)[[:space:]]+[0-9.]+(px|cqh)[[:space:]]+[1-9][0-9.]*(px|cqh)' "${HTML[@]}" 2>/dev/null \
       | grep -v 'vc-shadow-card')
if [ -n "$SOFT" ]; then
  printf '%s\n' "$SOFT"
  warn "blurred box-shadow — paper cuts out with a hard offset shadow, zero blur"
else
  ok "shadows are hard-offset"
fi

# ---------------------------------------------------------- 11. real media
echo
echo "11 · real media density"
MEDIA=$(grep -ohE '<(img|video)[[:space:]>]' "${HTML[@]}" 2>/dev/null | wc -l | tr -d ' ')
say "found $MEDIA <img>/<video> elements across ${#HTML[@]} composition(s)"
if [ "$MEDIA" -lt 8 ]; then
  warn "fewer than 8 real assets — the style wants >=1 per 20s, minimum 8"
fi

echo
if [ $FAIL -eq 0 ]; then
  printf '\033[32mPASS\033[0m — vibecode gate clean\n'
else
  printf '\033[31mFAILED\033[0m — fix the above before rendering\n'
fi
exit $FAIL
