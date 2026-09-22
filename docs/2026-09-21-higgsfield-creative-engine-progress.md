# CURRENT STATE

> **2026-09-22 audit verdict: not fully production-ready.** Fixes and HOW TO are live at `6e644fc`. Current full local suite: 206 tests green (2 PostgreSQL-only skips); previous full Linux/PostgreSQL CI green at `a81f5b2`. Latest CI cannot start due GitHub billing/spending restrictions. Live Higgsfield preflight fails HTTP 401, so model access and price remain unverified. Render Free sleeps. See Task 9 and `docs/2026-09-22-creative-audit.md` for evidence and exact follow-ups. ZERO paid generation.

- Latest completed step: exact Creative Engine product tree transferred and verified in GitHub CI; 173/173 SQLite and 173/173 PostgreSQL tests pass.
- Branch: `feature/chatgpt-content-engine-mcp`.
- Latest shipped product commit: `67c6751179d96c4b910f022ccfce817d46d0633f` (`feat(creative): complete shared Higgsfield Creative Engine`).
- Transfer cleanup commit: `ac727ab8594e7546d8f7eb090bfdca7b5bc8c2f4` (temporary verification workflow removed).
- Baseline commit: `1b6ae03a342a95c0e43690625bfeab2cce72e040`.
- Main reference: `d88524467ef216cf521d2e8fcf9bd54741eb3dc7`.
- Deploy: LIVE on Render service `content-engine-mcp` in confirmed workspace `My Workspace` (`tea-d06041ali9vc73bqfn80`), deploy `dep-daoqaldg1s2s73889n4g`, branch `feature/chatgpt-content-engine-mcp`, deployed head `dbba2e54fe2cae44a698955ceae4cfbc6d40e902`.
- Production startup: Neon migration `engine.0013_prompt_library` applied successfully; MCP StreamableHTTP session manager and Uvicorn started; Render marked service live at `https://content-engine-mcp.onrender.com`.
- Verification: GitHub Actions run `35658336105` verified exact payload SHA-256, all 25 product blob hashes, migrations/check/static/MCP startup, 173 SQLite tests and 173 PostgreSQL tests. Production live checks additionally verified health 200, login/root 200 after redirect, OAuth status/discovery 200, protected-resource metadata 200 and unauthenticated MCP 401 with Bearer challenge. No Render error/critical logs were present after deploy.
- Remaining external verification: the Render connector cannot reveal secret environment values, so Golfkupongers server-side Higgsfield credential/account availability is not claimed as verified. Do not substitute Jonas personal Higgsfield workspace. Account-scoped estimate/preflight must pass through the deployed server before any paid generation.
- Next exact task: perform the server-side non-billable Higgsfield account estimate/preflight through an authenticated Content Engine call when available, then present the exact priced paid smoke-test proposal and stop for explicit approval.
- Paid generations: ZERO; explicit approval is required before any real paid smoke test.

## Binding brief

The user supplied the full implementation brief in `Inklistrad text(7).txt` on 2026-09-21. Its requirements supersede the earlier plan when they differ. Work continues inline in this session; no approval pauses for routine technical decisions. Existing Render service, Neon, R2, company/user boundaries, OAuth, MCP and generation history must be preserved. No personal Higgsfield credential fallback and no automatic retry of possibly billable submissions.

## Master checklist

- [x] Repository and branch topology verified
- [x] Full relevant repository audit and baseline tests
- [x] Official API/SDK and model-contract audit
- [x] Updated implementation plan and architecture rulings
- [x] Structured creative brief and context boundary
- [x] Versioned model intelligence, router, prompt/parameter compiler, preflight
- [x] Prompt Library persistence, retrieval and UI
- [x] Official SDK/REST adapter decision and fail-closed cost policy
- [x] Durable duplicate-safe lifecycle, webhook, polling/recovery and R2 completion
- [x] Shared UI and MCP integration, ownership tests
- [x] UX and diagnostics review
- [x] Full test suite, migrations, security checks and extra review
- [ ] Existing Render deployment and live non-billable verification
- [ ] Final handoff and explicitly priced paid-test proposal (not execution)

## Architecture rulings

1. Ruling: retain the existing feature branch and existing MCP/OAuth implementation, rather than implementing the plan's new MCP server/service identity. The plan is on `main`, not the feature branch; it describes an older state. `main` is two commits ahead and 94 behind the feature branch; its two added changes are plan documentation and README only. A blind branch replacement would discard existing functionality.
2. Ruling: use the supplied latest brief as the binding spec and challenge the older plan against code and official documentation. Do not merge unrelated work or rewrite the application.
3. Ruling: never interpret an UNKNOWN paid submission as permission to submit again. Without provider-side idempotency, describe the guarantee accurately as at-most-once local submission plus reconciliation, not universal exactly-once delivery.

## Task 1a: Repository topology

### Status
DONE (read-only repository verification only).

### Files changed
`docs/2026-09-21-higgsfield-creative-engine-progress.md`.

### What changed / why
Created this canonical handoff ledger immediately. Located the original plan on `main`; confirmed the actual implementation branch exists and contains the existing MCP CI workflow.

### Verification / tests
GitHub `get_repo`, `fetch` branches and recursive tree, `fetch_file` on both branches, and `compare_commits(feature/chatgpt-content-engine-mcp, main)`. Local `python --version` and module availability inspection. No product tests have run yet.

### Result / external verification
Repository reads VERIFIED. Application behavior NOT verified. Render NOT verified. No paid calls.

### Known issues
Full source and dependency setup pending. Render workspace confirmation pending.

