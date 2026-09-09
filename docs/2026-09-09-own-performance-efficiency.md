# Mätt scraper-effektivitet och automatisk Own Performance

Detta dokument kompletterar och ersätter berörda fasta gränser/learning-begränsningar i tidigare dokument. Befintliga Django-modeller, Apify, Postiz, media och GitHub Actions används; inga workers eller queues har tillkommit.

## Scraperkostnad: vad varje hämtning faktiskt gav

Alla Apify-importer mäts i samma `ScrapeRequest` som reserverar budget före betald start. `result.yield` innehåller returnerade rader, nya unika objekt, ändrade redan kända objekt, oförändrade kända objekt, tidigare kända totalt, ogiltiga/upprepade rader, nytt användbart utfall och kostnad per användbart objekt. Ett objekt räknas en gång: nytt, ändrat eller oförändrat. Ändrade metrics eller aktiv status räknas som ändrat användbart data; AI har separat hash för relevanta innehållsändringar. Saknad eller noll nyttig output ger ingen påhittad kostnadskvot.

`AnalysisMemo.scrape_request` kopplar ny AI-behandling till ursprungskörningen. Samma analys för identisk creative används över flera annons-ID:n utan extra AI-anrop. Historiska analyser före spårningen tilldelas inte retroaktivt ett påhittat ursprung. Driftstatistiken räknar bekräftat slutförda nya analyser; avvisade/osäkra försök finns i memo-loggen men presenteras inte som lyckade analyser.

Återläsning återanvänder körningens mätning och kan lägga till tidigare ogiltiga objekt som nu faktiskt går att importera, utan att räkna tidigare objekt igen eller multiplicera kostnaden. Äldre dataset utan mätning vid första importen får inte en rekonstruerad ”exakt” historisk effektivitet. **Inställningar → Scraping: kostnad och nytt värde** visar senaste högst 100 körningar, total rapporterad kostnad, mätt nytt värde och nästa discovery-policy. Historik per konto ligger kvar i databasen.

Efter kompletta discovery-körningar utan nya objekt förlängs intervallet stegvis till 2, 4 och 7 dygn. Ny publicering återställer normalt daglig kontroll; två aktiva urval kan öka storleken till 20. Primär Instagram använder minst 10 enligt Actor-kontraktet. Meta Ads använder 5–20 med utrymme för det faktiskt observerade resultatsetet, så storleken inte sänks under ett känt användbart urval bara för att annonserna redan finns. Uppmätt kostnad per returnerad rad används även för att förlänga intervallet om nästa beräknade urval kostar över ungefär 0,05 USD. Intervallet är högst sju dygn. Budgettaket gäller fortfarande över alla källor.

Veckovis status-refresh hålls separat och ändrar inte discovery-policy utifrån sitt historiska urval. Felaktig eller ofullständig hämtning räknas aldrig som ett ”tyst konto”. Ett misslyckat första försök återställer aldrig backfillflaggan. Manuell start och daily läser samma adaptiva state. En schemaläggare som går en gång per dygn kan som mest kontrollera dagligen; ”oftare” betyder tätare än inaktiva konton, inte en ny intradagsscheduler.

| Actor | Inkrementellt stöd som används | Begränsning |
|---|---|---|
| `esdrasdw/instagram-content-scraper` | Begränsat nytt flöde, adaptiv frekvens/storlek | Saknar cursor/datumfilter; kända posts kan fortfarande debiteras. Veckorefresh använder senaste 30. |
| `apify/instagram-post-scraper` | `onlyPostsNewerThan` från watermark minus två dygn och `skipPinnedPosts` vid discovery; `basicData` | Endast reserv vid verkligt otillräcklig primär. Datumfilter används inte för avsiktlig status-refresh. |
| `eiv/meta-ads-library-scraper` | Verifierat sid-ID, leveransdatum från watermark och två dygns överlapp | Leveransdatum är inte skapelsedatum; aktiva äldre annonser återkommer. Ingen dokumenterad cursor/”exclude known IDs”. Befintlig paus vid ofullständig capped discovery behålls. |

Framtida scrapers ska gå genom `sync.dispatch` och `scraper_efficiency.record_yield`, beskriva sina verkliga capabilities och använda källans starkaste tillgängliga inkrementella filter. Lokal deduplicering är inte ett påstående om att externa dublettkostnader har försvunnit.

