# Higgsfield Creative Engine + ChatGPT MCP — implementation plan

**Date:** 2026-09-21  
**Repository:** `ulle73/content-engine`  
**Status:** Approved plan / not yet implemented  
**Primary goal:** Turn Content Engine into the single creative-media backend for both the Content Engine UI and ChatGPT, using Higgsfield's pay-as-you-go API rather than the Higgsfield ChatGPT subscription/plugin.

---

## 1. Executive decision

Build the Higgsfield integration **inside this repository**, but as a clean reusable subsystem that can be called from both:

1. the existing Django Content Engine UI, and
2. a separate remote MCP process deployed from the same repository for ChatGPT.

Do **not** create a separate `golfkuponger-higgsfield-mcp` repository.

Do **not** fork a community Higgsfield MCP as the product foundation.

Use a little from each relevant upstream source:

### Production dependency / source of truth

**`higgsfield-ai/higgsfield-client` — official Python SDK**

Use this as the primary production integration because Content Engine is Python/Django. It was updated on 2026-09-17 with the current API host, upload handling, polling and Agent API support.

Use it for:

- authenticated submission
- request IDs
- status polling
- result retrieval
- cancellation where supported
- media upload
- webhook support where appropriate
- official error classes / lifecycle behavior

The project should move away from maintaining raw Higgsfield request plumbing where the official SDK provides the same capability safely.

### Secondary upstream reference

**`higgsfield-ai/higgsfield-js` — official JavaScript/TypeScript SDK**

Do not add Node or this package to Content Engine.

Use it as a **contract/parity reference** when the Python SDK or docs are unclear, especially for:

- current v2 endpoint behavior
- retry semantics
- status mapping
- webhook behavior
- upload handling
- newly shipped features that may land in one SDK before the other

### Selective design inspiration only

**`Hikhakk/higgsfield-mcp-unified` — community MCP, MIT, alpha**

Do not fork it and do not depend on it at runtime.

Selectively reimplement useful ideas in Content Engine:

- `recommend_model`
- `validate_params`
- `preflight_check`
- structured error taxonomy
- bounded retry/backoff for safe read operations
- circuit-breaker style health protection
- batch submission pattern
- prompt scaffolds
- model capability metadata

Explicitly **do not** copy its experimental cloud-web backend architecture:

- no Clerk cookies
- no reverse-engineered `fnf.higgsfield.ai` calls
- no browser/TLS impersonation
- no inferred/unverified endpoints in production
- no consumer-web-session automation

Only documented official API/SDK behavior is allowed in production.

---

## 2. Current state in Content Engine

The repository already has the core infrastructure that a separate Higgsfield service would otherwise duplicate.

Existing pieces:

- Django/Python application
- `MediaGeneration` with provider ID, status, prompt, parameters and usage
- `MediaAsset` with company ownership and R2 persistence
- Neon/PostgreSQL
- private R2 media storage
- user/company access boundaries
- start-image handling
- Higgsfield cost estimation before paid submission
- per-video spend ceiling
- prevention of blind duplicate paid submissions
- result download and MP4 validation
- Postiz handoff
- daily execution framework
- explicit handling of uncertain paid API calls

Current Higgsfield implementation is in `engine/media_providers.py` and uses direct REST.

Current limitations:

- one hard-coded video model
- ten-second video assumption
- simple prompt construction
- no model router
- no proper model capability registry
- no ChatGPT/MCP surface
- no autonomous prompt optimization by model
- no unified image/video creative director
- no production webhook flow for Higgsfield completion
- the last live video test was blocked by insufficient API credits
- docs and code reflect the 2026-09-08 model state and need re-verification

---

## 3. Final target

A user should be able to write either in ChatGPT or Content Engine:

> Create a premium 9:16 Golfkuponger reel where the camera flies low over a Swedish golf course in morning mist. Realistic, cinematic, around 8 seconds.

The system should automatically:

