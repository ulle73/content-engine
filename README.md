# Social Content Engine

Företagsunderlag → tre idéer → redigerbara Facebook-/Instagramtexter → utkast i **hosted Postiz**. Slutgranskning, kalender, schemaläggning, publicering och resultat hanteras i Postiz.

**Brightbean är borttaget.** Läs [arkitekturbeslutet](docs/2026-09-07-arkitekturbeslut.md). Social Media Skills används direkt som innehållsreferenser, och Django tillhandahåller standardfunktionerna för webbappen. Företag och innehållskörningar kompletteras av referenskonton, importer, poster, snapshots och beslutshändelser. En separat låsrad skyddar registreringen av första administratören.

## Kom igång i webbläsaren

Öppna appens adress. Om inget konto finns visas **Skapa första administratören** automatiskt. Fyll i e-post, företag och ditt valda lösenord. Du loggas in och kan lägga till fler företag direkt i UI. Inga terminalkommandon eller förskapade lösenord behövs för användaren.

På en publik HTTPS-installation behövs också installationskoden från webbhotellets inställning `SETUP_TOKEN`. Render skapar den automatiskt; kopiera den från Render → Environment till formuläret. Det hindrar besökare från att ta över en ny installation. Registreringen stängs när det första kontot skapats. Vanlig inloggning kräver aldrig installationskoden.

1. Välj företag och spara profil, egna textexempel, aktuella fakta, källa och giltighetsdatum.
2. Skapa tre idéer och välj en att skriva.
3. Granska och redigera kanaltexterna.
4. Anslut företagets Postiz-konto och välj rätt Facebook-/Instagramkanaler. Nyckeln lagras krypterad.
5. Välj företagets bild/video, ladda upp eller generera alternativ direkt från inlägget. Välj **Använd** och skicka utkastet till Postiz. Slutgranska och schemalägg där.

## Installation för driftansvarig

Python 3.13. Ingen Node-byggkedja, Docker, egen Meta-app eller publiceringsworker.

```powershell
git submodule update --init vendor/social-media-skills
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\start.ps1
```

Konfiguration: `.env.example`. Hemligheter hör hemma i `.env` lokalt eller webbhotellets miljövariabler. Befintlig `OPENAI_API_KEY` återanvänds med ägarens godkännande. Behåll `SECRET_KEY` och `POSTIZ_ENCRYPTION_SECRET` mellan driftsättningar. Render-konfigurationen finns i `render.yaml`; startkommandot kör databasens migrering automatiskt. PostgreSQL är ett krav för publik drift, inklusive transaktionslåset vid första registreringen. SQLite stöds lokalt och i isolerade tester.

Produktionsdatabasen `content_engine_app` ligger sedan 2026-09-13 i Neon-projektet `orange-band-72152493`, under ägarens verifierade konto. Befintliga användare, företag, ContentRuns, observations- och lärhistorik har kopierats från den tidigare Neon-servern och jämförts med radantal och SHA-256 över fullständiga rader. Media ligger kvar i samma privata R2-bucket och Postiz-krypteringsnyckeln är bevarad. Den gamla databasen är kvar för återgång. Se [migreringsrapporten](docs/2026-09-13-production-migration.md) innan eventuell återställning; byt aldrig tillbaka utan att först bevara data som skapats efter migreringen.

Redigerare, OAuth och MCP körs tillsammans på `https://content-engine-mcp.onrender.com/`, med MCP på `/mcp`. Endast `feature/chatgpt-content-engine-mcp` används för denna driftsättning; `main` har inte ändrats eller mergats.

## Media och AI-generering

**Välj bild eller video** öppnar företagets media i innehållsflödet. Egna uppladdningar prioriteras. Den gemensamma Creative Engine-motorn används både av webbgränssnittet och ChatGPT MCP: en naturlig beskrivning blir en strukturerad brief med begränsad företagskontext, verifierat modellval, modell-specifik prompt/parametrar, lokal preflight och kostnadsskydd. Prompt Library kan bidra med ett fåtal abstrakta inspirationsmekanismer men dess råtext behandlas som opålitlig data och kopieras inte in i provider-prompten.

