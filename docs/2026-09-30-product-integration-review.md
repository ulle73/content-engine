# Content Engine: produktintegration, 30 september 2026

Arbetet utgår från hämtad `origin/main` på `c72f63ca5ab0723c47da2630a529314d1736a7f4`, på branch `codex/product-flow-integration`. Lokal `main` är orörd. Ingen push eller produktionsändring ingår.

## Resultat och konkreta fel

| Problem i appen efter merge | Förändring |
| --- | --- |
| Motion hade schema, modeller, renderkö och worker, men saknade webbflöde och registrerade MCP-verktyg. | Motion nås från Media och contentutkast. Gemensamma tjänster driver formulär, versioner, preview, godkännande, slutrendering och åtta MCP-verktyg. |
| Motion skapade alltid ett separat ContentRun. | Ett projekt kan kopplas till ett befintligt lokalt utkast och bevara dess copy. En fristående video kan senare få copy och dyker då upp i utkastlistan. |
| Fristående Motion/Creative-utkast saknade komplett företagssnapshot; äldre ofullständiga snapshots kunde orsaka 500 inför leverans. | Webbens idéflöde, MCP, Motion och Creative använder en gemensam faktasnapshot. Leveransgates skyddar även tonalitet, saknat/ändrat underlag och preview-media. Äldre ofullständigt underlag ger ett begripligt fel och uppdateras inte tyst. |
| Motion-preview och storyboardbilder kunde blandas med publicerbar media; MCP:s lista var smalare än webbens. | Gemensam filtrering och validering används i bibliotek, medieväljare, MCP, direktval och leverans. Slutvideo återanvänds som vanlig MediaAsset. |
| Manuell Sequence med två uppladdade bilder saknade ett nästa steg till klipp. | En explicit åtgärd kopplar intilliggande bilder genom befintlig `create_clip`. Den skapar inga generationer, är idempotent och bevarar befintliga klipp och planer. |
| Contentbriefen tappades när man gick till Sequence. | Utkastets titel och bildbrief följer med från content/Creative till Sequence. |
| Interna studio-, Motion- och Sequence-körningar syntes som tomma inläggsutkast. | Interna mediejobb hålls undan. Motion/Creative-utkast med skriven copy syns och går att fortsätta med. Utkastlistan skiljer text, bild och video. |
| Windows-sökvägar gjorde Remotion-build och CLI-rendering felaktiga. Renderad MP4 kunde bli `yuvj420p` och underkännas vid ingestion. | Native fil-URL-konvertering och explicit BT.709 ger kompatibel `yuv420p`. Smoke-scriptet använder serverns verkliga kvalitetskontroll. |
| Avbrutet Motion-jobb kunde returnera gammal status via MCP. | Den gemensamma tjänsten returnerar uppdaterad generationsstatus. Regressionstest och faktiskt HTTP-anrop verifierar `canceled`. |
| Månadsöversikten accepterade vissa fält som sedan ignorerades. | Mallens kontrakt, formulär och MCP visar endast innehåll som faktiskt används. Oanvända fält avvisas. Inga nyckeltal hittas på. |
| Svenska katalogtexter lästes med Windows standardkodning. | Katalogen läses uttryckligen som UTF-8. |
| Mobil medieväljare, långa videoprompter och reviewrubrik kunde skapa sidscroll eller bryta sönder ord. | Filter begränsas till skärmen, detaljerad prompt visas på begäran och radbryts, rubriken får full bredd. |
| Lokala tester läste produktionskonfiguration från `.env`; nyföretagsflöden importerade ML-DLL även utan träningsdata. | Testinställningar läser inte `.env`. Native ML-import sker först när tillräckligt antal träningsobservationer finns. Produktionskrav och safeguards är kvar. |

Ingen modell eller migration har lagts till. Befintliga Company-, ContentRun-, MediaAsset-, OperatorAction-, Sequence- och Motion-modeller används. Anpassade Motion-scener från MCP skyddas från att skrivas över av det enklare webbformuläret.

## Flöden som faktiskt användes i webbläsaren

Appen startades med egen SQLite-databas, lokal medialagring och syntetiskt Golfkuponger-underlag. `.env` lästes inte. Huvudskärmarna användes och granskades visuellt: skapa/utkast, review, Creative/medieväljare, mediabibliotek, promptbibliotek, Sequence, Motion, organisk/paid inspiration, Marknaden, egna resultat, inställningar och kostnader. Tomma och fyllda lägen ingick.

1. **Inspiration → Creative:** ett tydligt syntetiskt, kvalificerat MarketItem öppnades i Marknaden. `Till Creative Engine` förde den egna anpassningen till ett riktigt Creative ContentRun. Promptgranskningen visade mekanism och företagets eget underlag. Jobbet avbröts före providerstart.
2. **Media → Motion → utkast:** projekt skapades i webbappen. En verklig lågupplöst video och storyboard renderades av separat Node-worker. Hela previewn spelades upp i webbläsaren utan mediafel, godkändes och följdes av en faktisk slutrendering. Slutvideon sparades i Media och valdes i samma ContentRun. Länken tillbaka till review fungerade; copy sparades och utkastet hittades åter på startsidan.
3. **Media → Sequence → klippgranskning:** två egna syntetiska bilder laddades upp. Den nya kopplingsåtgärden skapade ett klipp. Granskningen visade båda bilderna, låst recept, modell, längd och format. En kandidat avbröts och en ny kunde förberedas. Pris-/credential-gaten behölls; ingen Higgsfield-generation startades.
4. **MCP ↔ webb:** en riktig lokal Streamable HTTP-klient upptäckte 38 verktyg, inklusive åtta Motion-verktyg. Utan token gav endpointen 401. Autentiserade anrop läste samma slut-MediaAsset som webbappen, godkände redan granskad preview, skapade projekt, blockerade final utan godkännande och köade/avbröt preview med korrekt slutstatus.