## Own Performance via befintlig Postiz-koppling

Daily har nu `own_discovery`, `own_snapshots`, `own_outcomes`, följt av target-specifik `learning`. Fel isoleras per inlägg/företag. Det behövs ingen ny Meta OAuth-app.

- Första Postiz-listningen har ett begränsat 90-dagarsfönster. Därefter används watermark med två dygns överlapp, högst en kontroll per 23 timmar. Även misslyckad första listning räknas som ett försökt backfill; nästa automatiska försök använder ett litet fönster.
- Endast `PUBLISHED` och företagets uttryckligen valda integrations-ID:n importeras. Postiz-ID och plattformens release-ID sparas. Säker run-match kräver exakt tidigare sparat Postiz-ID **och** integrations-ID; textlikhet används aldrig. Native release-ID deduplicerar dubbelregistrerade Postiz-poster.
- Manuellt skapade och äldre inlägg som Postiz-listningen faktiskt returnerar får delta i baseline. Historik från före Postiz-kopplingen eller skapad direkt på plattformen är inte garanterad av detta API. Ingen egen scraper har byggts för att kringgå begränsningen.
- `GET /analytics/post/{postId}?date=7` returnerar i granskad implementation **aktuella livstidstotaler daterade idag**, även om parametern heter date. De summeras inte till fabricerade historiska dygnsvärden. Okänd tidsserieform avvisas och sparat arbete på andra inlägg fortsätter.
- Instagram Views, Reach, Likes, Comments, Saves och Shares behåller sin betydelse. Facebooks Postiz-label ”Impressions” representerar upstream `post_total_media_view_unique`, alltså reach; den lagras därför som reach. `percentageChange` ignoreras. Saknade metrics förblir saknade; explicit uppmätt 0 sparas som 0.
- List-API:t saknar medieformat. Reel accepteras endast från uttrycklig inställning; säker koppling till vald Content Engine-media kan ge image/video. Annars sparas unknown. Appen påstår inte att okänt format är en Reel eller carousel.
- Aktiva posts följs ungefär dagligen till första observationen vid 7–8 dygn. Därefter avslutas rutinmässiga refreshes. En äldre importerad post får en aktuell observation för baseline, inte påhittade dag-1/dag-7-snapshots. Äldre posts utan användbart svar avslutas efter tre misslyckade försök.
- Snapshotnyckeln är post + källdag + mätkontrakt + checkpoint. Ett separat slutcheckpoint får finnas samma kalenderdag som en tidigare daglig observation; det undviker att en siffra före sju dygn felaktigt används som slutresultat. Samma checkpoint kan inte skapas dubbelt. Snapshotdata och historiska outcomes skrivs inte över.

**Insikter → Egna resultat** visar verkliga metrics, matchat innehåll och jämförelsen mot egna posts med samma plattform, format, mätkontrakt och åldersfönster. Baseline använder median, minst tre andra posts och högst låg säkerhet med färre än tio peers. Underlag efter observationen får inte läcka bakåt. Baseline och exakta peer-snapshot-ID:n fryses per observation. Noll normalnivå ger ingen oändlig eller påhittad relativ prestation. Ålder utgår från Postiz `publishDate`; exakt faktisk Meta-publiceringssekund är inte separat verifierad.

## Automatisk learning och Paid-mål

Det ursprungliga exakta manuella sjudygnsfönstret behålls. Automatiska aktuella totalsiffror i daily kan inte ärligt kallas exakt dag 7: de använder egna mål med **7–8 dygns observationsfönster**. Instagram: `(likes + comments) / views × 1000`. Facebook: `reactions / reach × 1000`. Måtten hålls isär från tidigare impressions-baserade mål. Snapshot måste vara kopplad till rätt run och prediction/features måste finnas från före publicering. Äldre inlägg utan sådana features bygger endast baseline. Features backdateras aldrig.

Paid väljer, när mått och giltig nämnare finns, ROAS, konverteringar per 100 klick, CPA med explicit valutakod, revenue per 1000 impressions med valutakod eller tidigare klickmål. Explicit `target` kan också anges i verifierad import. Spend/revenue för ROAS ska ha gemensam verifierad valuta. Olika valutor blandas inte i CPA- eller revenue-modeller. Noll spend/conversions eller saknade värden skapar ingen odefinierad label. En ny kompletterad mål-label kan tillkomma utan att en gammal label ändras.

