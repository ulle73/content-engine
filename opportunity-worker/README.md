# Golfkuponger Opportunity OS Worker

Long-running build worker for Opportunity OS. n8n owns policy and orchestration; this service only executes explicitly authorized, capability-gated build jobs.

## LLM routing

All coding builds run through OpenRouter.

Model tiers:

- `free` (default): `z-ai/glm-5.2:free`
- automatic free fallback: `openrouter/free`
- `premium` (explicit only): `z-ai/glm-5.3-flash`
- `premium_max` (explicit only): `qwen/qwen3.8-max-0902`

Paid tiers never activate automatically and never silently downgrade to a free model. A build must explicitly carry `modelTier: "premium"` or `modelTier: "premium_max"`. Jobs without a tier remain on the free path.

Optional Railway overrides:

- `OPENROUTER_MODEL`
- `OPENROUTER_FREE_FALLBACK_MODEL`
- `OPENROUTER_PREMIUM_MODEL`
- `OPENROUTER_PREMIUM_MAX_MODEL`

The OpenRouter credential is available to the Codex process for API authentication but is excluded from the shell environment exposed to the coding agent. The worker also scans staged changes for configured secrets before committing.

## Safety

The worker builds on a separate `opportunity-os/<opportunity-id>` branch. n8n owns the later finalization decision, and only exact targets in `GITHUB_AUTODEPLOY_TARGETS` can be finalized.
