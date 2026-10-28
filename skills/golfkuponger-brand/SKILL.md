---
name: golfkuponger-brand
description: Golfkupongers visuella identitet och tonalitet för annonser, video, bilder och copy. Använd ALLTID när något ska skapas för Golfkuponger (ad, Reels, story, bild, slutkort, rubrik, caption, Remotion-mall, Higgsfield-prompt) eller när en storyboard/AdBrief granskas, även om ordet "brand" inte nämns.
---

# Golfkuponger – brand

Målet är att varje annons ska kännas som Golfkuponger utan att loggan behövs: premium skandinavisk golf, trovärdig, aldrig billig eller AI-generisk.

> **Allt här är ett utgångsläge, inte regler.** Bryt mot vad som helst när idén blir bättre av det: andra färger, typsnitt, mer text, glitch, whips, 3D, studs, hårda klipp, fräck humor. Börja i Content Library (`skills/studio`) och välj en färdig, snygg mall. Det enda som inte är smak är fakta: påståenden i reklam kommer från faktabanken i `golfkuponger-friskvard`.

## Känsla i en mening

Ett mjukt morgonljus över en välskött svensk bana, någon som faktiskt spelar, och en kort, självklar text som säger vad du får.

## Fotorealistiska golfbilder — särskild guide

För bilder där golfare, utrustning eller banmiljö ska se ut som verkliga fotografier: följ även [golfrealism-guiden](../../docs/2026-10-28-golf-photo-realism-guide.md). Den innehåller fem valbara motivmallar, fysisk kontroll av händer/klubbor, gräszoner, referensstrategi, hard-fail-kriterier och ett föreslaget A/B-test. Använd den endast för fotografiska uppdrag; illustration, humor och andra uttryck ska inte tvingas in i dokumentär realism. Guiden är evidensinformerad men ännu inte validerad i egna generationstester.

## Bildspråk

**Ja**
- Fotorealistiskt, naturligt och atletiskt. Riktiga människor som spelar, inte poserar.
- Mjukt ljus (morgon och kväll), dämpad mättnad, grönt som dominerande färg.
- Skandinaviska banor: tallskog, hav, öppna landskap, svenskt väder.
- Lugnt och luftigt: gott om andrum runt motivet så text får plats.
- Riktiga skärminspelningar för portal, webb, app och kvitto. Återskapa aldrig UI med AI.

**Brukar se billigt ut (undvik om det inte är poängen)**
- Amerikansk country club-glans, palmer, öken, överdriven lyx.
- AI-typiska tecken: plastig hud, för perfekta gräsmattor, konstiga händer och klubbor, glow.
- Stock-leenden rakt in i kameran, high-fives, "affärsfolk på golfbana".
- Mättade färger, neonaccenter, tunga filter.
- Text inbakad i genererade bilder. Text läggs alltid ovanpå i Remotion.

**Tecknat (illustration/animation)** – Jonas 2026-10-13: platt vektor räcker inte, sikta på *premiumillustration*:
djupgrön bakgrund med mjuka diagonala ljusstrålar och guldstoft/glimtar, ett varmt ljust stenbord med mjuka skuggor
(ljus uppifrån vänster), föremål med volym (sidbunt, guldkanter, guldringar, papperstextur), guld som accent, riktig
eld med glöd och gnistor, säsongsdekor i hörnen (höstkvist, granris med guldkulor). Fortfarande tecknat – inga
fotorealistiska ytor. Exempel: mallen `golfkuponger.template.arsskifte` (`library/templates/golfkuponger-arsskifte`).

## Tourleif – vår återkommande figur

**Använd alltid Tourleif** när Golfkuponger gör tecknat eller animerat innehåll med en person (Jonas 2026-10-13).
Tecknad golfare i grön keps med Golfkupongers **riktiga logga** (officiella `logo-final.png`, aldrig ritad eller AI) och
grön piké med krämvit krage. Uttryck: glad, jublar, förvånad, gråter, lurig, blinkar, skriker. Kod, utseenderegler och karaktärsark:
`library/templates/golfkuponger-tourleif/` (`find.py tourleif`). Nya poser byggs i samma modul och visas för Jonas innan
de används. Filmade sketcher med skådespelare använder samma namn (receptet `gk-recurring-character-sketch`).

**Chefen** är Tourleifs återkommande motspelare när en film behöver en chef, HR eller arbetsgivare (Jonas 2026-10-14):
flint, glasögon, mustasch, marinblå kavaj, grön slips; ovetande, skeptisk, nöjd. `library/templates/golfkuponger-chefen/`.

## Färger

Tokens kommer från `engine/motion/brand.py` (preset `golfkuponger`), som speglar `gk-design-system.css`. Tokens är standard; avvik när en mall eller idé kräver det (t.ex. experiment-site-temats guld `#D6A536`, kräm `#F8F4EC` och mörkgrönt `#01170F`).

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
- Hooks fungerar ofta i VERSALER för tempo.
- Kort text läses snabbast i rörlig video (AdBrief tipsar vid fler än 8 ord per scen, men stoppar inget).
- Text läses bäst på lugna ytor eller en halvtransparent grön platta (`background` @ 70–85 %). Andra lösningar (text bakom motivet, konturtext, textur-fyllning) finns i biblioteket.

