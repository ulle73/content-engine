# Daglig drift och officiell logga

## Gemensam entrypoint

`python manage.py run_daily` är appens centrala dagliga körning. GitHub Actions-workflowen `competitor-intelligence.yml` heter nu **Content Engine Daily** och anropar enbart detta kommando efter installation/migreringskontroll. Schemat är fortsatt 06:17 UTC. Inga nya scheduler-tjänster, workers eller köer har lagts till.

Nuvarande steg i `engine/daily_stages.py`:

1. Konkurrentimport: återanvänder `start_import` och `collect_import`, inklusive nuvarande konservativa fallback, normalisering, snapshots och 23-timmarsgräns för nya starter.
2. Färdig media: återanvänder befintliga provider-jobb och hämtar färdiga filer. **Daily startar aldrig nya betalda bild-/videogenereringar.** Köade jobb öppnas i appen av användaren; obekräftade starter kräver kontroll.
3. Rensning: tar bort utgångna, oanvända mediafiler via befintlig lagring. Valda filer, loggor och aktiva startbilder skyddas. Lokala filer rensas inte av en värd konfigurerad för R2.
4. AI-analys: samma kandidatval och klassificering som tidigare. Varje post körs separat. Misslyckade importer hindrar inte analys av redan sparat underlag; kända pågående importer inväntas inom tidsbudgeten.

Den tidigare `refresh_competitors`-entrypointen finns kvar för kompatibilitet/manuell konkurrentkörning. Affärsreglerna för scraping och ranking har inte skrivits om.

## Delvisa fel, återkörning och logg

`DailyRun` är dagens körning, `DailyStep` en arbetsenhet med företag, stegversion och stabil nyckel. Lyckade enheter sparas omedelbart, utanför någon gemensam lång transaktion. Ett fel i en enhet, i ett företags urval eller i en leverantör fångas vid den gränsen; andra enheter får fortsätta.

Samma dags omkörning återanvänder loggen och hoppar över `success`/`skipped`. `pending` pollas inom en gemensam standardbudget på 720 sekunder. Fel får ett nytt försök vid en uttrycklig omkörning, inte vid varje pollingvarv. Ursprungliga import-/generationstabeller skyddar även över dygnsgränser mot dubbla providerstarter. Exakt-en-gång-debitering vid okänd extern POST kan inte garanteras; obekräftade starter återspelas därför aldrig automatiskt.

- `success`: alla moment är klara eller behöver ingen åtgärd.
- `partial`: arbete har sparats men något är väntande, blockerat eller behöver åtgärdas. Kommandot avslutas normalt och GitHub visar en warning samt en job summary.
- `failed`: inget arbete lyckades och fel återstår, eller själva körningen/databasen inte kan fungera. GitHub-jobbet blir rött.

Momentets status, antal exekveringar/statuskontroller, säkert felmeddelande och resultat-id:n ligger i databasen och visas företagsavgränsat under **Inställningar → Daglig körning**. API-svar, credentials och godtycklig exception-text skrivs inte till loggen. GitHub får motsvarande sammanställning i `GITHUB_STEP_SUMMARY`.

En kort PostgreSQL-transaktion låser tilldelningen av en 20-minuters lease. Varje arbetsmoment förnyar den. Detta fungerar även med Neons transaktionspooler; ingen session-advisory-lock eller transaktion hålls under API-anropen. En kraschad process lämnar sparade delresultat. Efter lease-expiry kan kommandot köras igen. En process som förlorat sin lease får inte fortsätta till nästa arbetsmoment. Vanliga steg måste ha kortare timeout än leasen; längre framtida träningssteg måste förnya leasen eller dela arbetet i återupptagbara enheter.

Driftkommandon:

```powershell
python manage.py migrate
python manage.py run_daily
python manage.py run_daily --company <företagets-uuid> --wait-seconds 0
```

`--wait-seconds 0` gör ett pass utan att vänta mellan statuskontroller. Sammanfattningen gäller dagens samlade körning även vid omkörning för ett enskilt företag. Avslutade moment görs inte om. Budgeten begränsar nya arbetsmoment och polling; ett redan startat API-anrop får avslutas inom sin egen timeout.

## Aktivera GitHub-schemat

Vid kontroll 2026-09-09 var repots Actions-secrets och repository-variabler tomma. Ingen credential har kopierats till GitHub och ingen automation har aktiverats av denna ändring.

Lägg följande under repository **Settings → Secrets and variables → Actions**:

| Actions-secret | Källa i appens driftmiljö |
|---|---|
| `CONTENT_DATABASE_URL` | `DATABASE_URL` för befintliga appdatabasen |
| `CONTENT_DJANGO_SECRET` | `SECRET_KEY` |
| `CONTENT_APIFY_TOKEN` | `APIFY_API_TOKEN` |
| `CONTENT_OPENAI_KEY` | `OPENAI_API_KEY` |
| `CONTENT_R2_ENDPOINT_URL` | `R2_ENDPOINT_URL` |
| `CONTENT_R2_BUCKET_NAME` | `R2_BUCKET_NAME` |
| `CONTENT_R2_ACCESS_KEY_ID` | `R2_ACCESS_KEY_ID` |
| `CONTENT_R2_SECRET_ACCESS_KEY` | `R2_SECRET_ACCESS_KEY` |
| `CONTENT_HIGGSFIELD_API_KEY` | `HIGGSFIELD_API_KEY` |
| `CONTENT_HIGGSFIELD_API_SECRET` | `HIGGSFIELD_API_SECRET` |