1. understand the creative intent,
2. load relevant company/content context when available,
3. convert the rough request into a structured creative brief,
4. choose the best verified Higgsfield model for that job,
5. adapt the prompt to that model,
6. choose valid resolution, duration, aspect ratio, audio and reference-media parameters,
7. validate the request locally before spending money,
8. estimate cost,
9. require approval only when the configured cost/quality policy requires it,
10. submit exactly once,
11. persist the Higgsfield request ID immediately,
12. expose clear progress,
13. receive completion through webhook where practical and use safe polling as fallback,
14. download the result into private R2,
15. attach the result to the correct company/generation,
16. return a usable preview/result to Content Engine or ChatGPT.

The user should **not** need to know which model, endpoint or parameter set Higgsfield requires.

---

## 4. User experience target

### ChatGPT

The normal interaction should be natural language.

Examples:

- "Create a 5 second cinematic drone-style golf video in 16:9."
- "Animate this uploaded image. Keep the clubhouse unchanged and add a slow push-in."
- "Make three different reel concepts from today's best Content Engine idea."
- "Use the cheapest good model for this."
- "Use the highest quality option under $1."
- "Show me the status of the video I started."

The MCP should expose a small tool surface; ChatGPT handles the complexity.

Recommended tools:

- `create_video`
- `animate_image`
- `create_image` or reuse the existing OpenAI image path where appropriate
- `estimate_media`
- `get_generation`
- `list_recent_generations`
- `cancel_generation` when the provider still allows it
- `get_content_context` for Content Engine-aware creation

Avoid exposing dozens of model-specific tools to the user.

### Content Engine UI

The existing media flow remains recognizable.

Improve it with:

- Automatic model choice by default
- Optional "quality / balanced / economy" intent
- Editable final prompt/brief for advanced use
- Cost shown before unusually expensive generation
- Better progress states
- More than one valid duration/aspect ratio where supported
- "Why this model?" details available but not forced on the normal user

---

## 5. Proposed internal architecture

Keep everything in this repository.

Suggested modules:

```
engine/
  creative/
    brief.py
    prompts.py
    router.py
    models.py
    validation.py
    policy.py
    errors.py
  providers/
    higgsfield.py
    openai_images.py
  media.py

mcp_server/
  server.py
  tools.py
  auth.py
```

Exact file names may change during implementation, but the separation should remain:

### Creative Director

Converts a rough user request plus available Content Engine context into a structured brief.

Example fields:

- purpose
- platform
- subject
- environment
- visual style
- camera movement
- shot type
- lens/look
- lighting
- pacing
- realism
- desired duration
- aspect ratio
- audio intent
- reference-media constraints
- must-preserve elements
- must-avoid elements
- visible-text requirements
- factual/company constraints

Do not rely on string stuffing alone.

Use structured output so the final generation prompt can be deterministic and testable.

### Prompt compiler

Turns the structured brief into provider/model-specific prompts.

Examples:

- text-to-video prompt
- image-to-video preservation prompt
- commercial/product prompt
- cinematic landscape prompt
- social reel prompt

The compiler must preserve Content Engine's existing factual protections:

- no invented results
- no invented testimonials
- no fictional documentary claims
- no competitor copying
- no accidental logo recreation
- exact company facts remain authoritative

### Model router

Selects only from **verified official API models**.

Inputs can include:

- text-to-video vs image-to-video
- desired duration
- aspect ratio
- resolution
- audio
- quality preference
- speed preference
- budget ceiling
- reference media needs
- current provider/model health

Output must explain its selection in machine-readable form, for logging/debugging.

Do not hard-code "one best model forever".

### Capability registry

Store a versioned local registry of models that have been verified against current official documentation/SDK and, where possible, live preflight.

Each model entry should include:

- model ID / endpoint
- modes
- durations
- resolutions
- aspect ratios
- audio support
- reference media roles
- known constraints
- cost-estimate support
- verification source
- verified date
- enabled/disabled flag