### Next exact task
Set up the complete isolated local source/test workspace and read `engine/media.py`, `engine/media_providers.py`, models, storage, operator/MCP/auth, templates, tests and deployment scripts.

### Commit
This ledger's creation commit is available from Git history; subsequent task entries will record verified commit SHAs.


## Task 1b: Isolated source and baseline verification

### Status
DONE.

### Files changed
Temporary `.github/workflows/creative-workspace.yml` (removed after successful transfer); this ledger.

### What changed / why
Transferred tracked source and public dependency wheels through one-day private GitHub artifacts because the local container cannot resolve external hosts. No `.git` credentials or production `.env`/data included. The initial YAML scalar containing `:all:` failed parsing; a literal block fixes the evidenced syntax error. No application code was changed by this infrastructure task.

### Verification / tests
- Local PyYAML minimal reproduction: invalid scalar fails; literal block parses.
- Source export run `35618113884`: success on `dce11df7aa2b51f2235a071819706cea2d67b2c2`.
- Existing MCP CI run `35618113976`: success (includes PostgreSQL job).
- Isolated `python manage.py test`: 119 passed in 7.971 seconds; no system-check issues.
- Read existing media/provider/storage models and lifecycle, operator/MCP/auth boundary, UI templates, existing tests, settings and deployment scripts. Read original plan from main.

### Result / external verification
Local unit/integration baseline verified. GitHub CI verified. No provider/live-generation or Render verification.

### Known issues
Render selection remains blocked pending the explicit workspace confirmation requested in chat.

### Next exact task
Prompt Library schema and service.

### Commit
Infrastructure commits `661f9a5791fec65657e9541e779cf625d6fb47f8`, `87f8c27af885870354a365f5876744eb066b5c4d`, YAML fix `dce11df7aa2b51f2235a071819706cea2d67b2c2`.

## Task 2a: Additive Prompt Library schema

### Status
DONE for schema only; library feature remains PARTIAL until service/UI are tested.

### Files changed
`engine/creative_models.py`, `engine/models.py`, `engine/migrations/0013_prompt_library.py`, `engine/test_creative_library.py`, this ledger.

### What changed / why
PromptEntry is company/author scoped, stores exact immutable-original fields separately from editable text, retains generation provenance, favorites and soft archive. PromptTerm has a dedicated indexed lookup to avoid loading the whole library. All media/generation records remain in the existing tables. Migration is additive.

### Verification / tests
- RED: `python manage.py test engine.test_creative_library` fails because PromptEntry does not exist.
- GREEN: same command, 1 passed.
- Regression: `python manage.py test`, 120 passed in 8.006 seconds; no system-check issues.
- `python manage.py makemigrations engine --name prompt_library`: generated additive migration 0013.

### Result / external verification
Schema/unit/mock database verified locally, not yet deployed. No paid calls.

### Known issues
Save/search/UI to follow; original immutability must also be enforced in service tests, not merely by an editable=False form flag.

### Next exact task
Add service and UI tests for exact preservation, company isolation, duplicate save, search/ranking and archive.

### Commit
The schema commit is identified in Git history; next entry records its SHA.

## Verified API findings / plan amendments

- Official Python SDK main audited at `aefd1ca677929762b9f69a7a7ea530a4a695d6a8`: `SyncClient._transport` installs a method-agnostic retry strategy, including generation POST responses 408/429/5xx. Its public constructor has no retry-disable option. Do not use that default for billable submits; do not monkey-patch private internals. Retain a thin official-REST adapter until a public zero-retry SDK contract is available and tested. This deliberately changes the old plan's unconditional SDK dependency.
- Official errors docs explicitly state generation POSTs have no idempotency key. UNKNOWN blocks any automatic resubmission.
- Official webhooks have no documented signature. Treat callback bodies as untrusted wake-up hints only and fetch authoritative results with authenticated GET; never trust callback ownership/URLs/status alone.
- Current console model API schemas, not the supplementary OpenAPI, are the model contract source. Docs-verified capability is distinct from account availability; account-scoped estimate must succeed before payment.
- Existing browser readiness checks only the generic split credentials, ignoring the primary GK credential. Fix when integrating the new studio.
- Existing generic video prompt forbids preserving logos, contradicting requested image-to-video preservation. Keep legacy jobs readable; new compiler gets explicit preserve/allow/forbid semantics.
- Existing provider results require an open browser to advance. Add durable recovery tied to the existing service; never start paid work from a webhook.

Official references checked 2026-09-21:
https://docs.higgsfield.ai/docs/concepts/errors
https://docs.higgsfield.ai/docs/how-to/webhooks
https://docs.higgsfield.ai/docs/concepts/billing-and-retention
https://docs.higgsfield.ai/docs/concepts/file-uploads
https://github.com/higgsfield-ai/higgsfield-client/tree/aefd1ca677929762b9f69a7a7ea530a4a695d6a8

## Transfer verification ruling

A full-file connector transfer accidentally omitted `OwnOutcome.recorded_at(auto_now_add=True)`. Blob-hash verification caught it before any branch was advanced; the defective unattached commit was not shipped. To avoid reserializing unchanged legacy files, temporary `creative-prepare.yml` now applies only an exact manifest-checked patch, runs migrations/MCP startup/full SQLite and PostgreSQL tests, and creates a Git commit object without updating any branch. The authenticated GitHub connector alone advances the existing feature branch after verification. No production secrets/data are used, and the temporary workflow will be removed at handoff. Local source remains the tested authoritative bytes.

## Task 2b: Prompt Library service and original protection

