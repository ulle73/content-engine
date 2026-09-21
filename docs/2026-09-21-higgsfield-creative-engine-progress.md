# CURRENT STATE

- Latest completed step: Prompt Library additive schema, migration and regression tests verified (120 tests).
- Branch: `feature/chatgpt-content-engine-mcp`.
- Baseline commit: `1b6ae03a342a95c0e43690625bfeab2cce72e040`.
- Main reference: `d88524467ef216cf521d2e8fcf9bd54741eb3dc7`.
- Deploy: NOT changed or verified in this session.
- Blocker: Render connector has no selected workspace. It lists `My Workspace` (`tea-d06041ali9vc73bqfn80`), but its contract requires explicit user confirmation before use. Asked Jonas; continue independent repository work.
- Local environment: complete tracked snapshot of `dce11df7aa2b51f2235a071819706cea2d67b2c2`, including submodule sources; isolated Python 3.13.5 virtualenv with offline wheels. No production credentials/data. Baseline CI and 119 local tests pass.
- Next exact task: implement/test prompt saving, immutable original text, indexed retrieval, tenant boundaries and Prompt Library UI.
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
- [ ] Prompt Library persistence, retrieval and UI
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
