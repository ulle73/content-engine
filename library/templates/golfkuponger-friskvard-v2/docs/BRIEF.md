# Friskvård v2 – regissörsbrief

## Filmen på en rad
"Din chef betalar din golf." En premium, energisk reklam som känns som en dyr byråfilm – inte AI-mall.
Tittaren ska tänka "vänta, kan jag göra så?" och sedan veta exakt hur: friskvårdsbidraget → Golfkuponger.

## Varför v1 inte räckte (fixa detta)
v1 (`library/templates/golfkuponger-friskvard-v1`) var: centrerad text på mörk bild, allt tonar in med blur,
samma rörelse i varje scen, ingen produkt, ingen referensgrammatik, ingen poängsatt kritik. Användaren:
"för generisk, typisk AI, inte professionell".

## Format och längd
- Master **9:16 (1080×1920)**, 22–26 s. Därefter **1:1** och **4:5** omkomponerade (inte beskurna) från samma tidslinje.
- Svenska. Inga stilregler – allt rörelsespråk tillåtet. Brand: djupgrönt `#01170F`/`#073C2B`, guld `#D6A536`, kräm `#F8F4EC` som utgångsläge.

## Fakta (bara dessa påståenden)
- Friskvårdsbidrag kan användas till golf: greenfee, range, lektioner (sajten golfkuponger.se/pages/friskvard).
- 300+ anslutna golfklubbar. Köp via förmånsportal (Benifex, ePassi, Söderberg & Partners, Edenred) eller direkt på golfkuponger.se.
- Beloppet: "upp till 5 000 kr/år" står på sajten men är **overifierat i faktabanken (F7)** – använd beloppet, undvik ordet "skattefritt", och notera det i leveransen.

## Bildmaterial
- Banbilder (riktiga, från sajten): `library/templates/golfkuponger-friskvard-v1/assets/*.jpg` (hero-skogsbana, klubb-*). `klubb-osteraker-gk` har en **golfare** – använd för text-bakom-motivet.
- Logotyper: `…/assets/golfkuponger-logo.png` (guldemblem), `golfkuponger-loggan02-2026-04-10-cropped.png` (ordmärke), portal-*.
- **Riktig produkt-UI**: fånga experiment-site i 9:16 med Playwright/Chrome: `https://golfkuponger.se/pages/friskvard?preview_theme_id=201846882645` och `https://golfkuponger.se/?preview_theme_id=201846882645` (priskorten 500–5 000 kr, "Populärast 2 000 kr", portal-sektionen). Avvisa cookie-bannern (icke-nödvändiga). Verktyg: `persa-short.tool.shoot-page-9x16` eller ren Playwright. Rita aldrig om UI:t från fantasin.

## Musik
Två ACE-Step-spår genereras i `work/friskvard-v2/music/` (track-a 120 BPM pop, track-b 100 BPM sports). Mät båda med
`npx hyperframes beats` (eller `library/prompts/motion-studio-playbook` beat_grid.py), lyssna-proxy: loudness-kurva per sekund.
Välj det som har tydligast drop/uppbyggnad, klipp in på en frasstart, låt slutackordet landa på sista bilden.
demucs finns i ACE-Step-miljön om stems behövs (t.ex. ducka trummor under kroken).

