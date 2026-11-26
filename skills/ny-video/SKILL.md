---
name: ny-video
description: Det fasta flödet när en ny video ska göras från en beställning ("jag vill göra en instruktionsvideo…", "gör en reel om…") – fasta frågor, väg A (referensfilm från kända företag → rea-video) eller väg B (tre riktningar ur idébanken i olika genrer), Blender-frågan och materiallistan, anti-slop-kontroll, storyboard, bygg och lärande tillbaka till banken. Använd ALLTID först när en ny video eller reel ska skapas; för ändringar i en befintlig film gäller skills/film.
---

# Ny video – från beställning till godkänd storyboard

Beslut Jonas 2026-11-26. Målet: aldrig generisk AI-slop. Därför börjar varje film på **idénivån** (idébanken
`library/ideas`), inte i en mall eller effekt, och Jonas väljer mellan **hela riktningar** – aldrig effekt för effekt.

## 1. Fasta frågor – ett meddelande, med förslag

Läs först bolagets brand- och faktaskill (`skills/golfkuponger-brand` + `golfkuponger-friskvard`, `faiv-*`). Ställ
sedan dessa fyra i **ett** meddelande, var och en med ett förslag. Svarar Jonas "kör" gäller förslagen.

1. **Var visas den?** (hemsida → 16:9, ofta utan ljud; Reels → 9:16; båda?)
2. **Längd?** (förslag utifrån innehållet och läsregeln)
3. **Vilket material finns?** (appens skärmar, banfoton, VIDEOS/, Tourleif/Chefen, egna inspelningar)
4. **Ska jag leta riktiga, kända företagsfilmer som inspiration?** Ja → väg A. Nej → väg B.

Fakta (köpflöde, siffror) tas ur faktabanken – fråga aldrig om sådant som står där.

## 2A. Väg A – referensfilm (Jonas sa ja)

Följ `skills/referens`: 3–5 riktiga filmer från kända företag som löser **samma problem** (inte samma bransch) →
Jonas väljer → `hamta.py` → rea-video + egen granskning → `storyboard.py --fran-rea` → skriv om varje scen till
vårt innehåll. Banken fyller på utförandet (effekter, text, ljud) som matchar referensens grepp. Gå sedan till 3.

## 2B. Väg B – tre riktningar ur banken (Jonas sa nej)

```bash
python scripts/riktningar.py work/<film> --forslag "<beställningen i ord>"   # 3 idéer i olika genrer → riktningar.json
```
Förslaget väljer idéer i **olika genrer**, lägger nyligen använda och 👎 längre ner och tar med minst en oprövad
idé för bredd. Byt gärna en idé för hand (`python library/tools/find.py "<ord>" --type idea`), men behåll tre genrer.

Fyll i varje riktning som en **helhet**: formspråk, bärande effekt/övergång (ur banken: `--type transition|effect`),
textbehandling (`--type text`), ljud (`skills/ljud`), en **stillbild** och helst ett **rörelsetest på ~3 s** av det
bärande ögonblicket (inte en färdig film). Rendera och visa:

```bash
python scripts/riktningar.py work/<film>        # → out/riktningar.png (stoppar om Blender-frågan/materialet saknas)
```
Jonas väljer en riktning och får låna en sak från en annan ("A men med texten från C").

## Blender-frågan – ställ den alltid

För **varje** riktning och i storyboarden: *hade det blivit mer premium med Blender?* Svara ja / delvis / nej, varför
och vilka scener. Tumregler (`tool-blender`):
- **Ja** när något fysiskt ska kännas äkta: telefon, kort/kupong, golfboll, logga i 3D, miniatyrvärld, makro,
  kamerafärd genom en värld, ljus och reflexer.
- **Delvis** när en enstaka hero-scen lyfts (renderas med alfa och läggs in i HTML-filmen).
- **Nej** när poängen är att det är äkta (POV, filmat, intervju) eller platt grafik/text bär filmen.
Blender renderas headless (Eevee ~1–1,5 s/bildruta i 1080×1920): testa i låg upplösning först. Brand-färger med
`view_transform = 'Standard'`. Safe zones och läsregeln gäller även här.

## Materiallistan – vad behövs för att den ska bli perfekt?

