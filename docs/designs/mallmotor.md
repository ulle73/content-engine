# Mallmotor för Content Engine

*   **Författare:** Claude (för Jonas)
*   **Status:** resolved
*   **Datum:** 2026-11-18
*   **Löst:** 2026-11-19

--------------------------------------------------------------------------------

## Översikt

Content Engine ska kunna göra samma innehåll som vi gör för hand i Claude Code, men som mallar i dashboarden.
Första exemplet är bilden "Golfare i [stad]" i 4:5 och 9:16.
Jonas väljer foto, etikett, bannamn, storlekar, mellanrum, loggstorlek och typsnitt, ser resultatet direkt och renderar.
Det han godkänner sparas i Google Drive i en ny mapp, CONTENT, och postas i Discord.

Mallen "slutmall" under "Generera video" fungerar redan ungefär så. Den blir förebilden och flyttas först till det nya upplägget.

Det långsiktiga kravet är att en ny film som Jonas gillar i Claude Code ska bli en mall genom att en mallmapp skrivs och en kontroll går igenom, utan ny kod i dashboarden.

## Problemet

I dag finns tre hinder:

1. **Varje mall kräver egen kod på flera ställen.**
   Slutmallens reglage och gränsvärden finns i tre kopior: i Django (`engine/smsfilm/spec.py`), i sidan (`slutmall.html`) och i `render.mjs`. En ny mall skulle kräva en fjärde och femte kopia, plus ny formulärkod i dashboarden.
2. **Kedjan klarar bara en fil per jobb.**
   En Golfare-annons ger två bilder (4:5 och 9:16). En JPG avvisas i dag.
3. **Godkänt innehåll hamnar inte automatiskt någonstans.**
   Jonas lägger filer i Drive för hand (beslut 2026-10-28). Det finns ingen mappstruktur för publicerat material, och presentkortsfilerna som delas med Gifted ligger i samma Drive.

Dessutom finns en risk i dagens data: ett sparat slutmallsjobb har bara de värden som skiljer sig från standard. Ändras ett standardvärde ändras gamla jobb tyst.

**Lösningen i korthet:** varje mall blir en mapp med en beskrivningsfil (`mall.json`), en sida som följer ett skrivet kontrakt och ett eget renderingsskript. Dashboarden bygger formuläret från beskrivningsfilen. Jobbet sparar alla värden och kan ge flera filer. En Godkänn-knapp laddar upp till Drive via den n8n-väg som redan finns.

## Mål

*   **Mallar i dashboarden:** Jonas kan göra en Golfare-stillbild i 4:5 och 9:16 med reglage, förhandsvisning och rendering, utan att öppna Claude Code.
*   **Slutmallar flyttade:** slutmallarna styrs av `mall.json`, och varje gammalt slutmallsjobb ger samma bild som före flytten. SMS-filmer som pekar på dem fungerar som förut.
*   **Ingen ny dashboardkod per mall:** en ny mall syns i dashboarden när mappen finns och kontrollen går igenom.
*   **Enkelt att göra nya mallar:** den första mallen (Golfare) byggs för hand. Den statiska kontrollen (`build_catalog.py --check`), sidkontrollen (`kontrollera_mallar.mjs`) och en lokal provrendering säger vad som saknas. Ett kommando som gör en film till en mallmapp (`ny_mall`) skrivs senare, när vi vet vad mallarna har gemensamt.
*   **Godkänn till Drive:** knappen lägger filen i en platt mapp, `CONTENT/01 Publicerat/`, med namnet `<kampanj>_<stad>_<variant>_<format>_v<NN>` och postar i Discord.
*   **Presentkortsfilerna skyddade:** n8n-flödet har ett fast mapp-id inbyggt och kan bara skapa nya filer där. Det tar inte emot något mapp-id utifrån och kan inte ändra, flytta eller radera något.
*   **Spårbarhet:** varje jobb sparar vilken kodversion som renderade det (`render_commit`), så att en fil går att felsöka i efterhand.

## Icke-mål

*   Att bygga eller ändra mallar inifrån dashboarden. Mallar byggs i Claude Code.
*   Att flytta SMS-filmen från HyperFrames.
*   Att publicera i Meta. Byrån laddar upp under 2026.
*   En bildbank med alla klubbfoton. Uppladdning per jobb i formuläret räcker först.
*   Sparade stilar, A/B-tester och massproduktion av många städer på en gång. "Duplicera jobb" räcker tills vidare.
*   Att flytta eller röra befintliga filer i Drive (VIDEOS, GOLFKUPONGER, GIFTED).
*   Notis när klipp läggs i `02 Källmaterial`. Den byggs senare, efter Godkänn-flödet.
*   Att rendera gamla jobb med gammal kod. "Rendera igen" använder dagens kod med de sparade värdena.

## Öppna frågor

*   **Golfares reglage:** vilka av de cirka 20 inställningarna visas direkt, vilka ligger under "Fler inställningar" och vilka tas bort? Jag föreslår en lista i Detaljerad plan.
*   **Dagsgräns:** ska 30 jobb per dag höjas för mallar? Med flera filer per jobb räcker 30 längre, så jag föreslår att vänta.

## Viktiga användarflöden (CUJ)

### CUJ 1: Jonas gör en Golfare-bild

*   **Givet:** mallen "Golfare i stad" finns i dashboarden, och Jonas har ett banfoto på datorn.
*   **När:** han väljer mallen, laddar upp fotot som bakgrund, skriver "Linköping" och bannamnet, flyttar fokuspunkten, ändrar loggstorleken och trycker Rendera.
*   **Då:** förhandsvisningen ändras medan han drar i reglagen. Efter renderingen finns två JPG-filer på jobbet, en i 4:5 och en i 9:16. Båda klarar kontrollen av säkra zoner. Jobbet sparar alla värden och `render_commit`, så att det går att spåra vilken kod som gjorde filen.

### CUJ 2: Jonas godkänner en fil

*   **Givet:** ett färdigt jobb med filer, och mappen `CONTENT/01 Publicerat` finns i Drive.
*   **När:** Jonas trycker Godkänn på 4:5-bilden och väljer kampanjen "golfare-i-stad".
*   **Då:** dialogen visar filnamnet innan något laddas upp: `golfare-i-stad_linkoping_a_4x5_v01.jpg`. Efter bekräftelse hamnar filen i `CONTENT/01 Publicerat/`, och ett kort med länk postas i Discord. Godkänner han en ny version av samma bild blir den `v02`. Inga filer utanför `01 Publicerat` påverkas.

