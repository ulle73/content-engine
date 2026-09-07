> HISTORISKT UNDERLAG: Tidslinje och byggordning är ersatta för första versionen. Se [aktuell leverans i timmar](../../2026-09-07-forsta-version.md).

# Social Content Engine – teknisk byggordning

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Leverera den svenska redaktionella produkten med återanvända skills och Postiz som publiceringstjänst.

**Architecture:** En Django-app för redaktionellt tillstånd och Postiz via publikt API för externa konton och leverans. Håll alla företagsdata inom obligatorisk företagskontext. Bygg inte en andra Meta-adapter eller ett eget köbibliotek.

**Tech Stack:** Python 3.12, Django 5.2 LTS med aktuell säkerhetspatch, PostgreSQL, Django Q2/ORM-broker, Django-templates/HTMX, OpenAI SDK, S3-storage, pytest och Playwright för de centrala användarflödena.

**Spec:** [Fullständig produkt- och projektplan](2026-09-07-social-content-engine.md), [användarens original](../../specs/2026-09-07-ursprungligt-underlag.md), [Postiz-jämförelse](../../research/2026-09-07-postiz-jamforelse.md).

## Globala krav

- ”Allt användargränssnitt ska vara på svenska.”
- ”Information från företag A får inte råka påverka företag B.”
- ”Initialt ska inget publiceras helt autonomt.”
- ”Lösningen ska kunna köras utan Docker.”
- ”Hemligheter får aldrig committas till Git.”
- ”riktiga bilder från företaget först.”
- Ingen extern publicering får ske utan mänskligt godkännande av exakt revision.
- Använd färdiga bibliotek för auth, databas, jobb, HTTP, filer och bildbearbetning. Återanvändningsvalen är beslutade; inga ytterligare kompletta sociala plattformar kombineras.

Detta är en byggplan. Filnamn, kommandon och kontrakt nedan beskriver vad som ska skapas; applikationen och dess tester finns ännu inte. Nya migrationer skapas i respektive uppgift och ingår i samma ändring. Implementation börjar först efter denna planeringsleverans.

## Filansvar

```text
config/                         Django-settings, URL-registrering och WSGI
apps/companies/                 Company, medlemskap, ChannelBinding och åtkomst
apps/editorial/models/          facts.py, sources.py, profiles.py, content.py, feedback.py
apps/editorial/services/        facts.py, context.py, ideas.py, drafting.py, approvals.py
apps/editorial/prompts/         versionslåsta anpassade instruktioner
apps/media/                     originalfiler, rättigheter, annotationer och bildurval
apps/publishing/                Postiz-adapter, dispatch, avstämning och leveransstatus
apps/competitors/               tillåten import, normalisering och mönster
apps/results/                   observationer, jämförbarhet och lärdomar
templates/editorial/            översikt, granskning, aktuellt, bilder, resultat
locale/sv/LC_MESSAGES/          svenska texter för ramverkets relevanta flöden
tests/contracts/               sparade/rensade API-kontrakt och adaptertest
tests/integration/             PostgreSQL, RLS, godkännande och jobb
tests/e2e/                     svensk webbläsarupplevelse
tests/fixtures/                syntetiska och anonymiserade testunderlag
evals/                          Gullbringa-bedömning och tidsordnad kvalitetsmätning
vendor-manifest.json            källrepo, SHA, fil, licens, ändringar och testversion
THIRD_PARTY_NOTICES.md           bevarade licenser och attribution
scripts/                       native installation, bygge och återställningskontroll
docs/runbooks/                  drift, kontofel, paus, återställning och uppdatering
```

Postiz-kod kopieras inte in. Huvudskillpaketet hämtas från den granskade SHA:n `6e30eeb2f6736bda8683b6bbaa674af3641d7945`; nyare version väljs bara efter differensgranskning. Licensen och den ursprungliga instruktionen behålls vid bearbetning. Webb-, kommentar- och företagsinnehåll laddas aldrig som exekverbara skills.

## Gemensamma kontrakt