### Status
DONE for service; UI and generation-engine integration remain separate tasks.

### Files changed
`engine/prompt_library.py`, `engine/creative_models.py`, `engine/test_creative_library.py`, temporary `creative-prepare.yml`, this ledger.

### What changed / why
Exact text preservation, SHA-256 per-company duplicate protection, original/company immutability enforced on model save and QuerySet update, independent editable copy, favorites, tags, archive/restore, generation provenance with explicit safe parameter allowlist. Added indexed multilingual concept and word retrieval, capped at five short inspiration examples and two database queries, with explicit HEURISTIC/untrusted labeling. No embeddings or paid analysis are claimed. Bulk input splits only on an explicit delimiter and requires a UI preview to follow. Temporary CI now ignores removal commits and uses the correct PostgreSQL healthcheck user.

### Verification / tests
- RED service suite: 15 failing tests because the service did not exist.
- GREEN initial service suite: 16 passed.
- Extra original-bulk-update and bounded-query tests added.
- `python manage.py test`: 137 passed in 8.147 seconds, system checks clean.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- Schema preparation run `35620499883`: 120 tests passed on SQLite and 120 on PostgreSQL; exact hash manifest matched. Prepared/advanced commit `15c76aef9a084eb9e1cf97eccd880172a5815802`; no Render deployment performed.

### External verification / known issues
Service locally verified; no production credentials or paid requests. UI not built yet. Render workspace confirmation remains outstanding. Handwritten semantic concept mapping is not an embedding system and cannot promise arbitrary paraphrase matching.

### Next exact task
Implement the usable Prompt Library page and security/form tests.

### Commit
Schema: `15c76aef9a084eb9e1cf97eccd880172a5815802`. Service is staged for the next logical library commit.


## Task 2c: Prompt Library UI and generation provenance

### Status
DONE for library UI and service integration. Use-in-Creative-Studio integration follows the studio task.

### Files changed
`engine/prompt_views.py`, `engine/test_prompt_ui.py`, `engine/urls.py`, `engine/static/css/creative-screen.css`, `engine/static/js/prompt-library.js`, `templates/engine/prompt_library.html`, `prompt_detail.html`, `prompt_bulk.html`, `prompt_extra_fields.html`, `library_tabs.html`, existing `media_library.html`, `media_job.html`, `templates/base.html`, `templates/components/navigation_links.html`, this ledger.

### What changed / why
Paste-save redirects to a fresh input without requiring metadata. A separate, signed 10-minute bulk preview is bound to authenticated user and company before atomic confirmation. Original and editable text are displayed separately. Search, kinds, labels, favorites, copying, removal and save-from-generation use the shared scoped service. Media has library subtabs rather than overcrowding the existing mobile navigation. All mutations use POST and CSRF; external prompt text is escaped and never treated as instructions.

### Verification / tests
- RED: `python manage.py test engine.test_prompt_ui`: 11 failures because the route did not exist.
- First GREEN attempt exposed an unbound-form error on an invalid signed token; fixed by validating a bound empty form. A text assertion incorrectly matched the page's explanatory copy; corrected to assert the actual empty result collection.
- `python manage.py test`: 148 passed in 8.361 seconds; system checks clean.
- `python manage.py makemigrations --check --dry-run`: no changes.
- Chromium offline render of real authenticated Django HTML and application CSS at 1440x1000 and 390x844: no horizontal overflow, primary save button visible, no page errors. Screenshots visually reviewed; improved the subtab contrast. Browser network policy blocks loopback navigation, so this is explicitly offline layout verification, not a browser/server end-to-end test. Django client tests do exercise the real authenticated views and database.

### Result / external verification
Local unit, integration, route/form/CSRF tests and offline visual checks pass. Library not yet deployed to Render. No paid model calls.

### Known issues
The Creative Studio use action will be added after its route exists; copy works now. Render workspace selection remains unconfirmed.

### Next exact task
Build and test typed brief, bounded company context, model registry, model-specific prompt/parameter compiler and preflight; then add the shared durable generation service.

### Commit
Previous shipped schema: `15c76aef9a084eb9e1cf97eccd880172a5815802`. Verified transfer configuration: `cb8286d26f8048e5eced04cd4e70cedca5525398`. Current library commit will be recorded after CI preparation and connector branch advancement.

### Transfer verification update
Temporary CI now also accepts size-bounded zlib/base64 transport of the native Git diff while still verifying every exact decoded file hash. This avoids manual reserialization of long source files over the connector. It preserves tracked executable modes, skips payload-deletion commits, and uses the explicit PostgreSQL test user in its health check. YAML and embedded Python were parsed/compiled locally; remove this temporary workflow after final handoff.


## Task 3: Shared Creative Director, registry, compiler and MediaGeneration integration

### Status
DONE for the provider-neutral planning layer and existing media-job integration. Live account availability remains a provider preflight concern; no paid request was made.

### Files changed
`engine/creative_core.py`, `engine/creative_registry.py`, `engine/creative_director.py`, `engine/test_creative_core.py`, `engine/media.py`, `engine/media_providers.py`, `engine/test_media.py`, `engine/prompt_library.py`, this ledger.

