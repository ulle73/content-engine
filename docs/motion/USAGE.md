# Motion i Content Engine

## Från ett inlägg till motionvideo

1. Öppna ett utkast och välj **Skapa motionvideo**. Befintlig text och contentidentitet behålls.
2. Välj mall och fyll i innehållet. Månadsöversikt kräver uttryckligen månad, antal, belopp och område.
3. Spara en version och välj **Förhandsvisa sparad version**. Förhandsvisningen renderas av separat worker.
4. Spela upp hela videon och granska storyboarden. Godkänn den när resultatet är rätt.
5. Välj **Skapa färdig video**. Slutvideon sparas som MediaAsset och väljs i samma utkast.
6. Välj **Fortsätt med utkastet** för att slutföra copy och gå vidare genom ordinarie granskning/leverans.

Du kan även börja under **Media → Motion**. Lägg sedan till copy i review; då syns arbetet på startsidan bland inläggsutkasten. Interna renderingar och bildgenerationer visas i sina respektive mediaflöden.

Förhandsvisningar och storyboardbilder hör till granskningen och kan inte väljas som inläggsmedia. En ny version kräver en ny godkänd preview. Slutvideor kan återanvändas i andra contentutkast genom det vanliga mediabiblioteket.

Fältet för slutvideo använder en befintlig video från företagets Media. Anpassade scener/ljud från MCP bevaras: webben visar dem för granskning och rendering men låter det förenklade formuläret skriva över dem först när specifikationen faktiskt kan återges utan förlust.

## Koppling till inspiration och sekvenser

I Marknaden kan **Till Creative Engine** föra en relevant mekanism och en egen anpassning till ett contentbrief. Externt originalunderlag fortsätter vara separat från företagets egna fakta. Creative- och contentflödena kan sedan öppna Sequence med samma brief.

För en manuell Sequence: lägg till minst två egna bilder, välj **Koppla bilderna till klipp**, och förbered/granska varje klipp. Kopplingen skapar en lokal struktur. En betald providerstart kräver fortfarande ordinarie granskning och godkännande.

## MCP

Webbappen och följande verktyg använder `engine.motion.service`, den gemensamma mallkompilatorn och samma modeller:

- `list_motion_templates`, `list_motion_projects`, `get_motion_project`
- `create_motion_project` med valfritt `run_id`
- `update_motion_project` med `expected_revision` och idempotency-nyckel
- `render_motion_project`, `approve_motion_preview`, `cancel_motion_render`

Skapa projekt först, köa preview, läs projektstatus, visa resultatet för användaren och godkänn sedan den granskade versionen. Final är spärrad utan en komplett godkänd preview av samma version. Alla anrop är scoped till det autentiserade företagets ägare. Se [OAuth och MCP](../chatgpt-business-mcp.md).

## Separat renderworker

### Tillfällig rendering på Windows utan extra molnserver

En konfigurerad dator kan köra `scripts/start-motion-local.ps1`. Processen hämtar jobb via utgående HTTPS, lyssnar endast på localhost och avslutas efter 15 minuters inaktivitet. Ingen Windows-tjänst, schemalagd uppgift eller automatisk start vid inloggning installeras. En ny körning startas manuellt när den behövs.

Servern använder `MOTION_WORKER_MODE=pull` och en gemensam slumpad `MOTION_WORKER_TOKEN`. `MOTION_WORKER_URL` lämnas tom. Datorns token ligger krypterad med Windows DPAPI i ignorerade `data/motion-local/token.dpapi`; licensläget i `data/motion-local/license-mode.txt` ska motsvara den faktiskt bekräftade licensen. Ingen hemlighet skrivs i skript eller Git.

Webbappen aktiverar renderknappen först när en autentiserad dator har hört av sig. Statusen upphör vid normal avslutning, eller senast 90 sekunder efter tappad kontakt. Ladda om projektsidan efter start eller stopp. Redan köade jobb ligger kvar och kan hämtas nästa gång renderingen startas. Förhandsvisning måste fortfarande granskas och godkännas innan slutrendering.

Django-webbrequesten renderar aldrig video. `motion-renderer/worker.mjs` hämtar hållbara jobb, använder lease/heartbeat och laddar tillbaka verifierade outputfiler. Avbrytna och utgångna leases kan inte spara resultat i efterhand.

På Django-servern:

```text
MOTION_WORKER_URL=https://<worker-origin>
MOTION_WORKER_TOKEN=<egen slumpad hemlighet med minst 32 tecken>
```

På workerprocessen:

```text
MOTION_API_URL=https://<content-engine-origin>
MOTION_WORKER_TOKEN=<samma hemlighet>
MOTION_LICENSE_MODE=<korrekt befintlig licensstatus>
PORT=<worker-port>
```

Worker accepterar `evaluation`, `eligible-free` och `company-license`. Lokal utvärdering använde `evaluation`. Produktionslicens och driftresurser ska fastställas före aktivering. HTTP till localhost kräver uttryckligen `MOTION_ALLOW_INSECURE_LOCAL=true`; offentlig origin ska använda HTTPS. Token och storagecredentials ska ligga i avsedd credentialstore/servermiljö.

Kör `npm ci`, `npm run typecheck`, `npm test`, `npm run build` och sedan `npm start` i `motion-renderer`. Workers pollar kön och kan även väckas av Django. `/healthz` visar workerstatus. En start utan ansluten worker visar ett tydligt meddelande i webbappen.

De lokala slutrenderingarna mätte upp till cirka 961 MB samlad RSS. Dimensionera drift utifrån faktisk last och lämna marginal för media, rendering och upload. Se [produktgranskningen](../2026-09-30-product-integration-review.md) för exakta mätningar och verifieringsgränser.
