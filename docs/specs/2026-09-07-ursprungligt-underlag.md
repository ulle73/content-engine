# Projekt: Social Content Engine för flera företag

## Uppdraget

Ta fram och bygg den bästa möjliga lösningen för att hantera Facebook- och Instagram-content för initialt **tre olika företag**.

Du ska själv analysera kraven, tillgängliga open-source-projekt, API:er och tekniska alternativ och därefter välja den arkitektur och implementation som ger bäst slutresultat.

Utgå **inte** från att tidigare föreslagna tekniska lösningar är rätt.

Exempelvis är det inte redan bestämt:

* vilka repo:n som ska användas
* om repo:n ska klonas, forkas, användas som inspiration eller inte användas alls
* om publicering ska ske direkt mot Meta eller genom ett befintligt system
* exakt frontend/backend-stack
* exakt databasstruktur
* exakt AI-provider
* exakt scraper
* exakt jobbsystem
* hur skills ska integreras

Det viktiga är slutresultatet och nedanstående mål.

---

# 1. Övergripande mål

Systemet ska göra det möjligt för en person att sköta sociala medier för flera företag med mycket liten manuell arbetsinsats, utan att kvaliteten blir generisk eller AI-liknande.

Systemet ska gå från:

**riktig information om företaget + tidigare content + företagets bilder + vad som fungerar historiskt + vad konkurrenter gör**

till:

**relevanta, färdiga och faktakontrollerade förslag för Facebook och Instagram.**

En människa ska huvudsakligen behöva:

1. kontrollera vad som föreslås
2. eventuellt göra en liten ändring
3. välja/byta bild vid behov
4. godkänna
5. låta systemet sköta resten

Systemet ska inte bara vara en AI-textgenerator.

Det ska vara en **redaktionell motor som kontinuerligt fattar bättre contentbeslut**.

---

# 2. Initial omfattning

Initialt:

* 3 företag
* Facebook
* Instagram

Systemet ska vara utformat så att fler företag kan läggas till senare utan att varje nytt företag kräver ny specialkod.

Det behöver däremot inte stödja tio olika sociala plattformar från början.

---

# 3. Extremt viktigt: enkelhet

Systemet ska kunna lämnas över till en annan person som aldrig tidigare sett det.

Den personen ska förstå hur det fungerar nästan direkt.

## Allt användargränssnitt ska vara på svenska.

Undvik tekniska uttryck i gränssnittet.

Visa exempelvis inte:

* Brand Brain
* Pipeline
* Ingest
* Source Item
* LLM
* Performance Index
* Publisher
* Worker
* Queue
* Fact extraction

Använd istället begripliga ord som:

* Företag
* Aktuellt just nu
* Innehållsförslag
* Godkänn inlägg
* Bilder
* Konkurrenter
* Publicerat
* Resultat
* Om företaget

Teknisk komplexitet får finnas bakom systemet.

Den får inte märkas för användaren.

---

# 4. Delegationstestet

En ny person ska utan utbildning inom cirka fem minuter kunna förstå:

* vilket företag personen arbetar med
* vad som behöver göras
* vilka inlägg som väntar på godkännande
* hur ett inlägg godkänns
* hur text ändras
* hur bild ändras
* hur ett förslag avslås
* hur ny aktuell information om företaget läggs till
* hur man ser vad som fungerat bäst tidigare

Om detta kräver en lång manual är UX:en inte tillräckligt bra.

---

# 5. Företagen måste vara helt separerade

Varje företag ska ha sin egen kunskap och historik.

Systemet behöver förstå bland annat:

* vad företaget är
* produkter/tjänster
* mål
* målgrupper
* positionering
* tonalitet
* uttryck som bör användas
* uttryck som bör undvikas
* vilka typer av content man vill göra
* vilka ämnen man inte vill använda
* tidigare content
* tidigare resultat
* konkurrenter
* bildmaterial
* aktuell information
* kampanjer
* events
* erbjudanden

Information från företag A får inte råka påverka företag B.

---

# 6. Företagets riktiga tonalitet