### CUJ 3: Claude gör en ny film till en mall

*   **Givet:** en film i `work/<film>/` som Jonas gillar.
*   **När:** Claude skapar mallmappen för hand, skriver `mall.json`, kör `build_catalog.py --check` och `kontrollera_mallar.mjs`, gör en lokal provrendering och öppnar en PR mot `main`.
*   **Då:** mallen syns i dashboarden efter nästa publicering, utan ändringar i Django, i dashboardens sidor eller i GitHub-flödet. Kontrollerna stoppar om `mall.json` inte följer schemat, om ett reglage aldrig används, om `KLAR`-signalen saknas eller om samma tid ger olika bilder.

### CUJ 4: Ett gammalt slutmallsjobb efter flytten

*   **Givet:** ett slutmallsjobb skapat före flytten, som en SMS-film pekar på.
*   **När:** flytten körs och någon öppnar jobbet, renderar det igen eller renderar SMS-filmen.
*   **Då:** formuläret visar samma värden som förut. Migreringen har frusit dagens standardvärden in i jobbet, så ett senare ändrat standardvärde påverkar det inte. Att renderingen ger samma bild kontrolleras mot referensbilder. SMS-filmen hittar sitt slut på samma jobb-id.

### CUJ 5 (senare): Nicholas ser nytt material

*   **Givet:** mappen `CONTENT/02 Källmaterial` finns.
*   **När:** Jonas lägger in nya klipp.
*   **Då:** ett kort postas i Discord med mappnamn och antal filer.

## Teknisk plan (arkitektur)

### Flödet från mallmapp till Drive

```text
library/templates/<mall>/
  mall.json      (reglage, gränser, format, standard per format, utdata)
  <sida>.html    (följer sidkontraktet)
  render.mjs     (mallens eget renderingsskript, byggt på render-bas)
  referens/      (referensbilder per format)
        │
        │  build_catalog.py --check      (statisk kontroll av mall.json)
        │  kontrollera_mallar.mjs        (sidkontroll, egen CI-jobb)
        ▼
Django (engine/smsfilm)
  läser mall.json → bygger formuläret generiskt
  förhandsvisning: sidan i en iframe, PARAMS via postMessage
        │  Jonas trycker Rendera
        ▼
SmsFilmJob (utökat)
  mall-id, ALLA värden (varden), render_commit (bara för spårning)
        │  service.dispatch()
        ▼
GitHub Actions  sms-film-render.yml
  glesa utcheckningen av main tar med library/templates och library/brand
  dashboard-worker.mjs → mallens render.mjs (Playwright + ffmpeg)
  ett varv per utdata × format (t.ex. 4:5 JPG, 9:16 JPG)
        │  flerfilsprotokollet: ett anrop per fil, sedan "klar"
        ▼
R2 + ny tabell SmsFilmOutput  (typ, format, variant, bredd/höjd, längd, fil)
        │  Jonas trycker Godkänn på en fil, väljer kampanj, ser filnamnet
        ▼
engine/review → ny rad i Publicering
  scripts/drive_upload.py ber n8n-flödet drive-uppladdning om en uppladdnings-URL
  n8n använder sitt fasta mapp-id; filen strömmas direkt från servern till Google
        ▼
Drive  CONTENT/01 Publicerat/<kampanj>_<stad>_<variant>_<format>_v<NN>.<ext>
        │
        ▼
Discord-kort med länk (discord.post i engine/review/discord.py)
```

### Mallmappen och `mall.json`

Varje mall är en mapp under `library/templates/`. `LIBRARY.json` pekar på `mall.json` med fältet `"mall": "mall.json"`. Mallar utan det fältet syns inte i dashboarden. Så kan biblioteket ha vanliga mallar (för Claude Code) och dashboardmallar sida vid sida.

`mall.json` (schema `mall/v1`) innehåller:

| Fält | Vad det styr |
| :--- | :--- |
| `schema`, `id` | Schemats namn och mallens id. |
| `titel`, `typ` | Namn i dashboarden; `bild` eller `video`. |
| `sida`, `render` | Filnamn för sidan och renderingsskriptet. |
| `reglage` | Lista med `nyckel`, `typ` (text, tal, färg, val, bild, typsnitt, av/på), `standard`, `min`/`max`/`steg`, `etikett` och `grupp`. Grupp `"Fler inställningar"` fälls ihop. |
| `standard_per` | Standardvärden som beror på ett annat val, t.ex. `{"format": {"4x5": {"fokus_y": 0.4}, "9x16": {"fokus_y": 0.5}}}`. Används för fokuspunkt och textstorlek per format. Nyckeln kan också vara ett val-reglage (steg 2: slutmallens skakning beror på effekten, `{"effekt": {"small": {"skak": 100}}}`). Format gäller först, sedan de andra i ordning. |
| `format` | T.ex. `4x5` = 1080×1350 och `9x16` = 1080×1920. |
| `utdata` | Vilka filer ett jobb ger, t.ex. `[{typ: "bild", format: ["4x5","9x16"]}]`. |

Gränsvärdena finns bara här. Django läser dem för att validera, formuläret för att rita reglagen och sidan får dem via `window.PARAMS`. De tre kopiorna i dag (spec.py, slutmall.html, render.mjs) försvinner.

### Sidkontraktet

Sidan är en vanlig HTML-fil som kan öppnas direkt i webbläsaren. Den följer fyra regler:

1. **In:** `window.PARAMS` sätts innan sidans skript körs (i förhandsvisningen via `postMessage`, vid rendering via Playwright). Utan PARAMS använder sidan standardvärdena, så den går att öppna fristående.
2. **Klar:** sidan sätter `window.KLAR = true` när typsnitt, bilder och video har laddats. Renderaren väntar en bestämd tid och avbryter sedan med ett tydligt fel. Hur lång tiden ska vara mäts i steg 1.
3. **Bildruta:** `window.frame(t)` ritar exakt tiden `t` i sekunder. Samma `t` ska alltid ge samma bild. En stillbild anropas med `t = 0`.
4. **Ut:** `window.INFO` talar om längd, bildfrekvens och eventuella varningar, t.ex. att en text gick utanför säker zon.