### What changed
- Added a strict Pydantic `CreativeBrief` plus bounded `CreativeContext`, model selection, preflight issue and plan objects.
- Added a versioned allow-listed registry. Only OFFICIAL/VERIFIED entries can be auto-selected; undocumented future models cannot enter routing. Current still-image routing is `gpt-image-2`; current video routing remains the existing verified `kling-video/v2.5-turbo/pro`.
- Added deterministic local intent parsing, complexity scoring, hard-capability routing, joint prompt/parameter compilation and preflight. An 8-second request is normalized locally to a verified 10-second Kling duration before any provider call.
- Added first-class image-to-video preserve/allow/forbid compilation. The legacy blanket logo-preservation ban is no longer applied to I2V, while generated still images retain the existing invariant that logos/wordmarks are never synthesized and the exact official logo is composited separately.
- Bounded company/run context is compiled as reference data only. Prompt Library retrieval is company-scoped and capped; only abstract mechanism metadata is compiled, never the raw untrusted saved prompt.
- Existing `MediaGeneration` remains the single job record. It now stores original request in `brief`, compiled provider prompt in `prompt`, and safe versioned diagnostics/provenance under `parameters.creative`. No parallel job database was added.
- Provider video payload now uses the already validated/compiled local duration instead of silently hard-coding 10 seconds.
- Fixed Prompt Library generation provenance to read the persisted structured brief from `parameters.creative`.

### Why
This keeps UI/MCP/future automations on one shared domain layer and makes model-specific prompt behavior explicit without adding an LLM call or a new paid step before cost preflight. The registry is deliberately small rather than guessing current provider capabilities.

### Verification
- RED/GREEN focused Creative Core suite: 10/10 passed.
- Creative Core + media integration: 23/23 passed.
- A full-suite regression exposed the existing still-image logo safety invariant; compiler was corrected and the targeted branding/core/media suite passed 27/27.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `python manage.py check`: clean.
- Final local SQLite suite: 160 tests passed in 8.574s.
- No external generation, estimate or billable POST was executed.

### External verification
- OpenAI official model catalog checked 2026-09-21 and confirms GPT-Image-2 as the current image-generation model.
- Higgsfield shared docs and prior same-day official API/SDK audit remain the source for async lifecycle/cost/idempotency rulings. Account availability is intentionally not inferred from docs; estimate/preflight must confirm it before payment.
- Unit/integration verified locally; PostgreSQL CI and Render are not yet verified for this task.

### Known issues
Render still requires explicit workspace selection. The authenticated Higgsfield MCP workspace read returned a temporary workspace error and is not used as Content Engine account availability evidence. No personal Higgsfield workspace fallback is allowed.

### Next exact task
Harden the official REST adapter and durable lifecycle: normalized errors, safe read retries only, webhook wake-up endpoint, bounded polling/recovery, completion-to-R2 idempotency and recovery tests.

### Commit
Local logical commit follows after this ledger update; GitHub branch advancement will occur only after exact patch transfer and CI verification.


## Task 4: Higgsfield lifecycle, webhook, recovery and provider safety

### Status
DONE in code/tests; production webhook delivery and real R2/provider behavior remain deployment/live-read verification tasks. No paid generation was executed.

### Files changed
`engine/media_providers.py`, `engine/media.py`, `engine/media_views.py`, `engine/urls.py`, `engine/settings.py`, `engine/management/commands/recover_media_jobs.py`, `engine/test_media.py`, `.env.example`, `render.yaml`, this ledger.

### What changed
- Added a normalized provider error taxonomy for invalid request, authentication/config, insufficient credits, rate limiting, provider unavailable and uncertain paid submission.
- Higgsfield GET status requests now use bounded retries with exponential backoff, jitter and `Retry-After` handling. Generation submit is explicitly marked `billable=True` and is attempted exactly once. Non-billable estimate/upload failures are no longer incorrectly classified as ambiguous paid submits.
- Implemented the documented `hf_webhook` query parameter behind `HIGGSFIELD_WEBHOOK_ENABLED`. Production Render blueprint enables it; localhost does not generate an HTTPS webhook URL.
- Added public POST-only `/webhooks/higgsfield/`. It validates the documented envelope, stores only safe receipt metadata, ignores webhook result URLs/errors, matches a known provider request id, then fetches authoritative status via authenticated GET. Unknown valid ids are acknowledged without leaking ownership. Duplicate terminal deliveries return 2xx.
- Added explicit `saving` state. A completed provider job is transactionally claimed before download/storage, preventing duplicate completion workers. If result download/R2 fails, no provider generation is repeated; stale recovery retries only result retrieval/storage.
- Internal terminal states now preserve `failed`, `nsfw` and `canceled` separately. `unknown` remains the fail-closed state for a potentially charged submit whose request id was not safely persisted.
- Added bounded `recover_media_jobs` plus management command. It checks already-started/stale jobs only and never starts queued paid work.
- Added cancellation: local queued jobs cancel without provider contact; known running Higgsfield jobs use the documented `/requests/{request_id}/cancel` endpoint. Ambiguous states are not canceled blindly.
- Updated browser provider readiness to prefer `HIGGSFIELD_API_KEY_GK`; retained legacy server fallback. Render declares the primary GK key plus legacy variables for a safe migration.

### Why
Current official Higgsfield docs explicitly permit retrying status GETs after network/5xx failures but warn that generation POSTs have no idempotency key and must not be automatically repeated after an ambiguous timeout. Webhooks can be duplicated and currently have no documented signature, so the request body is a wake-up hint rather than authoritative ownership/result data.

### Verification
- Focused media/provider/webhook suite: 20/20 passed.
- Webhook tests prove an attacker-supplied payload URL is ignored; authenticated status URL is used instead.
- Duplicate webhook test leaves exactly one persisted asset.
- Recovery test forces result download failure, leaves durable `saving`, ages it, then completes through recovery without a generation submit.
- Retry test proves transient GET executes bounded retries while ambiguous billable POST executes once.
- Webhook URL test verifies percent-encoded `hf_webhook` is added only with feature flag + HTTPS APP_URL.
- `python manage.py test`: 167 passed in 8.623s.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `python manage.py check`: clean.

