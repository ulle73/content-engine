# Verifiering 2026-09-08

Befintlig Django/PostgreSQL-app, httpx och hosted Postiz behålls. Inga nya dependencies, workers eller publiceringsfunktioner. Instagram-konton är redigerbara databasrader per företag; de fem startkontona är inte hårdkodade.

## Verkliga Apify-resultat

| Konto | Unika poster | Snapshots | Rapporterad kostnad USD |
| --- | ---: | ---: | ---: |
| DECADE Golf | 93 | 183 | 0,3331 |
| Lou Stagner Golf | 36 | 36 | 0,0972 |
| Arccos Golf | 92 | 92 | 0,2484 |
| Practical Golf | 92 | 92 | 0,2484 |
| Shot Scope | 92 | 92 | 0,2484 |
| Totalt | 405 | 495 | 1,1755 |

Kostnader är summerad `usageTotalUsd` från Apify, inklusive verifieringsomkörningar. En obekräftad start kontrollerades mot Apifys körningslista: ingen motsvarande fjärrkörning fanns. Ingen kostnad har fabricerats för den. OpenAI-kostnad ingår inte i tabellen.

Primär Actor är fortfarande `esdrasdw/instagram-content-scraper`. Första DECADE-körningen gav 36 poster men misslyckad vidare paginering med upstream HTTP 401, trots övergripande `SUCCEEDED`. Reserven `apify/instagram-post-scraper` behövdes och gav 93 poster. Övriga fyra kontons första primärförsök gav inga användbara poster; reserven gav tabellens historik.

Senaste verkliga primärförsöket gav 24 av 30 begärda DECADE-poster, kostnad 0,0012 USD. Den då körande äldre regeln startade reserven, som gav 30 poster för 0,081 USD. Efter korrigeringen spelades exakt detta verkliga dataset och Actor-rapport genom den färdiga importkoden i separat minnesdatabas: 24 poster, 24 snapshots, användbar partiell import, ingen fallback och inga dubletter vid omkörning. Detta är replay av verkliga API-resultat, inte ytterligare en betald scrape.

Reservregeln tolererar minst 80 % levererade poster även vid ett fel på sista sidan, högst 20 % poster som inte kan normaliseras och minst 70 % användbara normaliserade poster. Användbar betyder caption plus minst ett exponerat värde för likes eller kommentarer. Saknade views, videolängd, slides eller enstaka captions räknas inte automatiskt som ett totalfel. En verkligt misslyckad fjärrkörning utlöser fortfarande reserv. Reserven ärver ursprunglig gräns 30/100; den fördubblar inte till en ny full backfill vid daglig hämtning.

Alla tre format finns: totalt 243 Reels/video, 108 bilder och 54 carousels. Caption, permalink/id, datum, likes, kommentarer, exponerade plays/views, längd och slides normaliseras. Saknade/dolda likes förekommer: 10 DECADE-poster saknade likes i senaste mätningen. Fyra captions saknas totalt och en videolängd saknas. Alla hämtade Reels hade ett exponerat visningsmått, men det är inte en garanti för framtida data. Måttets ursprungliga namn sparas. Ingen konkurrentmedia laddas ned till appen.

## Signal och beslut

Samma konto och format jämförs vid liknande postålder med minst fem peers. En enkel reservbaslinje jämför annars med minst fem äldre poster observerade efter 14 dagar. Den får högst en fjärdedels confidence, märks låg säkerhet i dashboard och sparat beslutsunderlag, och ersätts automatiskt av age-matched data. Den används inte som bevis för återkommande starka mönster.

Live i UI: DECADE-post `Dc3dYPdR-Uf` gav en tillfällig jämförelse på 3,09× mot sju äldre bilder, confidence 0,175. Signalen skapade tre riktiga OpenAI-idéer. Vald idé blev **Var försvann slaget – före eller efter missen?**, rank 1, 81,0 poäng. Facebook-/Instagramtexter skapades och sparades i ContentRun `edaf2ecb-5fb2-4f73-9ab5-808d2aeb736a`. Signal, baseline-typ, snapshot-id:n, egen faktakälla och delpoäng ligger kvar som oföränderligt underlag. Testkörningen är märkt `verification` så att den kan uteslutas från framtida preferensinlärning.

Även tidigare vertikal körning `4d1961f3-ecae-4e05-a827-095de84d0669` finns kvar. Det tidigare bildutkastet i Postiz verifierades separat för både Facebook och Instagram. Inga nya publiceringar har gjorts under Competitor Intelligence-arbetet.

495 snapshots är riktiga observationer från flera importer samma dag. De är inte historiska dag-1/3/7-värden. Verklig flerdagarsacceleration är därför ännu inte verifierad. Riktade tester verifierar acceleration, avplaning och att för täta mätningar aldrig påstås vara dygnstillväxt.

## Learning-kontrakt och drift

`ContentRun.context.competitor_signals` sparar signalens observationer, jämförelseunderlag, AI-mekanismer och score. `ideas[].ranking` sparar rankerversion, delpoäng, ursprunglig position och score. `ContentEvent` sparar `ranked`, `selected`, `rejected`, `draft_created`, `edited` med före/efter, `approved` och `postiz_draft` med externa post-id:n. Utkast i Postiz betyder aldrig publicerat.

Framtida faktiska publiceringar kan lägga `published`-händelser med post-id, kanal, publiceringsdatum och URL. Framtida resultat kan lägga `outcome` med samma post-id, verkligt mättidstillfälle, faktisk postålder, önskat fönster 1/3/7/14 dagar och nullable metrics. Unika källobservationer och deduplicering ska då verifieras innan importen aktiveras. Ingen sådan resultathämtare eller tränad modell är byggd nu; befintliga händelser och versionssatta signaler ger underlaget för en framtida modell i shadow mode.

Dagligt kommando återupptar körningar, begränsar automatiska nya försök och signalerar terminala fel med exitkod. GitHub-workflow är färdig men avstängd i väntan på godkänd konfiguration av Actions-secrets och `CONTENT_INTELLIGENCE_ENABLED=true`. Ingen hemlighet har flyttats till GitHub. Lokal UI använder den befintliga Neon-databasen; detta är inte bevis för en extern webbdriftsättning.

20 riktade tester passerar, liksom Ruff och migrationskontroll. Testerna omfattar även lagrat learning-spår, konservativ fallback, ingen dubbelstart vid osäkert API-svar och att interna rankingfält inte skickas till textskrivningen.