Python validerar och avvisar felaktiga värden. Sidan klämmer bara värden inom gränserna, för säkerhets skull, och tar inga egna beslut.

`visa_zoner: true` i PARAMS ritar de säkra zonerna ovanpå bilden. Det används vid lokal provning och av sidkontrollen.

Förhandsvisningen tar emot `postMessage` bara från dashboardens egen adress (`event.origin` kontrolleras).

### Renderingen

Varje mall behåller sitt eget `render.mjs`. Ett gemensamt skelett (`library/templates/_mall/render-bas.mjs`) gör det som alla delar: starta Playwright, sätta PARAMS, vänta på KLAR, ta bildrutor och skriva JPG/PNG eller skicka bildrutor till ffmpeg. Skelettet byggs på de verktyg som redan finns i `.claude/skills/animate/tools/` (`pw.mjs` för Playwright och `framehash.mjs` för att jämföra bildrutor). Mallen skriver bara det som är speciellt för den.

`dashboard-worker.mjs` loopar över `utdata × format` från jobbet och laddar upp varje fil för sig enligt flerfilsprotokollet:

1. Servern skickar med en lista över väntade filer (`worker_payload`).
2. Workern gör ett anrop per fil, med typ, format och variant.
3. Ett sista anrop markerar jobbet som klart.
4. Ett upprepat anrop ger samma resultat. Det bygger på samma lås och sha256-kontroll som `engine/motion/outputs.save_output` redan använder.

Ett fel i en fil gör att hela jobbet markeras som misslyckat, med filnamnet i felmeddelandet.

Workflowen gör en gles utcheckning av `main` som tar med `library/templates` och `library/brand`. `render_commit` sparas på jobbet bara för spårning. Om utseendet ändras av misstag fångas det av referensbilderna, inte av att gammal kod körs.

### Datamodellen

- **`SmsFilmJob` får tre fält:** `mall_id`, `varden` (alla värden, ifyllda med standard vid skapandet) och `render_commit` (bara för spårning). `kind` behålls för SMS-filmer.
- **Ny tabell `SmsFilmOutput`:** jobb, typ (bild/video), format, variant, bredd, höjd, längd och fil (`MediaAsset`). `output_asset` på jobbet behålls och pekar på 9:16-filen, så befintliga sidor och SMS-filmens slutkoppling fungerar som förut. `_slutmall_outro` och funktionerna som använder den uppdateras så att de väljer 9:16-utdata.
- **Ny tabell `Publicering`:** utdata, kampanj, stad, variant, format, version, Drive-filens id, länk, `upload_url` och status. Raden är unik på (kampanj, stad, variant, format, version). Godkännandet låser raderna med `select_for_update`, så två godkännanden samtidigt kan inte få samma version. Kampanj, stad och variant görs om till säkra namn: små bokstäver, å/ä→a, ö→o, mellanslag→bindestreck och bara tecknen a–z, 0–9 och bindestreck.
- **Migrering `0045_mallmotor.py`:** fyller `varden` för varje gammalt slutmallsjobb. Dagens standardvärden fryses in via `slutmall_default(nyckel, effekt)`, plus det som sparats i `form`. Gamla jobb får format 9x16, och en `SmsFilmOutput` skapas för befintlig fil. Reglaget `mall` behåller sitt namn.
- **Storleksgränser oförändrade:** `OUTPUT_MAX_BYTES` (120 MB, `engine/smsfilm/service.py`) och gränsen i `media.py` (80 MB) ändras inte här. En ändring blir en egen PR.

### Säkra zoner

Zonerna finns redan i `edit-renderer/src/safezones.js`: topp 14 %, botten 35 %, sidor 6 % och höger 14 %. Mallarna och sidkontrollen läser den filen. Kopiorna i `slutmall.html` och `render.mjs` tas bort. Ingen ny zonfil skapas.

### Drive

```text
CONTENT/
  01 Publicerat/
    golfare-i-stad_linkoping_a_4x5_v01.jpg
    golfare-i-stad_linkoping_a_4x5_v02.jpg
    golfare-i-stad_linkoping_a_9x16_v01.jpg
```

- **Platt mapp.** Allt godkänt hamnar direkt i `01 Publicerat`. Kampanjen står först i filnamnet, så filerna sorteras ändå per kampanj. `02 Källmaterial` och `03 Arkiv` läggs till senare.
- **Skapas för hand, en gång.** Jonas skapar CONTENT och `01 Publicerat` innan steg 5. Ingen kod skapar mappar.
- **Fast mapp-id i n8n.** Id:t för `01 Publicerat` sparas i n8n-flödet. Servern skickar bara filnamn och storlek. Flödet tar inte emot något mapp-id utifrån, kontrollerar inga föräldramappar och läser inget i Drive. Det kan bara skapa nya filer i den enda mappen.
- **Befintlig väg byggs ut.** `scripts/drive_upload.py` och n8n-flödet `drive-uppladdning` byggs ut i stället för att nya byggs. `request_session` och `put_file` bryts ut till funktioner, eftersom filen i dag avslutar med `sys.exit`. Miljövariablerna `GK_DRIVE_UPLOAD_URL` och `GK_DRIVE_UPLOAD_SECRET` behålls.
- **Filen går aldrig genom n8n.** n8n får bara en liten textförfrågan (filnamn och storlek) och svarar med en uppladdnings-URL. Sedan strömmar servern bilden eller filmen direkt till Google, utan att hela filen ligger i minnet. n8n:s databas på Railway rör aldrig filen.
- **Flödet sparar inga körningar.** Alla fyra inställningarna sätts: `saveDataSuccessExecution=none`, `saveManualExecutions=false`, `saveExecutionProgress=false` och `saveDataErrorExecution=none`. De läses tillbaka efter varje sparning. Flödet svarar bara med felkoder, aldrig med innehåll.
- **Inga dubbletter.** Varje godkännande har en rad i `Publicering`. Avbryts en uppladdning återupptas den med samma `upload_url`, som gäller i ungefär en vecka. Finns redan ett Drive-fil-id på raden görs ingen ny uppladdning.
- Godkännandet sparas i `engine/review` med Drive-länken, så dashboarden visar att filen är publicerad.
- **Inget återkommande godkännande.** Uppladdningen använder n8n:s befintliga Google-koppling ("Google account"), samma som flödet "CE – Ny fil i Drive → Discord". Den kopplingen har körts var 5:e minut sedan 2026-10-28 utan ett enda fel, så den löper inte ut varje vecka. Ingen ny inloggning, ingen testläges-app och ingen förnyelse var 7:e dag behövs.
- **Inga dubbla Discord-kort.** Notisen skickas med `discord.post`. CONTENT ligger utanför de mappar som flödet "Ny fil i Drive → Discord" bevakar, så samma fil ger inte två kort.

