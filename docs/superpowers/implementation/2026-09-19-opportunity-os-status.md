# Opportunity OS implementation status — 2026-09-19

## State

The approved Opportunity OS architecture is implemented as an active n8n subsystem, with fail-closed production gates around unverified builds.

### n8n workflows

| Workflow | ID | State |
|---|---|---|
| 50 OS – Goal Strategist | sIGpS9dNlfimmdqY | active |
| 51 OS – Context Snapshot | p1eSbFN44Ut4WsNj | active |
| 52 OS – Opportunity Generator | dsTecSTIEfrLUHQ2 | active |
| 53 OS – Evidence Enricher | 4C7K6Z6riCLzlg0c | active |
| 54 OS – Opportunity Judge | dbK3UvO9iVn5ejXT | active |
| 55 OS – Opportunity Publisher | nbq26xqEcGhOLWlK | active |
| 56 OS – Discord Interactions | 8hmPoU7WozzQ8vt4 | active |
| 57 OS – Build Orchestrator | vzDSkLzUyXQwjoFD | active, fail-closed |
| 58 OS – Outcome Tracker | JBtxoGRjppnZr7Ej | active |
| 59 OS – Self Optimizer | oJztJn3jOBTKNAlq | active |

Existing AI Radar 30–37 remains active during transition. Workflow 32's main Discord UX has already been simplified and its TESTA button removed.

### Data Tables

- GK_OS_GOALS — DSrDJjPLaWIZAUx8
- GK_OS_HUNTS — ubWk8wl5Sku46U9T
- GK_OS_CONTEXT — FPLQ7RO1yGhi1jgg
- GK_OS_OPPORTUNITIES — Y6Un17Jx5xujBS4h
- GK_OS_FEEDBACK — aewM2GUKeBYkUSma
- GK_OS_ACTIONS — gJEnjDuSb6ptFGWZ
- GK_OS_BUILD_JOBS — sjoFAESQDqVZLo0r
- GK_OS_OUTCOMES — CXBnzTOB0mXcRvib
- GK_OS_CONFIG — rIfpfUDeD01tzguo

## Verified behavior

- Strategic goals are AI-proposed but cannot self-activate. Seeded strategic goals remain PROPOSED until Jonas activates them.
- Context Snapshot hashes rows and a second unchanged run produced no writes.
- Order context is aggregate-only and intentionally excludes customer PII.
- The n8n Notion credential cannot currently read the Company Brain/Growth System pages. The workflow records explicit CONTEXT_GAP rows instead of pretending the data is current. A verified connector snapshot is seeded separately in GK_OS_CONTEXT.
- Opportunity generation uses a free structured-output model when available. Free-provider rate limits do not grant build authority.
- No-source/internal hypotheses use deterministic evidence handling rather than spending an LLM call.
- Only a fully reviewed opportunity with verified target and known pricing may expose BYGG.
- Strong but unverified ideas can become IDEA_TO_CONSIDER and be rated without a BYGG button.
- Main Opportunity OS Discord cards hide internal scores, confidence, workflow IDs and implementation targets.
- MER INFO is stored analysis; it does not trigger an extra model call.
- Non-Jonas mutation QA passed: a non-Jonas rating attempt completed without creating a feedback row.
- Goal MER INFO is readable by non-Jonas users.
- One real strategic goal proposal has been sent to the existing #ai-radar channel. Goal activation remains Jonas-only.
- Outcome Tracker and Self Optimizer are published and manual production runs completed.
- Self Optimizer keeps Jonas Fit separate from Business Value and uses a minimum sample size before personalization.

## Model behavior

Opportunity OS model nodes are pinned to the free structured-output model:

`google/gemma-4-31b-it:free`

The system is explicitly resilient to free-provider rate limiting:
- generator errors end the run without poisoning stored state,
- evidence without external sources uses deterministic handling,
- Judge/Skeptic has a deterministic fallback that can surface a rankable IDEA but can never grant BYGG authority.

## Discord transition

- Current Radar workflow 32 remains live but now uses the simplified pedagogical card and no TESTA button.
- Opportunity OS goal proposals are live.
- Opportunity OS opportunity publishing remains in shadow mode until real candidate quality is verified.
- Existing signed Discord workflow 37 still verifies Ed25519 signatures and legacy buttons remain supported.
- OS custom IDs are forwarded to workflow 56.
- Nicholas/readers may use MER INFO; only Jonas may rate or mutate goals/actions.

## BUILD worker

Worker source exists under `opportunity-worker/` and includes:
- HMAC request verification,
- zero-spend / Shopify MAIN / missing-capability policy gates,
- Codex SDK repository worker,
- GitHub branch isolation and test/build checks,
- callback signing,
- unit tests for auth and policy behavior,
- Dockerfile and CI workflow.

Railway service:
- name: opportunity-os-worker
- service ID: bc48584b-cae6-421b-ab8b-e7736ea207ba
- root: /opportunity-worker
- Dockerfile builder
- health check: /health

### External blocker

The worker has no deployment yet.

A second verified blocker exists in n8n: Code nodes cannot access process.env and $env access is blocked in this installation. Therefore the n8n → worker HMAC secret cannot be read from environment inside a Code node. Dispatch must use a credential-backed authentication mechanism (for example an n8n HTTP Header Auth credential) rather than embedding a secret in workflow code. Railway reports the source branch `opportunity-os-spec` as a STAGED change and requires Railway dashboard 2FA to commit it. Railway also reports that its GitHub integration does not currently have access to `ulle73/content-engine`.

Because of that external authorization block:
- `worker_enabled=false`
- Build Orchestrator creates durable jobs but stops at BLOCKED_CAPABILITY / WAITING_COST_APPROVAL rather than pretending to build
- Opportunity OS opportunity publishing remains shadow-only, so no user can receive a BYGG button that the backend cannot yet honor end-to-end.

## Remaining cutover gates

1. Approve the staged Railway branch/source change with 2FA and ensure Railway GitHub access to `ulle73/content-engine`.
2. Create a credential-backed n8n → worker authentication secret; do not place the secret in workflow code or Data Tables.
3. Obtain a healthy worker deployment and authenticated callback/dispatch path.
3. Run a reversible end-to-end BUILD QA, including failure/rollback.
4. Verify at least one real Opportunity OS opportunity card and interaction path.
5. Set `publisher_shadow_mode=false`.
6. Disable direct old Radar publishing (workflow 32) only after the new Opportunity Publisher succeeds in production.

Until those gates pass, the system intentionally remains reversible and fail-closed.