Unverified models must never be silently selected.

### Higgsfield provider

Primary implementation should use the official `higgsfield-client` Python SDK.

It owns:

- client creation
- upload
- submission
- request ID extraction
- status mapping
- result retrieval
- cancellation
- webhook helpers where supported
- provider error normalization

Keep credentials server-side.

### Policy layer

Decides whether to:

- run directly
- ask for cost approval
- reject unsupported parameters
- downgrade resolution/duration
- choose a cheaper model

The policy must be explicit and configurable.

Example starting rule:

- normal inexpensive generation under configured threshold: run without an extra confirmation
- expensive generation / multiple outputs / high resolution / long duration: return estimate and request explicit approval

No silent expensive fallback.

---

## 6. Job lifecycle

Generation remains asynchronous.

Required state handling:

`queued -> starting -> running -> completed`

Terminal alternatives:

- `failed`
- `nsfw`
- `canceled`
- `unknown`

Rules:

1. Create `MediaGeneration` before provider submission.
2. Claim the job transactionally.
3. Submit only once.
4. Persist `request_id` immediately after confirmed submission.
5. Never blindly retry a possibly billable POST after a timeout.
6. Safe GET/status calls may use bounded retries and backoff.
7. Completion is preferably webhook-driven.
8. Polling remains a fallback and manual status path.
9. Download result once and store it in R2.
10. Repeated webhook/poll events must be idempotent.
11. Ownership is checked before any result is exposed through MCP or web UI.

The existing "unknown" state is important and must remain fail-closed.

---

## 7. Prompt intelligence

Do not simply reuse the five short prompt templates from the community MCP.

Use them only as inspiration.

The Content Engine prompt layer should be materially stronger:

### Stage A — intent extraction

Turn natural language into a structured brief.

### Stage B — context merge

Merge only relevant:

- company profile
- voice
- current verified facts
- selected idea
- caption
- target channel
- inspiration mechanism
- reference-image metadata

### Stage C — creative direction

Add useful cinematography only when it supports the request:

- framing
- movement
- lens/look
- lighting
- subject motion
- temporal sequence
- composition
- transition style
- environmental motion

Avoid generic "cinematic, 35mm, volumetric" keyword stuffing.

### Stage D — model compilation

Translate the brief into the form that the selected model handles best.

### Stage E — preservation constraints for image-to-video

Explicitly define:

- what may move
- what may not change
- identity/product/architecture preservation
- no invented text/logos
- camera-only motion when requested

### Stage F — optional quality loop

Do not regenerate automatically.

If a later phase adds automated visual review, it may score a completed result and suggest a revised prompt, but a second paid generation requires policy approval.

---

## 8. MCP design

The MCP is a **thin remote interface to Content Engine**, not a second business-logic implementation.

All real generation logic stays in `engine/`.

The MCP calls the same service functions the Django UI uses.

This guarantees:

- one prompt engine
- one router
- one cost policy
- one generation history
- one ownership model
- one Higgsfield integration

### Deployment

Same Git repository, separate process/service.

Initial target:

- existing Content Engine web app remains on Render
- remote MCP can be deployed as a separate lightweight service, initially Railway if that is the fastest ChatGPT-compatible deployment
- both use the same Neon database, R2 bucket and shared provider configuration

Do not duplicate databases or media storage.

If running the MCP on Render proves equally simple and stable, one hosting provider is preferable. Hosting is an operational choice, not an architectural dependency.

### MCP authentication

The remote MCP must not be a public unauthenticated generation endpoint.

Use a dedicated server-side MCP credential/auth layer.

Never expose Higgsfield credentials to ChatGPT.

For the first private Golfkuponger deployment, one trusted service identity is enough. Multi-user OAuth is only needed if external users are added later.

---

## 9. Upstream repositories and how we use them

### A. higgsfield-ai/higgsfield-client