### Verktyg för nya mallar

- **`python library/tools/build_catalog.py --check`** kontrollerar statiskt att `mall.json` följer schemat, att gränser och standardvärden hänger ihop och att mallen inte pekar på en bildfil i repot.
- **`node library/tools/kontrollera_mallar.mjs`** öppnar varje mallsida i Chrome och stoppar om ett reglage aldrig läses av sidan, om KLAR saknas, om samma `t` ger olika bilder, om text hamnar utanför säker zon eller om bilden skiljer sig mer än 0,5 % av pixlarna från referensbilden. Den körs i ett eget CI-jobb med Node och Chrome.
- **`node library/templates/<mall>/render.mjs --lokal`** renderar lokalt med samma skelett som molnet.
- **Video följer `skills/ljud`.** Videomallar väljer ljud enligt ljudreglerna. Stillbilder har inget ljud.
- Skillen `/film` får ett avsnitt "Gör en film till en mall" som beskriver stegen.
- **`ny_mall` skrivs senare.** Den första mallen byggs för hand. Ett kommando som gör en film till en mallmapp skrivs när vi vet vad mallarna har gemensamt.

## Alternativ som vägdes

### Alternativ A: En gemensam renderare för alla mallar

*   **Fördelar**: All renderingskod finns på ett ställe. En rättning i
    renderaren gäller direkt för alla mallar.
*   **Nackdelar**: Slutmallen är en video med animerad logga, och Golfare i
    stad är en stillbild med foto, etikett och banskylt. En renderare som ska
    klara båda behöver specialfall för varje mall, och de specialfallen växer
    för varje ny mall.
*   **Varför det valdes bort**: Vi valde ett delat skelett
    (`render-bas.mjs`) som sköter det som är lika i alla mallar: starta
    webbläsaren, vänta på KLAR, ta bilder, koda med ffmpeg, ladda upp. Varje
    mall behåller sin egen `render.mjs` för det som skiljer.

### Alternativ B: Bara en delad fil med gränsvärden

*   **Fördelar**: Minsta möjliga ändring. Tar bort dagens tre kopior av
    gränserna i `spec.py`, `slutmall.html` och `render.mjs`.
*   **Nackdelar**: Ger inget generiskt formulär. Varje ny mall kräver
    fortfarande en egen vy, ett eget formulär och egen validering i Django.
*   **Varför det valdes bort**: Målet är att en ny mall ska kunna läggas till
    utan kod i dashboarden. `mall.json` innehåller gränserna och dessutom
    reglage, format och utdata, så samma fil löser båda problemen.

### Alternativ C: Färdigt formulärbibliotek som läser JSON Schema

*   **Fördelar**: Ett beprövat bibliotek bygger formuläret, och JSON Schema
    är en känd standard för validering.
*   **Nackdelar**: Våra reglage är speciella: bild med fokuspunkt, text där
    `*ord*` blir guldmarkerat och standardvärden som beror på ett annat val
    (till exempel skak som beror på effekt). Biblioteket klarar inte dem utan
    lika mycket egen kod som att bygga formuläret själva. Det blir också ett
    nytt beroende i dashboarden.
*   **Varför det valdes bort**: Vi bygger ett litet eget formulär som läser
    `mall.json` och har ett fast antal reglagetyper.

### Alternativ D: Remotion som motor

*   **Fördelar**: Remotion är byggt för video i React och har bra verktyg för
    förhandsvisning och rendering.
*   **Nackdelar**: Båda mallarna vi har i dag är byggda i HTML och renderas
    med Playwright och ffmpeg, och det fungerar. Att byta motor betyder att
    skriva om dem och bygga en ny worker. Remotion kräver också licens för
    företag över en viss storlek.
*   **Varför det valdes bort**: Bytet ger inget för de här mallarna. Sidkontraktet
    (`window.PARAMS`, `KLAR`, `frame(t)`) hindrar inte att en enskild mall
    senare byggs på annat sätt, så länge den följer kontraktet.

### Alternativ E: Ny jobbtabell (`TemplateJob`)

*   **Fördelar**: Ren början utan gamla fält, och mallar hålls helt isär från
    SMS-filmer.
*   **Nackdelar**: SMS-filmer använder slutmallar som avslutning i dag. En ny
    tabell bryter den kopplingen, och kön, dagsgränsen, granskningen och
    versionerna måste byggas om eller dubbleras.
*   **Varför det valdes bort**: Det är säkrare att lägga till fält i
    `SmsFilmJob` (mall_id, varden, render_commit) och lägga filerna i en ny
    tabell `SmsFilmOutput`.

### Alternativ F: En fil per format eller variant som eget jobb

*   **Fördelar**: Enkel modell: ett jobb ger en fil. Ett fel i ett format
    stoppar inte de andra.
*   **Nackdelar**: Varje jobb kostar ungefär en minut i GitHub Actions bara
    för att starta. En stad i två format och tre varianter blir sex jobb, och
    dagsgränsen på 30 jobb tar slut efter fem städer.
*   **Varför det valdes bort**: Ett jobb loopar över utdata × format och
    sparar varje fil som en rad i `SmsFilmOutput`. Om en fil misslyckas syns
    det på just den raden.

### Alternativ G: Egen Google-inloggning i appen (`drive.file`)

*   **Fördelar**: Med `drive.file` ser appen bara filer den själv skapat, så
    den kan inte läsa eller ändra presentkortsfilen.
