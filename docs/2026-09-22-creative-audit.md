# Creative Engine audit — 2026-09-22

Branch: `feature/chatgpt-content-engine-mcp`. Implementation: `a81f5b2`.

## Scope and evidence

This is a code, automated-test and authenticated production audit. Paid provider generation and Postiz delivery/publication are excluded from execution. A green mocked provider test is not proof of a real generated result.

Full GitHub CI [35725147029](https://github.com/ulle73/content-engine/actions/runs/35725147029) passed: 206 tests on PostgreSQL 17 without skips; 206 on SQLite with two PostgreSQL-only concurrency tests skipped. Checks also cover migrations, static collection and MCP ASGI startup import. Local Windows full run has four pre-existing SciPy DLL application-control failures; security controls were not disabled.

| Area | Corrections and automated evidence | Production evidence / remaining limit |
|---|---|---|
| Prompt Library | Create/edit/favorite/archive/restore, immutable original, company ownership, CSRF, duplicate provenance and scoped heuristic inspiration | Authenticated UI checks recorded below |
| Brief/compiler/router | Long briefs, timeline endpoint, Swedish duration, actual image size/quality, explicit unsupported ratio warning, versioned compiler | One verified model per output kind; no claim of a broad automatic model marketplace |
| Review and payment | Queued preview is non-billable; no paid status poll; 10-minute approval; failed recheck invalidates approval; price increase/cap blocks submit | Actual server credential estimate recorded below; no paid request |
| Concurrency/idempotency | Independent PostgreSQL connections prove single active job and one paid adapter invocation under concurrent submit | Provider cannot guarantee exactly-once after network ambiguity; UNKNOWN intentionally blocks resubmit |
| Higgsfield lifecycle | Safe GET retries, no billable POST retry, timeout/malformed responses, cancel, untrusted webhook hint, saving lease, idempotent storage, bounded recovery | Actual provider completion, cancel and webhook delivery require a paid request and remain unverified |
| OpenAI images | Generate/edit parameters and quality, decoded result validation, ambiguous 5xx/storage failure -> UNKNOWN | No live image generation. Interrupted synchronous image response cannot be fetched again automatically; operator reconciliation required |
| I2V | Visible selected reference is uploaded, provider credential never sent to signed storage URL | Upload and estimate checks recorded below; preservation is a prompt instruction, not a guarantee |
| Files/storage | Private R2 adapter, company-scoped access, media validation, limits, expiry/used-reference preservation, DNS pin with original TLS name | Real read-only HTTPS pinning check 200; new R2 write/read recorded below |
| MCP/OAuth | Scoped tokens/audience/expiry, owner isolation, revision guards, malformed DCR protection; added preview/start and prompt tools | No Content Engine connector is exposed in this Codex session. Full ChatGPT OAuth consent + tool execution is not claimed |
| UI/HOW TO | Native accessible reusable dialog, concise steps and progressive detail, direct unpaid studio entry, unfinished-job links | Browser/keyboard/responsive checks recorded below |
| Deployment/data | Existing ASGI lifespan recovery, direct Neon migration lock, no schema drift | Neon applied engine.0013 and operator_bridge.0001 confirmed. Render free plan is not continuous processing; healthcheck correction needs Dashboard access |

## Safety boundaries

- No paid Higgsfield or OpenAI generation, no Postiz send, no publishing or scheduling.
- No provider secrets copied into reports or client pages; no global Codex configuration changes.
- No main-branch changes, no account/plan upgrades, no production data deletion.
- Audit-created fixtures are identifiable and retained or recoverably archived; job cancellation before submit does not contact a generation provider.

## References checked

- [Higgsfield model discovery and shared contracts](https://docs.higgsfield.ai/docs/llms.txt): console model schema has priority over supplementary OpenAPI.
- [Upload contract](https://docs.higgsfield.ai/docs/concepts/file-uploads): signed storage headers, no provider credential forwarding.
- [Cancellation contract](https://docs.higgsfield.ai/docs/api-reference/requests/cancel-a-queued-request): accepted cancellation is HTTP 202, only before provider processing.
- [Error/retry contract](https://docs.higgsfield.ai/docs/concepts/errors): ambiguous paid submissions must not be retried automatically.
- [Render free service limitations](https://render.com/docs/free): idle spin-down and no production availability guarantee. An always-on compute plan is a separate user decision.

## Production verification ledger

Pending deployment and browser checks; this document must not be interpreted as a completed production-readiness verdict until the ledger below is finalized.