**Role:** Primary production dependency.

**Use:**

- Python SDK
- official API request lifecycle
- uploads
- polling/status
- result retrieval
- cancellation
- webhook support
- official error handling
- Agent API only as an optional future experiment

**Do not:**

- couple business logic to undocumented SDK internals
- assume Agent API access exists
- use Agent API as a requirement for v1

### B. higgsfield-ai/higgsfield-js

**Role:** Secondary official reference.

**Use:**

- compare endpoint behavior
- compare V2 lifecycle and retry semantics
- identify SDK feature parity gaps
- inspect newly released official behavior

**Do not:**

- install Node just for Higgsfield
- add it as a runtime dependency

### C. Hikhakk/higgsfield-mcp-unified

**Role:** Architecture/pattern reference only.

**Use ideas from:**

- model recommendation
- parameter validation
- preflight
- typed tool outputs
- error taxonomy
- retry/backoff for safe operations
- circuit-breaker ideas
- batch patterns
- prompt resource concepts

**Do not use:**

- its experimental web backend
- Clerk cookie auth
- Cloudflare/TLS workarounds
- reverse-engineered private endpoints
- inferred models as production routes
- its model list as source of truth
- the repository itself as a runtime dependency

### D. Higgsfield official docs/OpenAPI

**Role:** Highest-priority contract source alongside the official SDK.

Before enabling a model, verify:

- endpoint exists
- schema
- terminal states
- upload roles
- estimate behavior
- webhook behavior
- current restrictions

---

## 10. Agent API decision

Higgsfield's official Python SDK added Agent API support on 2026-09-17.

Do **not** make it part of the core v1.

Reasons:

- requires account access
- introduces another agentic decision layer
- cost/behavior is less transparent than our own Creative Director + router
- Content Engine already has OpenAI reasoning/context
- we want one auditable prompt/model policy

Add a later experiment behind a feature flag:

`HIGGSFIELD_AGENT_EXPERIMENT=false`

Test it only if it can demonstrably improve:

- model selection
- prompt interpretation
- multi-step creative tasks

without losing cost control or auditability.

---

## 11. Migration from current Higgsfield code

Do not rewrite the whole media system.

Incrementally replace provider internals while preserving existing invariants.

### Keep

- `MediaGeneration`
- `MediaAsset`
- R2 storage
- Neon/PostgreSQL
- transactional job claim
- `unknown` state
- duplicate prevention
- spend ceiling
- ownership checks
- file validation
- Postiz integration

### Replace/refactor

- raw Higgsfield request helper
- hard-coded Kling 2.5 choice
- fixed 10-second video payload
- old upload implementation where the official SDK can safely replace it
- single generic video prompt
- model-specific logic mixed into `media_providers.py`

### Compatibility

Existing jobs must remain readable.

Do not reinterpret old `parameters` or `provider_id` values.

New generation metadata should add fields inside JSON where possible before introducing schema changes.

---

## 12. Data to persist for new generations

At minimum record:

- requested user brief
- structured creative brief
- compiled provider prompt
- selected provider
- selected model
- selection reason
- source/reference asset IDs
- final submitted parameters
- estimated credits/USD
- cost policy decision
- provider request ID
- lifecycle timestamps
- provider terminal status
- result asset ID
- errors
- prompt/router/capability-registry versions

This makes later learning possible:

> Which prompts/models actually produce media Jonas chooses and publishes?

That is more valuable than only saving the final URL.

---

## 13. Success criteria

The implementation is considered successful when all of the following are true.

### Functional

- A natural-language ChatGPT request can start a Higgsfield generation through the Content Engine MCP.
- The same creative engine is used from the Content Engine UI.
- Text-to-video works with at least one currently verified model.
- Image-to-video works with at least one currently verified model.
- Request ID is stored before subsequent status handling.
- A completed provider result is copied into private R2.
- ChatGPT can retrieve status/result without receiving Higgsfield credentials.
- The result remains linked to the correct company/user context.

