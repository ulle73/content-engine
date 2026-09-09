# Meta Ads, inkrementell sync och learning

## Användning

**Insikter → Annonser** visar sparade annonser, observationer, budskap, hook, erbjudande, CTA, återkommande teman och en egen företagsvinkel. Lägg till annonsören med en Ads Library-länk som innehåller `view_all_page_id`, eller ange Facebook-sidans numeriska ID separat. Välj land. Vanliga sidnamn räcker inte för säker identifiering: i verklig verifiering returnerade actorns automatiska sidupplösning annonser från sex olika annonsörer. Endast den valda sidans ID accepteras nu.

**Skapa egen annonsidé** ger tre originalidéer från företagets verifierade underlag och den valda signalen. Copy innehåller primärtext, rubrik, beskrivning, CTA och verifierad landningssida om sådan finns. Befintligt mediabibliotek, uppladdning, OpenAI-bild och Higgsfield-video återanvänds. Kampanjen sätts upp i Meta Ads Manager; paid-utkast får inte skickas som organiska Postiz-inlägg. Organic fortsätter via hosted Postiz.

Format, medielänkar och landningssida sparas om källan faktiskt ger dem. AI analyserar text och metadata, inte bild-/videopixlar. Originalet länkas i Ads Library. Saknade uppgifter förblir okända. Aktiv status gäller observationstillfället; frånvaro i en begränsad körning innebär aldrig att en annons stängts av. Lång synlighet, antal varianter och återkommande teman är inte prestationsbevis. Konkurrent-CTR, CPA, ROAS och konverteringar konstrueras aldrig.

## Gemensam kostnadsgräns och sync-kontrakt

Alla nya scraperintegrationer ska använda `engine.sync.dispatch`, `ScraperState` och `ScrapeRequest`. Inga betalda starter direkt från views, scheduler eller fristående scripts. Sparad reservation skapas under företagslås **före** provider-POST; körningsnyckeln återanvänds över UI och daily. Bekräftade körnings-ID:n återupptas. Timeout/okänd start hålls för manuell kontroll, aldrig automatisk omsändning. Ingen kö eller extra scheduler införs.

`SCRAPER_DAILY_BUDGET_USD` är 1 USD per företag/dygn som standard, hårt begränsad till högst 10. Summan använder rapporterad faktisk kostnad eller reserverat tak tills kostnaden är känd. Providerpriser kan ändras; detta är ett reservationsskydd tillsammans med Apifys `maxTotalChargeUsd`, inte en garanti om extern fakturering. Arbete som inte ryms väntar. Samma princip gäller aktiva och okända körningar. Definitivt avvisad start registreras med noll kostnad.

| Källa | Första begränsade urval | Discovery | Äldre status | Tak per körning |
|---|---|---|---|---|
| Instagram primär | 100 posts, högst ett backfillförsök | 10 senaste, högst var 23:e timme | 30 senaste högst veckovis | 0,05 USD |
| Instagram reserv | Ärver primärens gräns | Endast vid väsentligt otillräcklig primär | Ingen extra rutinmässig reserv | 0,25 USD |
| Meta Ads | 30 dagars leveransfönster, högst 50 annonser, ett försök | Vattenmärke minus två dagars överlapp, högst 20 | 90 dagars begränsat leveransfönster, högst 30, högst veckovis | 0,15 USD |

Redan existerande Instagramhistorik räknas som initialiserad. Ett misslyckat backfillförsök orsakar inte ny backfill; veckoförsöket registreras före POST så ett fel inte gör bred refresh dagligen. Stabila post-/annons-ID:n deduplicerar objekt. Observationer dedupliceras per objekt och providerkörning. Äldre annonsdataset kan läsas om från UI utan ny betald scrape och utan att äldre status skriver över nyare observationer.

Actorerna har begränsningar: Instagramprimären saknar cursor/datumfilter och hämtar därför ett litet aktuellt överlappande flöde. Mycket aktiva konton kan få luckor. Ads datumfilter gäller **leveransdagar**, inte skapelsedagar; långlivade annonser kan återkomma. Detta är begränsade urval, aldrig ett löfte om full historik. Om Ads discovery/backfill når gränsen pausas nya betalda hämtningar tills användaren uttryckligen accepterar historikluckan och fortsätter med nytt. Begränsad veckokontroll stoppar inte discovery.

Klassificering använder `engine.sync.analysis` och `AnalysisMemo`, med innehålls-/företagskontext-/modellhash. Oförändrat underlag återanvänds. En ren ändring av aktiv status utlöser ingen ny AI-analys. `INTELLIGENCE_DAILY_ANALYSES` är 12 nya/förändrade analyser per företag/dygn, högst 50. Avvisat 4xx-anrop får försöka igen efter 23 timmar; osäkra anrop kräver operatörskontroll för att undvika dubbel debitering. Memo-status, modell, försöksantal och tid finns i databasen; driftfel visas även i Inställningar. Osäkra betalda starter får inte återställas utan kontroll i leverantörens körningslogg.

`run_daily` använder befintliga separata delresultat och kompletteras med `ads_import`, `ads_analysis` och `learning`. Fel isoleras per företag/konto/analys. Sparat arbete behålls, nästa invocation återupptar återstående moment. GitHub Actions startar samma Django-command, ingen affärslogik i YAML. Befintliga Actions-secrets räcker. Valfria kostnadsinställningar kan sättas på appvärden; workflow använder säkra standardvärden.

