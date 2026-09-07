# Beslut: ta bort Brightbean innan fortsatt utveckling

Datum: 2026-09-07. Ersätter tidigare val av Brightbean i planen och leveransordningen.

## Utgå från målet

En administratör ska hantera flera företags egna fakta och röst, skapa bra innehåll med befintliga Social Media Skills och lämna granskade utkast till hosted Postiz. Det behövs en liten webbapp för underlag och granskning, inte ytterligare en publiceringsplattform.

## Kritisk granskning

Brightbean gav snabb tillgång till inloggning, arbetsytor och en sidram, men drog samtidigt in dess organisations- och medlemsmodell, inläggsmodell, kalender, OAuth-server, MCP, bakgrundsjobb och frontendbygge. Våra kanaltexter lagrades både i ContentRun och Brightbeans Post. De flesta funktionerna användes inte eller överlappade det som hosted Postiz redan ska göra. Framför allt var appen direkt beroende av AGPL-kod genom settings, URL:er, modeller och mallar; det var inte bara en extern tjänstekoppling. Att välja detta fundament utan att först förankra licenskonsekvensen var ett för stort arkitekturbeslut.

**Beslut: ta bort Brightbean helt ur den aktiva implementationen.** Ingen wrapper runt Brightbean, inga avkopierade modeller eller sidmallar, och ingen ny frontendplattform som ersättning.

## Den minsta motiverade lösningen

| Del | Återanvändning / ansvar |
| --- | --- |
| Innehållshantverk | Oförändrade MIT-licensierade Social Media Skills: ideation, content pillars, caption writer, cross-platform repurposing |
| Textgenerering | Befintlig OpenAI SDK, strukturerade svar och eget företagsunderlag |
| Inloggning och formulär | Standard-Django med BSD-licens: auth, sessions, CSRF, lösenordsvalidering, ORM |
| Egen kod | Företagsunderlag, sparade idéer/utkast, granskningsformulär och en liten Postiz HTTP-klient |
| Konton och publicering | Hosted Postiz: Meta-anslutning, kalender, schemaläggning, publicering och resultat |
| Drift | En Python-webbprocess och befintlig hanterad PostgreSQL; ingen Node-byggkedja, egen kö eller scheduler |

Två affärsmodeller ersätter arbetsytor, medlemskap, BrandContext och dubbla inlägg: Company och ContentRun. Därtill finns en singleton för transaktionssäker första registrering. Bibliotekets auth-tabeller återanvänds, ingen egen lösenordslösning byggs.

Att bara använda skills + Postiz utan egen app vore mindre kod, men skills är instruktioner och Postiz ersätter inte vårt formulär för verifierade fakta, giltighet och företagsröst. Att bygga en större agentplattform eller behålla en andra publiceringsplattform saknar stöd i det ännu oprövade kärnflödet.

## Första start

En ny installation visar administratörsformuläret i UI. Det skapar konto och första företaget atomärt med Djangos lösenordshashning och loggar in användaren. Första registreringen låses mot samtidiga anrop i PostgreSQL och stängs därefter. På en publik installation används en engångskod från Render-inställningarna; lokalt behövs ingen sådan. Inga bootstrap-kommandon eller terminalskapade användarlösenord ingår längre.

## Licens och befintligt tillstånd

Brightbean-submodulen, dess runtime-importer, mallar och byggsteg är borttagna. Nuvarande egen kod har inte tilldelats en ny publik licens; ägaren får välja det separat. MIT-noticen för skills finns kvar. Tidigare AGPL-versioner finns kvar med sina licensvillkor i Git-historiken; borttagandet omlicensierar inte dessa retroaktivt. Detta är ett källkods- och beroendebeslut, ingen allmän juridisk garanti om alla användningsfall.

Vid bytet hade den gamla Neon-databasen noll företagsunderlag och noll innehållskörningar. Den bevaras. Nya tabeller har en egen databas på samma befintliga Neon-branch, vilket undviker att blanda två inkompatibla auth-/migreringshistoriker. Inget extra databaskluster byggs.

## Dyraste obevisade antagandet

**Vi har ännu inte bevisat att användarens hosted Postiz-abonnemang och verkliga Meta-konton ger fungerande API-åtkomst för våra utkast och bilder.** Dokumentation och mocktester bevisar endast förväntat format. Nästa bevis ska vara ett granskat utkast med en riktig bild till rätt företagskonto i Postiz, följt av kontrollerad publicering med ägarens godkännande. Inga fler funktioner före detta bevis.

Andra praktiska begränsningar: modellens företagsröst och kvalitet måste bedömas på verkliga underlag, källcitat garanterar inte alla påståenden, och ett avbrutet överföringsförsök kan behöva kontrolleras manuellt i Postiz. Hosted Postiz minskar underhåll men skapar ett medvetet tjänsteberoende och en abonnemangskostnad.

## Källor

- Django-licens: https://github.com/django/django/blob/main/LICENSE
- Social Media Skills-licens: https://github.com/social-media-skills/skills/blob/main/LICENSE
- Postiz API: https://docs.postiz.com/public-api/introduction

## Verifiering efter ändringen

- Ren installation utan Brightbean: 10 direkta produktionsberoenden; tidigare lista hade 31 poster inklusive utvecklingsverktyg.
- Nio riktade tester passerar. Inga saknade migreringar eller brutna paketberoenden.
- Verkliga AI-anrop i den rena miljön: tre idéer, Facebook- och Instagramtext på 13,9 sekunder. Syntetiska fakta, ingen publicering.
- Startvyn granskad visuellt i webbläsaren; den visar första administratörens formulär på svenska.
- Postiz och publik driftsättning är fortfarande inte verifierade.