*   **Nackdelar**: Ett nytt lösenord att sköta. Den nya Google-appen skulle
    börja i testläge, där inloggningen löper ut efter 7 dagar tills appen
    granskats av Google. (Det gäller bara det här bortvalda alternativet, inte
    den valda vägen via n8n.) Inloggningsrutan kan inte
    visas i dashboardens ram. Presentkortsfilen blir inte säkrare totalt,
    eftersom n8n:s inloggning med full åtkomst finns kvar. Appen ser inte
    heller mappar eller klipp som Jonas lägger in för hand.
*   **Varför det valdes bort**: Vi använder den befintliga vägen via n8n
    (`scripts/drive_upload.py`), där filen går direkt till Google. Skyddet
    ligger i n8n-flödet: det har ett fast mapp-id och får bara skapa filer
    där.

### Alternativ H: Bildbank först

*   **Fördelar**: Jonas väljer bild ur en lista med klubbar i stället för att
    ladda upp. Klubbens namn kan fyllas i automatiskt.
*   **Nackdelar**: Kräver import av cirka 360 klubbars bilder till R2,
    metadata per klubb och ett sökbart väljargränssnitt innan första mallen
    kan användas.
*   **Varför det valdes bort**: Golfare i stad kan starta med ett
    uppladdningsfält och ett fokusreglage. Banken kan läggas till senare som
    en ny reglagetyp utan att mallarna ändras.

### Alternativ I: Delade JS-byggstenar direkt (etikett, banskylt, logga)

*   **Fördelar**: Gul etikett med ÅÄÖ-fix, banskylt med plats-ikon och logga
    skrivs en gång och ser likadana ut i alla mallar.
*   **Nackdelar**: Med bara en mall som använder dem vet vi inte vilka delar
    som verkligen är gemensamma. En ändring i en delad byggsten kan tyst
    ändra utseendet i alla mallar, även i redan godkända.
*   **Varför det valdes bort**: Byggstenar lyfts ut först när en andra mall
    behöver samma sak. Referensbilderna i varje malls `referens/` fångar en
    ändring som av misstag ändrar utseendet.

## Icke-funktionella krav

### Säkerhet och skydd av Drive

- **Gifted-filerna rörs aldrig.** Mappen GIFTED och presentkortsfilen som delas med getgifted.com ligger utanför CONTENT. n8n-flödet har ett fast mapp-id (`01 Publicerat`) och kan bara skapa filer där. Det tar inte emot något mapp-id utifrån och kan inte läsa, ändra, flytta, dela eller radera något.
- **Inga filer genom n8n.** n8n tar bara emot filnamn och storlek. Bilder och filmer strömmas direkt från servern till Google. Flödet sparas med `saveDataSuccessExecution=none`, `saveManualExecutions=false`, `saveExecutionProgress=false` och `saveDataErrorExecution=none`, och inställningarna läses tillbaka efter varje sparning. n8n-databasen på Railway växer därför inte av uppladdningarna.
- **Inget återkommande godkännande.** Inloggningen mot Google är den som redan finns i n8n och som har gått var 5:e minut sedan 2026-10-28 utan fel. Ingen ny Google-app, ingen testläge-inloggning och inget att godkänna var 7:e dag.
- **Inga foton i git.** Repot är publikt. Bakgrundsbilder och klipp ligger i R2 eller lokalt i `work/`, aldrig i `library/`. `build_catalog.py --check` stoppar en mall som pekar på en bildfil i repot.
- **Hemligheter ligger utanför repot.** `GK_DRIVE_UPLOAD_URL` och `GK_DRIVE_UPLOAD_SECRET` är miljövariabler på Render. Mapp-id:t för CONTENT finns bara i n8n-flödet. Inget av dem skrivs i `mall.json`, i loggar eller i jobbets `varden`.
- **Förhandsvisningen är avgränsad.** En generisk vy `slutmall_preview` (`<mall>/<fil>`) serverar bara filer som står på en lista över tillåtna filer. Dagens CSP behålls, och adresserna byggs med namngivna URL:er.
- **Bara inloggade får skapa och godkänna.** Mallsidorna och Godkänn-knappen ligger bakom samma inloggning som resten av dashboarden.

### Prestanda och gränser

- **Kön har samma tak som i dag:** högst 3 aktiva jobb och 30 jobb per dygn. En kampanjkörning (till exempel 10 städer i 2 format) räknas som ett jobb med flera utdatafiler, inte som 20 jobb.
- **Väntetid.** En bild tar ungefär 1–2 minuter från klick till färdig fil, eftersom GitHub Actions behöver ungefär en minut för att starta. Förhandsvisningen i dashboarden visas direkt i webbläsaren, utan att vänta på renderingen.
- **Filstorlek.** Gränserna är oförändrade: 120 MB i `engine/smsfilm/service.py` och 80 MB i `media.py`. En film som blir större stoppas med ett tydligt fel i stället för att laddas upp. En ändring av gränserna blir en egen PR.
- **Sidan måste bli klar i tid.** Svarar mallsidan inte med KLAR inom gränsen avbryts jobbet med felet "Mallen laddade inte", och vilken mall och vilka värden det gällde sparas. Gränsen mäts i steg 1.
- **Strömmad uppladdning och nedladdning.** Filer läses och skickas i delar, så att servern aldrig har en hel film i minnet.

### Driftsäkerhet

- **Misslyckad Drive-uppladdning går att göra om.** Filen ligger kvar i R2. Jobbet visar "Uppladdning misslyckades" och en knapp för att försöka igen. Ett nytt försök fortsätter med samma `upload_url` från raden i `Publicering`. Finns redan ett Drive-fil-id laddas inget upp igen, så ingen dubblett skapas.
- **Versionsnummer krockar inte.** Numret i filnamnet (`v01`, `v02` …) räknas fram i databasen när filen godkänns, med radlås, inte i Drive. Två godkännanden samtidigt kan inte få samma nummer.
- **Gamla jobb fungerar efter flytten.** Ett slutmallsjobb skapat före flytten öppnas, visas och kan köras om med samma resultat (se CUJ 4).

### Felsökning

- **Status syns i dashboarden.** Varje jobb visar steget det står i (köad, renderar, klar, uppladdad, fel) och ett felmeddelande på vanlig svenska.
- **Varje fil går att spåra.** Varje utdatafil hör till ett jobb som sparar mall, värden och `render_commit` (den kodversion som renderade den). En fil i Drive går därför att felsöka i efterhand.
- **n8n sparar inga körningar.** Flödet svarar bara med felkoder. Fel syns i dashboarden, inte i n8n:s körningslista.