Indata till tjänstelagret valideras med dataklasser/Pydantic. Inget tenant-ID eller integration-ID hämtat från en modelltext accepteras som behörighet. API-ID:n är strängar även om leverantörens exempel ser ut som UUID eller CUID.

```python
# apps/companies/contracts.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class CompanyContext:
    company_id: UUID
    actor_id: int
    role: str  # "admin" eller "editor", fastställt från medlemskap på servern
```

```python
# apps/publishing/contracts.py
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class ProviderReceipt:
    provider_post_id: str | None
    state: Literal["accepted", "published", "failed", "unknown"]
    platform_post_id: str | None = None
    permalink: str | None = None

# PostizClient-kontrakt, implementeras i T01:
# list_channels() -> list[dict]
# upload_media(path: str, content_type: str) -> dict
# create_post(payload: dict) -> ProviderReceipt
# list_posts(start_iso: str, end_iso: str) -> list[dict]
# cancel_post(provider_post_id: str) -> ProviderReceipt
# post_metrics(provider_post_id: str, days: int) -> list[dict]
```

Det exakta leverantörsschemat för uppladdning och borttagning hämtas från Postiz dokumentationsindex under T01. Vi uppfinner inte endpointnamn från kontraktets metodnamn. `cancel_post` betyder stopp av en ännu opublicerad leverans; borttagning av ett publicerat inlägg kräver en separat tydlig användarhandling.

Följande endpoints ägs av vår app och binder alltid `company_id` till autentiserat medlemskap:

| Endpoint | Ansvar |
|---|---|
| `GET /api/foretag/{company_id}/oversikt` | Arbetslista och antal åtgärder. |
| `POST /api/foretag/{company_id}/aktuellt` | Spara rå nyhet och tidstolkning. |
| `POST /api/foretag/{company_id}/fakta/{fact_id}/bekrafta` | Ansvarig bekräftar konkreta värden och giltighet. |
| `POST /api/foretag/{company_id}/forslag/{id}/versioner` | Skapa ny immutable text-/bildrevision. |
| `POST /api/foretag/{company_id}/forslag/{id}/godkann` | `revision_id`, innehållshash och explicit kanal/tid. |
| `POST /api/foretag/{company_id}/forslag/{id}/avsla` | Skäl och eventuell kommentar. |
| `POST /api/foretag/{company_id}/publiceringar/{id}/pausa` | Stoppa lokalt eller begär/avstäm externt stopp. |
| `GET /api/foretag/{company_id}/resultat` | Begripliga insikter med evidens och osäkerhet. |

Felkontrakt: 401 saknar session, 403 saknar behörighet, 404 objekt finns inte inom aktuellt företag, 409 revision/tillstånd har ändrats och 422 innehållet klarar inte kontrollerna. Svaret innehåller svensk `message` och stabil intern `code`. Tokens eller råa leverantörssvar returneras aldrig till redaktören.

## T01 – bevisa Postiz och native grund

**Filer:** skapa `config/settings.py`, `apps/publishing/contracts.py`, `apps/publishing/postiz.py`, `tests/contracts/test_postiz.py`, `tests/fixtures/postiz/`, `scripts/setup.ps1`, `scripts/build.sh`, `docs/research/postiz-capability-matrix.md`, `pyproject.toml` och låsfil.