Lista allt filmen behöver, markera **finns** (med var) eller **saknas** (med hur vi skaffar det): skärminspelningar,
foton per bana, filmade klipp, poser för Tourleif/Chefen, ljud, röst, fakta, slutbild i rätt format. Det som saknas
visas i rött på arken. Fråga Jonas om det saknade **innan** bygget – bygg aldrig på gissningar
(jfr "be om underlag per bana").

## Anti-slop – underkänn innan Jonas ser det

En riktning eller storyboard underkänns om den bärs av något av detta:
- stockmontage + kinetisk text ("Upptäck mer", "Ta kontroll", "Det är dags")
- svävande 3D-telefon på gradient utan berättelse, centrerad gradienttitel, glasmorfism utan anledning
- samma whoosh på varje rörelse, syntade ljud, generisk "corporate"-musik
- "I en värld där…", rubriker som kan stå på vilket företags film som helst
- en idé som inte går att säga i en mening, eller som inte hade kunnat vara någon annans film med logga utbytt
Fråga: *kunde den här filmen ha haft en annan logga i slutet?* Om ja – inte klar.

## 3. Storyboard – samma för båda vägarna

Valet blir ett `"storyboard"`-block i `work/<film>/film.json` med `blender` och `material` för hela filmen
(`skills/video-regler` avsnitt 2). `./make.sh storyboard` → `out/storyboard.png` → Jonas godkänner →
`storyboard.py --godkann` → `./make.sh bild` (spärrad tills dess).

## 4. Publikens resultat in i banken (Meta)

Banken ska lära sig av publiken, inte bara av Jonas tycke. Uppdatera minst en gång i månaden och alltid innan en ny
förslagsrunda om resultaten är äldre än 30 dagar (`work/_idebank/resultat.json`, fältet `hamtad`):
1. Dashboard-MCP `data_fraga`, **en fråga per säsongsfönster** (säsongerna i `library/ideas/sasonger.json`: vinter
   jan–feb, vår mar–maj, sommar jun–aug, höst sep–okt, deadline nov–dec; `ads_daily` sparar 120 dagar): table
   `ads_daily`, filter `platform = Meta`, `date_from/date_to` = säsongens dagar, group_by `[ad, format]`, summor
   `cost→kr, impressions→vis, clicks→klick, outcome→kv, purchases→kop, offline_purchases→portal, video_3s_views→v3,
   thruplays→tp`, having `kr >= 20`. Spara som `work/_idebank/export-<säsong>-<år>.json`:
   `{"fran": "...", "till": "...", "rows": [...]}`.
2. `python library/ideas/resultat.py importera work/_idebank/export-*.json` – säsongerna sparas i
   `work/_idebank/historik.json` (samma säsong och år ersätts), så historiken växer även när `ads_daily` rullar vidare.
3. Läs "Ej kopplade": titta på bilden (dashboardens `creatives`/meta-ads `ads_get_creatives`) och lägg en regel i
   `library/ideas/annonskoppling.json` – eller en ny idé om konceptet saknas i banken. `resultat.py berakna` räknar om.

**Mätbarhet:** under 10 kundvagnar eller 500 kr = för lite (påverkar inte); 10+ = indikation (±~50 %, halv vikt);
30+ kundvagnar och 1 500 kr = mätbart (±~30 %, full vikt). Varje idé jämförs med **övriga annonser i samma säsong**
(index), med 90 %-intervall och slutsatsen "säkert bättre/sämre/ingen säker skillnad". Förslagen
(`riktningar.py --forslag`) använder **nuvarande säsong** när den är minst en indikation, annars alla säsonger; arket
visar "Publiken i Meta" per riktning. Siffrorna stannar lokalt i `work/` (repot är publikt).
Vi skapar, publicerar och ändrar inget i Meta – byrån laddar upp; vi läser bara.

## 5. Lärande tillbaka till banken

När Jonas valt eller underkänt: lägg ett omdöme på idén i `library/ideas/make_ideas.py` (`omdome`: datum, Jonas,
👍/👎, kommentar; `anvand` när en film görs) och kör `python library/ideas/make_ideas.py && python
library/tools/build_catalog.py`. Godkänd film på en oprövad idé → `status="verified"` med filmen som bevis. Ny bra
idé som inte fanns → ny post. Det är så nästa förslagsrunda blir bättre och inte upprepar sig.