### Utrullning och återgång

- **Ordning.** Slutmallarna flyttas först till den nya strukturen och kontrolleras mot referensbilder. Först därefter byggs Golfare-mallen och sist Godkänn och Drive.
- **Varje steg kan publiceras för sig.** Servern tar emot både det gamla och det nya formatet från workern innan workern byts. Ett steg kan alltså gå till `main` utan att nästa är klart.
- **Migreringen fyller i nya fält** (`mall_id`, `varden`, format 9x16 för gamla jobb). Den ändrar inga befintliga värden och kan backas.
- **Återgång.** En trasig ändring backas genom att PR:en återställs. Referensbilderna i `<mall>/referens/` fångar en ändring som av misstag ändrar utseendet innan den når `main`.
- **Allt går via PR.** `main` är produktion på Render. Ingen ändring går direkt till `main`.

### Underhåll

- **En sanning per mall.** Gränser och standardvärden finns bara i `mall.json`. Dagens tre kopior (i `spec.py`, `slutmall.html` och `render.mjs`) tas bort.
- **Fel upptäcks före produktion.** `build_catalog.py --check` körs i testerna och stoppar en mall vars `mall.json` saknar fält eller har värden utanför gränserna. `kontrollera_mallar.mjs` körs i ett eget CI-jobb och stoppar en sida som inte uppfyller sidkontraktet eller inte stämmer med referensbilden.
- **En ny mall rör ingen gemensam kod.** Att lägga till en mall betyder en ny mapp under `library/templates/`. Django, formuläret och kön behöver inte ändras.

## Detaljerad plan

Arbetet delas i fem byggsteg. Varje steg blir en egen PR mot `main`, kan publiceras för sig och ska vara färdigt och kontrollerat innan nästa börjar. Ett sjätte steg listar sådant som kan byggas senare.

### Filer som skapas eller ändras

**Nya filer**

| Fil | Vad den gör |
| :--- | :--- |
| `library/templates/_mall/mall.schema.json` | JSON-schemat för `mall/v1`. Används av Django och `build_catalog.py --check`. |
| `library/templates/_mall/render-bas.mjs` | Det gemensamma skelettet, byggt på `pw.mjs` och `framehash.mjs`: starta Playwright, sätt PARAMS, vänta på KLAR, anropa `frame(t)`, skriv JPG/PNG eller skicka bildrutor till ffmpeg, läs `window.INFO`. |
| `library/tools/kontrollera_mallar.mjs` | Sidkontrollen: öppnar varje mallsida i Chrome och kontrollerar sidkontraktet, säkra zoner och referensbilder (högst 0,5 % ändrade pixlar). |
| `library/templates/golfkuponger-slutmallar/mall.json` | Slutmallarnas reglage och gränser, flyttade från `spec.py`. |
| `library/templates/<mall>/referens/` | Referensbilder per format för varje mall. |
| `engine/smsfilm/mallar.py` | Läser alla `mall.json`, validerar värden mot gränserna och fyller i standardvärden per format (`standard_per`). Ersätter de delar av `spec.py` som handlar om slutmallar. |
| `engine/review/drive.py` | Skapar raden i `Publicering`, anropar `drive_upload.py`, återupptar med `upload_url` och sparar Drive-länken. |
| `engine/migrations/0045_mallmotor.py` | Nya fält, tabellerna `SmsFilmOutput` och `Publicering`, och datamigreringen av gamla slutmallsjobb. |
| `engine/test_mallar.py` | Tester för läsning och validering av mallar, migreringen och flera utdatafiler. Testnamnen anger vilket steg de hör till. |
| `engine/test_drive.py` | Tester för Godkänn och Drive, med n8n och Google ersatta av testsvar. Testnamnen anger vilket steg de hör till. |

**Ändrade filer**

| Fil | Ändring |
| :--- | :--- |
| `engine/smsfilm/models.py` | `SmsFilmJob` får `mall_id`, `varden`, `render_commit`. Nya modeller `SmsFilmOutput` och `Publicering`. |
| `engine/smsfilm/spec.py` | Slutmallarnas gränser tas bort. SMS-filmens egna gränser blir kvar. |
| `engine/smsfilm/views.py` | En generisk vy för alla mallar: lista, formulär, förhandsvisning, rendera, godkänn. `slutmall_preview` blir generisk (`<mall>/<fil>`) med en lista över tillåtna filer. CSP behålls och URL:erna är namngivna. |
| `engine/smsfilm/service.py` | `dispatch()` skickar mall-id, värden, `render_commit` och listan över väntade filer. `_slutmall_outro` och funktionerna som använder den väljer 9:16-utdata. Storleksgränsen är oförändrad. |
| `engine/smsfilm/worker_api.py` | Flerfilsprotokollet: ett anrop per fil, ett sista "klar"-anrop, upprepade anrop ger samma resultat. Tar emot både gammalt och nytt format. |
| `engine/review/…` | Godkännande med kampanjval, filnamn i dialogen, versionsräknare med radlås och knappen "Försök igen". |
| `engine/review/discord.py` | Godkännandet postar med `discord.post`. |
| `scripts/drive_upload.py` | `request_session` och `put_file` bryts ut till funktioner som kan anropas från Django. Strömmad uppladdning. |
| `templates/engine/mall_form.html` (ny) och `sms_film.html` | Formuläret ritas från `mall.json`. "Fler inställningar" fälls ihop. Förhandsvisningen är en iframe som får värdena via `postMessage` och kontrollerar `event.origin`. |
| `library/templates/golfkuponger-slutmallar/slutmall.html`, `render.mjs`, `LIBRARY.json` | Följer sidkontraktet och använder `render-bas.mjs`. Gränserna och zonkopiorna i sidan och skriptet tas bort. |
| `library/templates/golfkuponger-golfare-i-stad/` | Ändras: får `mall.json`, en sida som följer sidkontraktet och `referens/`. `annonser/*.json`, `LIBRARY.json` och `slutscen.mjs` behålls. `rendera.mjs` ersätts av ett `render.mjs` byggt på `render-bas.mjs`. |
| `library/templates/imessage-samtal/dashboard-worker.mjs` | Loopar över `utdata × format` och laddar upp en fil i taget enligt flerfilsprotokollet. |
| `.github/workflows/sms-film-render.yml` | Den glesa utcheckningen tar med `library/templates` och `library/brand`. |
| `.github/workflows/…` (CI) | Nytt jobb med Node och Chrome som kör `kontrollera_mallar.mjs`. |
| `library/tools/build_catalog.py` | Ny flagga `--check` för statisk kontroll av `mall.json`. |
| `skills/film/SKILL.md` | Nytt avsnitt "Gör en film till en mall". |

