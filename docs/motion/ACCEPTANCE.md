# Acceptance ledger

Only PASS, FAIL, BLOCKED, NOT RUN. Evidence must exist for every PASS.

| Gate | Required evidence | State |
|---|---|---|
| Existing app integration | Owner-scoped UI/MCP, existing MediaAsset and ContentRun | NOT RUN |
| MotionSpec | Versioned strict schema, hostile input tests | NOT RUN |
| Engine separation | Creative plans compile; only Remotion renders | NOT RUN |
| Durable jobs | Claim/lease/retry/cancel/idempotency/concurrency tests | NOT RUN |
| Preview gate | Representative actual frames and low-resolution video; same-hash approval | NOT RUN |
| Video | Actual H264/AAC renders 9:16, 1:1, 16:9 | NOT RUN |
| Audio | Decode non-silent mix; uploaded music/SFX/fades/ducking | NOT RUN |
| Catalogue | Distinct useful entries, provenance, real previews | NOT RUN |
| Novice UI | Browser from discovery to retained final asset | NOT RUN |
| Advanced UI | Order, duplicate/delete, effects/timing editing | NOT RUN |
| Brand | Verified real logo/tokens/font, not invented | NOT RUN |
| Wrapped | 877, 721515 SEK, Stockholm, real impact video | NOT RUN |
| MCP | Real authenticated transport discovery/draft/preview/final/asset | NOT RUN |
| Tests | Whole existing and new suite | NOT RUN |
| Build | Production build, migrations and Node typecheck | NOT RUN |
| Deployment | Live health, worker and stored output read-back | NOT RUN |
| Rights | All named sources reviewed; correct commercial entitlement | NOT RUN |
| Documentation | User/developer docs and small matching router skill | NOT RUN |
| Final audit | Separate novice/advanced/agent/failure/maintainer checks | NOT RUN |

Current facts: main and production diverged; work branch created from production. Direct container internet cannot resolve hosts; dependencies transferred through isolated GitHub Actions artifacts. Production Render plan is free; no paid upgrade authorized.