AI:n ska inte nöja sig med beskrivningar som:

"professionell men personlig".

Den bör kunna lära sig från företagets riktiga material, exempelvis:

* tidigare Instagraminlägg
* tidigare Facebookinlägg
* webbplats
* nyheter
* annan företagskommunikation
* exempel på content företaget gillar
* exempel på content företaget ogillar

Målet är att nytt content faktiskt ska kännas som företagets content.

Inte som generisk AI-copy.

---

# 7. Aktuell information om företaget

Systemet måste känna till vad som händer **just nu**.

Exempel:

* nyheter
* events
* tävlingar
* kampanjer
* nya produkter
* ändrade öppettider
* aktuell banstatus
* nya medarbetare
* aktuella erbjudanden
* saker som just inträffat

Information ska kunna komma både automatiskt och manuellt.

---

# 8. "Aktuellt just nu"

Det ska finnas ett extremt enkelt sätt för en människa att ge systemet färsk information.

Exempel:

> Gullbringa har fått nya rangebollar idag. Bilder kommer senare.

Det ska inte kräva en AI-prompt eller tekniskt formulär.

Systemet ska förstå att detta är ny aktuell information som kan bli relevant för kommande content.

Man ska kunna se:

* vad som är aktuellt
* när informationen lades till
* hur länge den gäller
* var informationen kommer ifrån

---

# 9. Färsk information får inte blandas ihop med gammal information

Ett viktigt problem att lösa är gammal fakta.

Exempel:

Om greenfee tidigare var 495 kr men nu är 695 kr får AI:n inte använda den gamla summan.

Detsamma gäller:

* gamla kampanjer
* gamla eventdatum
* gamla öppettider
* tidigare personal
* tidigare erbjudanden
* tillfälliga nyheter

Systemet behöver därför kunna förstå skillnaden mellan:

**permanent företagskunskap**

och

**information som bara är aktuell under en viss period.**

---

# 10. Källor och faktakontroll

AI:n ska inte hitta på företagsfakta.

För varje innehållsförslag bör det gå att förstå var de viktiga uppgifterna kommer ifrån.

Exempel:

> Tävlingsdatum: verifierat från tävlingssidan.

> Pris: verifierat från aktuell prislista.

Om en viktig uppgift inte kan verifieras ska systemet hellre varna än gissa.

## Absolut mål:

**0 publicerade hallucinationer om företagets fakta.**

Fel ton är dåligt.

Fel pris, datum eller erbjudande är ett produktfel.

---

# 11. Företagets riktiga bilder ska prioriteras

Grundprincip:

**riktiga bilder från företaget först.**

AI-genererade golfbanor, lokaler, människor eller produkter som inte finns på riktigt ska inte användas för att representera företaget.

AI-bildgenerering är däremot lämpligt för exempelvis:

* grafik
* konceptbilder
* infografik
* illustrationer
* bakgrunder
* kampanjmaterial där verklighetsåtergivning inte krävs

Vi accepterar att bildgenerering kostar pengar.

---

# 12. Smart bildbibliotek

Systemet bör kunna förstå företagets bilder.

Exempelvis:

* vad bilden föreställer
* miljö
* personer
* årstid
* orientering
* bildkvalitet
* möjliga användningsområden

Målet är att AI:n ska kunna föreslå en relevant riktig bild till ett innehållsförslag istället för att någon manuellt letar genom hundratals filer.

---

# 13. Bildrättigheter

Det bör gå att lagra relevant information om användningsrättigheter.

Exempel:

* får användas på sociala medier
* får användas i annonser
* fotograf
* innehåller barn
* samtycke verifierat
* eventuellt sista giltighetsdatum

Systemet ska inte automatiskt rekommendera bilder som inte är godkända för användningen.

---

# 14. Content ska börja med idéer

Systemet bör skilja på:

**content-idé**

och

**färdigt inlägg.**

Det är viktigt.

Först ska motorn hitta de bästa sakerna företaget borde prata om.

Därefter ska de bästa idéerna utvecklas till faktiska posts.

