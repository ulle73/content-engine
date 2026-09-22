# Creative Engine audit — 2026-09-22

Branch: `feature/chatgpt-content-engine-mcp`. Main implementation: `a81f5b2`; browser follow-up fixes: `6e644fc`.

## Scope and evidence

This is a code, automated-test and authenticated production audit. Paid provider generation and Postiz delivery/publication are excluded from execution. A green mocked provider test is not proof of a real generated result.

Full GitHub CI [35725147029](https://github.com/ulle73/content-engine/actions/runs/35725147029) passed on `a81f5b2`: 206 tests on PostgreSQL 17 without skips; 206 on SQLite with two PostgreSQL-only concurrency tests skipped. Checks also cover migrations, static collection and MCP ASGI startup import. Earlier Windows runs had four SciPy DLL application-control failures; security controls were not disabled. The final full local run on **6e644fc passed all 206 tests (two PostgreSQL-only skips)**, plus Django check and migration drift check.

Latest GitHub run [35758303565](https://github.com/ulle73/content-engine/actions/runs/35758303565) did not start either job: account payment failure/spending-limit restriction, confirmed by check annotations. Therefore exact-current Linux/PostgreSQL CI is unavailable, not a test regression. No billing settings changed. The latest follow-up is locally verified; the PostgreSQL concurrency implementation is unchanged from the fully green CI commit.

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
| Deployment/data | Existing ASGI lifespan recovery, direct Neon migration lock, no schema drift | Neon applied engine.0013 and operator_bridge.0001 confirmed. Render healthcheck corrected to /healthz and read back; free plan is not continuous processing |

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

Final runtime `6e644fcb422a75a778f919ae4a4ea608aea9d71d`, Render deploy `dep-dapbbh5bedkc7388e9c0`, live at 17:09:25 UTC. Browser confirms readable 16px help disclosures and persistent preflight failure after reload, with no paid start button. Later evidence-only documentation commits do not alter runtime code.

**Verdict: not fully production-ready.** The code and non-billable UI paths are verified as described below; the server's Higgsfield credential currently fails HTTP 401, Render Free sleeps, and real provider completion/ChatGPT OAuth execution remain unverified.

- Production prompt `7dc7f522-dae9-4d86-9e67-04438f441b55` created, edited, favorited, archived and restored through UI. Edited text differs from intact original. Both test generation plans record its ID as inspiration, confirmed with read-only Neon SQL.
- After verification, the dummy prompt was recoverably archived again to exclude it from future inspiration. Two unpaid draft records and the one labeled R2 dummy image remain as audit fixtures. One image job is canceled; two video plans are queued with empty provider IDs. No existing user data removed.
- HOW TO verified on desktop and 390px mobile viewport (352px dialog, no horizontal overflow); close autofocus, Escape and return focus work. Temporary viewport/CDP emulation reset. Browser-discovered 10px disclosure text fixed to 16px and `Animera` label aligned with actual action.
- R2 dummy image `1b9e1ec4-929b-4e00-b14b-ad1e79d2a476`: upload succeeded, browser decoded 1024x1024 image; Neon confirms `storage_backend=r2`. Selected into draft `d82bcd34-f457-473b-9577-642b8aa9ec38`, `used_at` set and expiry null. No Postiz action.
- Text-to-video run `48afc937-48c6-48c5-affe-0e39342f2c42`, job `aa6d2e49-2538-4c3e-9b02-743fe2853e33`: actual server estimate returned 401, job remains queued without provider ID or price. No paid start button. Both dedicated GK variable names are present in Render; secret values kept masked. User asked to correct the matched credential.
- Image preview job `c75a576e-77d9-423d-b596-521bf3343796`: `gpt-image-2`, n=1, 1024x1024, quality=low. Review rendered and queued cancellation succeeded without provider invocation. This does not verify the OpenAI account or an actual image generation.
- I2V job `90ad8e0d-b4dd-480e-918d-4bb17e3f3bc3` shows the actual selected dummy reference, 5 seconds, square composition request. Preflight also returns 401 before upload; live Higgsfield storage upload and estimate are blocked by credentials.
- `/healthz` and authorization metadata 200; unauthenticated `/mcp` 401 with challenge. Healthcheck configured `/healthz` in Render and confirmed via connector. Startup logs show no pending migrations. No error/critical entries in the observed post-deploy window (12:07–17:07 UTC); the handled provider 401 is evidenced in UI, not claimed absent.
- Free-plan cold starts can discard an unprocessed form submission. DB/library was checked before repeating any upload/save. This infrastructure behavior requires an always-on service for reliable availability; no artificial keep-alive or paid plan upgrade was introduced.

## Required follow-up

1. Correct the server's Golfkuponger Higgsfield credential and repeat **Uppdatera priskontroll** on the same queued jobs. No new generation is necessary.
2. Resolve GitHub Actions billing/spending restriction and rerun the latest workflow.
3. Decide whether production requires always-on Render compute. Free cannot provide that guarantee.
4. Verify ChatGPT's actual consent/refresh/tool session once its connector is available; no new OAuth client or broad permissions were created in this audit.
5. Only after an authenticated estimate succeeds: present the exact model, compiled prompt, duration/input and fresh price for explicit approval of a single paid smoke test. Currently **no credible price is available**, so none is invented and no paid approval request is made.
