# Repogranskning – 7 september 2026

## Rekommenderad kombination

**Senaste vägval: social-media-skills/skills + hostad Postiz och en svensk redaktionell app.** Brightbean är förstahandsreserv för samlad egen native drift. Efter användarens fråga om Postiz granskades dess publika API och hostade pris; se [den kompletterande jämförelsen](2026-09-07-postiz-jamforelse.md). Kodfynden om Brightbean nedan kvarstår som underlag för reservvalet.

Underlaget nedan bygger på README, manifest, licenser, utvald källkod och GitHubs aktuella metadata. Det är en arkitekturgranskning, inte en komplett säkerhetsrevision. Applikationerna har inte installerats eller testkörts lokalt. Funktionspåståenden skiljs från observerad kod och körda upstream-kontroller.

## Alla tio kandidater

| Repository | Verifierad licens i snapshot | Återanvändningsbeslut | Skäl, drift och underhåll |
|---|---|---|---|
| [social-media-skills/skills](https://github.com/social-media-skills/skills) | MIT | Kopiera ett granskat urval med licens och låst revision | Användbar struktur för företag, tonalitet, ämnen och produktion. Markdown, ingen egen drift. Den kompletta katalogen är onödigt stor. Instruktioner om verktyg, globala företagsfiler och publicering måste anpassas till vår applikation. |
| [charlie947/social-media-skills](https://github.com/charlie947/social-media-skills) | MIT | Återanvänd valda textinstruktioner; skriv om datakopplingen | Tonalitet, content-matris och Reel-struktur är relevanta. Delar är LinkedIn-specifika. `post-scorer` använder bland annat viktade interaktioner och erbjuder en annan persons benchmark som reserv. Det får inte bli företagsbevis eller vår statistiska modell. Ingen separat server. |
| [Freespirits/social-auto-engine](https://github.com/Freespirits/social-auto-engine) | MIT | Referens för produktionsflödet; ingen sammanslagning av hela appen | FastAPI, HTMX, SQLite och APScheduler; lätt lokal start. Repo beskriver early alpha. Den lästa schemaläggaren använder separat SQLite-fil. AI/video och MCP prioriteras, medan vår viktigaste uppgift är företagsfakta. Att kombinera dess konton, databas och kö med Brightbean skulle dubblera kärnan. |
| [HagaiHen/facebook-mcp-server](https://github.com/HagaiHen/facebook-mcp-server) | MIT | Studera adaptergränser; inget runtime-beroende | En liten Facebook-wrapper. Lästa `facebook_api.py` använder globalt `PAGE_ID`/`PAGE_ACCESS_TOKEN` och HTTP-anrop utan explicit timeout i `_request`. Inte en färdig grund för tre helt separerade företag och ingen komplett Instagramprodukt. Brightbean har redan motsvarande integration. |
| [prodkit-labs/instagram-competitor-intelligence](https://github.com/prodkit-labs/instagram-competitor-intelligence) | MIT | Återanvänd normaliserings-/rapportidéer och utvalda Pythonfunktioner efter tester | Litet receptrepo med mockflöden och dataleverantörsberoende. `src/metrics/engagement.py` beräknar likes + kommentarer dividerat med följare; saknade värden blir noll. Detta uppfyller inte kravet på avvikelse mot samma kontos normala utfall. Vi behåller provenance och bygger korrekt tids- och kontojämförelse. |
| [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) | AGPL-3.0 | **Hostad tjänst via API är huvudvalet; ingen fork i V1** | Dokumenterade API:er för publicering och resultat. Egen drift är mer omfattande: PostgreSQL, Redis och Temporal. Hostad tjänst flyttar detta driftansvar till leverantören men kräver verifierat API-kontrakt, kontoindelning och abonnemang. |
| [brightbeanxyz/brightbean-studio](https://github.com/brightbeanxyz/brightbean-studio) | AGPL-3.0 | **Reservgrund för samlad egen native drift** | Befintliga modeller, publiceringsadapter, godkännanden, bildbibliotek och analytics ger stor återanvändning. Dokumenterad native utveckling. Aktuell `render.yaml` använder Docker. Django-uppgradering och företagsspecifika kontroller behövs innan produktionsbruk. |
| [inovector/mixpost](https://github.com/inovector/mixpost) | MIT för Lite | Andrahandsreserv: betald Pro som separat publiceringsmotor | Gratis Lite stöder Facebook, X och Mastodon; Instagram ingår i Pro/Enterprise enligt leverantören. PHP/Laravel ger en andra teknikstack om vi behåller Pythonmotorn. Native installation finns. MIT för Lite innebär inte att Pro kan kopieras eller distribueras på samma villkor. |
| [timgit/pg-boss](https://github.com/timgit/pg-boss) | MIT | Väljs bort i Django-kombinationen | Bra PostgreSQL-baserad kö för Node.js. Behöver inte Docker. Skulle här skapa en separat Node-process trots att Brightbean redan använder databasbaserade jobb. Återbesök bara vid ett faktiskt byte till Node. |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | Sustainable Use License och separata Enterprise-delar; GitHub `NOASSERTION` | Väljs bort | Extra arbetsflödesmotor ger dubbla statussystem, credentials och felsökning. Licensen är inte MIT och har begränsningar för användning/distribution. Vi väljer bort n8n på grund av produkt- och driftkomplexitet; Docker är inte det avgörande skälet. |

Mixposts plattformsindelning är kontrollerad mot [leverantörens pris- och editionssida](https://mixpost.app/pricing). Postiz infrastruktur är kontrollerad mot dess [utvecklingskonfiguration](https://github.com/gitroomhq/postiz-app/blob/36d5fc7b3ac3f17178b1589cf7a7337523017a41/docker-compose.dev.yaml). n8ns licensuppdelning framgår av [LICENSE.md](https://github.com/n8n-io/n8n/blob/6f64dc6ae3d3a1e9b9069544a901deee9c0c0aaf/LICENSE.md).

## Revisioner som granskningen avser

Stjärnor, ålder och grön CI används som underlag för underhållsbedömning, aldrig som produktionsgaranti. Revisionerna är ankare för reproducerbar research, inte ett beslut att behålla föråldrade säkerhetsberoenden.

| Repository | Branch | SHA | Senaste commit på denna branch, UTC |
|---|---|---|---|
| social-media-skills/skills | main | `6e30eeb2f6736bda8683b6bbaa674af3641d7945` | 2026-07-19 |
| charlie947/social-media-skills | main | `d2e948719eafc8ed9e2436357ad18489bb371a81` | 2026-08-30 |
| Freespirits/social-auto-engine | main | `1a21f2a8c19c4c2d09e5b98b3d2e89ba10e9ec18` | 2026-07-18 |
| HagaiHen/facebook-mcp-server | main | `61b2128555d7582b19daf772186c03bc051c1c05` | 2026-04-23 |
| prodkit-labs/instagram-competitor-intelligence | main | `f62ded1edb57259f79869224c5247cedb5d1bc35` | 2026-05-09 |
| gitroomhq/postiz-app | main | `36d5fc7b3ac3f17178b1589cf7a7337523017a41` | 2026-09-03 |
| brightbeanxyz/brightbean-studio | main | `d85fce192e687d20e8fd7e9449a40ad7952ec7c3` | 2026-08-13 |
| inovector/mixpost | main | `df57648b866310446703f5294350552b62735df5` | 2026-03-16 |
| timgit/pg-boss | master | `ba02f39a068c350a8de11821d218044a4df6490d` | 2026-09-06 |
| n8n-io/n8n | master | `6f64dc6ae3d3a1e9b9069544a901deee9c0c0aaf` | 2026-09-07 |

## Viktiga kodfynd i Brightbean

1. **Företagsstruktur finns.** `Organization`, `Workspace`, medlemskap och `WorkspaceScopedManager` finns. Managern filtrerar först när `.for_workspace(...)` anropas. Den är inte automatiskt ett skydd för godtyckliga `.objects.all()`-frågor. Vår plan kräver obligatorisk företagskontext i nya tjänster och isoleringstester av alla åtkomstvägar. [Kod](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/apps/common/managers.py).
2. **Bildbibliotek kan delas inom organisation.** `MediaAsset.workspace` kan vara null och `for_workspace_with_shared` finns. Vi väljer en organisation per företag och ett arbetsområde inom varje. Inga bilder delas automatiskt mellan företag. [Modell](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/apps/media_library/models.py).
3. **Godkännande finns, men grundinställningen är av.** `Workspace.approval_workflow_mode` har `NONE` som standard. Projektets onboarding ska tvinga obligatoriskt internt godkännande och publiceringskontrollen ska gälla även alternativa API- och administrationsvägar. [Modell](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/apps/workspaces/models.py).
4. **Det finns flera sätt att skapa inlägg.** `create_post(...)` används av Agent API, medan HTMX-formuläret har en egen väg. Integration av faktagranskning får inte stanna vid en ny knapp. Kontrollerna ska sitta i gemensamma tjänster och omedelbart före extern publicering. [Tjänst](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/apps/composer/services.py).
5. **Publicering är värd att återanvända.** `PublishEngine` har kontovisa statusar, låsning, retry och provider-dispatch. Granskningen bevisar inte att alla timeout- eller avbrottssituationer är säkra. Vi utökar med bindning till godkänd revision och explicit hantering av okänt publiceringsutfall. [Motor](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/apps/publisher/engine.py).
6. **Analytics ger inte färdiga 24-/72-timmarspunkter.** `PostInsightsSnapshot` skriver över samma dags mätning. Vi återanvänder hämtningen men behöver kompletterande oföränderliga observationer med faktisk tid och postålder. [Modell](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/apps/analytics/models.py).
7. **AI-namnet betyder inte att vår innehållsmotor ingår.** `apps.intelligence` kopplas till externa URL:er och organisationsabonnemang. Funktionen hålls avstängd; en ny lokal `apps.editorial` använder våra valda promptmoduler. [Konfiguration](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/config/settings/base.py).
8. **Support och native drift måste rättas.** `requirements.txt` anger Django `>=5.1,<5.2`. Django 5.1 är utan support; 5.2 LTS är ett lämpligt uppgraderingsmål, med senaste säkerhetspatch och kompatibilitetstest. `render.yaml` använder `runtime: docker`, men `Procfile` visar vanliga Pythonprocesser. Native Render-konfiguration ska provas, inte antas fungera. [Beroenden](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/requirements.txt), [Djangos supporttabell](https://www.djangoproject.com/download/), [Render-konfiguration](https://github.com/brightbeanxyz/brightbean-studio/blob/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/render.yaml).

## Vad är faktiskt testat av upstream?

Brightbeans granskade SHA har en [slutförd grön CI-körning](https://github.com/brightbeanxyz/brightbean-studio/actions/runs/31685593504). Trädet innehåller 86 Pythonfiler vars namn börjar med `test`; detta är filantal, inte antal godkända testfall. CI-konfigurationen innehåller pytest mot PostgreSQL. Inga testloggar har använts för att påstå verklig Meta-publicering.

Social Auto Engines granskade SHA har också [grön CI](https://github.com/Freespirits/social-auto-engine/actions/runs/29661069322). De fem senaste hämtade Postiz-körningarna var administrativa arbetsflöden; de används inte som bevis för produktens tester.

## Licenshantering om Brightbean-reservvägen väljs

En modifierad Brightbean-applikation behandlas som AGPL-programvara. Behåll licenstexter och attribution. Planera en tillgänglig länk till motsvarande källkod för de användare som interagerar med den modifierade tjänsten; licensen kräver inte i sig att hemligheter eller företagens data publiceras. MIT-delar kan införlivas med deras notices bevarade. Denna leverans utgår från att källkod till den modifierade applikationen får erbjudas dess användare. Om affärsmodellen kräver att koden hålls hemlig även för dem, ska grunden bytas före implementation. [Brightbeans AGPL-text, särskilt avsnitt 13](https://raw.githubusercontent.com/brightbeanxyz/brightbean-studio/d85fce192e687d20e8fd7e9449a40ad7952ec7c3/LICENSE).

## API-underlag och kunskapsgräns

Metas officiella Instagram-samling beskriver professionella konton, publicering och skilda loginflöden. Den är bättre grund än ett tredjepartsrepos löfte, men exakt åtkomst för våra sex konton är ännu inte testad. Flera direktlänkar till `developers.facebook.com` gav 429 eller kunde inte hämtas. Därför är exakta scopes, formatgränser, Graph-version och Business Discovery-fält verifieringspunkter i etapp 0, inte antaganden om redan beviljad åtkomst. [Metas officiella samling](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api), [Metas insights-samling](https://www.postman.com/meta/instagram/folder/23987686-f659d7d1-d74c-44e4-9192-9b1e8694c511).

Metas offentliga information skiljer mellan tillåten och otillåten automatisk insamling. Att data går att se offentligt eller att en Apify-actor finns bevisar inte tillåten användning. Konkurrentkopplingen kräver därför verifierad metod och tydligt redovisad täckning. [Meta om automatisk insamling](https://about.fb.com/news/2021/04/how-we-combat-scraping/).