---

# 15. Idéer ska baseras på verkliga signaler

Idégenereringen bör kunna ta hänsyn till:

* vad som händer i företaget nu
* företagets affärsmål
* företagets contentområden
* vad företaget redan publicerat
* företagets egna historiska resultat
* relevant omvärld
* konkurrenternas content
* konkurrenternas ovanligt bra content
* tillgängliga riktiga bilder
* hur aktuell idén är

AI:s fria fantasi bör komma längre ned i prioritet.

---

# 16. Undvik repetition

Systemet ska känna till tidigare publicerat content.

Det ska exempelvis kunna upptäcka:

> Vi publicerade nästan exakt detta för två veckor sedan.

Återanvändning kan ibland vara rätt.

Oavsiktlig AI-repetition är inte rätt.

---

# 17. Konkurrentbevakning

Detta ska vara en viktig del av systemet.

För varje företag ska relevanta konkurrenter kunna definieras.

Systemet ska kunna analysera offentligt content från deras Facebook- och Instagramkonton där det är praktiskt och tillåtet.

Intressant data kan exempelvis vara:

* post
* caption
* datum
* format
* likes
* kommentarer
* shares
* Reel-views
* andra offentliga engagemangssignaler

---

# 18. Konkurrentdata måste normaliseras

Ett inlägg med 500 likes är inte automatiskt bättre än ett med 100 likes.

Konton har olika publikstorlek och normal performance.

Systemet bör därför försöka hitta:

**posts som presterar ovanligt bra jämfört med vad just det kontot normalt gör.**

Exempel:

Normalt:
100 likes

Aktuell post:
370 likes

=> tydlig outlier.

Det är mer intressant än absoluta likes.

---

# 19. Förstå VARFÖR konkurrentinnehåll fungerar

Systemet bör kunna analysera exempelvis:

* ämne
* format
* hook
* Reel/bild/carousel
* längd
* person i bild eller inte
* bakom kulisserna
* utbildande
* underhållning
* community
* kommersiellt/icke kommersiellt
* CTA
* text-overlay
* timing

Målet är att identifiera mönster.

Inte att kopiera andra företags posts.

---

# 20. Konkurrenter ska ge inspiration – inte styra allt

Den egna historiska datan ska väga tyngre.

Om konkurrenternas ban-Reels går bra men Gullbringas egna junior-Reels går ännu bättre bör systemet förstå det.

Grundprincip:

1. aktuell sanning om företaget
2. företagets mål och strategi
3. företagets egen performance
4. tidigare publicerat
5. konkurrentinsikter
6. generella best practices
7. AI:s egna fria idéer

---

# 21. Comments kan vara en viktig signal

För särskilt framgångsrika offentliga posts kan kommentarer ge information om vad målgruppen faktiskt undrar över.

Exempel:

Post:
"Banan öppnar fredag."

Kommentarer:

* När öppnar rangen?
* Är restaurangen öppen?
* Kan man boka redan nu?

Detta kan ge nya contentidéer.

---

# 22. Contentproduktion

När en idé väljs ska systemet kunna skapa relevant material för Facebook och Instagram.

Exempel:

* captions
* anpassning mellan Facebook och Instagram
* Reel-idéer
* Reel-scripts
* carousels
* Story-idéer
* hooks
* CTA
* hashtags när det faktiskt behövs
* brief till fotograf/video
* förslag på befintlig bild
* prompt för AI-bild när AI-bild är motiverad

Det behöver inte alltid vara exakt samma copy på Facebook och Instagram.

---

# 23. Visa varför ett förslag skapades

För varje contentförslag bör användaren på enkel svenska kunna förstå:

### Varför föreslås detta?

Exempel:

* Aktuell nyhet från Gullbringa
* Bana är ett prioriterat ämne
* Liknande Gullbringa-inlägg har fungerat bra
* Konkurrenternas bakom-kulisserna-content går ovanligt bra
* Ämnet har inte använts nyligen
* Bra riktiga bilder finns