## Format och safe zones

- **9:16 (Reels och Stories)**: håll text, logga och produkt borta från översta ~14 % (270 px), nedersta ~35 % (670 px), ~6 % till vänster och ~14 % till höger. Där ligger profilnamn, bildtext, knappar och CTA.
- **4:5 / 1:1 (feed)**: mer luft, rubrik i övre tredjedelen.
- Ofta smart att bygga 9:16 först. Feed-formaten blir bäst som omkomponeringar, inte beskärningar.

## Rörelse (Remotion)

- Lugnt tempo med precisa övergångar. Mjuka ease-out, korta fades, diskreta slides.
- Allt rörelsespråk är tillåtet – glitch, shake, whips, studs, 3D, morphs. Välj det som bär idén; biblioteket har färdiga, verifierade varianter.
- Hooken ska synas inom första sekunden. Rörelse i bild från frame 0.
- Ljud: lugn bed, en tydlig ljudcue på hook och CTA. Annonsen ska fungera helt utan ljud.

## Ton i text

- Varm, rak och självklar svenska. "Kompis som tipsar", inte säljare som skriker.
- Konkret före smart: säg vad man får och hur, inte ordvitsar.
- Du-tilltal brukar fungera bäst. Utropstecken och emoji är tonval, inte förbjudna.
- Fakta får bara komma från `golfkuponger-friskvard` eller annan verifierad källa (`AdBrief.facts`).

**Bra:** "Ditt friskvårdsbidrag brinner inne. Gör det till golf."
**Dåligt:** "🔥 MISSA INTE!!! Världens bästa golfdeal!!!"

## Tonregister

Användaren beskriver ofta tonen med vardagsord ("lite rolig och fräck", "seriös", "stressa dem lite"). Översätt till ett av fyra register och använd mallen som hör till. Inom alla register gäller resten av den här skillen.

| Register | Låter som | Passar | Brukar inte passa | Mall |
|---|---|---|---|---|
| **Lugn premium** | Självklar, varm, få ord | Korta påståenden, tystnad, stora bilder | Brådska, utropstecken | `golf-premium` |
| **Informativ** | Kompis som förklarar | Konkreta steg, riktiga skärmar | Säljfloskler | `friskvard-portal-ad`, `friskvard-direct-ad` |
| **Brådskande** | Vänlig påminnelse med klocka | Deadline (verifierad), förlust ("snart borta") | Skrämsel, falska deadlines, "ALLA förlorar" | `golf-sista-chansen` |
| **Fräck** | Glimten i ögat | Överraskande hook, självironi, golfhumor, lätt överdrift som alla förstår är skämt ("Din chef bjuder på golf") | Håna arbetsgivare, kollegor eller andra golfare, svordomar, sexuella anspelningar, påhittade fakta i skämtform | `golf-fracka` |

**Fräck, gjort rätt:** hooken överraskar, vändningen förklarar med glimten i ögat, och punchline plus bevis landar i något sant. Skämtet får aldrig vara ett faktapåstående. "Din chef bjuder på golf" fungerar bara om vändningen direkt säger vad det betyder (friskvårdsbidraget).

## Text som ska se bra ut stort

- Rubriker skalas så att det **längsta ordet** får plats på en rad. Långa sammansättningar, som "Friskvårdsbidraget", blir därför små. I stora text-scener (hook, punch, statement) ska du hellre skriva "Bidraget" eller "Ditt friskvårdsbidrag" med radbrytning (` / `).
- Tumregel: ca 6 ord i hook-scener och 8 i övriga – bryt när det blir bättre.

## Slutkort

**Alla Golfkuponger-klipp slutar med slutbilden Spotlight** (beslut av Jonas 2026-10-09, bekräftat 2026-10-13):
`edit-renderer/outros/golfkuponger/spotlight-<9x16|4x5|1x1>.mp4`, 3,1 s – svingande guldlogga på mörkgrönt, "Mer golf.
Fler upplevelser." och originalljudet orört. Molnklippet lägger på den automatiskt (`engine/edit/outros.py`); i egna
renderare (HyperFrames, Remotion, Python, `/animate` …) klipps den in sist av dig. Gör inget eget slutkort ovanpå eller
före den – låt filmens sista bild gå över i mörkgrönt (#0c140f, slutbildens första bildruta), så öppnar den sig ur mörkret.

Utan slutbilden (bara om beställaren ber om det): djupgrön bakgrund, officiell logga centrerad (`company.official_logo`,
aldrig AI-genererad), en rad nytta och `Golfkuponger.se`. 2 sekunder.

## Snabbgranskning (frivillig checklista)

1. Känns det skandinaviskt, lugnt och premium? Inget AI-skimmer?
2. Hinner man läsa texten, och ligger den inom safe zones?
3. Hook synlig inom 1 s, CTA i sista scenen?
4. Bara brand-tokens och officiell logga?
5. Alla påståenden i `facts` och verifierade?