### External verification
Docs verified 2026-09-21 against official Higgsfield pages for webhook delivery, polling/backoff, retry safety, billing/retention and queued cancellation. Live webhook delivery, provider account availability and real R2 write remain unverified until deployment; no billable smoke test was run.

### Known issues
Render workspace selection is still an external connector blocker. The service currently cannot be deployed/inspected through the connector until Jonas explicitly selects the Render workspace required by the connector contract.

### Next exact task
Add thin MCP generation diagnostics/list/cancel interfaces around the same domain services, then simplify the existing AI-studio/status screens and expose safe diagnostics without provider internals in the default UX.

### Commit
Local logical commit follows; GitHub branch will advance only after exact transfer and PostgreSQL CI verification.


## Task 5: Thin MCP surface and human-first Creative Studio UX

### Status
DONE in code/tests. Browser screenshot rendering is NOT claimed as verified because the execution environment's Chromium policy blocks loopback, file and data-URL navigation; authenticated Django views and responsive DOM/CSS behavior remain covered by integration/static review instead.

### Files changed
`engine/mcp_operations.py`, `engine/mcp_server.py`, `engine/operator_media.py`, `engine/media.py`, `engine/media_views.py`, `engine/urls.py`, `templates/engine/media.html`, `templates/engine/media_job.html`, `engine/static/css/media-screen.css`, `engine/test_media.py`, `engine/test_mcp_media.py`, `README.md`, `docs/chatgpt-business-mcp.md`, `docs/2026-09-08-media.md`, this ledger.

### What changed
- Kept MCP thin: `generate_media` still calls the shared operator/domain layer and now accepts only the natural `quality` / `balanced` / `economy` priority. Added company/run-scoped read/list/cancel generation tools around the same `MediaGeneration` rows; no provider-specific MCP server or duplicate routing logic was created.
- Added safe generation serialization with human status, persisted original request, selected model/reason, compiler/registry versions, bounded structured brief, safe parameters, estimate and provider request id. Secrets and `logo_sha256` stay out of MCP diagnostics.
- Added explicit company-bounded recent-generation queries and idempotent domain cancellation. Existing `_run` / company resolution remains the ownership boundary for MCP tool calls.
- Simplified the web AI Studio around natural-language intent, three understandable priorities and format instead of raw model/provider controls. Model, duration and provider details live in collapsed diagnostics.
- Rebuilt the status page around understandable lifecycle steps, bounded polling backoff, clear `unknown` fail-closed recovery, cancel controls and prompt-library handoff. Status polling explicitly reuses the same job and never creates replacement paid work.
- Updated current README/MCP docs and marked the 2026-09-08 media verification as historical where newer lifecycle/credential behavior supersedes it.

### Why
The binding brief requires one shared engine with a low-friction default UX and technical details available only when useful. Keeping all generation logic in Django domain services also preserves restart recovery, company ownership, cost policy and duplicate protection for UI, MCP and future automation callers.

### Verification
- New MCP operation tests: safe diagnostics, company-scoped history, idempotent cancel.
- New UI/security tests: priority/format controls, escaped user prompt in diagnostics, persisted priority, invalid priority rejected before job creation, POST-only company-scoped cancel route.
- Focused `engine.test_media engine.test_mcp_media operator_bridge.tests`: 35/35 passed.
- Full `python manage.py test`: 173/173 passed in 8.742s.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `python manage.py check`: clean.
- `python manage.py collectstatic --noinput`: success.
- MCP app import under `engine.mcp_settings`: success.
- `python -m compileall -q engine operator_bridge`: success.
- Responsive CSS has explicit one-column breakpoints for the new priority controls and existing media grids. Chromium screenshot attempts were blocked by environment browser policy before app content loaded, so no screenshot is marked verified.

### External verification
No external generation, provider write or paid request. Render not yet touched. PostgreSQL CI for this combined patch remains the next verification gate.

### Known issues
Render connector still requires explicit user confirmation of its workspace before any service read/write. A real Higgsfield paid generation remains forbidden until Jonas explicitly approves the final priced smoke test.

### Next exact task
Perform the extra security/consistency review, remove temporary interrupted-transfer artifacts, generate an exact hash-manifested Git patch, run existing GitHub SQLite/PostgreSQL verification and advance the feature branch only if that CI is green.

### Commit
Local logical product commit: `237e5be550187f88d6da464611caf58f320426f6` (`feat(creative): expose shared engine through MCP and UI`). GitHub branch advancement is intentionally deferred to exact-transfer/PostgreSQL CI.


## Task 6: Final local regression, security and consistency review

### Status
DONE locally. PostgreSQL CI and production deployment are separate verification stages.

### Files changed
This ledger only; review covered the complete current Creative Engine/MCP/media diff.

### What changed / why
No new product behavior was required by the extra pass. Reviewed paid-write call sites, diagnostics redaction, company/run scoping, webhook trust boundary, recovery behavior, current README/MCP/media documentation and dependency consistency. The one static-review interruption was a false positive caused by the test that intentionally calls `higgs(..., billable=True)` to prove retry safety; production code has exactly one billable Higgsfield submit site.

### Verification / tests
- Final local `python manage.py test`: 173/173 passed in 8.476s.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `python manage.py check`: clean.
- `python -m pip check`: no broken requirements.
- Static production-code scan: exactly one `billable=True` Higgsfield generation submit site, `engine/media_providers.py`; no secret-like fields in diagnostics serialization.
- `git diff --check`: clean.