MCP-transporttestet använde uttrycklig lokal testidentitet. Det verifierar inte ChatGPTs externa OAuth-consent, refresh eller produktionsanslutning; de befintliga auth- och scope-testerna ingår i Django-sviten.

## Verifiering

| Kontroll | Utfall |
| --- | --- |
| Full Django-svit | **504 tester**, `OK`, tre PostgreSQL-specifika concurrency-tester hoppade över på SQLite. Sista körning 10,530 s. |
| Riktade Motion/Sequence UI-tester | 27 tester passerade; nya regressioner ingår även i den fulla sviten. |
| Django system check | Inga fel. |
| Migrationer | Befintliga migrationer applicerades i isolerad databas. `makemigrations --check --dry-run`: inga ändringar. |
| Node/Remotion | 13/13 tester, TypeScript-check och bundle-build passerade. |
| Verkliga renders | Preview 9:16 samt final 9:16, 1:1 och 16:9. Serverns ingestion, full FFmpeg-dekodning, bildantal, upplösning, H.264/AAC och icke-tyst ljud utan clipping verifierades. |
| Responsiv kontroll | 16 skärmar × fyra faktiska CSS-bredder: 320, 390, 767 och 1440 px. Alla 64 kontroller saknade horisontell sidscroll och serversida med fel. Ändrade vyer granskades också med screenshots. |
| Ny Python-kod | Ruff på Motion-formulär, vyer, MCP och nya UI-tester passerade. `git diff --check` passerade. |

Renderns mätningar gäller syntetiskt Monthly Wrapped, 538 bildrutor, 30 fps:

| Render | Storlek | Tid | Högsta samlade RSS |
| --- | --- | --- | --- |
| Preview 9:16 | 360 × 640 | 37,00 s | 507,4 MB |
| Final 9:16 | 1080 × 1920 | 43,83 s | 946,3 MB |
| Final 1:1 | 1080 × 1080 | 37,34 s | 677,8 MB |
| Final 16:9 | 1920 × 1080 | 43,77 s | 960,6 MB |

Den separata webbanvändningen renderade dessutom Kinetisk text som preview och final. Dessa resultat passerade verklig upload/ingestion och sparades i den lokala databasen.

Testerna kördes med Python 3.12, Django 5.2.17, scikit-learn 1.7.2, scipy 1.16.3 och numpy 2.3.4, inom befintliga dependency-intervall. Den gamla Python 3.14-miljön blockerades av Windows native-DLL-policy. Inga produktdependencies eller säkerhetspolicyer ändrades för att kringgå den. Den isolerade miljön har FFmpeg för befintliga videofixtures.

Två äldre leveransfixtures kompletterades med företagets `voice`, som redan finns i riktiga content-snapshots. Assertions för faktisk MP4-upload, explicit godkännande, ingen dubbelöverföring och återhämtning efter okänd Postiz-status behölls. Nya tester bevisar även att ändrad tonalitet, saknat underlag och Motion-preview stoppar leverans före nätverksanrop.

### Lokala bevis och reproduktion

Bevisfilerna ligger under ignorerad `data/` och innehåller enbart lokala testresultat:

- `data/product-full.log`
- `data/product-mcp-transport.log`
- `data/product-review/mcp-transport-evidence.json`
- `data/product-review/responsive-evidence.json`
- `data/product-review/smoke/smoke-results.json` och MP4-filer per format
- `data/product-review/motion-desktop.jpg`, `review-mobile.jpg`, `home-mobile-final.jpg`

```powershell
.venv-clean/Scripts/python.exe manage.py test --settings=engine.test_settings --noinput
.venv-clean/Scripts/python.exe manage.py check --settings=engine.test_settings
.venv-clean/Scripts/python.exe manage.py makemigrations --check --dry-run --settings=engine.test_settings
# I motion-renderer:
npm test
npm run typecheck
npm run build
# Från reporoten, med ffmpeg/ffprobe tillgängliga i PATH:
.venv-clean/Scripts/python.exe scripts/motion_render_smoke.py
```

För PostgreSQL används en separat testdatabas via `TEST_DATABASE_URL` och `engine.postgres_test_settings`, aldrig appens produktionsdatabas.

## Nästa meningsfulla steg

- **Sequence till en sammanhängande slutfilm:** det befintliga systemet hanterar klipp, kandidater, bildrevisioner och övergångar. En explicit export/sammansättning av valda segment till en enda film är ett separat produktsteg; det har inte lagts till här.
- **Produktionsacceptans för Motion:** dimensionera separat worker efter mätt minnesåtgång, konfigurera riktiga origin/token och fastställ korrekt kommersiell licensstatus. Verifiera R2-read-back, PostgreSQL-låsning och den publika OAuth/MCP-kedjan före rollout. Inget resursköp eller deployment har gjorts.
- **Katalog och avancerad editing:** granska/rendera samtliga mallar och verkliga företagsmedier. Webbformuläret stödjer mallinnehåll; fri scenordning, duplicering och timing/effect-editor återstår. Anpassade specs kan redan redigeras via MCP utan att webben förstör dem.
- **Live-provideracceptans:** betald bild/video, aktuell scraping, extern textmodell och Postiz-överföring/publikation har inte körts live i denna granskning. De befintliga testerna, gränserna för okänd providerstatus och pris-/godkännandegates är kvar.

Se [Motion: användning och drift](motion/USAGE.md) och den uppdaterade [acceptanslistan](motion/ACCEPTANCE.md) för gränsen mellan lokal verifiering och full produktionsacceptans.