## Shotlist (beat-kvantiserad – justera efter vald låt)
| # | Tid | Vad | Byggstenar ur biblioteket |
|---|---|---|---|
| 1 Krok | 0–3 s | Golfaren (Österåker) friläggs; jättestor text **"DIN CHEF"** bakom honom, sedan **"BETALAR"**, **"DIN GOLF."** slår in på slagen. Himlen driver (cinemagraph). Kamerapush + kick på varje slag. | `nextphase.persa.emphasis-behind-head` (z-ordning), frilägg med `npx hyperframes remove-background` eller RVM (`work/persa-short/rvm_env`), `live-carousel.photo.cinemagraph-sky`, `live-carousel.photo.camera-push-shake`, `live-carousel.photo.extrusion-headline` |
| 2 Vändning | 3–6 s | Light-leak flash-through → "Med friskvårdsbidraget." → en glödande guldsfär där **5 000 kr** räknar upp och landar på dropet. | `nextphase.motiongraphics.light-leak` / `hf-skeletons.shader.light-leak`, `nextphase.motiongraphics.device-orb-countup` (omfärgad guld/grön), `hyperframes.registry.text-shimmer` |
| 3 Produkt | 6–13 s | Riktig sajt i 9:16: push-in, gul markeringssvep över "Friskvård", cursor klickar "2 000 kr – Populärast", priskort lyfter ut i 3D. | `nextphase.short.page-highlight`, `nextphase.motiongraphics.device-cursor-card`, `nextphase.short.parallax-zoom` |
| 4 Köpväg | 13–17 s | "Sök Golfkuponger i din portal": fyra portallogotyper som belysta glasbrickor flyger in i ett 3D-rutnät, kameran dyker genom. | `nextphase.motiongraphics.device-grid-3d`, `nextphase.motiongraphics.materials` (glass tile), `nextphase.short.vfx-liquid-background` som övergång |
| 5 Bevis | 17–21 s | **300+ golfklubbar**: banbilder byts på varje slag med whip/zoom, siffran står fast, skylt med klubbnamn. | `hf-skeletons.shader.cinematic-zoom` / whip-pan, `live-carousel.photo.flare-shockwave` på sista slaget |
| 6 CTA | 21–25 s | Guldemblemet blur-revealas exakt på slaget, ordmärke, **"Låt chefen bjuda."** + **golfkuponger.se** med glanssvep; slutackord. | `nextphase.short.logo-blur-reveal`, `golfkuponger.friskvard-v1.emblem-endcard`, `hyperframes.registry.text-shimmer` |

Genomgående: varm filmgrade + grain (`nextphase.short.grade-persa-svg`, `nextphase.short.grain-overlay`), rörelseoskärpa
på snabba moment, något nytt händer var 2–4:e sekund, inget "allt tonar in", ingen centrerad-text-på-gradient som default.

## Ljud
Musik + SFX på uppmätta slag (whoosh vid övergångar, sub-hit på dropet/5 000 kr, klick på cursor, chime på emblemet).
SFX: `library/kits/motion-studio` sfx_lib (verifierade) eller HyperFrames SFX. Mix −14 LUFS, true peak ≤ −1 dBTP
(mall: `library/templates/golfkuponger-friskvard-v1/mix-soundtrack.ps1`).

## Arbetsgång med grindar
1. Fånga UI + frilägg golfaren + välj låt + beatgrid → `work/friskvard-v2/docs/shotlist.md` med exakta tider.
2. Bygg i HyperFrames (utgå från `hf-skeletons.template.a-social-reel` eller fritt), en sub-komposition per scen.
3. **Kritikloop (minst 3 rundor):** kontaktkarta 1 bild/slag, mobiltest (360 px bredd), strip runt snabba moment.
   Poäng 1–10: krok första 2 s · läsbarhet på mobil · rörelsekvalitet · variation · komposition/djup · varumärke · ljudsynk · "känns det dyrt?".
   Logga i `work/friskvard-v2/docs/review_log.md`, fixa de 3 sämsta, upprepa tills allt ≥ 8.
4. `npx hyperframes lint` + `check` rena. Rendera 9:16 high, sedan 1:1 och 4:5.

## Leverans
- `work/friskvard-v2/renders/friskvard-v2-9x16.mp4`, `-1x1.mp4`, `-4x5.mp4`, kontaktkarta, poster.
- Spara som mall: `library/templates/golfkuponger-friskvard-v2/` + `LIBRARY.json` (template + varje återanvändbar scen, verifierade med previews i `library/previews/gk.friskvard-v2.*`), kör `python library/tools/build_catalog.py`.
