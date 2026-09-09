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

Den nya databasen `content_engine_app` ligger på samma Neon-projekt/branch som tidigare. Den gamla databasen `content_engine` finns kvar orörd för återgång; den innehöll inga innehållskörningar eller företagsunderlag vid bytet. Gamla Brightbean-tabeller och migreringar ska **inte** återanvändas med den nya appen. Det är ett medvetet engångsbyte före användardata, inte en migreringsväg för redan använda Brightbean-installationer.

## Media och AI-generering

**Välj bild eller video** öppnar företagets media i innehållsflödet. Egna uppladdningar prioriteras, OpenAI skapar bildalternativ/varianter och Higgsfields officiella API kan skapa video från text eller en startbild. Filer ligger i privat R2; metadata och val ligger i befintlig Neon. Använd media skyddas mot radering. Se [konfiguration, API-kontrakt, verifiering och begränsningar](docs/2026-09-08-media.md).

Den riktiga bildkedjan till R2 och ett valt inlägg är verifierad. Higgsfields nycklar, startbilduppladdning och prisförfrågan fungerar; verklig videogenerering är ännu blockerad av `not_enough_credits` på API-kontot. Ett vanligt Higgsfield-abonnemang ska inte antas innebära att det aktuella API-saldot räcker.

## Competitor Intelligence

Öppna **Konkurrentsignaler** för företaget. Lägg till Instagram-profiler, hämta historik, aktivera/inaktivera konton och skapa egna idéer från signalerna. All historik ligger i befintlig PostgreSQL. Apify sköter scraping via befintlig httpx; inga mediefiler hämtas till appen.

Primär Actor är `esdrasdw/instagram-content-scraper`. Reserven `apify/instagram-post-scraper` startas vid verkligt körningsfel, explicit fel med under 80 % levererade poster, över 20 % ogiltiga poster eller under 70 % användbara normaliserade poster. Enstaka luckor och saknade valfria metrics utlöser inte fallback. Första importen begär högst 100 poster, därefter 10 dagligen och 30 högst veckovis; reserven ärver gränsen. Primären har 0,05 USD och reserven 0,25 USD kostnadstak, inom en gemensam daglig företagsbudget. Ett misslyckat första försök orsakar aldrig automatisk ny backfill.

Samma konto och format jämförs vid liknande postålder, minst fem peers. Vid kallstart används om möjligt äldre posters observerade nivå efter minst 14 dagar, tydligt märkt **låg säkerhet**, med högst 0,25 confidence. Riktigt age-matched underlag ersätter detta automatiskt. Historiska dag-1-värden och dygnstillväxt konstrueras aldrig ur dagens totalsiffror. Momentum kräver mätningar minst 18 timmar isär; acceleration behöver tre sådana mätningar.

AI tolkar caption och metadata till en mekanism och en egen företagsvinkel. Företagets verifierade uppgifter är faktakällan. Idérankingen sparar ingående signaler, snapshots, baseline-typ, jämförelseunderlag, delpoäng och version. Händelser sparar val, avvisande, redigering och Postiz-utkastets id. Learning fryser nu predictions och features för Organic och Paid separat; egna verkliga sjudygnsresultat kan registreras i UI eller importeras. Automatisk resultatinsamling är ännu inte kopplad. Se [Ads, kostnadsskydd och learning-kontrakt](docs/2026-09-09-ads-learning.md).

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