`engine/media.py` ändras inte.

**Utanför repot**

- **n8n:** det befintliga flödet `drive-uppladdning` byggs ut med det fasta mapp-id:t för `01 Publicerat`. Alla fyra lagringsinställningarna sätts och läses tillbaka efter varje sparning.
- **Render:** inga nya miljövariabler. `GK_DRIVE_UPLOAD_URL` och `GK_DRIVE_UPLOAD_SECRET` används.
- **Drive:** Jonas skapar mappen CONTENT med undermappen `01 Publicerat` för hand, en gång, före steg 5. Ingen kod skapar eller ändrar något utanför `01 Publicerat`.

### Byggsteg

**Steg 1: Mallformatet och renderingsskelettet**

- Skapa `mall.schema.json` och `render-bas.mjs` (byggt på `pw.mjs` och `framehash.mjs`).
- Lägg till `--check` i `build_catalog.py` och skriv `kontrollera_mallar.mjs` med eget CI-jobb.
- Mät hur lång tid en sida behöver för att bli KLAR och sätt gränsen därefter.
- **Klart när:** `build_catalog.py --check` och `kontrollera_mallar.mjs` godkänner en liten testmall och stoppar fyra trasiga varianter av den (fel i schemat, saknad KLAR, olika bild för samma `t`, text utanför säker zon). Inget i dashboarden ändras ännu.

**Steg 2: Slutmallarna flyttas till den nya strukturen**

- Skriv `mall.json` för slutmallarna. Låt `slutmall.html` och `render.mjs` följa sidkontraktet och läsa zonerna från `edit-renderer/src/safezones.js`.
- Behåll de gamla gränserna i `spec.py` tills steg 3, så att dashboarden fungerar under tiden.
- **Klart när:** fem befintliga slutmallsjobb (olika portaler, effekter och format) renderas lokalt med `--lokal` och jämförs bildruta för bildruta mot de filer som redan ligger i R2. Skillnaden ska vara högst 0,5 % av pixlarna per bildruta, och ingen bildruta får sakna text eller logga. Bilderna sparas som referensbilder i `golfkuponger-slutmallar/referens/` och visas för Jonas.

*Utfall 2026-11-19.* Det fanns bara tre slutmallsjobb i produktionen, och bara ett av dem var renderat med dagens kod. Jämförelsen gjordes därför i två delar:

- Sex varierade fall med olika portaler, effekter, format och stilval. Varje fall renderades med den gamla koden från `main` och med den nya, lokalt. Högst 0,008 % ändrade pixlar per bildruta, och längd och antal bildrutor var lika.
- Produktionsjobbet jämfördes mot sin fil i R2, som renderats på Linux. Högst 0,32 % ändrade pixlar per bildruta.

Två ändringar i sidkontrollen följde av det här:

- **Slump:** sidkontrollen räknar bara synliga skillnader. Chrome ritar oskärpa med ett brus på högst 6 av 255.
- **Zoner:** för video kontrolleras zonerna på slutbilden och vid tiderna i `INFO.zon_tider`, inte mitt i en effekt. Smäll gör ordet 2,3 gånger större medan det landar.

Förhandsvisningen hämtar nu sidan via `sms-film/mall/<mall>/<fil>`, eftersom sidan importerar `_mall/sida.mjs`. Den glesa utcheckningen i `sms-film-render.yml` tar med `library/templates/_mall` och `edit-renderer/src`.

*Utfall steg 3–5, 2026-11-19 (Claude).*

**Steg 3: sparat och kontrollerat**
- **Var formaten sparas:** formaten sparas i ett eget fält, `formats`, på jobbet, inte i `varden`.
- **Formatberoende standardvärden:** standardvärden som beror på formatet lämnas utanför `varden`, så att sidan väljer rätt värde per format.
- **Mallens mapp:** workern lägger till mallens mapp i den glesa utcheckningen när mappen saknas (`git sparse-checkout add`). En ny mall kräver därför ingen ändring i workflowen.
- **Prov i webbläsaren:** formuläret, förhandsvisningen och en hel körning med den riktiga workern mot en lokal server provades. Ett jobb gav både 9:16 och 4:5.

**Steg 4:** mallen är jämförd sida vid sida med `golfare-i-linkoping_A-still_4x5.jpg` och ger samma utseende. Banans namn står med flit under säkra ytan i 9:16, så det räknas inte i sidkontrollens zoner.

**Steg 5: fyra avvikelser från designen**
- **Eget n8n-flöde.** Ett nytt flöde, "CE – Publicera till CONTENT" (`content-engine-publicera`), har det fasta mapp-id:t. Det används i stället för att bygga ut `drive-uppladdning`, eftersom Claudes andra uppladdningar använder det flödet med valfri mapp. Lagringsinställningarna är satta och lästa tillbaka.
- **Mappen är delad.** n8n:s Google-koppling är kontot jonas.rydqvist89@gmail.com. CONTENT skapades därför i Min enhet hos info@svenskagolfkuponger.se, där VIDEOS och GIFTED ligger, och delades som redigerare med samma två konton som VIDEOS. Den fick ingen publik länk.
- **Var koden ligger.** `Publicering` och uppladdningen ligger i `engine/smsfilm` (`publicera.py`), bredvid filerna de publicerar, i stället för i `engine/review`.
- **Discord-notisen** skickas till företagets granskningskanal med `discord.post`.

**Steg 5: provat mot riktiga Drive**
- En fil på 708 byte skickades med GIFTED-mappens id. Den hamnade ändå i `01 Publicerat`.
- Två godkännanden av samma bild i dashboarden gav `v01` och `v02`.
- GIFTED-mappen och presentkortsfilerna har oförändrad ändringstid.