OpenAI används för bild och Higgsfields officiella API för video från text eller startbild. Färdig media sparas i privat R2 och befintliga `MediaGeneration`/`MediaAsset` i Neon; ingen separat generation-databas har införts. Higgsfield-webhook används som completion-signal när den är aktiverad, medan autentiserad statusläsning och bounded polling/recovery är sanningskälla. En möjlig betald generation-POST retrias aldrig automatiskt efter ett oklart svar. Resultat markeras inte som klara förrän de säkrats i Content Engine storage.

Golfkupongers serverflöde använder `HIGGSFIELD_API_KEY_GK` som primär credential och får inte falla tillbaka till Jonas personliga Higgsfield-workspace/subscription. Äldre servervariabler finns kvar endast för bakåtkompatibel migrering. Kontots aktuella modell-/kredittillgänglighet verifieras fail-closed med leverantörens estimate innan betalning; den tidigare 2026-09-08-observationen `not_enough_credits` ska därför inte behandlas som aktuell status. Ingen betald videogeneration kördes i Creative Engine-implementationen 2026-09-21. Se [löpande Creative Engine-status](docs/2026-09-21-higgsfield-creative-engine-progress.md) och [äldre mediareferens](docs/2026-09-08-media.md).

## Competitor Intelligence

Öppna **Konkurrentsignaler** för företaget. Lägg till Instagram-profiler, hämta historik, aktivera/inaktivera konton och skapa egna idéer från signalerna. All historik ligger i befintlig PostgreSQL. Apify sköter scraping via befintlig httpx; inga mediefiler hämtas till appen.

Primär Actor är `esdrasdw/instagram-content-scraper`. Reserven `apify/instagram-post-scraper` startas vid verkligt körningsfel, explicit fel med under 80 % levererade poster, över 20 % ogiltiga poster eller under 70 % användbara normaliserade poster. Enstaka luckor och saknade valfria metrics utlöser inte fallback. Första importen begär högst 100 poster, därefter 10 dagligen och 30 högst veckovis; reserven ärver gränsen. Primären har 0,05 USD och reserven 0,25 USD kostnadstak, inom en gemensam daglig företagsbudget. Ett misslyckat första försök orsakar aldrig automatisk ny backfill.

Samma konto och format jämförs vid liknande postålder, minst fem peers. Vid kallstart används om möjligt äldre posters observerade nivå efter minst 14 dagar, tydligt märkt **låg säkerhet**, med högst 0,25 confidence. Riktigt age-matched underlag ersätter detta automatiskt. Historiska dag-1-värden och dygnstillväxt konstrueras aldrig ur dagens totalsiffror. Momentum kräver mätningar minst 18 timmar isär; acceleration behöver tre sådana mätningar.

AI tolkar caption och metadata till en mekanism och en egen företagsvinkel. Företagets verifierade uppgifter är faktakällan. Idérankingen sparar ingående signaler, snapshots, baseline-typ, jämförelseunderlag, delpoäng och version. Händelser sparar val, avvisande, redigering och Postiz-utkastets id. Learning fryser predictions och features för Organic och Paid separat. Daily hämtar nu egna publicerade Postiz-inlägg och aktuella metrics, sparar snapshots/baseline och skapar outcomes när mätfönster och tidigare frysta features finns. Se [kostnadseffektivitet och automatisk Own Performance](docs/2026-09-09-own-performance-efficiency.md).

**Inställningar** visar vad varje scraper faktiskt returnerat, nya/ändrade/oförändrade objekt, ny AI-behandling, kostnad och kostnad per användbart objekt. Frekvens och storlek anpassas från utfallet och faktisk kostnad; tysta konton kontrolleras mer sällan. Externa dublettkostnader som Actor-kontraktet inte kan undvika redovisas öppet.

