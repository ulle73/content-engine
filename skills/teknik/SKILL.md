---
name: teknik
description: Teknikbanken – bevisade tekniker och metoder för video och karuseller (krokar, retention, vändningar, bevis, CTA, struktur) från reels som gått bra och från våra egna godkända filmer. Använd ALLTID inför varje ny video eller karusell för att välja vilka tekniker som passar bäst, och när någon skickar en länk till en video med en teknik/metod som ska sparas.
---

# Teknikbanken

Mallar säger **hur något ser ut**. Tekniker säger **vad som får folk att stanna, titta klart och agera** – t.ex. "ett
ord knäpps bort och vänder budskapet", "fel utfall → spola tillbaka → rätt utfall", "vägg av allt". Varje teknik är
en post i Content Library med typ `technique` (`library/techniques/`) med roll, varför den fungerar, tajming, hur vi
bygger den tecknat och filmat, en konkret Golfkuponger-idé och **bevis** (källa, kreatör, likes, datum – eller vår egen
godkända film).

Roller: `krok` (0–3 s), `retention` (mönsterbrytning mitt i), `vändning`, `bevis`, `cta`, `struktur` (hela filmens form),
`övergång`, `text`.

## A. Inför varje video och karusell – välj tekniker (obligatoriskt)

Gör detta i `skills/studio` steg 2, före förslagen och beslutsrundan.

1. **Sök per roll** med ord från beställningen:
   ```bash
   python library/tools/find.py "<idé> krok" --type technique --limit 8
   python library/tools/find.py "<idé> retention" --type technique --limit 5
   python library/tools/find.py "<idé> cta avslutning" --type technique --limit 5
   python library/tools/find.py "<idé>" --type technique --medium carousel     # karuseller
   ```
   Läs hela beskrivningen (`library/techniques/<slug>.md`) för de som ser lovande ut.
2. **Välj en kombination:** 1 krok + 1 struktur eller retention (var 2–4 s ska något nytt hända) + 1 cta/avslutning.
   Fler tekniker är inte bättre – välj de som passar budskapet. Golfkupongers slutbild ligger ändå alltid sist.
3. **Motivera i förslaget/beslutsrundan** på en rad per teknik: "Krok: `teknik.ord-knapps-bort` – 'FRISKVÅRD ÄR ~~INTE~~
   GOLF' vänder en vanlig missuppfattning på 2 s." Visa preview om den finns. Låt beställaren byta.
4. **Status:** alla tekniker i banken är **godkända** (`verified`) – Jonas skickar bara bevisade tekniker. Vårt
   **eget utförande** godkänns separat: står `eget_exempel: ej byggt än` så visa ett utkast (stillbild/kort test) i
   beslutsrundan. När beställaren godkänt filmen: lägg filmen som extra bevis med `"godkänd"`, gärna en egen preview i
   `library/previews/teknik.<slug>.jpg` och filmens mall i `exempel`.
5. Hittar du ingen passande teknik: säg det och föreslå närmaste. Uppfinn gärna nytt – och spara det om det godkänns.

## B. Lägga till tekniker från en länk ("här är en video med en bra teknik")

**ChatGPT eller webbappen:** använd nu den integrerade granskningsvägen först. ChatGPT: `suggest_techniques_from_link` ger numrerade förslag men sparar ingenting; visa dem och invänta uttryckligt godkännande innan `approve_techniques` med `confirmed=true` och valda nollbaserade index. Webbappen: fliken **Teknikbanken** → klistra in HTTPS-länk → granska → kryssa för → godkänn. Godkända företagstekniker lagras i Neon och syns i samma `search_content_library` som de statiska teknikerna, men ändrar inte GitHub-filerna. Externa performancepåståenden är aldrig automatiskt bevisade.

**Claude Code för gemensamma, versionshanterade tekniker:** använd befintligt manuellt flöde nedan när tekniken ska delas mellan alla företag.

1. **Hämta och bryt ner** (videon stannar lokalt i `work/references/`, aldrig i git):
   ```bash
   .venv/Scripts/python.exe -I library/techniques/hamta.py "<länk>"
   ```
   Ger `video.mp4`, `meta.json` (kreatör, likes, kommentarer, visningar, datum, längd), `kontaktark.png` (bild var
   0,67 s med tid), `klipp.txt` (bildbyten) och `klipp-NN.png`. Funkar för Instagram, TikTok, YouTube, Facebook och
   direktlänkar. **Karuseller** (`/p/`-länkar) ger `slide-NN.jpg` / `slide-NN.mp4` (+ `slide-NN-kontakt.png` för
   videoslides) och ett kontaktark med alla slides. Kräver inloggning: be användaren ladda ner filen och kör samma steg på filen med ffmpeg.
2. **Titta på riktigt** på kontaktarket och varje klippbild (Read-verktyget på bilderna). Skriv ner klipp för klipp:
   vad händer, när, hur länge, vilken text, vilket ljudgrepp. Läs beskrivningen i meta.json – den förklarar ofta greppet.
3. **En post per distinkt teknik** – inte en per video. En reel kan ge 1–6 tekniker. Kolla dubbletter först:
   `python library/tools/find.py "<teknikens kärna>" --type technique`. Finns den redan: lägg till länken som extra
   bevis i den befintliga posten (`bevis` kan vara en lista) i stället för en ny.
4. **Skriv in den** som en rad i `TEKNIKER` i `library/techniques/make_library.py` – alla fält: `id`
   (`teknik.<kort-slug>`), `namn`, `roll`, `medium`, `kort`, `hur`, `varför`, `tajming`, `tecknat`, `filmat`,
   `golfkuponger` (konkret idé för oss), `taggar` (svenska + engelska sökord), `bevis` (länk, kreatör, likes,
   kommentarer, datum, `lokal_kopia`). Ingen `preview` – kreatörens bilder publiceras aldrig hos oss. Tekniken blir
   godkänd direkt (`tillagd` = dagens datum); `eget_exempel` visar "ej byggt än" tills en egen film godkänts.
5. **Generera och kontrollera:**
   ```bash
   python library/techniques/make_library.py && python library/tools/build_catalog.py
   python library/tools/find.py "<sökord>" --type technique
   ```
6. Jobba på en branch, commit, öppna PR (`main` deployas). Svara användaren med en kort tabell: teknik, roll, varför,
   idé för Golfkuponger.

## Regler

- **Låna mekaniken, aldrig innehållet:** inte referensens bilder, personer, formuleringar, musik, varumärke eller
  påståenden. "This is NOT a hook" blir t.ex. vår egen rad, i vår stil, med Tourleif eller våra riktiga bilder.
- Bevis ska vara verkliga siffror från `meta.json` (inte uppskattade) med datum. Saknas siffror: skriv det.
- Teknikerna är utgångspunkter, inte regler. Husreglerna (`skills/video-regler`: läsregeln, safe zones, slutbild,
  ljud) gäller ändå.
