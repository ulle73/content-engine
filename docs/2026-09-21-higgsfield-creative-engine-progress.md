# CURRENT STATE

- Latest completed step: Prompt Library service and UI verified (148 tests); offline Chromium layout checked at 1440px and 390px.
- Branch: `feature/chatgpt-content-engine-mcp`.
- Latest shipped product commit: `15c76aef9a084eb9e1cf97eccd880172a5815802` (schema; 120 SQLite and 120 PostgreSQL CI tests passed).
- Baseline commit: `1b6ae03a342a95c0e43690625bfeab2cce72e040`.
- Main reference: `d88524467ef216cf521d2e8fcf9bd54741eb3dc7`.
- Deploy: NOT changed or verified in this session.
- Blocker: Render connector has no selected workspace. It lists `My Workspace` (`tea-d06041ali9vc73bqfn80`), but its contract requires explicit user confirmation before use. Asked Jonas; continue independent repository work.
- Local environment: complete tracked snapshot of `dce11df7aa2b51f2235a071819706cea2d67b2c2`, including submodule sources; isolated Python 3.13.5 virtualenv with offline wheels. No production credentials/data. Baseline CI and 119 local tests pass.
- Next exact task: implement the structured Creative Brief, versioned registry, compiler and Creative Director tests.
- Paid generations: ZERO; explicit approval is required before any real paid smoke test.

## Binding brief

The user supplied the full implementation brief in `Inklistrad text(7).txt` on 2026-09-21. Its requirements supersede the earlier plan when they differ. Work continues inline in this session; no approval pauses for routine technical decisions. Existing Render service, Neon, R2, company/user boundaries, OAuth, MCP and generation history must be preserved. No personal Higgsfield credential fallback and no automatic retry of possibly billable submissions.

## Master checklist

- [x] Repository and branch topology verified
- [x] Full relevant repository audit and baseline tests
- [ ] Official API/SDK and model-contract audit
- [ ] Updated implementation plan and architecture rulings
- [ ] Structured creative brief and context boundary
- [ ] Versioned model intelligence, router, prompt/parameter compiler, preflight
- [x] Prompt Library persistence, retrieval and UI
- [ ] Official SDK adapter and fail-closed cost policy
- [ ] Durable duplicate-safe lifecycle, webhook, polling/recovery and R2 completion
- [ ] Shared UI and MCP integration, ownership tests
- [ ] UX and diagnostics review
- [ ] Full test suite, migrations, security checks and extra review
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