### Intelligence

- User does not have to know model names.
- Router selects only verified compatible models.
- Prompt is materially improved from the rough request.
- Image-to-video prompts contain preservation constraints.
- Model-specific parameter schemas are validated before submission.
- Router can honor budget/quality/speed intent.

### Cost and safety

- Cost estimate is checked where supported.
- Configured spend ceiling cannot be bypassed by automatic fallback.
- No blind retry of an uncertain paid submission.
- Duplicate MCP/tool calls do not create duplicate paid generations.
- Expensive generation requires approval according to policy.
- Secrets are server-only.

### Reliability

- Provider 429/5xx/read failures produce useful structured errors.
- Safe polling honors backoff.
- Webhook processing is idempotent.
- A process restart does not lose the generation.
- A user can resume/check an existing generation.
- Failure of the MCP process does not corrupt the Django web application.

### Verification

- Unit tests for router, validation, prompt compiler, policy and status mapping.
- Integration tests with mocked Higgsfield SDK.
- One real low-cost T2V generation.
- One real low-cost I2V generation.
- Result bytes validated and stored in R2.
- One successful ChatGPT-to-MCP-to-Higgsfield-to-R2 end-to-end test.
- No real test is repeated merely because of a timeout.

---

## 14. What a failed implementation looks like

The project is **not successful** if any of these are true:

- We fork `higgsfield-mcp-unified` and become dependent on its private web backend.
- We maintain a second standalone generation database outside Content Engine.
- ChatGPT and Content Engine use different prompt/router logic.
- A user has to manually choose raw endpoint slugs for normal use.
- Model selection is a hard-coded single model with no capability validation.
- Unverified/inferred endpoints can be selected automatically.
- API secrets enter browser/mobile/ChatGPT-visible configuration.
- A timeout can trigger an automatic second paid submission.
- The MCP exposes generation without authentication/ownership checks.
- Completion URLs remain only on Higgsfield and are not persisted to R2.
- Jobs are lost on process restart.
- The system claims completion before the output is actually downloaded/validated.
- Prompt "optimization" is only generic keyword stuffing.
- A large third-party repo is copied wholesale when a small internal implementation is enough.
- The integration forces a Node runtime into the existing Python app without a clear benefit.
- We remove existing fail-closed cost/duplicate protections to make the happy path simpler.

A technically working demo that violates these conditions should be treated as a failed architecture.

---

## 15. Implementation phases

### Phase 0 — live contract verification

Before production code changes:

1. Read current Higgsfield docs/OpenAPI.
2. Verify the official Python SDK version available from PyPI.
3. Verify credentials against the API.
4. Check current balance.
5. Probe model availability without paid generation where possible.
6. Verify estimate endpoints/behavior.
7. Verify upload flow.
8. Record a small initial verified capability registry.

Deliverable: a versioned list of models we are willing to use.

### Phase 1 — official SDK adapter

1. Add `higgsfield-client`.
2. Build a small internal adapter.
3. Map existing Content Engine credentials into the SDK without exposing them.
4. Normalize provider statuses/errors.
5. Preserve the current uncertain-submission safety rule.
6. Add adapter tests.

No user-facing model router yet.

### Phase 2 — capability registry + validation

1. Add verified model metadata.
2. Add local parameter validation.
3. Add preflight.
4. Add model health/disable switch.
5. Add version/verification date logging.

### Phase 3 — Creative Director + prompt compiler

1. Define Pydantic structured creative brief.
2. Add intent extraction using the existing OpenAI model.
3. Merge Content Engine context safely.
4. Add model-specific prompt compilers.
5. Add tests with fixed inputs/snapshots.
6. Keep a manual editable prompt/brief escape hatch.

### Phase 4 — model router + cost policy

