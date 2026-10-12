# FAIV – "Hitta faran" (9:16, ~39 s)

Godkänd av ägaren 2026-10-12. Tittaren får leta efter faran i mörkret med vanligt helljus, misslyckas två gånger,
sedan tänds extraljusen ("DÄR."), en ljusstråle-slider jämför helljus och extraljus, fakta om reaktionssträcka,
"SE MER. TIDIGARE." och slutkort med logga. Hela tidslinjen med tider, text, effekter och ljud: `MANUS.md`.

Ren Python (numpy/PIL/scipy från repots `.venv`) + ffmpeg. Inget nätverk utom första hämtningen av Mixkit-ljuden.

## Ny film från mallen

```bash
cp -r library/templates/faiv-hitta-faran work/<namn>
cd work/<namn>
./make.sh                       # hämtar Mixkit-ljud, graderar, renderar, mixar -> out/faiv-hitta-faran-9x16.mp4
```

Kör alltid i en kopia under `work/` (gitignorerat) – aldrig i `library/`.

**Byta material:** lägg två exakt linjerade bilder (samma kamera, mörkt och ljust) i `src/dark.webp` och
`src/lit.webp`, och loggan i `src/logo.png`. Uppdatera sedan bildkoordinaterna i `render.py`:
`DEER_BOX`, `EYES`, `VP` (vägens flyktpunkt), `ANCHOR` (push-in) – och i `prep.py`: `BADGES` (märken att retuschera bort)
och zonen runt objektet som ska dämpas (`soft_ellipse(...)` i `main`). Ta bort `build/` innan nästa körning.

## Reglage

| Var | Vad |
|---|---|
| `prep.py` `DARKEN` | Hur svårt det dolda objektet är att se (0,55 godkänt; visa 3 nivåer innan du väljer) |
| `render.py` tidslinjen (`T_S1` …, `S4_LINE2`, `SLIDER_*`, `FACT_*`, `END_*`) | Alla tider. `check_reading()` stoppar renderingen om läsregeln bryts |
| `render.py` `TEXT_Y` | Höjden där all text utom slutkortet börjar |
| `render.py` scenfunktionerna | Texterna (`scene_*`) och listan `TEXTS` (som läsregeln kontrollerar) – ändra båda |
| `audio.py` `CHOICE` | Tändljud (`H1`–`H6`) och sikte (`S1`–`S6`); provning: `python -I audition.py` → `out/ljudprovning.mp4` |
| `audio.py` `MUSIC`, `TRACK_IN`/`TRACK_HIT` | Musik; låten är kalibrerad så att klick → "SE MER." är exakt 8 takter (en assert stoppar annars) |
| `audio.py` `WHOOSH_GAIN_DB` m.fl. | Godkända nivåer – ändra inte utan att beställaren lyssnat |

Ändrar du tiderna mellan klicket och "SE MER." måste avståndet fortfarande vara 8 takter i låten (19,2 s),
eller så väljer du ett annat ställe i låten (`node .claude/skills/animate/tools/beats.mjs`).

## Filer

`prep.py` (retusch, gradering, 2× uppskalning) · `render.py` (bildrutor) · `audio.py` (musik + effekter, stems) ·
`audition.py` (ljudprovning) · `sheet.py` (kontaktkarta av stillbilder: `python -I render.py --stills 1.2 9.9 …`) ·
`fetch_assets.py` (hämtar Mixkit-filerna) · `make.sh` (hela kedjan, loudnorm -14 LUFS) · `MANUS.md`.

## Licenser

- Bilderna och loggan: FAIV:s eget material (endast för FAIV).
- `music/stress-2.m4a`: genererad med ACE-Step, eget material.
- Mixkit-låten och Mixkit-effekterna **ligger inte i mallen** (licensen förbjuder spridning i mallar);
  `fetch_assets.py` hämtar dem. Låten: reklam online och sociala medier ok, inte tv/radio. Se `music/README.txt`
  och `sfx-mixkit/SOURCES.txt`.
- Pixabay-effekterna läses från `~/.claude/skills/media-use/audio/assets/sfx`.