**Steg 3: Datamodellen och det generiska formuläret**

- Nya fält, `SmsFilmOutput`, migreringen `0045_mallmotor.py` och `mallar.py`.
- Den generiska vyn, formuläret och den generiska `slutmall_preview`. Slutmallarna visas nu genom dem.
- Flerfilsprotokollet i `worker_api.py`. Servern tar emot både gammalt och nytt format.
- `dashboard-worker.mjs` och workflowen hanterar flera filer.
- Ta bort slutmallarnas gränser i `spec.py`, `slutmall.html` och `render.mjs`.
- **Klart när:**
  - alla tester går igenom, även de gamla för SMS-filmen, och testerna med radlås körs mot Postgres,
  - migreringen körs fram och tillbaka på en kopia av produktionsdatabasen utan att något befintligt värde ändras,
  - en slutmall skapas i förhandsvisningen (preview_start) och renderas till både 9:16 och 4:5 i samma jobb, och båda filerna syns i dashboarden,
  - ett gammalt slutmallsjobb öppnas och renderas om, och resultatet stämmer med referensbilden (CUJ 4).

**Steg 4: Mallen Golfare i stad**

- Mallen byggs för hand i den befintliga mappen `golfkuponger-golfare-i-stad/`, med reglagen i listan nedan. Inget `ny_mall`-kommando skrivs.
- Referensbilder för 4:5 och 9:16 läggs i `referens/`.
- **Klart när:** Jonas gör en Golfare-bild för en ny stad i dashboarden och får 4:5 och 9:16 utan att röra koden. Bilden jämförs bredvid originalet (originalbilden i Drive). `--check` och `kontrollera_mallar.mjs` godkänner mallen, och `visa_zoner` visar att etikett, bannamn och logga ligger inom säkra zoner.

**Steg 5: Godkänn och Drive**

1. **Först en kontroll, innan någon kod skrivs.** Jonas har skapat CONTENT och `01 Publicerat`. Flödet `drive-uppladdning` byggs ut med det fasta mapp-id:t, och `scripts/drive_upload.py` provas med en testfil på några kB. Det ska visa att filen hamnar i `01 Publicerat` och att uppladdnings-URL:en fungerar för servern utan egen Google-inloggning. Fungerar det inte får Jonas veta det innan något mer byggs.
2. Flödets fyra inställningar läses tillbaka: `saveDataSuccessExecution=none`, `saveManualExecutions=false`, `saveExecutionProgress=false`, `saveDataErrorExecution=none`.
3. `Publicering`, `drive.py`, kampanjval, filnamn i dialogen, versionsräknaren, `discord.post` och "Försök igen".
- **Klart när:**
  - en godkänd fil hamnar i `CONTENT/01 Publicerat/` med rätt namn och ett Discord-kort med länk,
  - ett andra godkännande av samma bild ger `v02`,
  - ett anrop till n8n som skickar med ett annat mapp-id ignoreras, och filen hamnar ändå i `01 Publicerat`,
  - en avbruten uppladdning som görs om fortsätter med samma `upload_url` och ger ingen dubblett,
  - två godkännanden samtidigt ger olika versionsnummer (testat mot Postgres),
  - n8n:s körningslista visar inga sparade körningar,
  - GIFTED-mappen och presentkortsfilerna har oförändrat "senast ändrad" efter testet.

**Steg 6: Senare, inte i denna design**

Kommandot `ny_mall`, en bildbank, sparade stilar (förinställningar per mall), kampanjkörning för många städer i ett klick, A/B-varianter, mapparna `02 Källmaterial` och `03 Arkiv` och notisen till Nicholas när nytt material läggs in. Var och en kan byggas ovanpå mallformatet utan att ändra det.

### Reglage för Golfare i stad

Golfare ger två JPG-filer per jobb, en i 9:16 och en i 4:5.

**Syns direkt**

| Reglage | Typ | Kommentar |
| :--- | :--- | :--- |
| Bakgrundsbild | bild | Laddas upp per jobb (`image_asset_ids`). |
| Fokuspunkt och zoom | tal, per format | Egen standard för 4:5 och 9:16 (`standard_per`), så att samma foto beskärs rätt i båda. |
| Etikettens text | text | Till exempel "Golfare i Linköping?". |
| Bannamn | text | Visas med plats-ikonen nere till vänster. |
| Etikettens storlek | tal | Gränser i `mall.json`. |
| Bannamnets storlek | tal | |
| Mellanrum | tal | Avståndet mellan etikettens rader och till bannamnet. |
| Loggans storlek | tal | |
| Typsnitt | typsnitt | Varumärkets typsnitt som standard, några godkända alternativ. |

**Fler inställningar (fälls ihop)**

| Reglage | Typ |
| :--- | :--- |
| Etikettens färg och textfärg | färg |
| Toning över bilden (styrka och riktning) | tal, val |
| Etikettens läge (höjd i bilden) | tal |
| Loggans läge | val |

Den gula etikettens höjning för Å, Ä och Ö (prickarna ska täckas) sköts av sidan själv och är inget reglage.

### Kontroll av helheten

- **Tester:** `.venv/Scripts/python.exe manage.py test engine --settings=engine.test_settings` efter varje steg. Testerna för steg 3 och 5 som använder radlås körs mot Postgres.
- **Mallkontroll:** `python library/tools/build_catalog.py --check` i testerna och `node library/tools/kontrollera_mallar.mjs` i ett eget CI-jobb, så att en trasig mall stoppas före `main`.
- **Lokal rendering:** `node library/templates/<mall>/render.mjs --lokal` för varje mall och format.
- **Dashboarden:** formulär, förhandsvisning och godkännande provas i webbläsaren via preview_start, med skärmbild till Jonas.
- **n8n:** alla fyra inställningarna läses tillbaka efter varje sparning av flödet.
- **Drive:** efter steg 5 kontrolleras att inga filer utanför `01 Publicerat` har ändrats.
- **Dokumentation:** när steg 5 är i produktion uppdateras kunskapsnoden i Notion (gren 9), och det manuella Drive-beslutet från 2026-10-28 markeras som Ersatt.

--------------------------------------------------------------------------------

*Drafted with EGM*
