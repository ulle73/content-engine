#!/usr/bin/env bash
# Generate the NextPhase faint-SFX library via the ElevenLabs Sound Effects API.
# Assets are rendered at normal level; "faint" is applied at MIX time, per-video.
# Reusable: edit the gen() list below to add/adjust sounds, then re-run.
#   usage:  bash scripts/gen-sfx.sh

cd "$(dirname "$0")/.." || exit 1   # repo root

# --- load the API key from .env (never printed) ---
if [[ -f .env ]]; then set -a; . ./.env; set +a; fi
KEY="${ELEVENLABS_API:-${ELEVENLABS_API_KEY:-}}"
if [[ -z "$KEY" ]]; then
  echo "ERROR: no ElevenLabs key in .env (expected ELEVENLABS_API=...)"; exit 1
fi

OUT="sfx"
mkdir -p "$OUT"
API="https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128"

fail=0
# gen <name> <duration_seconds> <prompt>
gen () {
  local name="$1" dur="$2" prompt="$3" body code size
  body=$(printf '{"text":"%s","duration_seconds":%s,"prompt_influence":0.5}' "$prompt" "$dur")
  code=$(curl -sS -w '%{http_code}' -o "$OUT/$name.mp3" \
    -X POST "$API" \
    -H "xi-api-key: $KEY" \
    -H "Content-Type: application/json" \
    -d "$body" 2>/dev/null)
  if [[ "$code" == "200" && -s "$OUT/$name.mp3" ]]; then
    size=$(du -h "$OUT/$name.mp3" | cut -f1)
    printf '  ok   %-16s %s\n' "$name.mp3" "$size"
  else
    printf '  FAIL %-16s HTTP %s :: %s\n' "$name.mp3" "$code" "$(head -c 300 "$OUT/$name.mp3" 2>/dev/null)"
    rm -f "$OUT/$name.mp3"; fail=1
  fi
}

echo "Generating NextPhase SFX library -> $OUT/"
gen whoosh         1.2 "A smooth clean whoosh for a camera zoom in or out, airy and subtle, quick, no music, no reverb tail"
gen pop            0.5 "A single soft UI pop, clean and bright, very short, like a bubble pop when text appears, no music"
gen click          0.5 "A crisp soft mechanical click, single clean short UI tap, no music"
gen magic-reveal   2.0 "A magical shimmer reveal, gentle sparkling chimes ascending, clean and light, for unveiling something, no music bed"
gen riser          2.5 "A rising tension riser, smooth building swell increasing in pitch and intensity, cinematic, clean, no beat"
gen swoosh         0.6 "A fast swoosh transition, quick sharp air movement, clean and short, no music"
gen camera-shutter 0.5 "A single DSLR camera shutter snap, crisp mechanical photo click, very short, no music"
echo "Done."
exit $fail
