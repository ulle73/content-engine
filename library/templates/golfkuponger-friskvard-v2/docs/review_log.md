# Friskvård v2 – kritiklogg

Verktyg: `library/prompts/motion-studio-playbook/review.py` (sheet var 0,5 s = 1 bild/slag, phone 360 px, strip runt snabba
moment) på den RENDERADE mp4:n. Bilderna ligger i `review/r<N>/`. Skala 1–10, hård regi.

## Runda 1 – `renders/draft1-9x16.mp4` (draft, 44 s render)

| Kriterium | Poäng | Bevis |
|---|---|---|
| Krok (0–2 s) | 8 | Ruta 0 visar redan DIN CHEF i slam över riktig bana, golfaren framför typen, BETALAR 1,0, DIN GOLF. 2,0. |
| Läsbarhet mobil | 7 | Allt stort läsbart, men ”eller direkt på golfkuponger.se” (40 px), namnskylt (40 px) små; sajtens brödtext är liten (ok – det är riktig UI, rubriken bär). |
| Rörelse | 6 | Död zon 3,4–4,0 (liten rubrik högst upp, tom mitt); 13,00 klipper in på en TOM ruta; dyket 15,5–16 åker in i Benifex-brickan i stället för genom mitten; frame-bred glansstrimma ligger kvar som artefakt vid 24,5. Ingen motion blur på slams. |
| Variation | 8 | Foto+typ → abstrakt sfär → riktig sajt med kamera/cursor/3D-kort → glasbrickor i 3D → snabba fotoklipp → endcard. |
| Komposition/djup | 7 | S2 tom mitt första sekunden; S6 topptung. Djupet i S1/S3/S4 bra. |
| Varumärke | 8 | Grön/guld/kräm, Playfair (sajtens rubrikfont), riktiga priskortet, riktiga portalloggor, emblem. |
| Ljudsynk | 6 | Cues ligger på rätt tider men renderaren sänkte ljudet 4,2 dB (mätt −18,2 LUFS i mp4) – fel loudness. |
| Känns dyrt? | 7 | Kroken och produktscenen ja; övergångarna S2/S4 och CTA-artefakten drar ner. |

**Tre sämsta → åtgärder**
1. *Rörelse:* S2-rubriken föds stor mitt i bild och FLIP:ar upp när sfären föds (4,00); S4 klipper in med rubrik/sökfält redan i rörelse (syns på ruta 1); brickorna sprängs utåt när kameran dyker så kameran går GENOM mitten; frame-svepet i S6 bort. Registry-komponenten `motion-blur` (shutter 720°) på ordslammen, 300+, glasbrickorna och kortet.
2. *Ljudsynk/loudness:* egen mux efter rendering (`tools/render.sh`): bilden från HyperFrames, ljudet = `assets/soundtrack.wav` (−14 LUFS, TP −1,5) som AAC 256k. Draft 2 mätt: −13,9 LUFS, −1,3 dBTP.
3. *Läsbarhet:* ”eller direkt på…” 40→48 px, namnskylt 40→46 px, S5-vit öppning kortad till 0,2 s så 300+ syns på dropet.

## Runda 2 – `renders/draft3-9x16.mp4`

| Kriterium | Poäng | Bevis |
|---|---|---|
| Krok | 8 | Oförändrad; motion blur på ordslammen syns som riktig shutter-smear (strip 0,93–0,97). |
| Läsbarhet mobil | 8 | Phone-test 360 px (`review/r2/phone.jpg`): alla rubriker, 5 000, chips, portaler, 300+, skylt, CTA läsbara. |
| Rörelse | 8 | 13,00-klippet har innehåll på ruta 1; dyket går genom mitten när brickorna sprängs utåt (15,5–16,0); artefakten borta. Kvar: brickornas blur visade dubbelbild med 10 samples → höjt till 24. |
| Variation | 8 | Oförändrad. |
| Komposition/djup | 7 | 4,00: rubriken låg ovanpå den nyfödda sfären; 4:5-produktintrot (8,0) visade sajten för liten (s=0,59). |
| Varumärke | 8 | Oförändrad. |
| Ljudsynk | 8 | Egen mux: −13,9 LUFS / −1,3 dBTP i mp4. SFX-toppar på 0/1/2/6/10,5/16/20/22/24 s. |
| Känns dyrt? | 7 | CTA:n är ren men lite platt; S2-början tunn. |

**Tre sämsta → åtgärder**
1. *Komposition:* S2-rubriken centreras ovanför sfärens plats och FLIP:ar upp 3,86; guldprickfältet syns svagt redan från 3,0; S3-introposen skalas mot formatets höjd (4:5 s 0,59 → 0,80, 1:1 0,76).
2. *Känns dyrt:* emblemet vrider sig i rymden (rotationY −38° → 0) medan det är suddigt och landar rakt på 22,00; spekulär glans maskad i emblemets eget guld vid 22,05 och på slutackordet 24,00.
3. *Rörelse:* motion-blur samples 24 på brickor/kort, 16 på ord/300+. `hyperframes check` (lint, runtime, layout, motion, contrast) rent i alla tre format efter att avsiktlig lagring markerats (`data-layout-allow-overlap/occlusion` på extruderingarna).

## Runda 3 – slutrendering `renders/friskvard-v2-9x16.mp4` (delivery)

Render: 9:16 delivery 76 s (bild 72 s + mux), 4:5 59 s, 1:1 56 s. Ljud i alla tre: −13,9 LUFS integrerat, −1,3 dBTP.

| Kriterium | Poäng | Bevis |
|---|---|---|
| Krok | 8 | Ruta 0: DIN CHEF i slam med shutter-blur, golfaren framför typen; tre ord på tre kickar 0/1/2 s. |
| Läsbarhet mobil | 8 | `review/r3/phone.jpg`: allt bärande (ord, 5 000 KR/ÅR, markerad rubrik, 2,000 kr, chips, portaler, 300+, skylt, CTA) läsbart vid 360 px. Sajtens brödtext är liten men är riktig UI-kontext, inte budskap. |
| Rörelse | 8 | Inga döda zoner >1 s utom 21,0–22,0 (avsiktlig suddig emblem-vridning före reveal). Shutter-blur på slams/brickor/kort, zoom-blur på fotobyten, whip S5→S6. |
| Variation | 8 | Sex scener med olika skala, riktning och rytm; något nytt var 0,5–2 s. |
| Komposition/djup | 8 | Text-bakom-motiv (S1), 3D-sajt med lyft kort (S3), perspektivgolv + glasbrickor (S4), alla tre format omkomponerade (kontaktkartor `renders/*-contact.jpg`). |
| Varumärke | 8 | Grön/guld/kräm, Playfair + Inter som sajten, riktig UI och loggor, emblem-glans. Bara fakta ur briefen; ”upp till 5 000 kr/år” = F7 overifierat (noterat). |
| Ljudsynk | 8 | **Foto/skylt-synk kontrollerad i slut-mp4:n** (`review/r3/sync.jpg`): bild och namnskylt byter på exakt samma ruta 17,000 / 18,000 / 19,000 (båda styrs av `tl.set` på samma tid). SFX på varje händelse, drop 16,0 = 300+, slutackord 24,0 = glanssvep. |
| Känns dyrt? | 8 | Riktig produkt, riktiga djuplager, filmgrade + korn, motion blur; svagast är 21–22 s och att flera foton är 2× uppskalade. |

Alla ≥ 8 → leverans. Kvarvarande småsaker: se ”kända problem” i leveransrapporten.