Det ska skapa förtroende för systemet.

---

# 24. Human approval

Initialt ska inget publiceras helt autonomt.

En människa ska godkänna content.

UI:t bör göra besluten mycket enkla:

* Godkänn
* Ändra
* Nej tack

Eventuellt även:

* Godkänn hela veckan

---

# 25. Systemet ska lära sig av ändringar och avslag

När ett förslag avslås eller behöver ändras är det värdefull data.

Exempel på anledningar:

* för säljigt
* låter AI-genererat
* för stelt
* tråkigt
* fel ämne
* fel information
* redan gjort
* dålig bild
* fel timing
* annat

Systemet bör på sikt använda denna information för att bli bättre.

---

# 26. Publicering

Det slutliga systemet ska kunna få godkänt content publicerat eller schemalagt på:

* Facebook
* Instagram

Hur detta bäst görs ska du själv utvärdera.

Det kan exempelvis vara direkt mot officiella Meta-API:er eller via något befintligt open-source-system.

Välj inte en tung lösning bara för att den finns.

Välj den lösning som bäst passar det faktiska behovet.

---

# 27. Performance efter publicering

Systemet ska försöka hämta relevanta resultat från egna publicerade posts.

Exempel:

* likes
* comments
* shares
* views
* reach när tillgängligt
* andra relevanta metrics

Resultat bör kunna följas vid flera tidpunkter om det ger bättre jämförbarhet.

---

# 28. Performance ska faktiskt påverka framtida content

Vi vill inte bygga en analytics-dashboard som ingen använder.

Om systemet lär sig:

> Gullbringas behind-the-scenes Reels presterar 2,1 gånger bättre än deras normala content.

ska det påverka framtida contentförslag.

Detta är centralt.

---

# 29. Resultatsidan ska vara enkel

Visa inte femtio grafer bara för att datan finns.

Användaren behöver snarare förstå:

### Det här fungerar bra

* bakom kulisserna
* personal
* ban-Reels
* juniorinnehåll

### Det här fungerar sämre

* generiska kampanjbilder
* vanliga sponsorposters

### Rekommendation

Gör mer av X.
Gör mindre av Y.

---

# 30. Exempel: Gullbringa Golf

Gullbringa Golf kan användas som ett bra första referensföretag.

Systemet bör för Gullbringa exempelvis kunna förstå information kring:

* golfbanan
* aktuellt skick/banskötsel
* tävlingar
* juniorverksamhet
* Academy
* medlemmar
* greenfee
* Pay & Play
* restaurang
* events
* personal
* klubbnyheter

Exempel på användarupplevelse:

Systemet upptäcker:

> Greenerna hålpipas.

Systemet ser även:

* Gullbringa har inte nyligen gjort samma content
* bakom-kulisserna-content från bana fungerar bra
* relevanta riktiga Gullbringa-bilder finns

Systemet kan då föreslå:

> Varför gör vi egentligen hål i en perfekt green?

med:

* förslag på format
* caption
* relevant riktig bild
* faktakällor
* förslag på publicering
* enkel förklaring till varför idén valdes

Människan granskar och godkänner.

---

# 31. Vad användaren helst ska se när systemet fungerar

Exempel:

## Gullbringa Golf

**Det här behöver din uppmärksamhet**

5 inlägg är klara att godkänna
1 inlägg saknar bild
1 uppgift behöver kontrolleras

### Den här veckan

Måndag
Varför hålpipar vi greenerna?
**Klar att godkänna**

Onsdag
KM-vinnarna
**Klar att godkänna**

Fredag
Helgens banstatus
**Saknar bild**

Det ska kännas mer som en enkel arbetslista än som ett avancerat marknadsföringsverktyg.

---

# 32. Vad systemet INTE ska försöka bli

Bygg inte en generell konkurrent till Hootsuite, Buffer eller Meta Business Suite.

Initialt behövs inte:

* komplett CRM
* DM inbox
* avancerad kommentarshantering
* eget Canva
* full bildredigerare
* avancerad videoredigerare
* annonser/Ads Manager
* influencerplattform
* avancerad kundportal
* komplicerade permissions
* mobilapp
* stöd för alla sociala nätverk
* avancerade agentteam bara för sakens skull
* stora analyticsdashboards utan tydlig nytta

Varje större funktion bör kunna motiveras genom minst en av:

1. bättre content
2. mindre manuellt arbete
3. mindre risk för fel

Annars hör den sannolikt inte hemma i första produkten.

---

# 33. Kostnad

Målet är inte längre absolut nollkostnad.

Det är helt acceptabelt att betala mindre summor för sådant som tydligt förbättrar systemet.

Exempel:

* bra LLM/API
* bildgenerering
* Apify eller annan stabil datakälla
* mindre externa API-kostnader

Undvik däremot dyra SaaS-abonnemang om samma sak rimligen kan lösas enkelt och stabilt på annat sätt.

Optimera inte bort några kronor om det leder till många timmars underhåll.

---

# 34. Docker

Ett uttryckligt krav/preferens:

**Lösningen ska kunna köras utan Docker.**

Undvik att göra Docker till ett krav för utveckling eller normal drift.

Detta ska vägas in när befintliga open-source-projekt utvärderas.

---

# 35. n8n

n8n har diskuterats.

Det kan self-hostas och Community Edition kan användas utan vanlig SaaS-avgift, men det finns inget krav på att n8n ska användas.

Lägg inte till ett separat automationssystem om vanlig applikationslogik ger en enklare lösning.

Samtidigt får du själv välja n8n om du efter analys kan visa att det faktiskt förenklar slutprodukten.

---

# 36. Open-source-projekt att utvärdera

Följande projekt har identifierats under research.

De ska ses som **referenser och möjliga byggblock**, inte som redan valda tekniska beslut.

## A. social-media-skills/skills

Mycket relevant.

106 social-media-skills för AI-agenter.

Innehåller bland annat:

* brand profile
* voice builder
* audience research
* social strategy
* content pillars
* goals/KPI
* idea generation
* content research
* competitor analysis
* viral reverse engineering
* content calendar
* captions
* video
* design
* analytics
* publicering

Viktig idé:

Alla skills arbetar från gemensam information om företagets brand och voice istället för att varje AI-anrop börjar från noll.

MIT-licens.

Repo:
**social-media-skills/skills**

---

## B. charlie947/social-media-skills

Mycket relevant som inspiration.

Detta är Charlie Hills system med skills för bland annat:

* voice-builder
* post-scorer
* reels-scripting
* hook-generator
* post-formatter
* content-matrix
* niche-research
* analytics

Särskilt intressant:

### post-scorer

Jämför nya drafts med verklig historisk performance.

### voice-builder

Bygger reproducerbar tonalitet från riktiga texter.

### content-matrix

Kombinerar contentområden med format för systematisk idégenerering.

### reels-scripting

Reverse-engineerar framgångsrika Reels.

MIT-licens.

Repo:
**charlie947/social-media-skills**

---

## C. Freespirits/social-auto-engine

Mycket relevant som referensarkitektur.

Projektet heter SocialBlast AI och försöker lösa ungefär samma övergripande problem:

* flera sociala konton
* Facebook
* Instagram
* AI-content
* brand voice
* approval queue
* publicering
* scraping via Apify
* schemaläggning
* flera AI-providers

Det kombinerar själv två tidigare projekt:

* HagaiHen/facebook-mcp-server
* charlie947/social-media-skills

Det är därför särskilt intressant att studera.

Projektet är dock fortfarande betydligt mindre och mindre beprövat än exempelvis Postiz.

Behandla det som:

**kod och idéer som kan vara mycket värdefulla**

inte automatiskt som:

**plattformen vi ska bygga allt på.**

MIT-licens.

Repo:
**Freespirits/social-auto-engine**

---

## D. HagaiHen/facebook-mcp-server

Facebook MCP-server ovanpå Graph API.

Kan bland annat:

* skapa Facebook-posts
* arbeta med comments
* hämta insights
* moderation
* låta AI-agenter använda Facebookfunktioner

