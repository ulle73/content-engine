#!/usr/bin/env bash
# content-engine: kör snap.mjs / export-frames.mjs med puppeteer-core + installerad Chrome.
# Verktygen installeras lokalt i work/bang-motion/_tools (gitignorerat) – inget globalt.
# Bruk:  bash .claude/skills/bang-motion/scripts/run.sh snap <projektmapp> <ut-mapp> 1 3.5 8 ...
#          bash .claude/skills/bang-motion/scripts/run.sh export <projektmapp> [FPS=30]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TOOLS="$ROOT/work/bang-motion/_tools"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$TOOLS"
if [ ! -d "$TOOLS/node_modules/puppeteer-core" ]; then
  (cd "$TOOLS" && npm init -y >/dev/null && npm i --no-fund --no-audit puppeteer-core@24 >/dev/null)
fi
cp "$HERE/snap.mjs" "$HERE/export-frames.mjs" "$TOOLS/"
cmd="${1:?snap|export}"; proj="$(cd "${2:?projektmapp}" && pwd)"; shift 2
url="file:///$(cygpath -m "$proj" 2>/dev/null || echo "$proj")/index.html?clean=1"
case "$cmd" in
  snap)   out="$(mkdir -p "$1" && cd "$1" && pwd)"; shift; URL="$url" node "$TOOLS/snap.mjs" "$out" "$@" ;;
  export) out="$proj/frames"; FPS="${1:-30}"
          URL="$url" OUT="$out" FPS="$FPS" node "$TOOLS/export-frames.mjs"
          ffmpeg -y -loglevel error -framerate "$FPS" -i "$out/f%05d.png" -c:v libx264 -pix_fmt yuv420p -crf 16 -movflags +faststart "$proj/out.mp4"
          echo "klar: $proj/out.mp4" ;;
  *) echo "okänt kommando: $cmd"; exit 1 ;;
esac
