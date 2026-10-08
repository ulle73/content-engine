# sfx/ — ljudpaletten (gratisversion)

Kitets originalpalett var **CreatingWithJerry's betalda SFX-pack** utan licens för vidarespridning,
så den togs bort vid importen till content-engine. Filnamnen (som `scripts/mix-sfx.sh` och
`reference/sound-design.md` använder) är desamma — innehållet är nu gratis:

```bash
python library/kits/nextphase/skills/nextphase-short-editing/scripts/make-free-sfx.py          # fyll på det som saknas
python library/kits/nextphase/skills/nextphase-short-editing/scripts/make-free-sfx.py --force  # bygg om allt
```

- **HyperFrames SFX-bibliotek** (Pixabay Content License, fritt även kommersiellt): whoosh, pop, click,
  magic-reveal (sparkle), riser (Pixabay-risern 0,9–3,5 s, crest i slutet), confirm (chime), ping, keyboard (typing).
- **Syntetiserat av `make-free-sfx.py`** (eget material): whoosh-2, swoosh, futuristic-click, swell,
  camera-shutter, highlighter, beep, vinyl-rewind.
- Källa per fil: `SOURCES.txt`.

**Byt gärna röst:** lägg valfri fil här med ett tydligt namn (`sfx/<namn>.mp3|wav`) så hittar
`mix-sfx.sh` den direkt. Fler gratisljud: `~/.claude/skills/media-use/audio/assets/sfx/` (glitch,
impact-bass, notification, error …) eller skillen `/media-use`.

**Betalt, valfritt:** `scripts/gen-sfx.sh` genererar 7 ljud via ElevenLabs (kräver `ELEVENLABS_API`
i `.env`, kostar krediter). Inte standard.

> Mätningarna i `reference/sound-design.md` (gain per ljud, "leading silence": magic-reveal 0,85 s,
> whoosh 0,50 s …) gällde originalpaketet. Den nya paletten har annan förtystnad — mät om med
> `ffmpeg -af volumedetect` / `silencedetect` innan du litar på siffrorna.

Mixern: `bash library/kits/nextphase/skills/nextphase-short-editing/scripts/mix-sfx.sh <in.mp4> <ut.mp4> <cues.txt>`
(anropa den alltid på sin plats i skillmappen — den hittar paletten via `../sfx/`).