### External verification
None added. No provider write and no paid generation.

### Known issues
Chromium visual rendering remains blocked by execution-environment navigation policy and is not claimed. Render still requires explicit workspace selection.

### Next exact task
Build a transfer patch against remote feature-branch state `685da1b0fa96fda50c44684aa17b48e020fd2c11`, remove temporary resume/export artifacts in that patch, trigger `creative-prepare.yml`, inspect SQLite/PostgreSQL CI output and advance the branch only to the prepared verified commit.

### Commit
Product code is in local commits through `237e5be550187f88d6da464611caf58f320426f6`; this ledger update follows as documentation-only commit before transfer.


## Task 7: Exact GitHub transfer and PostgreSQL verification

### Status
DONE for repository transfer and CI. Production deployment remains BLOCKED only by the Render connector's required workspace selection.

### Files changed
No additional product behavior was added during transfer. Temporary transfer-only GitHub files/workflows were removed after verification; this ledger was updated.

### What changed
- Rebuilt the interrupted transfer from the exact locally verified Git diff rather than trusting the corrupt earlier payload.
- Encoded the transfer as six bounded chunks plus a SHA-256 readiness marker. GitHub CI reconstructed the bytes, verified payload SHA-256 `bf39f757dc6820b7f4ca7dba2e212d16e4e24fa1bc25040c516c13940a56d619`, decoded the native patch and checked all 25 expected Git blob hashes before testing.
- The first transfer run `35658061690` correctly failed closed because the isolated Git worktree did not contain the already-pinned `vendor/social-media-skills` submodule working files. The failure was two `FileNotFoundError` errors in old source-quote tests, not a product-code regression; the branch was not advanced.
- The CI harness was fixed to populate that pinned, already-checked-out submodule into the isolated worktree without changing product bytes.
- Rerun `35658336105` passed all gates and prepared commit `67c6751179d96c4b910f022ccfce817d46d0633f`.
- The GitHub connector advanced `feature/chatgpt-content-engine-mcp` to that prepared commit with a non-force ref update.
- Verified transfer artifacts `.creative-work.patch`, `.creative-patch-ready` and `.creative-patch-chunks/*` are absent from the shipped product tree.
- Removed temporary `.github/workflows/creative-prepare.yml` in cleanup commit `ac727ab8594e7546d8f7eb090bfdca7b5bc8c2f4`.

### Why
The transfer path deliberately fails closed: locally tested bytes must equal GitHub-tested bytes before a branch moves. A CI/worktree infrastructure mistake therefore cannot silently ship different product code.

### Verification / tests
Successful GitHub Actions run `35658336105`:
- exact payload SHA-256: matched
- exact expected product Git blob hashes: 25/25 matched
- migrations applied including `engine.0013_prompt_library`
- Django system check: clean
- collectstatic: success
- MCP app import/start check: success
- SQLite: 173 tests in 14.814s, `OK`
- PostgreSQL: 173 tests in 8.796s, `OK`
- prepared commit: `67c6751179d96c4b910f022ccfce817d46d0633f`
- prepared tree: `100c116068e594ed83b7aa008b2922dc5f59c5ce`
- feature branch updated without force
- temporary transfer payload/chunks verified absent afterward

### External verification
GitHub repository and GitHub Actions: VERIFIED. Render deployment/startup: NOT YET VERIFIED. Higgsfield real provider write: NOT RUN. Paid generation: ZERO.

### Known issues
- Render connector requires Jonas to explicitly select `My Workspace` (`tea-d06041ali9vc73bqfn80`) before the existing `content-engine-mcp` service can be inspected or changed.
- Chromium screenshot QA remains blocked by the execution environment's navigation policy and is not claimed as verified.
- A real paid Higgsfield smoke test still requires explicit approval after deployment and non-billable verification.

### Next exact task
After explicit Render workspace selection, inspect the existing service and deploy only the verified branch. Verify build/startup, migrations, health, MCP endpoint, OAuth flow, logs, environment readiness and webhook URL without creating a paid generation. Then document the exact priced paid smoke-test proposal and stop for approval.

### Commit
Verified product commit: `67c6751179d96c4b910f022ccfce817d46d0633f`.
Transfer-workflow cleanup: `ac727ab8594e7546d8f7eb090bfdca7b5bc8c2f4`.


## Task 8: Render production deploy and live non-billable service verification

### Status
DONE for deployment, database migration, process startup, public health/OAuth/MCP boundary and post-deploy error review. Golfkupongers Higgsfield server credential/account availability remains intentionally UNVERIFIED until an authenticated server-side estimate can be exercised; no personal Higgsfield connection is an acceptable substitute.

### Render target
- Workspace: `My Workspace` (`tea-d06041ali9vc73bqfn80`) — explicitly confirmed by Jonas.
- Service: `content-engine-mcp` (`srv-daj9cfgae00c7392t5c0`).
- Repo/branch: `ulle73/content-engine` → `feature/chatgpt-content-engine-mcp`.
- Auto deploy: off.
- Build command: `bash scripts/build.sh`.
- Start command: `bash scripts/start-mcp.sh`.
- Region: Frankfurt.
- Production URL: `https://content-engine-mcp.onrender.com`.