Det är också en av grunderna som Social Auto Engine byggts från.

Relevant framför allt för att studera hur Meta/Facebook-funktionerna abstraherats.

Repo:
**HagaiHen/facebook-mcp-server**

---

## E. prodkit-labs/instagram-competitor-intelligence

Relevant framför allt för competitor intelligence.

Innehåller exempel för:

* flera konkurrentkonton
* hämta publika Instagram-posts/Reels
* ranka top performers
* hashtag trends
* creator mentions
* jämföra konkurrenter
* veckorapporter
* CSV-export
* schemaläggning

MIT.

Projektet är fortfarande litet.

Se det därför huvudsakligen som:

**referensimplementation och idébank för konkurrentanalys.**

Repo:
**prodkit-labs/instagram-competitor-intelligence**

---

## F. gitroomhq/postiz-app

Mycket stort och etablerat open-source-projekt för social scheduling.

Har bland annat:

* Instagram
* Facebook
* många andra plattformar
* scheduling
* analytics
* team
* API
* automation

Aktuellt repo har cirka 35k+ stars.

Nackdelar för vårt behov:

* betydligt större system än vad vi initialt behöver
* tung teknisk stack
* self-hosting är mer omfattande
* AGPL-3.0

Det ska framför allt utvärderas som:

* möjlig publiceringslösning
* referens för integrationer
* referens för scheduling

Inte automatiskt som grunden till hela produkten.

Repo:
**gitroomhq/postiz-app**

---

## G. brightbeanxyz/brightbean-studio

Open-source social-media-management-system med tydligt multi-client/agency-fokus.

Innehåller bland annat:

* organisations/workspaces
* flera kunder
* Facebook
* Instagram
* kalender
* approvals
* analytics
* content composer
* client roles
* flera sociala nätverk
* officiella plattforms-API:er

Intressant om behovet senare växer från 3 företag till betydligt fler.

AGPL-3.0.

Repo:
**brightbeanxyz/brightbean-studio**

---

## H. inovector/mixpost

Etablerad self-hosted scheduler / Buffer-alternativ.

Relevant framför allt för:

* scheduling
* publicering
* social-account management

MIT-licens.

Content intelligence är mindre central än i projekten ovan.

Repo:
**inovector/mixpost**

---

## I. timgit/pg-boss

Inte ett social-media-system.

Node.js-jobbkö som använder PostgreSQL och kan hantera bland annat:

* schemalagda jobb
* cron
* retries
* dead-letter jobs
* background processing

Relevant endast om arkitekturen behöver sådan funktionalitet och om detta ger en enklare lösning än ytterligare infrastruktur.

MIT.

Repo:
**timgit/pg-boss**

---

## J. n8n-io/n8n

Generell workflow-automation.

Kan:

* schemalägga workflows
* ansluta API:er
* AI-workflows
* approvals
* automation

Self-hosting finns.

Fair-code, inte vanlig MIT.

Det finns inget krav på att n8n används.

Repo:
**n8n-io/n8n**

---

# 37. Viktig fråga du ska lösa själv

Analysera samtliga relevanta repo:n och avgör själv:

* vilka delar som är bra
* vilka delar som inte passar
* vad som bör återanvändas
* vad som bör byggas själv
* om något repo kan användas nästan direkt
* om något bara ska användas som inspiration
* om flera projekt bör kombineras
* om det är bättre att inte bero på dem alls
* licenskonsekvenser
* underhållsrisk
* komplexitet
* Dockerberoenden
* hur enkelt systemet blir att lämna över

Utgå inte från principen:

> Ju mer färdig open-source-kod, desto bättre.

Mindre egen kod är bara bättre om slutresultatet också blir enklare och stabilare.

---

# 38. API:er och externa tjänster

Det är acceptabelt att lösningen senare behöver exempelvis:

* LLM API-key
* bildgenererings-API
* Apify-token eller motsvarande
* Meta App/API credentials
* andra relevanta integrationsuppgifter

