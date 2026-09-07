# Social Content Engine

Första versionen för skarp användning: företagsunderlag → tre idéer → redigerbara Facebook-/Instagramtexter → utkast i hostad Postiz. Slutgranskning, schemaläggning, publicering och resultat sker i Postiz.

Social Media Skills bidrar med innehållshantverket. Brightbean bidrar med inloggning, företagshantering och datalagring. Kopplingen finns i engine/. Ingen egen Meta-app, publiceringsworker eller Docker behövs.

## Kör

Python 3.13 och Node behövs vid installation. Klona med --recurse-submodules.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix vendor/brightbean-studio/theme/static_src ci
npm.cmd --prefix vendor/brightbean-studio/theme/static_src run build
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\start.ps1
```

Konfiguration läses från .env och miljövariabler. Se .env.example. Befintlig OPENAI_API_KEY återanvänds med användarens godkännande. Hemligheter versionshanteras inte.

## Använd

1. Logga in och välj företag.
2. Spara profil, egna textexempel, aktuella fakta, källa och giltighetsdatum.
3. Skapa tre idéer och välj vilken som ska skrivas.
4. Granska och redigera kanaltexterna.
5. Anslut Postiz en gång per företag och välj rätt konton. API-nyckeln lagras med Brightbeans kryptering.
6. Välj riktig bild och kanaler. Skicka utkastet till Postiz och slutgranska där.

Tomma/utgångna underlag stoppas. Ändrade fakta kräver nya idéer. Källcitaten kontrolleras mot inskriven text. Detta verifierar ursprunget, inte sanningen i alla AI-påståenden. Människan granskar fakta och bildrättigheter.

## Drift

Render i Frankfurt + PostgreSQL hos Neon + hostad Postiz. Bilder skickas till Postiz; företagsdata förlitar sig inte på appens lokala disk. render.yaml och scripts/ innehåller driftkommandon. Ingen egen publiceringsworker körs.

bootstrap_owner skapar första administratören från BOOTSTRAP_ADMIN_EMAIL/PASSWORD utan att ändra befintliga konton. Behåll SECRET_KEY och ENCRYPTION_KEY_SALT vid omstarter. Ta bort bootstrap-lösenordet ur driftmiljön efter första uppstart.

Timeout vid överföring markeras som oklar. Ingen automatisk omsändning görs: kontrollera Postiz först. Publiceringstillståndet ägs av Postiz.

## Verifierat och kvar

- Fyra riktade tester passerade: företagsåtkomst, sparade utkast, giltighet och Postiz-payload.
- Verkliga AI-anrop gav tre idéer och kanaltexter på 18,2 sekunder med syntetiskt underlag. Lokal rapport: data/generation-check.json. Ingenting publicerades.
- Databasen är skapad i Neon Frankfurt och migrerad.
- Postiz-kontot är ännu inte anslutet. Ingen livepublicering är verifierad.
- Webbimport, konkurrentanalys, videoproduktion och återkoppling från resultat kommer efter att kärnflödet används.
- Brightbeans återanvända gränssnitt är delvis engelskt; vårt innehållsflöde är svenskt.

Den äldre veckoplanen ersätts för första versionen av [leveransordningen i timmar](docs/2026-09-07-forsta-version.md). [Ursprungsunderlaget](docs/specs/2026-09-07-ursprungligt-underlag.md) finns kvar som framtida krav. Se [licenser](THIRD_PARTY_NOTICES.md).