R2/Higgsfield behövs för sina arbetsmoment; saknad provider-konfiguration ska inte stoppa oberoende moment. Databas och Django-secret krävs för att starta appen. Sätt sedan repository-variabeln **`CONTENT_INTELLIGENCE_ENABLED=true`** (namnet behålls för kompatibilitet) och kör **Run workflow** en gång. Workflowen lägger aldrig in en egen Meta-app eller publicerar innehåll.

## Framtida outcomes, learning och ML

Nya moment registreras som `Stage(name, factory, version, requires)` i samma Django-register. `factory(company)` ger stabila arbetsnycklar och funktioner som returnerar `Result(status, message, data)`. Ingen egen performance-insamling eller ML-träning har implementerats i denna ändring.

Exempel på framtida stegordning: `own_performance` → `outcomes` → `shadow_training`. Ange `requires=("own_performance",)` för outcomes och motsvarande för träning. Ett hårt beroende som saknar lyckat underlag blockerar det beroende steget men hindrar inte import, media eller andra företag. Detta är testat med simulerade outcomes/shadow-steg.

För framtida datafönster ska arbetsnyckeln innehålla dataset/fönster och relevant version. Spara `observed_at`, `as_of`, käll-id:n, input-hash och modell-/kodversion i resultatet och i respektive domäntabell. En `DailyStep` är exekveringslogg, inte ersättning för outcomes, träningsdataset eller utvärderingshistorik. Publicera ett nytt modell-/resultat-id först när hela dess validerade underlag är klart. Shadow mode ska inte automatiskt ändra publicering eller produktionsrankning.

## Officiell logga

Under företagets **Inställningar** kan PNG, WebP eller JPEG laddas upp/bytas, högst 8 MB. Transparent PNG rekommenderas. Filen sparas oförändrad i befintlig mediahantering (privat R2 i drift) med `purpose=logo`, SHA-256, filnamn och versions-id. Företagets `official_logo` är den uttryckliga referensen till aktuell version. Ingen logga hämtas från webben eller skapas åt företaget automatiskt.

Vid bildgenerering finns **Lägg till officiell logga**. Ingen logga innebär att detta val inte kan användas. Bildmodellen instrueras att skapa obrandad bild och får inte själva officiella logofilen som generativ input. Appen lägger i stället originalfilens pixlar på en neutral yta i nedre högra hörnet med Pillow. Vid behov görs vanlig proportionell nedskalning, utan AI-omritning. Originalfilen ändras aldrig. Fri placering, logga i perspektiv/på föremål och videologga ingår inte.

Jobbet låser loggaversion och hash vid skapandet. Efter ett byte använder nya jobb den nya versionen; redan skapade jobb och bilder behåller sin historiska referens. Saknad eller förändrad originalfil stoppar bildgenereringen före API-anropet. Gamla loggaversioner skyddas mot radering.

En obrandad basbild sparas separat i samma privata lagring för bilder med pålagd logga. **Gör variant** använder den rena basbilden, aldrig den AI-redigerade kopian av en pålagd logga. Därefter läggs aktuell officiell logga på igen om vald. Även animering använder ren basbild; video får ingen loggapåläggning. En godtycklig redan brandad uppladdad bild har ingen sådan basbild: använd en ren startbild för redigering om en inbakad logga måste lämnas orörd. Modellen kan fortfarande göra oönskade detaljer i bakgrunden; den slutliga bilden granskas före Postiz.

## Verifierat 2026-09-09

- 47 tester passerade: tidigare competitor/media-tester samt delvisa fel, företag-/momentisolering, omkörning, lease, pending/avbruten körning, framtida stegberoenden, loggabyte, exakt fil/pixelreferens och korrupt loggafil utan AI-anrop.
- Riktig daily mot Neon: `e5286350-9928-4a8f-9648-b56644c7cff1`, tio lyckade moment och två äldre Higgsfield-fel som `attention`; slutstatus `partial`, exitkod 0. En omkörning hade **noll** upprepade lyckade moment. Inga nya Apify-runs startades eftersom de fem kontona redan hade färska observationer. Detta verifierar återanvändning och status; nya scrape-resultat producerades inte i denna körning.
- Riktig R2: originalfilens bytes/SHA-256, oförändrade logopixlar utan behov av skalning, ren basbild och byte av loggaversion kontrollerades i ett separat testföretag. AI-svaret var simulerat i det testet; inget påstås om en ny verklig AI-generering. Ingen riktig företagslogga har ersatts.
- GitHub-scheduler är förberedd i kod men inte liveaktiverad; secrets/variabel saknas. Egen performance/ML är endast en förberedd utökningspunkt.
- PostgreSQL-låset verifierades med två samtidiga riktiga anslutningar: den andra transaktionen kunde inte ta samma lås medan den första höll det, och kunde ta låset efter rollback. Inga affärsdata ändrades av låstestet.

Referenser: [GitHub job summaries](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary), [PostgreSQL transaction advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS).