### Deployment
Triggered manual Render deploy `dep-daoqaldg1s2s73889n4g` after confirming the service already targeted the verified feature branch. Render checked out `dbba2e54fe2cae44a698955ceae4cfbc6d40e902`; this is the documentation head immediately above verified product commit `67c6751179d96c4b910f022ccfce817d46d0633f`. The ordinary repository CI for that head had already passed both verify and PostgreSQL jobs.

### Production verification
Render build/start logs:
- build successful
- `engine.0013_prompt_library... OK` against production Neon
- server process started
- `StreamableHTTP session manager started`
- `Application startup complete`
- Uvicorn bound `0.0.0.0:10000`
- Render status: `live`

External read-only HTTP checks:
- `GET /health/` → 200, `{"status":"ok"}`
- root/login flow → 200 login page after expected redirect
- `GET /oauth/status/` → 200, unauthenticated status
- `GET /.well-known/oauth-authorization-server` → 200; issuer and OAuth endpoints use the production Render origin and scope `content-engine.operate`
- `GET /.well-known/oauth-protected-resource` → 200; resource is `https://content-engine-mcp.onrender.com/mcp`
- unauthenticated `GET /mcp` → 401 with Bearer challenge and resource metadata, as required

Post-deploy Render log review found no `error` or `critical` entries in the deployment/live-check window.

### What is deliberately not claimed
The Render connector supports environment-variable updates but does not expose existing secret values. Therefore this task does not claim that `HIGGSFIELD_API_KEY_GK`, R2 credentials or any other secret was read back. R2/Neon operational continuity is supported by successful production startup/migration and existing architecture, but a new media write was not created merely to test storage.

Golfkupongers Higgsfield account-scoped model/credit availability also remains unverified. The connected Higgsfield ChatGPT app is not a valid substitute for the server credential and previously returned a workspace-read error. The correct next provider check is a non-billable estimate/preflight executed by the deployed Content Engine using its own server credential. A paid generation must not be used as a credential test.

### Paid activity
ZERO paid Higgsfield generations. ZERO paid smoke tests.

### Next exact task
Execute an authenticated, server-side non-billable Higgsfield estimate/preflight through Content Engine once that call path can be exercised without exposing credentials. If it passes, present the exact model, duration/parameters and estimated price for one minimal paid smoke test and stop for Jonas explicit approval before submission.

## Task 9: Independent end-to-end audit, 2026-09-22

### Scope and baseline

Requested branch fast-forwarded cleanly from `690defa` to `11a1082`. Local `main` remains `e92f85b9317ba7e9ac40baf990e01072c8073c8e`; no merge into main. Existing production service and workspace reverified with Render: free plan, auto deploy off, healthCheckPath **empty** despite `/healthz` in the blueprint. Current deployment remains `dbba2e54` at this stage. Error/critical log query since the prior deployment returned none. Browser witnessed the free-plan cold start before login. User completed ordinary production login; company-scoped Golfkuponger views work, with no existing runs or media.

Full local baseline: 173 tests, 2 failures and 3 errors. Four stem from Windows application control blocking SciPy native DLL imports (learning/own-performance); one from missing local MCP test environment. These are not hidden or reported as passing. CI must rerun the entire suite on the deployment's supported Python 3.13, including PostgreSQL.

### Implemented audit corrections (verification ongoing)

- User-visible review step: queued jobs no longer submit through browser or MCP status polling. Video price/parameters are obtained separately, explicit start requires a review less than ten minutes old, and a fresh higher estimate blocks payment. Image price uncertainty is explicitly shown. Tests reproduce the old unintended paid poll and missing preview.
- Reusable accessible native HOW TO dialog on Creative/Prompt/Media pages, with five first-use steps, three dummy examples, statuses, preservation caveat, prompt reuse and ChatGPT flow. Additional detail is collapsed. Uses existing dialog styling and keyboard behavior.
- Direct Media → AI studio entry creates only a local empty draft, avoiding a prerequisite paid text-generation step. Per-form UUID deduplicates repeated creation; foreign company tokens are rejected.
- Explicit archived prompt filter/restore, immutable original retained. Generation provenance keeps its first consistent generation link and records the estimate from the correct usage field, along with image size/count/quality.
- Long (up to 6000 character) valid briefs no longer violate the library search's 1000-character limit. Timeline ranges use their final endpoint; Swedish `5-sekunders` is parsed. Explicit image ratio determines actual image size; unsupported exact ratios are disclosed. Image priority now selects low/medium/high quality instead of all options silently using medium.
- Dedicated GK key no longer combines with another account's legacy secret. Billable HTTP 408 and non-object responses become UNKNOWN, not retryable failures. OpenAI ambiguous server responses, invalid output encoding and storage failures after accepted image output block automatic/new duplicate submission.
- Image-to-video sends the actual visible source asset, including its existing branding; only still-image editing uses the unbranded base.
- Webhook envelope rejects scalars and malformed types, records a hint under row lock, and returns without provider/storage I/O. Payload URLs remain untrusted. Authenticated reconciliation runs in the existing ASGI lifespan and never submits queued jobs. Recovery includes old saving jobs and rotates pending jobs fairly. Saving leases increased to ten minutes to avoid competing download/storage attempts during slow I/O.
- OAuth DCR rejects malformed IPv6 URLs, unexpected HTTPS ports and non-string grant types without a server error.

### Verification ledger

- RED: new audit tests reproduced long-brief exception, duration/format/quality mismatches, paid status poll, malformed webhook handling, missing restore/help/preflight, credential mixing and inconsistent provenance.
- First focused GREEN after initial fixes: **79 tests passed**, including media, prompt UI/library and creative core.
- Additional RED: synchronous webhook I/O, missing standalone entry, malformed DCR, OpenAI 500 ambiguity, I2V wrong reference and start after delivery reproduced. Follow-up verification pending.
- No live provider generation, no paid smoke test, no Postiz delivery/publication.

