# Acceptance ledger

Only PASS, FAIL, BLOCKED, NOT RUN. Evidence must exist for every PASS.

Updated 30 September 2026 from `origin/main` on `codex/product-flow-integration`. PASS below means the stated local evidence exists; it does not imply deployment or all catalogue templates are accepted. Detailed evidence and remaining scope: [product integration review](../2026-09-30-product-integration-review.md).

| Gate | Required evidence | State |
|---|---|---|
| Existing app integration | Local browser and authenticated MCP transport share the final MediaAsset and ContentRun; company isolation tests | PASS |
| MotionSpec | Whole Django and Node schema suites, including hostile input and version checks | PASS |
| Engine separation | Actual Node worker renders; active Motion jobs are excluded from Higgsfield polling | PASS |
| Durable jobs | Lease/retry/cancel/idempotency tests pass locally; independent PostgreSQL concurrency remains unverified | NOT RUN |
| Preview gate | Actual complete browser preview/storyboard, approval and subsequent stored final; stale-revision tests | PASS |
| Video | Actual H264/AAC 9:16, 1:1, 16:9 renders, server ingestion and full decoding | PASS |
| Audio | Built-in mix decoded, non-silent and not clipping; full uploaded-music/fades/ducking acceptance remains | NOT RUN |
| Catalogue | Distinct useful entries, provenance, real previews | NOT RUN |
| Novice UI | Actual browser discovery/create/preview/approve/final/review/copy; final retained as MediaAsset | PASS |
| Advanced UI | Order, duplicate/delete, effects/timing editing | NOT RUN |
| Brand | Verified real logo/tokens/font, not invented | NOT RUN |
| Wrapped | 877, 721515 SEK, Stockholm, real impact video | NOT RUN |
| MCP | Authenticated local HTTP discovery/create/queue/cancel/approval/final read-back pass; public OAuth/ChatGPT acceptance remains | NOT RUN |
| Tests | 504 Django tests, OK with 3 PostgreSQL-only skips; 13/13 Node tests | PASS |
| Build | Local Remotion bundle and typecheck; migrated isolated database; Django check and migration drift check | PASS |
| Deployment | Live health, worker and stored output read-back | NOT RUN |
| Rights | All named sources reviewed; correct commercial entitlement | NOT RUN |
| Documentation | Usage/drift guide and evidence report added; matching router skill is outside this review | NOT RUN |
| Final audit | Separate novice/advanced/agent/failure/maintainer checks | NOT RUN |

Current facts: this review branch starts from fetched `main` at `c72f63c`. Local `main` is unchanged. An isolated Windows environment and synthetic data were used; no production deployment, paid provider start, resource purchase or external publication was performed. Real logo/rights, full catalogue, advanced UI, public OAuth and PostgreSQL concurrency remain explicit acceptance work.