`OwnOutcome.target` är målkontraktet för den faktiska labeln. En prediction för samma mål används om den finns, annars används den tidigare frysta idéposten som feature-ankare utan att dess eventuella prognos för ett annat mål räknas som en prognos för detta mål. Shadow-utvärdering använder alltid rätt modells mål och dess prospektiva predictions.

Daily upptäcker nya mål/labels och tränar separat per företag, Organic/Paid och mål. Samma tidsdelade Ridge-utvärdering, purge av för sent kända labels och shadow-gränser behålls. Målet och outcome-ID:n ingår i modellversionen. CPA rankas med lägre prognostiserad kostnad som bättre; övriga mål har rätt högre-riktning. Automatisk träning innebär aldrig automatisk promotion. Verkliga Meta Ads Manager-resultat matas tills vidare in via verifierad UI/import, med exempelvis conversions, spend, revenue och currency. Ingen ny OAuth-omväg har byggts.

```powershell
python manage.py run_daily
python manage.py learning import --company COMPANY_UUID --channel paid --file own-results.json
python manage.py learning train --company COMPANY_UUID --channel paid --target roas_7d
```

GitHub Actions behöver `CONTENT_POSTIZ_ENCRYPTION_SECRET` för att dekryptera befintliga företagskopplingar. Den befintliga lokala krypteringshemligheten lades i detta Actions-secret utan att visas i chatten eller checkas in. Inga nya scheduler-variabler behövs; `CONTENT_INTELLIGENCE_ENABLED=true` gäller fortfarande.

## Verifierat 2026-09-09

**Riktig Apify-data:** DECADE, primär Actor, run `d6bdL4LFCh7isZF08`, CompetitorImport 21 / ScrapeRequest 11. Tio returnerade, en ny, nio förändrade befintliga, inga oförändrade; 0,000500 USD och 0,000050 USD per nytt/förändrat objekt. Ingen reserv-Actor eller ny AI-analys behövdes i den verifieringen. Kostnadsvyn visade dessa tal. Äldre körningars kostnad finns kvar men deras saknade detaljmätning fylls inte med gissningar. Denna verifierings nya Apify-kostnad är 0,000500 USD; det sammanlagda registrerade beloppet inklusive tidigare utveckling var 0,122650 USD.

**Riktig Postiz-data:** fyra poster returnerades i 90-dagarslistningen; en var publicerad Instagram och tre var utkast. Publicerad post `cmtrsugiy0qbqqk0yemt6bolc` / release `17990438949020807` matchades exakt till run `7097a7ff-dac8-4436-b835-ec4ad9f3bbe5`. Snapshot sparade Views 5, Reach 2, Likes 0, Comments 0, Saves 0 och Shares 0. Saknade impressions konstruerades inte. Vid omkörning hoppades båda API-stegen över och antalet snapshots var fortfarande ett. UI visade resultatet, okänt format och otillräcklig baseline.

**Endast testat med syntetiska data:** mogen 7–8-dygns-snapshot → immutable outcome → target-specifik learning, temporal baseline 1,8× med låg confidence, mål med CPA/ROAS/konverteringar, modellträning/shadow/production-gräns och lägre-är-bättre för CPA. Det verkliga publicerade inlägget är ännu för ungt för slutwindow och skapades före nya frysta predictions. Ingen verklig modellträning eller promotion kan påstås vara bevisad av det.

**Externa begränsningar kvar:** primärens överlappande Instagramhämtningar, Ads leveransfilter och resultatgränser, Postiz omfattning/format/tidssemantik, otillräcklig verklig baseline/labels och separat verifierad Paid-import. Lokal app och Neon verifierades; detta är inte i sig bevis på publik apphosting. Daily verifieras även via befintligt GitHub-workflow vid leverans.

Primärkällor: [Postiz list posts](https://docs.postiz.com/public-api/posts/list), [Postiz post analytics](https://docs.postiz.com/public-api/analytics/post), [Facebook-provider](https://github.com/gitroomhq/postiz-app/blob/main/libraries/nestjs-libraries/src/integrations/social/facebook.provider.ts), [Instagram-provider](https://github.com/gitroomhq/postiz-app/blob/main/libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts), [reserv-Actor input](https://apify.com/apify/instagram-post-scraper/input-schema).
