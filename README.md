# Social Content Engine

Företagsunderlag → tre idéer → redigerbara Facebook-/Instagramtexter → utkast i **hosted Postiz**. Slutgranskning, kalender, schemaläggning, publicering och resultat hanteras i Postiz.

**Brightbean är borttaget.** Läs [arkitekturbeslutet](docs/2026-09-07-arkitekturbeslut.md). Social Media Skills används direkt som innehållsreferenser, och Django tillhandahåller standardfunktionerna för webbappen. Två affärsmodeller: företag och innehållskörning. En separat låsrad skyddar registreringen av första administratören.

## Kom igång i webbläsaren

Öppna appens adress. Om inget konto finns visas **Skapa första administratören** automatiskt. Fyll i e-post, företag och ditt valda lösenord. Du loggas in och kan lägga till fler företag direkt i UI. Inga terminalkommandon eller förskapade lösenord behövs för användaren.

På en publik HTTPS-installation behövs också installationskoden från webbhotellets inställning `SETUP_TOKEN`. Render skapar den automatiskt; kopiera den från Render → Environment till formuläret. Det hindrar besökare från att ta över en ny installation. Registreringen stängs när det första kontot skapats. Vanlig inloggning kräver aldrig installationskoden.

1. Välj företag och spara profil, egna textexempel, aktuella fakta, källa och giltighetsdatum.
2. Skapa tre idéer och välj en att skriva.
3. Granska och redigera kanaltexterna.
4. Anslut företagets Postiz-konto och välj rätt Facebook-/Instagramkanaler. Nyckeln lagras krypterad.
5. Välj företagets bild och skicka utkastet till Postiz. Slutgranska och schemalägg där.

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

## Kontroller och begränsningar

Nio riktade tester passerar i en ren installation och täcker första registrering, installationskod, lösenord/CSRF, företagsåtkomst, idé→utkast, utgångna fakta, Postiz-format, godkännande och osäkra överföringar. Kör `python manage.py test engine --settings=engine.test_settings`; tester använder alltid separat minnesdatabas.

Efter arkitekturbytet gav ett nytt verkligt AI-prov i den rena miljön tre idéer och kanaltexter på 13,9 sekunder med syntetiska fakta. Genereringslogiken återanvänds oförändrad. **Postiz är ännu inte anslutet och inget flöde mot verkliga sociala konton är verifierat.**

Källcitat kontrolleras mot inskriven text; det bevisar inte sanningen i alla AI-påståenden. Människan granskar fakta och bildrättigheter. Vid osäkert Postiz-svar görs ingen automatisk omsändning; kontrollera utkasten där först. Företagets konton väljs manuellt, och Postiz-avtalets API-åtkomst måste provas innan vidare funktioner byggs.

Denna ändring lägger inte till webbimport, konkurrentanalys, video eller egen statistik. [Ursprungsunderlaget](docs/specs/2026-09-07-ursprungligt-underlag.md) finns kvar. Se [tredjepartslicenser](THIRD_PARTY_NOTICES.md).

Djangos driftkontroll ger endast två HSTS-råd om subdomäner och preload. De aktiveras inte innan en slutlig domän är vald; HTTPS och säkra sessionscookies är påslagna i publik drift.