## Learning: egna resultat, separata kanaler

`Prediction` fryser idéfeatures, full signalproveniens, kontexthash, featureversion, modellversion, mål och tid före redaktörens val. Utan tränad modell är prediction-värdet **null**, inte ett påhittat ML-tal. Organic och Paid hålls separerade per företag i data, träning och aktivering. Konkurrentdata är features; val, avvisanden och redigeringar är redaktionell återkoppling, aldrig performance-labels.

Registrera riktiga egna resultat via länken i ett sparat utkast, eller importera en export med:

```powershell
python manage.py learning import --company COMPANY_UUID --channel paid --file own-results.json
python manage.py learning train --company COMPANY_UUID --channel paid
python manage.py learning evaluate --company COMPANY_UUID --channel paid --model EXACT_VERSION
python manage.py learning promote --company COMPANY_UUID --channel paid --model EXACT_VERSION
```

Importfilen är en JSON-lista med `run_id`, `source` (`meta_export`, `postiz_export`, `manual_verified`), stabilt `external_id`, `published_at`, `window_end`, `observed_at` (ISO med tidszon), `metrics` och `evidence` (rapportlänk). Använd samma externa ID även om samma objekt senare importeras från annan resultatkälla. Uppgifter måste vara verkligt uppmätta, och prediction måste vara skapad före publiceringen. `window_end` ska vara exakt sju dygn efter publicering och resultatet avläst därefter. Felaktiga rader isoleras. Upprepning återanvänder sparat resultat; motstridiga labels skrivs inte över.

Organic kräver impressions, likes och comments; målet är interaktioner per 1 000 impressions under sju dygn. Paid kräver impressions och clicks; målet är klick per 1 000 impressions under sju dygn. Klickmålet är **inte** lönsamhet. Faktisk spend, revenue och conversions kan sparas när de finns, men används inte som labels för denna modellversion. Saknade värden ersätts aldrig med noll. Ett innehåll ger högst en sjudygnslabel i nuvarande modell. Automatisk insamling från egna annonskonton är ännu inte kopplad; samma validerade ingestfunktion är gränssnittet för framtida integration.

Första modellen är standardiserad Ridge-regression (scikit-learn), lagrad som transparent JSON med koefficienter. Minst 80 egna labels krävs. Senaste 25 procent (minst 20) är kronologisk holdout; träningslabels som inte var kända före första holdout-prediction tas bort. Minst 40 träningslabels ska återstå. Utvärdering sparar MAE, jämförelse mot träningsmedelvärde, exakta outcome-ID:n och tidsgräns.

Nya modeller stannar i **shadow** och ändrar inte ordningen. Samma kandidat behålls tills den hunnit samla prospektiva resultat. Produktion kräver uttrycklig promotion, minst 20 egna shadow-resultat och minst 10 procent bättre MAE än baseline både historiskt och i shadow. Det är en enkel skyddsgräns, inte bevis på kausal förbättring eller garanterad affärsnytta. Modellens mål bör granskas innan aktivering. Ingen modell har aktiverats i produktion vid leverans.

## Verifiering 2026-09-09

- Riktig `eiv/meta-ads-library-scraper`: Shot Scope, Ads Library-sid-ID `1546044185663001`, GB. Körning `RpjPcdT4sXElrR7ig` gav 30 rader från sex annonsörer. Efter verifiering mot själva Ads Library sparades 15 korrekta annonser och 15 snapshots; 15 andra annonsörers rader sorterades bort. Samma betalda dataset lästes om, ingen ny scrape för korrigeringen.
- Två tidigare Arccos-urval var tomma (inte bevis på att företaget saknar annonser); bevakningarna är pausade i väntan på verifierat sid-ID. Två ogiltiga inputförsök avvisades före körning. Inputkontrakt korrigerat till tillåtna länder och versala plattforms-enums. Nya anrop använder explicit sid-ID i Ads Library-URL, inte implicit sidnamnsupplösning.
- Bekräftad Ads-kostnad för dessa accepterade körningar: **0,120150 USD**. Ny organisk kontroll: fyra användbara tiopostsurval, **0,002000 USD**, totalt **0,122150 USD** Apify. Lou Stagners primär gav HTTP 429 i actorns rapport; andra konton sparades. Ingen ny reserv-Actor startades under verifieringen.
- Riktig klassificering → tre idéer → copy → tre frysta paid-predictions: ContentRun `96d1105c-e862-4c44-814d-e3932535e77e`, från annons `1781503786316516`. Granskningsvyn och befintligt mediabibliotek öppnades i webbläsaren. Utkastet är inte publicerat. OpenAI-kostnad i USD har inte rapporterats av denna verifiering.
- Lokala tester körs mot separat minnesdatabas, inklusive felisolering, budgetar, identitetsfiltrering, dublettskydd, gamla dataset, frysta features, temporal purge, kanalisolering, shadow och promotion. Modelltjänsten verifierad med syntetiska labels; inga fabricerade labels läggs i produktionsdatabasen.
- Additiva migrationer applicerade på befintlig Neon. Lokal UI/API-verifiering är inte i sig bevis på publik hosting.

Primärkällor: [Ads Actor input](https://apify.com/eiv/meta-ads-library-scraper/input-schema), [Instagram Actor input](https://apify.com/esdrasdw/instagram-content-scraper/input-schema), [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html).
