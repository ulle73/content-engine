# Vad händer med ditt friskvårdsbidrag vid årsskiftet? – 9:16, 21,5 s

Tecknad premiumillustration (SVG i Chrome, `src/scene.js`; platt första version i `src/scene-v1-platt.js`), 1080×1920, 30 fps. Djupgrönt med ljusstrålar och guldstoft, stenbord, bordskalender med sidbunt och guldringar, rivna blad landar på bordet, grönt presentkort med guldram brinner, höstkvist → granris med guldkulor i hörnen. Verklig tid nedan (scentid + 0,4 s efter
bläddringen, `sceneTime`). Läsregeln kontrolleras i `render.mjs` och stoppar renderingen. All text börjar på y = 300.
Safe zones: allt viktigt inom x 65–1015, y 270–1250 (kontrollerat med hjälplinjer, `out/safe.png`).

| Tid (s) | Bild | Text | Ljud |
|---|---|---|---|
| 0,00–0,9 | Rivkalender (vänster) på skrivbord, 1 OKTOBER; sedel "FRISKVÅRDS-/BIDRAGET" (höger), höstlöv | – | Musik A (Running Out of Time) |
| 0,15–5,40 | Bladen rivs (0,75, 1,3), sedan allt snabbare genom okt–nov. Sedeln tänds 0,9 och brinner hela tiden | VAD HÄNDER MED DITT / FRISKVÅRDSBIDRAG / **VID ÅRSSKIFTET?** (112 px) | Blad, tändsticka 0,9, sprak som växer, bläddring 1,75–10,4 |
| 5,40–8,75 | Sedeln pulserar, snö när december närmar sig | HAR DU / **FRISKVÅRDSBIDRAG** / KVAR? (116 px) | |
| 8,75–12,40 | December kryper: 25…29 dec (rivs 10,75–12,0); ~86 % av sedeln uppbränd vid nyår | DEN **31 DECEMBER** / BRINNER DET INNE. (124 px) | Riv + tick på sista bladen; musik A hårt stopp 12,4 |
| 12,30–12,70 | 30 dec lyfts, röda 31 syns | – | Tystnad 12,4–12,5 |
| 12,50–12,70 | Golfbollen flyger in och slår igenom "31" | – | Svagt sus 12,5 → **papper rivs 12,70** (R1, ~6 dB lägre än förra versionen) + golf-14 svagt under |
| 12,70–13,75 | Pappersbitar, ljusstrålar, lågan kvävs, hålet växer till vårbana | – | Musik B (Under the Sun) från 12,72 |
| 13,75–17,90 | Bollen studsar (14,0 / 14,42), rullar i koppen 15,18; sedelstumpen singlar ner och vänds till guldkupong "FRISKVÅRDSBIDRAGET – GOLF" (15,35–15,75) | ANVÄND / FRISKVÅRDEN / TILL **GOLF I TID.** (126 px, 13,95–17,9) | Studs, **putt i koppen 15,18** (inbeeld), kupong 15,38 |
| 17,85–18,40 | Iris stänger på koppen till mörkgrönt | – | Musik B tonar ut |
| 18,40–21,50 | Slutbild Spotlight, snabbare tempo (3,1 s) | – | Slutbildens originalljud |

Fakta: 31 december (F6). Beloppet är borttaget (Jonas 2026-10-13: "Friskvårdsbidraget" i stället för 3 000 kr).
Ljud: filmdelen -13,9 LUFS / -1,0 dBTP mätt efter AAC (gain → lågpass 15,5 kHz → limiter). Stems: `out/stem-*.wav`.
Godkända ljud (ändra inte): inbeeld golf_putting (kopp). Rivljud väljs i ljudprovningen (R1–R5). Källor: `SOURCES.txt`.
