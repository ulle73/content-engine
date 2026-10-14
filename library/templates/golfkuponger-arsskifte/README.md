# Golfkuponger – "Vad händer med ditt friskvårdsbidrag vid årsskiftet?" (9:16)

Godkänd av Jonas 2026-10-13 ("klarar kvalitetstestet"). Tecknad premiumillustration, ritad som SVG i Chrome och
renderad bildruta för bildruta (deterministiskt), ljud mixat i Python. Två filmer ur samma kod:

| Film | Längd | Sida | Ljud | Manus |
|---|---|---|---|---|
| **Rivkalendern** | 21,5 s | `src/scene.html` | `audio.py` | `MANUS.md` |
| **Spola tillbaka** | 32,9 s | `src/scene2.html` | `audio2.py` | `MANUS-spola.md` |

Båda slutar med slutbilden Spotlight (`edit-renderer/outros/golfkuponger/`).

## Ny film från mallen

```bash
cp -r library/templates/golfkuponger-arsskifte work/<namn>
cd work/<namn>
./make.sh            # alla | v1 | spola  -> out/gk-arsskifte-9x16.mp4, out/gk-arsskifte-spola-9x16.mp4
```

`fetch_assets.py` hämtar alla ljud ur **ljudbanken** (`library/sounds`, Mixkit-ljud laddas ner och md5-kontrolleras)
och bygger loggan från den officiella filen. Kräver node + Playwright (`.claude/skills/animate/setup.ps1`), ffmpeg och
repots `.venv`. Kör alltid i en kopia under `work/` – aldrig i `library/`.

## Återanvändbara delar

| Del | Var | Reglage |
|---|---|---|
| Bordskalender med sidbunt, guldringar, rivna blad som faller ur bild | `src/scene.js` `calendar`, `page`, `tornPages` | `TEAR`-schemat (när varje blad rivs), `CAL_S`, `HINGE` |
| Presentkort som brinner (eld, glöd, gnistor) | `src/scene.js` `note`, `burnAt`, `flameAt` | `BURN_END` (hur mycket som brinner upp) |
| Bollen slår hål → ny värld bakom (hål-reveal) | `src/scene.js` `holeR`, `holePath`, `spring` | `TL.impact`, `revealStart/End` |
| Premiumrummet: ljusstrålar, guldstoft, stenbord, säsongsdekor | `src/scene.js` `background`, `goldDust`, `decor` | `d` (dag 0–91 styr säsongen) |
| **Förbudsmärke som slår ner + larm** ("Tjernobyl") | `src/sf.js` `prohibition`, `alarmLights`; `src/scene2.js` `partStop` | slår i 0,25 s, larm 1,6 Hz |
| **Gråtande golfare** med Golfkupongers logga på kepsen | `src/sf.js` `cryingGuy` | snyftning, tårflöde |
| **❚❚ / ◀◀ / ▶** stora tecken, VHS-tracking, filmen baklänges | `src/sf.js` `pauseIcon`, `rewindIcon`, `trackingSlices`; `src/scene2.js` `partRewind`, `partPlay` | `M.rew`, `REW_TO` (var spolningen landar) |
| Text med markerade ord, läsregeln, safe zones | `textLayer` + `render.mjs` (stoppar vid för kort lästid) | `TEXTS` (fönster i verklig tid), `size` per block |

Stillbilder av delarna: `node sf-render.mjs` (→ `out/sf-sheet.png`), rörliga: `node sf-anim.mjs A-forbud 3`.

## Ljud

Alla val är godkända av Jonas och låsta i koden (`CHOICE`): musik A1/B1, rivljud R1, kopp K1, larm L3, smäll M2,
knapp P1, gråt G1. Ljudbanken har roll, licens, exakt utdrag och nivåtips per ljud: `python library/sounds/sounds.py list`.
Loudness: gain → lågpass 15,5 kHz → limiter (skarpa transienter toppar annars över 0 dB efter AAC).

## Lärdomar från den här filmen (står också i skills/video-regler)

- Läsregeln styr längden – texterna avgör tidslinjen, inte tvärtom.
- Allt viktigt inom safe zones x 65–929, y 270–1250; texten så stor som de tillåter.
- Ingen textskugga i markerade rutor; rutan täcker Å/Ä/Ö.
- Rivna blad ska falla ur bild, inte landa och försvinna.
- Ge tittaren tid att känna det goda ("ååh, golf") innan det tas ifrån en; markera var spolningen stannar.