**Insikter → Egna resultat** visar publicerade posts och riktiga Postiz-metrics. Historiska posts utan predictions från före publicering bygger baseline, aldrig fabricerade träningslabels. Automatiska aktuella totalsiffror använder ett tydligt separat 7–8-dygnsfönster. Paid kan utvecklas mot ROAS, konverteringar, CPA och revenue från verifierade resultat, med separata mål och valutor. GitHub Actions använder även `CONTENT_POSTIZ_ENCRYPTION_SECRET` för befintliga krypterade företagskopplingar.

### Meta Ads och learning

**Insikter → Annonser** använder `eiv/meta-ads-library-scraper` med verifierat Facebook-sid-ID. Nya och förändrade annonser sparas, analyseras och kan bli egna annonsidéer och copy via **Skapa** och det befintliga mediaflödet. Konkurrentannonser är inspiration, aldrig uppmätt performance. Standardtaket är 1 USD per företag/dygn för alla scrapers och 12 nya AI-klassificeringar. Oförändrade analyser återanvänds.

Modellträning använder egna uppmätta labels, kronologisk utvärdering och shadow mode. Produktionspåverkan kräver tillräckligt bra historiskt och prospektivt resultat samt uttrycklig promotion. Ingen modell aktiveras bara för att data finns. [Användning, gränser och verklig verifiering](docs/2026-09-09-ads-learning.md).

### Daglig hämtning

Den centrala entrypointen är nu **`python manage.py run_daily`**. Den kör konkurrentimport, insamling av färdig media, säker rensning och AI-analys med separata sparade delresultat. Delvis lyckad körning ger varning/status utan att kasta bort lyckat arbete. GitHub Actions anropar kommandot; framtida outcomes/shadow/ML läggs i Django-registret. **Inställningar** innehåller driftloggen och företagets officiella logga. Se [drift, aktivering och loggans versionshantering](docs/2026-09-09-daily-and-logo.md).

`APIFY_API_TOKEN` läses från miljön. `APIFY_USER_ID` är valfri kontometadata, aldrig autentisering. Manuell hämtning och status finns i UI. Scheduler använder `python manage.py run_daily`; även det äldre `refresh_competitors --wait` går genom samma reservationsskydd. Primäractorn saknar cursor/datumfilter och hämtar därför ett begränsat aktuellt överlapp, inte hela historiken. Mycket aktiva konton kan få dataluckor.

GitHub-workflowen **Content Engine Daily** finns för daglig körning 06:17 UTC. Den är **avstängd tills secrets och aktiveringsvariabel satts**. Driftansvarig lägger Actions-secrets enligt [driftdokumentet](docs/2026-09-09-daily-and-logo.md), och sätter repository-variabeln `CONTENT_INTELLIGENCE_ENABLED=true`. Ingen credential checkas in. Miljönycklar flyttas inte automatiskt till GitHub. Kommandot använder den befintliga databasen; det kräver inga egna workers och kan köras i en befintlig schemaläggare.

## Kontroller och begränsningar

Kör `python manage.py test engine --settings=engine.test_settings`. Tester använder separat minnesdatabas. Riktade tester täcker första registrering, företagsåtkomst, källcitat, idé→utkast, Postiz-kontrakt, återhämtning, import-idempotens, tolerans för dataluckor, konservativ reservhämtning, age-matched/kallstartsbaslinjer och verkliga tidsintervall i momentum.

Den verkliga publiceringskedjan verifierades med bild och separata Facebook-/Instagram-utkast för Sänk Dig Golf i hosted Postiz. Inget publicerades. Källcitat väljs från ett strukturerat urval av företagets exakta text; detta bevisar inte sanningen i alla AI-påståenden. Människan granskar fakta och bildrättigheter. Vid osäkert Postiz-svar görs ingen automatisk omsändning.

[Ursprungsunderlaget](docs/specs/2026-09-07-ursprungligt-underlag.md) och [tredjepartslicenser](THIRD_PARTY_NOTICES.md) finns kvar. Djangos driftkontroll ger två HSTS-råd om subdomäner och preload; de aktiveras först när slutlig domän är vald. HTTPS och säkra sessionscookies är påslagna i publik drift.