**In:** [Postiz offentliga API](https://docs.postiz.com/public-api/introduction), granskad plan, tillgängliga testcredentials. **Ut:** fungerande `PostizClient` enligt ovan, dokumenterad kapabilitetsmatris och native processer. Ingår i etapp 0.

- [ ] Spara observerade schemas för konto, uppladdning, post, status, avbrytande och analytics i rensade testfixturer. Dokumentera källa, datum och faktiskt kontoslag; inga hemligheter eller verkliga kommentarer i Git.
- [ ] Skriv adaptertest för 401, 429, semantisk API-error i 200-svar och timeout efter skickat skapandeanrop. Kör `pytest tests/contracts/test_postiz.py -q` och se att saknad implementation ger fel.
- [ ] Implementera en enda HTTP-adapter. GET får begränsade återförsök. Skapande-POST återförsöks inte vid tvetydigt utfall. Varje nätverksanrop får explicit connect/read-timeout, loggmaskning och storleksgräns.
- [ ] Starta Django, Postgres och Q2 med ORM-broker utan Docker på Windows och native Linux-staging. Verifiera att en köad uppgift överlever omstart.
- [ ] Genomför det riktiga sexstegsprovet i Postiz-jämförelsen när godkänt testmaterial och kontobehörighet finns. Dokumentera om resultat saknas i stället för att godkänna testet med exempeldata.
- [ ] Kör kontrakttest igen och lås godkända versioner. Gör en separat ändring med meddelandet `feat: establish verified Postiz publishing contract`.

Obligatoriskt testkontrakt för normaliseringen `normalize_postiz_state(raw: dict) -> ProviderReceipt`, som T01 implementerar. Fixturernas `state` och `releaseId` mappas efter faktiskt observerat API-kontrakt:

```python
def test_accepted_is_not_published():
    from apps.publishing.postiz import normalize_postiz_state
    receipt = normalize_postiz_state({"id": "p-1", "state": "QUEUE"})
    assert receipt.provider_post_id == "p-1"
    assert receipt.state == "accepted"
    assert receipt.platform_post_id is None
```

Grundbeviset underkänns om nödvändig kontotäckning, återläsning eller native-jobb inte fungerar. Avtals- och tillståndsfrågor som kräver ägarens medverkan får inte ersättas med antaganden.

## T02 – företag och databasgränser

**Filer:** skapa `apps/companies/models.py`, `contracts.py`, `access.py`, `db_context.py`, `migrations/`, `tests/integration/test_company_isolation.py` och `tests/fixtures/company_data.json`.

**In:** Djangos user/session och Postgres från T01. **Ut:** `resolve_context(user, company_id) -> CompanyContext`, transaktionshantering och `ChannelBinding` som kopplar företag till Postiz-ID.

- [ ] Skapa två syntetiska företag med samma faktanyckel men olika värden, egna bilder, egna kanaler och en användare utan behörighet till B. Testa HTTP, tjänstelager, direkt SQL, fil-URL, sökning och bakgrundsjobb.
- [ ] Implementera Company, CompanyMembership och ChannelBinding. Lägg unik constraint på provider + integration-ID så att samma kanal inte kan kopplas till två företag av misstag.
- [ ] Lägg RLS på affärstabeller, `FORCE ROW LEVEL SECURITY`, en app-roll utan `BYPASSRLS` och transaktionslokal kontext. Sätt kontext först efter kontroll av medlemskap. Sessioner/medlemskap läses i separat begränsad auth-väg; ingen global företagskontext på en återanvänd anslutning.
- [ ] Lägg sammansatta nycklar/FK för affärsrelationer med företag. Görs inom respektive modelluppgifts migration när nya tabeller tillkommer.
- [ ] Kör `pytest tests/integration/test_company_isolation.py -q` mot riktig Postgres. Testa saknad kontext och återanvänd anslutning efter rollback. Leverera som `feat: enforce company isolation`.

RLS-mönster för nya företagstabeller; tabellnamn och FK registreras i migrationen för varje modell:

```sql
ALTER TABLE editorial_factversion ENABLE ROW LEVEL SECURITY;
ALTER TABLE editorial_factversion FORCE ROW LEVEL SECURITY;
CREATE POLICY company_scope ON editorial_factversion
USING (company_id = NULLIF(current_setting('app.company_id', true), '')::uuid)
WITH CHECK (company_id = NULLIF(current_setting('app.company_id', true), '')::uuid);
```

Detta skyddar mot glömda filter. Appserverns egen behörighetskontroll behövs fortfarande; en klient får aldrig själv välja den betrodda SQL-kontexten.

## T03 – svensk arbetslista och redigering

**Filer:** skapa `apps/editorial/views.py`, `urls.py`, `forms.py`, `templates/editorial/{overview,review,current}.html`, `templates/registration/login.html`, `tests/e2e/test_editorial_workflow.py`.

**In:** CompanyContext och sessionsinloggning. **Ut:** vyer och endpoints enligt tabellen ovan; testbara postrevisioner. Etapp 1.

- [ ] Skapa en klickbar serverrenderad arbetslista med syntetiska fall: klar, saknar bild, behöver faktakontroll och misslyckad leverans.
- [ ] Implementera företagsswitch, textändring, bildbyte och ”Nej tack”. Godkännande visar konton och tid; endpointen returnerar 422 tills T07/T08:s kontroller är klara.
- [ ] Lägg svenska texter även för login, tomma vyer, formulärfel, e-post och felstatus. Alla knappar har begripliga namn och tangentbordsfokus.
- [ ] Kör webbläsartest och det manuella femminuterstestet. Rätta hinder i arbetsflödet innan fler navigationsdelar läggs till. Leverera som `feat: add Swedish editorial worklist`.

Webbläsarassertions för T03; `page` är pytest-playwrights Page och testet loggar in med en syntetisk seedanvändare innan dessa steg:

```python
from playwright.sync_api import expect

def assert_review_controls(page):
    expect(page.get_by_role("heading", name="Innehållsförslag")).to_be_visible()
    expect(page.get_by_role("button", name="Godkänn", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Byt bild", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Nej tack", exact=True)).to_be_visible()
```

Dessa synlighetskontroller kompletterar, men ersätter inte, verkliga beslutstester i T08 och T12.

## T04 – källor, giltighet och aktuella fakta

**Filer:** skapa `apps/editorial/models/sources.py`, `facts.py`, `services/facts.py`, `services/source_fetch.py`, `tests/integration/test_fact_versions.py`, `tests/unit/test_fact_validity.py`.

**In:** CompanyContext, tillåten URL eller CurrentUpdate. **Ut:** SourceRevision och FactVersion med provenance, giltighet och kontrollstatus. `fact_is_eligible(fact: dict, publish_at: datetime, observed_as_of: datetime) -> bool` är ett rent hjälpfilter; konflikter och tenant kontrolleras av `resolve_facts(ctx, keys, publish_at, observed_as_of)`.

- [ ] Skriv följande testfall: gammalt pris i nyligen importerad post; framtida prisändring; två motstridiga giltiga priser; event som redan slutat; källa som ger 503; mänsklig notis med ”idag”.
- [ ] Implementera oföränderliga käll-/faktaversioner och explicita statusar. Ett misslyckat crawl ändrar aldrig en faktas `verified_at`.
- [ ] Implementera källa-till-påstående-koppling, autoritet per faktanyckel och kritisk mänsklig bekräftelse. Håll tidsstämplar för giltighet och kännedom separata.
- [ ] Kör `pytest tests/unit/test_fact_validity.py tests/integration/test_fact_versions.py -q`. Leverera som `feat: track current facts with verifiable sources`.

```python
from datetime import datetime, timezone

def test_future_fact_is_not_available_in_historical_replay():
    from apps.editorial.services.facts import fact_is_eligible
    at = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)
    fact = {
        "status": "verified", "valid_from": at, "valid_to": None,
        "recorded_at": datetime(2026, 9, 8, tzinfo=timezone.utc),
        "verified_at": datetime(2026, 9, 8, tzinfo=timezone.utc),
    }
    assert fact_is_eligible(fact, publish_at=at, observed_as_of=at) is False
```

Tidsfilter implementeras som bekräftad status + registrerad/kontrollerad senast observationstid + `valid_from <= publish_at < valid_to` när slut finns. Okänd eller utgången status är aldrig publiceringsbar.

## T05 – återanvänd skills och verklig tonalitet

**Filer:** skapa `apps/editorial/prompts/`, `services/context.py`, `services/voice.py`, `models/profiles.py`, `vendor-manifest.json`, `THIRD_PARTY_NOTICES.md`, `evals/voice_cases.jsonl`, `tests/unit/test_context_package.py`.

**In:** granskade skills, företagets textexempel och godkända faktaversioner. **Ut:** `build_context(ctx, allowed_facts, voice_samples, signals) -> dict`, `VoiceProfile` och strukturerade promptmoduler.

- [ ] Välj 8–12 moduler från huvudpaketet; kopiera licens, källrevision och original per vald modul. Ändra globala profilfiler till obligatorisk företagskontext, ta bort modellens verktygs-/publiceringsinstruktioner och dokumentera förändringen.
- [ ] Strukturera paketet i `facts`, `style_examples`, `strategy`, `signals` och `constraints`. Gamla priser i stilexempel får inte hamna i `facts`.
- [ ] Skapa reproducerbar tonalitet från riktiga exempel. Ingen lånad persons historiska performance eller sample-voice får användas som reserv för företagets egen profil.
- [ ] Blindbedöm tonalitet på minst tio texter per företag. Logga direkt godkännande/ändringar och välj modell på redaktionell tid och kvalitet.
- [ ] Kör `pytest tests/unit/test_context_package.py -q` och spara evalresultat utan privat rådata i Git. Leverera som `feat: integrate versioned editorial skills`.

Testets kontrakt: varje faktarad och stilexempel har `company_id`; `build_context` ska avvisa främmande data, inte bara stryka den tyst:

```python
import pytest

def test_context_refuses_foreign_style():
    from uuid import UUID
    from apps.companies.contracts import CompanyContext
    from apps.editorial.services.context import build_context
    ctx = CompanyContext(UUID(int=1), actor_id=1, role="editor")
    with pytest.raises(ValueError, match="company"):
        build_context(ctx, [], [{"company_id": str(UUID(int=2)), "text": "Hej"}], [])
```

## T06 – rättighetsstyrt bildbibliotek

**Filer:** skapa `apps/media/models.py`, `rights.py`, `selection.py`, `uploads.py`, `tests/integration/test_media_access.py`, `tests/unit/test_media_rights.py` och `templates/editorial/images.html`.

**In:** företagsfil + manuella rättigheter. **Ut:** MediaAsset, AssetRights och `eligible_for_social(rights: dict, publish_at: datetime) -> bool`; bildurvalet konsumeras i T07.

- [ ] Testa okänd rättighet, återkallat samtycke, framtida utgång, fel företag, skadlig filtyp och otillåten privat URL.
- [ ] Återanvänd lagrings-/bildbibliotek, kontrollera MIME/innehåll och ta bort känslig EXIF ur publiceringsvarianter. Original hålls privat.
- [ ] Lägg motivannotation som förslag, säsong, alt-text och kvalitetskontroll. Behandla person-/barnmarkering som granskning, inte identifikation eller samtycke.
- [ ] Implementera tre rankade riktiga bildförslag, beskärningspreview och tydligt ”Saknar bild”. Grafiska mallars fakta ritas med vanlig kod.
- [ ] Kör `pytest tests/unit/test_media_rights.py tests/integration/test_media_access.py -q`. Leverera som `feat: select authentic media within verified rights`.

```python
from datetime import datetime, timezone

def test_rights_must_cover_publication_time():
    from apps.media.rights import eligible_for_social
    rights = {"social_allowed": True, "status": "verified", "revoked": False,
              "expires_at": datetime(2026, 9, 8, tzinfo=timezone.utc)}
    assert not eligible_for_social(rights, datetime(2026, 9, 9, tzinfo=timezone.utc))
```

## T07 – idé till granskningsklart inlägg

**Filer:** skapa `models/content.py`, `services/ideas.py`, `services/drafting.py`, `services/validation.py`, `services/repetition.py`, `tests/integration/test_draft_evidence.py`, `evals/gullbringa_pilot.jsonl`.

**In:** fakta från T04, kontext från T05, bilder från T06 och historiska posts. **Ut:** Idea, IdeaEvidence, PostRevision och DraftEvidence. `validate_claims(claims: list[dict], facts: dict) -> list[str]` returnerar stabila blockeringskoder.

- [ ] Testa uppdiktat pris, käll-ID som inte finns, belopp med fel valuta/villkor, ogrundad uppgift i alt-text/overlay och oavsiktlig upprepning.
- [ ] Skapa först idéer med verkliga signaler. Rangordna därefter i kod och generera bara de bästa. Spara rankingkomponenter och exakt underlag till svenska förklaringar.
- [ ] Skriv FB- och IG-versioner med strukturerad claimlista. Separera riktiga fotografier, graphic brief, Reel-manus och färdig video så att ingen ofärdig tillgång visas som publiceringsklar.
- [ ] Begränsa rättningsförsök till två; ett fortsatt faktaproblem går till mänsklig kontroll. Generera inte en obegränsad loop.
- [ ] Bedöm 30 idéer och 12 utkast från Gullbringas verkliga underlag. Gå vidare först när pilotkriterierna i huvudplanen klaras. Leverera som `feat: generate evidenced company content proposals`.

```python
def test_old_price_cannot_be_claimed_against_new_fact():
    from apps.editorial.services.validation import validate_claims
    facts = {"price-v2": {"value": "695", "currency": "SEK", "status": "verified"}}
    claims = [{"fact_id": "price-v2", "value": "495", "currency": "SEK"}]
    assert "FACT_VALUE_MISMATCH" in validate_claims(claims, facts)
```

Det här numeriska testet är nödvändigt men inte tillräckligt. Semantisk genomgång av hela utkastet och referenser för alla publicerbara påståenden ingår.

## T08 – revisionsbundet godkännande och leverans

**Filer:** skapa `services/approvals.py`, `apps/publishing/models.py`, `dispatch.py`, `reconcile.py`, `tasks.py`, `tests/integration/test_approval_dispatch.py`, `tests/contracts/test_ambiguous_postiz_write.py`.

**In:** godkänd PostRevision och CompanyContext. **Ut:** ApprovalSnapshot och Publication; `approval_hash(payload: dict) -> str`, `dispatch_publication(publication_id: str) -> ProviderReceipt`. Payload omfattar företag, kanaler, text, filhashar/ordning, fakta-/rättighetsversioner och tid.

- [ ] Testa text-/bildbyte efter godkännande, ändrade fakta, återkallad rättighet, ändrad kanal/tid, samtidiga klick och två arbetare.
- [ ] Beräkna hash från kanoniskt serialiserat innehåll. Lås Publication och godkänd revision transaktionellt, gör slutkontroll och spara försöksidentitet före extern effekt.
- [ ] Håll planerade tider lokalt tills kontrollerna är klara. Skicka via Postiz och spara kvittens; `accepted` får inte mappas till ”Publicerat”.
- [ ] Vid timeout efter skickat POST: spara `unknown`, stäm av och blockera blinda retry. Företaget får ett svenskt åtgärdsmeddelande vid olöst utfall. Separera kanaler så att ett lyckat FB-inlägg inte skickas igen när IG fallerar.
- [ ] Kör `pytest tests/integration/test_approval_dispatch.py tests/contracts/test_ambiguous_postiz_write.py -q`. Prova stopp före och efter överlämning live. Leverera som `feat: enforce revision approval before Postiz delivery`.

```python
def test_approval_changes_when_target_account_changes():
    from apps.editorial.services.approvals import approval_hash
    approved = {"company_id": "c1", "revision_id": "r1", "integration_id": "ig-a",
                "caption": "Välkommen", "media": ["sha256:abc"],
                "facts": ["f1"], "rights": ["right-v1"], "at": "2026-09-08T10:00:00Z"}
    changed = dict(approved, integration_id="ig-b")
    assert approval_hash(approved) != approval_hash(changed)
```

Detta hashprov kompletteras med ett integrationstest där nätverksadaptern aldrig anropas när lagrad godkännandehash avviker. Att bara jämföra hashvärden bevisar inte att publiceringsspärren används.

## T09 – konkurrentbevakning och användbara avvikelser

**Filer:** skapa `apps/competitors/{models,imports,normalize,scoring,tasks}.py`, `tests/unit/test_competitor_baseline.py`, `tests/contracts/test_competitor_import.py`, `docs/research/competitor-access.md`.

**In:** dokumenterad tillåten källa med faktiska fält. **Ut:** CompetitorObservation och företagsspecifika signaler; `relative_lift(value: float | None, baseline: list[float]) -> float | None` samt `comparable(a: dict, b: dict) -> bool`.

- [ ] Prova tre relevanta konkurrenter. Registrera saknade data och tillåtna användningar. Utan tillåten automatisk källa byggs importvägen med explicit status om begränsad bevakning.
- [ ] Granska utvalda MIT-delar i Prodkit före kopiering. Bevara notices. Ersätt saknade-värden-till-noll och följarkvot som enda framgångsmått.
- [ ] Implementera jämförelse inom samma konto, format, definition och postålder. Minst 20 observationer krävs för normal relativ signal; mindre underlag ger `None`/svag signal.
- [ ] Skapa möjliga mönster med egna exempel, inte kopierade captions. Anonymisera relevanta frågor från kommentarer och koppla varje använd signal till en IdeaEvidence.
- [ ] Kör `pytest tests/unit/test_competitor_baseline.py tests/contracts/test_competitor_import.py -q`. Leverera som `feat: turn permitted competitor observations into ideas`.

```python
def test_missing_and_zero_baseline_do_not_create_fake_winners():
    from apps.competitors.scoring import relative_lift
    assert relative_lift(None, [100.0] * 20) is None
    assert relative_lift(370, [0.0] * 20) is None
    assert relative_lift(370, [100.0] * 20) == 3.7
    assert relative_lift(370, [100.0] * 3) is None
```

## T10 – tidsmässigt korrekta egna resultat

**Filer:** skapa `apps/results/{models,postiz_metrics,comparability,tasks}.py`, `tests/integration/test_metric_observations.py`, `tests/unit/test_metric_comparability.py`.

**In:** publicerade Postiz-/plattform-ID:n och resultat-API. **Ut:** MetricObservation med värde eller null, definition, faktisk hämtningstid, postålder och källperiod. `same_cohort(a: dict, b: dict) -> bool`.

- [ ] Hämta riktiga svar för FB-bild, IG-bild och därefter Reel. Dokumentera måttens definition och vilka historiska posts som alls går att återläsa genom Postiz.
- [ ] Spara append-only 24h/72h/7d-observationer med toleransfönster och faktiska tider. Missade mätningar är missade; backfilla inte en yngre postålder med ett senare värde.
- [ ] Separera egna imports historiska totalsummor från nya observationer. Befintliga äldre Meta-posts kan behöva export eller ett begränsat läs-API; Postiz åtkomst till dem antas inte.
- [ ] Testa mätdefinitionsbyte, dolda värden, API-fel och dubbel hämtning med samma observations-ID.
- [ ] Kör `pytest tests/integration/test_metric_observations.py tests/unit/test_metric_comparability.py -q`. Leverera som `feat: preserve comparable post performance observations`.

```python
def test_seven_day_views_are_not_compared_with_day_one_views():
    from apps.results.comparability import same_cohort
    a = {"company_id": "a", "channel": "instagram", "format": "reel",
         "metric_definition": "views-v1", "age_bucket": "24h", "paid": False}
    b = dict(a, age_bucket="7d")
    assert same_cohort(a, b) is False
```

## T11 – feedback som ändrar framtida urval

**Filer:** skapa `apps/editorial/models/feedback.py`, `services/feedback.py`, `apps/results/learning.py`, `templates/editorial/results.html`, `tests/integration/test_learning_effect.py`, `evals/replay.py`.

**In:** mänskliga beslut, tidslogg, textdiffar och jämförbara MetricObservation. **Ut:** versionerad LearningRule och korta resultatkort. `select_eligible_rules(rules: list[dict], decision_at: datetime) -> list[dict]`.

- [ ] Registrera skäl till avslag och faktisk ändringstid. Se till att avslag på timing inte automatiskt förbjuder ämnet.
- [ ] Skriv integrationstest som visar att en tillåten ny lärdom förändrar prioriteringen för nästa jämförbara idé, medan samma regel inte kan påverka ett annat företag.
- [ ] Skriv tidsordnad replay där framtida mätpunkter och sent tillagda faktauppgifter inte finns i beslutsunderlaget.
- [ ] Visa högst tre positiva mönster, två svagare och ett experiment. Allt visar baslinje, antal och osäkerhet; ingen automatisk kausal slutsats.
- [ ] Kör `pytest tests/integration/test_learning_effect.py -q` och blindbedöm nya förslag. Leverera som `feat: apply traceable editorial learning`.

```python
from datetime import datetime, timezone

def test_learning_cannot_use_future_measurements():
    from apps.results.learning import select_eligible_rules
    future = {"id": "rule1", "observed_at": datetime(2026, 10, 1, tzinfo=timezone.utc)}
    assert select_eligible_rules([future], datetime(2026, 9, 7, tzinfo=timezone.utc)) == []
```

## T12 – pilot, driftsättning och överlämning

**Filer:** skapa `tests/e2e/test_three_company_week.py`, `scripts/restore-check.ps1`, `scripts/restore-check.sh`, `docs/runbooks/{weekly-use,incidents,restore,updates}.md`, `docs/reports/pilot-acceptance.md`, `render.yaml` och CI-konfiguration.

**In:** fungerande T01–T11, kontoägarnas godkända material och namngivna tre företag. **Ut:** accepterad pilot och dokumenterad driftsatt revision. Inga mallresultat får räknas som uppmätta.

- [ ] Kör en hel syntetisk vecka för tre företag med rättningar, avslag, bildbyte, paus och kanalseparata leveransfel. Kontrollera SQL, jobb och UI tillsammans.
- [ ] Genomför de riktiga kvalitetsmåtten i huvudplanen under fyra pilotveckor per företag. Logga även rättningar och driftundantag i den manuella veckotiden.
- [ ] Återställ databas, objekt och godkännanden till isolerad miljö. Stoppa dispatch tills varje redan överlämnad publicering stämts av mot Postiz; återspelning av gamla jobb får inte skapa nya posts.
- [ ] Prova native deployment och rollback, stannad worker, felaktig API-nyckel, utgången anslutning och kostnadstak. Larm ska peka på rätt företag och nästa handling.
- [ ] Kör lämpliga befintliga tester, `python manage.py check --deploy`, migrationskontroll, relevant dependency-/secretskontroll och webbläsarprov. Dokumentera vad som är lokalt, staging och live.
- [ ] Leverera kort svensk användarguide och separat driftguide. Godkänn V1 först när noll publicerade faktiska sakfel, företagsskydd och användbarhetskrav är uppfyllda. Registrera mätosäkerhet och återstående begränsade format tydligt.

Återställningsprovets minsta maskinläsbara rapport:

```json
{
  "environment": "isolated-restore",
  "dispatch_enabled": false,
  "company_count_matches": true,
  "asset_checksums_match": true,
  "approval_snapshots_match": true,
  "external_publications_reconciled": true,
  "duplicate_dispatch_attempts": 0
}
```

Värdena ovan är kontraktet för ett godkänt test, inte ett redan uppmätt resultat. Om någon kontroll är falsk lämnas dispatch avstängd och återställningsrutinen rättas.

## Kontroll av planens fullständighet

- [ ] Varje originalkrav har en koppling i huvudplanens kravmatris.
- [ ] Postiz-dokumentationen skiljs från verifierade svar för de verkliga kontona.
- [ ] Inga privata nycklar eller verkliga personers rådata finns i källkod/testfixturer.
- [ ] Ingen del förutsätter ett nytt godkännandeflöde i Postiz som dess API inte visar stöd för.
- [ ] Ingen UI-status påstår publicerat, kontrollerat eller återkallat utan motsvarande bevis.
- [ ] Reservvägen Brightbean kräver ett nytt grundbevis; dess kod blandas inte in tyst.

Gör varje T-uppgift som en separat granskningsbar leverans med relevanta tester och dokumentation. Om en uppgift är för stor delas den efter verifierbar funktion, utan att ändra de gemensamma kontrakten. Externa inköp, kontoanslutningar och testpubliceringar ingår i senare implementation med konkret användarbehörighet; denna leverans är planen.
