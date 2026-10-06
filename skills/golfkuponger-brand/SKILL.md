---
name: golfkuponger-brand
description: Golfkupongers visuella identitet och tonalitet för annonser, video, bilder och copy. Använd ALLTID när något ska skapas för Golfkuponger (ad, Reels, story, bild, slutkort, rubrik, caption, Remotion-mall, Higgsfield-prompt) eller när en storyboard/AdBrief granskas, även om ordet "brand" inte nämns.
---

# Golfkuponger – brand

Målet är att varje annons ska kännas som Golfkuponger utan att loggan behövs: premium skandinavisk golf, lugn, trovärdig, aldrig billig eller AI-generisk.

## Känsla i en mening

Ett mjukt morgonljus över en välskött svensk bana, någon som faktiskt spelar, och en kort, självklar text som säger vad du får.

## Bildspråk

**Ja**
- Fotorealistiskt, naturligt och atletiskt. Riktiga människor som spelar, inte poserar.
- Mjukt ljus (morgon och kväll), dämpad mättnad, grönt som dominerande färg.
- Skandinaviska banor: tallskog, hav, öppna landskap, svenskt väder.
- Lugnt och luftigt: gott om andrum runt motivet så text får plats.
- Riktiga skärminspelningar för portal, webb, app och kvitto. Återskapa aldrig UI med AI.

**Nej**
- Amerikansk country club-glans, palmer, öken, överdriven lyx.
- AI-typiska tecken: plastig hud, för perfekta gräsmattor, konstiga händer och klubbor, glow.
- Stock-leenden rakt in i kameran, high-fives, "affärsfolk på golfbana".
- Mättade färger, neonaccenter, tunga filter.
- Text inbakad i genererade bilder. Text läggs alltid ovanpå i Remotion.

## Färger

Tokens kommer från `engine/motion/brand.py` (preset `golfkuponger`), som speglar `gk-design-system.css`. Använd tokens, aldrig egna hex-värden.

| Token | Hex | Användning |
|---|---|---|
| background | `#082f27` | Djupgrön bas, slutkort, textplattor |
| accent | `#0f7a50` | Knappar, markeringar, progress |
| foreground | `#ffffff` | Text på mörkt |
| muted | `#e8f7ef` | Ljusa ytor, sekundär text på mörkt |
| paper | `#f6f8f7` | Ljus bakgrund |
| ink | `#111814` | Text på ljust |
| **gold** | *TODO – saknas i presetet* | Sparsam premium-detalj: tunn linje, CTA-kant, ikon. Aldrig stora ytor. |

Grön dominerar, vitt ger luft och guld används sparsamt.

## Typografi

- Inter (enligt presetet). Rubriker i Semibold/Bold, brödtext i Regular.
- Hooks får skrivas i VERSALER för tempo, men max en versalrad per scen.
- Max 8 ord på skärmen per scen (`AdBrief`-regel). Hellre två korta scener än en lång.
- Text ligger på lugna ytor eller på en halvtransparent grön platta (`background` @ 70–85 %), aldrig direkt på stökig bild.

## Format och safe zones

- **9:16 (Reels och Stories)**: håll text och logga inom de mittersta ~70 % av höjden. Topp ~14 % och botten ~20 % täcks av plattformens UI, och högerkanten av knappar.
- **4:5 / 1:1 (feed)**: mer luft, rubrik i övre tredjedelen.
- Bygg alltid 9:16 först. Feed-formaten är omkomponeringar, inte beskärningar.

## Rörelse (Remotion)

- Lugnt tempo med precisa övergångar. Mjuka ease-out, korta fades, diskreta slides.
- Ingen studsande text, inga glitch- eller shake-effekter, inga snabba zoom-whips mer än en gång per annons.
- Hooken ska synas inom första sekunden. Rörelse i bild från frame 0.
- Ljud: lugn bed, en tydlig ljudcue på hook och CTA. Annonsen ska fungera helt utan ljud.

## Ton i text

- Varm, rak och självklar svenska. "Kompis som tipsar", inte säljare som skriker.
- Konkret före smart: säg vad man får och hur, inte ordvitsar.
- Du-tilltal. Inga utropstecken i rubriker. Max ett emoji i caption, inget i videon.
- Fakta får bara komma från `golfkuponger-friskvard` eller annan verifierad källa (`AdBrief.facts`).

**Bra:** "Ditt friskvårdsbidrag brinner inne. Gör det till golf."
**Dåligt:** "🔥 MISSA INTE!!! Världens bästa golfdeal!!!"

## Slutkort

Djupgrön bakgrund, logga centrerad (officiell logga via `company.official_logo`, aldrig AI-genererad), en rad nytta och `Golfkuponger.se`. 2 sekunder.

## Snabbgranskning (kör före låsning)

1. Känns det skandinaviskt, lugnt och premium? Inget AI-skimmer?
2. Max 8 ord per scen och text inom safe zones?
3. Hook synlig inom 1 s, CTA i sista scenen?
4. Bara brand-tokens och officiell logga?
5. Alla påståenden i `facts` och verifierade?