Arkitekturen ska dock kunna utvecklas och testas så långt det är rimligt innan alla produktionsnycklar finns.

Hemligheter får aldrig committas till Git.

Ta fram själv vilka credentials som faktiskt behövs baserat på den arkitektur du väljer.

---

# 39. Bra slutresultat

Projektet är lyckat om:

### Content

Minst ungefär 80 % av de föreslagna idéerna känns relevanta nog att överväga för publicering.

En hög andel färdiga posts ska kunna godkännas direkt eller efter mycket små ändringar.

---

### Fakta

Inga hallucinerade priser, datum, events eller andra företagsuppgifter publiceras.

---

### Tid

Efter intrimning ska en person kunna hantera en veckas content för ett företag med mycket liten manuell arbetsinsats.

Ett rimligt mål är ungefär:

**15–20 minuter mänskligt redaktionellt arbete per företag och vecka**

utöver fotografering/video och andra aktiviteter som naturligt måste göras ute i verksamheten.

---

### Enkelhet

En ny användare förstår arbetsflödet inom några minuter.

---

### Lärande

Efter några månader ska systemets rekommendationer vara bättre än från början eftersom det använder:

* approvals
* rejects
* ändringar
* egen performance
* tidigare content
* konkurrentmönster

---

### Relevant automatisering

Människan ska främst fatta beslut.

Systemet ska göra förarbetet.

---

# 40. Dåligt slutresultat

Projektet är misslyckat om:

* användaren fortfarande måste komma på alla idéer själv
* AI:n skriver generiskt content
* företagen låter likadant
* systemet återupprepar samma ämnen
* gammal information återanvänds som aktuell
* fakta hallucineras
* användaren manuellt måste leta efter bilder hela tiden
* competitor scraping samlar data utan att påverka idéerna
* analytics visas men påverkar inte framtida beslut
* användaren måste förstå tekniska begrepp
* systemet kräver omfattande utbildning
* systemet får fler funktioner men arbetsflödet blir långsammare
* det kräver mer administration än att göra content manuellt
* systemet blir en dålig kopia av Hootsuite istället för en bra contentmotor

---

# 41. Viktigaste KPI:erna

Prioritera produkt-KPI:er som faktiskt säger om motorn fungerar.

Särskilt:

### Direct approval rate

Hur stor andel kan godkännas direkt?

### Minor edit rate

Hur stor andel kräver bara små ändringar?

### Reject rate

Hur många förslag är helt fel?

### Manual minutes per published post

Hur mycket mänsklig tid krävs?

### Fact failure rate

Hur ofta upptäcks felaktiga eller obekräftade faktauppgifter?

### Repetition rate

Hur ofta föreslår systemet för liknande content?

### Performance versus historical baseline

Blir företagets content faktiskt bättre över tid?

---

# 42. Grundprincip

När du står inför tekniska val ska du optimera för:

**bättre content + mindre mänskligt arbete + mindre risk för fel + extrem enkelhet för slutanvändaren.**

Inte för:

* flest tekniker
* flest agents
* flest integrationer
* snyggast arkitekturdiagram
* mest autonom AI
* minst möjliga API-kostnad

---

# 43. Ditt uppdrag innan implementation

Gör först en kritisk analys.

Identifiera:

1. det dyraste obevisade antagandet
2. de största tekniska riskerna
3. vilka repo:n som faktiskt är värdefulla
4. vilka repo:n som kan skapa mer problem än de löser
5. vilka delar som bör testas innan resten byggs
6. hur resultatet bör valideras mot riktiga Gullbringa-data
7. vilken arkitektur som bäst når produktmålet
8. vilka API-nycklar/accounts/credentials som behövs
9. vad som kan byggas/testas utan dessa
10. hur systemet hålls enkelt nog för att lämnas över till en icke-teknisk person

Välj sedan själv den bästa vägen.

Det slutliga målet är inte att bygga exakt det som beskrivits tekniskt.

Det slutliga målet är att lösa arbetsuppgiften bättre än vi gör manuellt idag.