### Further completed audit corrections

- New MCP `preview_media` and `start_prepared_media` separate non-billable preparation from explicit paid start, enforce company/user ownership and revision, and return safe diagnostics. `search_creative_prompts`, `save_creative_prompt`, and `update_creative_prompt` expose scoped search/edit/favorite/archive/restore. Existing direct generation tools remain compatible and explicitly describe their paid effect.
- Media downloads and signed input uploads pin the validated public DNS address while preserving the original Host and TLS SNI/certificate validation; redirects/private addresses are rejected. Real read-only pinned HTTPS request to the official Higgsfield docs returned 200. Credentials are never forwarded to storage URLs.
- Invalid fresh preflight clears prior review/price approval. Malformed upload metadata/status responses produce recoverable errors. Recovery rotates failed status reads so one bad request cannot starve all work. All ambiguous OpenAI 5xx responses block duplicate paid retry.
- Media library links unfinished jobs, including queued reviews and UNKNOWN jobs. Removed the unused legacy generation prompt implementation. Compiler/brief versions bumped to `2026-09-22.1`; verified model registry unchanged.
- Latest local full run: **206 tests**, 2 failures + 2 errors from the known Windows SciPy application-control blocks, 2 PostgreSQL lock tests skipped on SQLite. No additional failures. Django check, migration drift check, dependency consistency, and whitespace check pass. Previous focused run: 108 passed (2 PostgreSQL-only skips). Full Linux/PostgreSQL CI is the deployment gate.
- Live Neon read-only check confirms `engine.0013_prompt_library` and `operator_bridge.0001_initial` applied. No schema changes required by this audit.

### Verified deployment and browser findings

- Commit `a81f5b213c5efb11db72af3f481ef8ab37975610`: full [CI 35725147029](https://github.com/ulle73/content-engine/actions/runs/35725147029) green (206 PostgreSQL tests, no skips; 206 SQLite tests, two PostgreSQL-only skips). Render deploy `dep-dap6usbm8hqs739vf0i0` live, startup migrations clean.
- User signed into Render. Set existing service Health Check Path to `/healthz`; connector read-back confirms it. `/healthz` and OAuth authorization metadata return 200; unauthenticated `/mcp` returns 401 with challenge.
- Production prompt `7dc7f522-dae9-4d86-9e67-04438f441b55`: create, edit, favorite, archive and restore verified in browser. Original morning-light instruction retained after editing to evening light.
- HOW TO opens with focus on Close, Escape closes and returns focus to trigger. At 390px viewport the dialog is 352px wide with no horizontal overflow. Found inherited 10px disclosure text: fixed to 16px. Aligned the help's animation label with the actual `Animera` control; archive action now states its recoverability.
- Dummy PNG `1b9e1ec4-929b-4e00-b14b-ad1e79d2a476` uploaded to production and loaded at 1024x1024. New unpaid studio run `48afc937-48c6-48c5-affe-0e39342f2c42` created.
- **Production blocker:** real server-side 5-second T2V estimate rejected with Higgsfield HTTP 401. Job `aa6d2e49-2538-4c3e-9b02-743fe2853e33` remains queued, no paid provider id, no start button. Render contains both GK key/secret names; values remain masked. User asked to correct the matched credential in Render, never paste it into chat. Account/model availability and price remain unverified.
- Failed preflight now persists its error safely on the job (previously only a one-request flash message); test demonstrated RED then GREEN. Browser-follow-up regression run: 65 passed.
- Free-plan cold start was also observed dropping an unprocessed form submission. No blind duplicate submission: empty DB/library verified before repeating. Continuous availability remains a deployment-plan decision.
- Detailed scope and residual risks: `docs/2026-09-22-creative-audit.md`.

### Final verification and handoff

- Final runtime `6e644fcb422a75a778f919ae4a4ea608aea9d71d` deployed **live** as `dep-dapbbh5bedkc7388e9c0` at 17:09:25 UTC. Browser confirms 16px help disclosures and that a failed preflight survives reload with paid start absent. Dedicated GK credential still returns 401; no estimate is invented.
- **Final local full suite: 206 tests, OK (2 PostgreSQL-only skips), 35.397 seconds.** Django check and migration drift check pass. Earlier Windows SciPy blocks did not recur; no OS protection was disabled. Exact-current CI run `35758303565` did not start due account billing/spending restriction (check annotations, not test failures). PostgreSQL concurrency code is unchanged from green run `35725147029`.
- Real image review: gpt-image-2, one 1024x1024 image, quality low; canceled before provider call. Actual dummy image used in second draft and Neon confirms R2, retained state and no expiry. I2V selects that reference but cannot reach provider upload/estimate because of authentication.
- Audit prompt was re-archived after retrieval verification so it does not influence future work. One clearly marked dummy image and two unpaid drafts remain, plus one canceled image job and two queued video plans; all provider IDs empty. Nothing published or sent to Postiz.
- Remaining external actions: correct matched GK API credential; restore GitHub Actions availability; decide on always-on Render compute; verify actual ChatGPT OAuth/tool session. Paid end-to-end provider completion requires a separate, exact-price approval after preflight is working. No paid approval is requested while price/account access is unknown.
- `main` remains `e92f85b9317ba7e9ac40baf990e01072c8073c8e`; all code stays on the requested feature branch. The final subsequent commit contains documentation evidence only and does not change the deployed runtime.