1. Route by capabilities first.
2. Score remaining models by quality/speed/cost intent.
3. Validate generated parameters.
4. Estimate cost.
5. Apply automatic-run vs approval threshold.
6. Persist router decision.

### Phase 5 — async completion + webhook

1. Add webhook endpoint.
2. Authenticate/verify according to current Higgsfield documentation.
3. Make webhook processing idempotent.
4. Download completed asset to R2.
5. Keep safe polling fallback.
6. Add cleanup/recovery command for stale active jobs.

### Phase 6 — Remote MCP

1. Add a small MCP server package/process in this repo.
2. Reuse engine service functions; no duplicated business logic.
3. Add private authentication.
4. Expose the minimal tool set.
5. Return generation ID immediately when work is asynchronous.
6. Let ChatGPT query/wait through `get_generation`.
7. Connect the remote MCP to ChatGPT.

### Phase 7 — Content Engine UI upgrade

1. Replace hard-coded model behavior with "Auto".
2. Add economy/balanced/quality intent.
3. Show cost when policy requires approval.
4. Show router/model details only as optional diagnostics.
5. Add richer status/progress.

### Phase 8 — end-to-end verification

Run one controlled real T2V and one I2V generation with a low spend cap.

Then verify ChatGPT remote MCP end-to-end.

Only after these pass should the old direct Higgsfield path be removed.

---

## 16. Testing strategy

Tests must cover failure paths at least as thoroughly as success paths.

Required categories:

- model capability matching
- unsupported duration/resolution
- invalid reference input
- router budget limits
- cost estimate missing
- cost exceeds limit
- duplicate request token
- provider timeout before request ID
- provider timeout after request ID
- 429
- 402 / insufficient credits
- 4xx bad input
- 5xx uncertain submission
- terminal failure
- NSFW
- cancellation
- duplicate webhook
- stale active job recovery
- R2 download failure after provider completion
- ownership violation via MCP
- disabled model
- registry version changes

Use mocked SDK calls for normal CI.

Real paid API tests must never be part of an automatic CI loop.

---

## 17. Deployment plan

### Existing web

Keep the current Content Engine deployment unchanged while the new subsystem is built behind feature flags.

### MCP process

Deploy from this repository as a separate process/service.

The process must:

- import the same `engine` service layer
- use the same database
- use the same R2
- use the same Higgsfield credentials
- have its own MCP authentication secret
- expose only HTTPS

No separate media database.

### Feature flags

Suggested:

- `HIGGSFIELD_CREATIVE_ENGINE_ENABLED=false`
- `HIGGSFIELD_MCP_ENABLED=false`
- `HIGGSFIELD_WEBHOOK_ENABLED=false`
- `HIGGSFIELD_AGENT_EXPERIMENT=false`

Promote one layer at a time.

---

## 18. Rollback

Rollback must be simple.

Until the new path is fully verified:

- keep the existing Content Engine UI behavior available
- do not migrate/delete existing generation rows
- do not change historical provider IDs
- gate new routing behind a feature flag
- retain ability to disable individual models instantly

If the SDK/router/MCP proves unstable, disable the new feature flag. Existing content, media and Postiz workflows must continue to work.

---

## 19. Definition of done

This project is done when Jonas can write in ChatGPT:

> Animate this image into a premium Golfkuponger reel. Slow cinematic push-in, morning atmosphere, vertical, keep the clubhouse and signs unchanged.

and, without manually selecting Higgsfield models/endpoints:

- ChatGPT invokes the Content Engine MCP
- Content Engine constructs a structured brief
- a verified compatible model is selected
- parameters are validated
- cost policy is applied
- exactly one paid job is submitted
- the request ID is persisted
- progress can be checked
- the completed MP4 is copied to R2
- the video is returned through the ChatGPT workflow
- the generation is visible in Content Engine history
- all provider/user/company ownership remains intact

The same internal code path must also power the equivalent action in the Content Engine UI.

That is the target architecture.
