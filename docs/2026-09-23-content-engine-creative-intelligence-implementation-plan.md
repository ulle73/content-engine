# Content Engine — Creative Intelligence Implementation Plan

**Date:** 2026-09-23  
**Status:** ACTIVE MASTER CHECKLIST  
**Repository:** `ulle73/content-engine`  
**Companion spec:** `docs/2026-09-23-content-engine-creative-intelligence-delta-spec.md`

> This is the execution ledger for the missing Creative Intelligence capabilities.  
> A future AI must update this file after every completed logical task.  
> **Never mark a checkbox complete merely because code exists. Mark it complete only when its stated acceptance criteria and verification requirements are satisfied.**

---

# 0. Operating rules for every future AI

## 0.1 Source of truth

Before changing code:

- read this file,
- read the DELTA spec,
- inspect current branch heads,
- inspect the current Render deployment,
- inspect the current implementation of files touched by the next task,
- re-check current official provider/model documentation for any model-specific work.

Do not assume a dated model capability is still current.

## 0.2 Preserve existing architecture

Do not rebuild or replace without a demonstrated reason:

- `CreativeBrief`
- `CreativeContext`
- `CreativePlan`
- `route_model()`
- existing model registry
- `MediaGeneration`
- `MediaAsset`
- R2 storage
- current paid-generation review flow
- UNKNOWN/at-most-once paid-submit protection
- Prompt Library safety boundary
- MCP/OAuth
- current content-performance learning
- editorial/performance separation

All new work should be additive and backwards compatible unless this ledger explicitly records a justified migration.

## 0.3 Definition of DONE

A task may be changed from `[ ]` to `[x]` only when all applicable items are true:

- implementation exists,
- focused tests pass,
- full regression suite passes or any known unrelated blocker is documented,
- migration drift is clean when schema changed,
- security/ownership boundaries are tested,
- cost/idempotency invariants are preserved,
- UI is visually/functionally checked when UI changed,
- provider contract is verified against current official documentation when provider behavior changed,
- live verification is completed when the task claims production behavior,
- this ledger records commit/deploy/evidence.

If a paid generation is required for final provider verification, stop before payment unless the user has explicitly authorized that paid generation.

## 0.4 Required task closeout format

Every completed task must add/update:

```text
Status:
Files changed:
What changed:
Tests:
Official/provider evidence:
Live verification:
Known limitations:
Commit:
Deploy:
Next exact task:
```

Do not delete prior evidence.

---

# 1. Current verified baseline

Baseline before this implementation program:

- Current shared branch state after documentation sync: `main` and `feature/chatgpt-content-engine-mcp` are synchronized.
- Existing Creative Engine already includes structured brief/context/plan, model routing, versioned registry, prompt compilation, start-image I2V, Prompt Library, generation preflight, cost approval, R2 persistence, MCP and closed-loop idea/copy learning.
- Video routing has architecture for choice but currently only one enabled verified video model in the registry.
- Current first-class I2V reference is `MediaGeneration.source_asset`.
- No first-class end-frame path exists.
- No trusted Creative Recipe layer exists.
- No project-level cinematic sequence model exists.
- No media-specific recipe/model performance-learning loop exists.

The DELTA spec contains the full verified gap analysis.

---

# 2. Phase A — Trusted Creative Recipe foundation

Goal: create a trusted, structured production-method layer without weakening Prompt Library safety.

## Task A1 — Define trusted CreativeRecipe domain model

- [x] Add a versioned provider-neutral `CreativeRecipe` domain object/registry.
- [x] Keep trusted recipes separate from user Prompt Library entries.
- [x] Support at minimum:
  - stable recipe id,
  - version,
  - name/description,
  - supported goals/formats,
  - required/optional reference roles,
  - camera/motion strategy,
  - continuity strategy,
  - negative constraints,
  - default duration/format intent,
  - draft/final policy,
  - compatible model families/capabilities,
  - evaluation criteria,
  - evidence sources,
  - verified date,
  - confidence/evidence level.
- [x] Recipe provenance is persisted into `MediaGeneration.parameters.creative`.
- [x] Existing jobs without recipe metadata remain readable.

### Acceptance criteria

- A normal existing image/video request still plans successfully without explicitly choosing a recipe.
- A known recipe can be selected deterministically.
- Unknown/untrusted recipe IDs fail safely.
- Raw Prompt Library text cannot become a trusted recipe instruction.
- Recipe id + version appear in safe generation diagnostics/provenance.

### Required tests

- recipe registry validation,
- invalid recipe rejection,
- fallback/no-recipe compatibility,
- Prompt Library isolation,
- provenance serialization.

### Closeout

Status: DONE — code + focused domain verification; repository CI is externally blocked before test execution by the already-known GitHub Actions billing/spending restriction. No application test step ran in workflow run `35923242551`; both jobs failed within ~2 seconds. This infrastructure blocker is unrelated to the code change and remains explicitly unresolved.  
Files changed: `engine/creative_core.py`, new `engine/creative_recipes.py`, `engine/creative_director.py`, `engine/media.py`, focused tests in `engine/test_creative_core.py` and `engine/test_media.py`.  
What changed: Added frozen/versioned trusted `CreativeRecipe` + `RecipeSelection`, canonical reference-role vocabulary, immutable indexed recipe registry, generic compatibility recipes for existing image/video paths, fail-closed explicit recipe resolution, and persisted recipe provenance. Existing Prompt Library remains untrusted and cannot select a recipe. No DB migration and no provider behavior change.  
Tests: Local Python 3.13 / Pydantic 2.13 focused smoke PASS for registry construction, JSON serialization, START_IMAGE role serialization, default video recipe, explicit/fail-closed recipe resolution and incompatible recipe rejection. Static integration review confirms `build_plan()` resolves recipes independently of Prompt Library inspiration and `create_job()` persists recipe id/version. New Django regression tests were added but GitHub-hosted execution is blocked by the account-level Actions restriction before steps start.  
Official/provider evidence: Not applicable; A1 changes no provider contract.  
Live verification: Not required for this provider-neutral, non-UI foundation. Render was not changed.  
Known limitations: Automatic semantic recipe selection is A2. Model-specific recipe compatibility/routing is B1/B3. Full Django/PostgreSQL CI must be rerun when GitHub Actions billing is restored.  
Commit: `b54d74e5b71cf2fd9247ebf1ae7c92e5175bd65b` (A1 branch head before merge)  
PR: #35  
Deploy: none  
Next exact task: B1

---

## Task A2 — Recipe selection from loose natural-language briefs

- [ ] Extend the existing Creative Director to select an appropriate recipe from a loose brief.
- [ ] Do not add a second router.
- [ ] Recipe selection must consider purpose/format, motion intent, reference needs and platform.
- [ ] Explicit user recipe choice overrides automatic recipe selection when valid.
- [ ] Store reason codes for selection.

### Acceptance criteria

Examples route sensibly:

- “premium orbit around a product” → orbit/product recipe,
- “bridge these two frames” → transition-bridge recipe,
- normal still-image request → existing generic image path,
- ordinary social video → no forced scroll recipe.

### Tests

- deterministic recipe-selection fixtures,
- explicit override,
- unsupported recipe/media combination,
- no regression to current generic flow.

### Closeout

Status: NOT STARTED  
Commit: —  
Deploy: —  
Evidence: —

---

# 3. Phase B — Model-specific knowledge and real multi-model routing

Goal: make existing Auto routing meaningful for video and grounded in current official guidance.

## Task B1 — Extend model intelligence with prompt/reference profiles

- [x] Extend current `ModelIntelligence` or add an adjacent trusted `ModelPromptProfile`.
- [x] Represent model-specific:
  - supported reference roles,
  - start/end frame support,
  - audio support,
  - durations,
  - resolutions,
  - aspect-ratio behavior,
  - prompt section strategy,
  - known constraints/failure modes,
  - compatible recipe capabilities,
  - official evidence URL/date/version.
- [x] Keep capability facts separate from account availability.
- [x] Account availability remains provider preflight/estimate truth.

### Acceptance criteria

- Compiler can ask the selected model profile how to structure a request.
- Unsupported combinations fail before provider spend.
- Stale/unverified entries cannot silently become Auto candidates.

### Tests

- evidence-level gating,
- capability mismatch,
- prompt-profile lookup,
- registry-version provenance.

### Closeout

Status: DONE — provider-neutral profile/capability foundation implemented and reviewed. GitHub-hosted Django/PostgreSQL execution remains blocked by the known account-level Actions billing/spending restriction before application steps start. Latest run `35924160444` completed as failure within ~5 seconds; both `verify` and `postgres` jobs failed before normal test execution.  
Files changed: `engine/creative_core.py`, `engine/creative_registry.py`, `engine/creative_director.py`, `engine/test_creative_core.py`. No migration.  
What changed: Extended the single existing `ModelIntelligence` with fail-closed versioned model profiles, mode-specific `ModeReferenceContract`, canonical reference-role capability checks, aspect-ratio behavior, prompt sections, negative-prompt capability, known constraints and recipe capabilities. New profiles default to `stale` and cannot enter Auto routing until explicitly verified and complete. Prompt compilation is now driven by trusted `prompt_strategy` + `prompt_sections`, not provider name. `ModelSelection` persists `profile_version` and `evidence_version` for reproducibility.  
Tests: Focused Python 3.13 contract smoke PASS for verified/stale gating, complete per-mode contracts, overlapping-role rejection logic, START_IMAGE support, END_IMAGE non-support for current Kling, and serialized profile/evidence provenance. Added Django regression tests for profile lookup, stale/incomplete exclusion, reference-role preflight and profile-driven compiler sections. Static branch-head verification confirms no accidental literal escape sequences remain after a connector patch was caught and corrected before merge.  
Official/provider evidence: OpenAI GPT-Image-2 model page + image-generation guide rechecked 2026-09-23: image input/output supported, high-fidelity image input, snapshot `gpt-image-2-2026-04-21`, recommended 1K sizes, and fixed high input fidelity for GPT-Image-2. Higgsfield Kling 2.5 Turbo Pro T2V/I2V docs rechecked 2026-09-23: 5/10 second durations, negative_prompt capability, no sound/aspect_ratio field, and `image_url` required for I2V. Public docs are capability evidence only; server account availability remains estimate/preflight truth.  
Live verification: Not required; no provider payload or live behavior changed and Render was intentionally not deployed.  
Known limitations: Current provider adapter does not yet send Kling `negative_prompt`; B1 records verified capability only. Current app still has one source image relation; C1 introduces persisted typed multi-reference relations. No Seedance/new model is enabled until B2/B3. Full Django/PostgreSQL CI must be rerun when GitHub Actions billing is restored.  
Code branch head before checklist closeout: `bdc38763c872c64d85b2007a7fed2cbe7a20b820`  
PR: #36  
Deploy: none  
Next exact task: B2

---

## Task B2 — Re-audit current Higgsfield video models

- [x] Re-read current official Higgsfield model catalog/API docs at implementation time.
- [x] Verify exact current model IDs and request fields.
- [x] Verify Seedance variants relevant to:
  - image-to-video,
  - start/end frame,
  - continuity,
  - duration,
  - resolution,
  - audio,
  - current price-estimate endpoint behavior.
- [x] Record evidence in code metadata and this ledger.
- [x] Do not infer server-account access from public docs.

### Acceptance criteria

- Every newly enabled model has an official source and verification date.
- No undocumented parameter is introduced.
- The exact model path used by estimate/submit is unit-tested.

### Closeout

Status: DONE — current provider-contract audit completed; no model enabled and no generation submitted.  
Artifact: `docs/2026-09-23-higgsfield-seedance-model-audit.md`.  
What was verified: Exact current API model paths and request schemas for Seedance 2.5 T2V/I2V/reference-to-video, Seedance 2.0 T2V/I2V/reference-to-video, shared authenticated estimate behavior, official Seedance continuity guidance, and Kling O3 First/Last Frame as an additional continuity candidate.  
Key B3 discoveries: Seedance duration is a range rather than the old fixed 5/10 tuple; endpoint/request capabilities differ by mode; Seedance defaults `generate_audio=true` while Content Engine defaults audio intent to none; Seedance 2.5 T2V exposes aspect ratio while its I2V API currently does not; exact provider path therefore belongs in the mode contract rather than being inferred globally.  
Official evidence: Higgsfield `docs/llms.txt` source-priority guidance; billing/retention estimate contract; current model-specific Open Higgsfield API pages for Seedance 2.5, Seedance 2.0 and Kling O3; Higgsfield Seedance help center and 2.5 prompt guide.  
Account evidence: A read-only Higgsfield MCP `seedance` catalog query was attempted and failed with workspace read error `423`. This is neither positive nor negative evidence for Golfkuponger's dedicated server credential. Account availability remains fail-closed until Content Engine's authenticated estimate succeeds.  
Tests: Documentation/contract audit only; no runtime code changed in B2. B3 must add unit tests for every exact endpoint path and payload before enabling models.  
Deploy: none  
Next exact task: B3

---

## Task B3 — Add verified Seedance/multi-model entries to existing router

- [x] Add only currently verified compatible models.
- [x] Keep Kling if still valid.
- [x] Update scoring to consider:
  - recipe compatibility,
  - required reference roles,
  - quality,
  - speed,
  - cost,
  - audio,
  - complexity.
- [x] Preserve current `route_model()` as the single Auto router.
- [x] Add reason codes showing why a model won.

### Acceptance criteria

Auto can genuinely choose between at least two verified video models for different jobs.

Example:

- generic video may choose one model,
- continuity + END_IMAGE must choose only a model that supports it.

### Tests

- multi-model candidate scoring,
- required end-frame routing,
- fallback when preferred model is disabled,
- economy/quality behavior,
- unsupported request fails before provider call.

### Closeout

Status: DONE — verified multi-model routing and mode-aware Higgsfield request compilation implemented on the existing single router. Hosted GitHub tests remain externally blocked before application steps; latest branch-head workflow `35925500304` failed in ~6 seconds with **0 steps** in both `verify` and `postgres`, matching the documented Actions account billing/spending restriction rather than an application test failure.  
Files changed: `engine/creative_core.py`, `engine/creative_registry.py`, `engine/creative_director.py`, `engine/media_providers.py`, `engine/media_views.py`, `templates/engine/media.html`, `engine/test_creative_core.py`, `engine/test_media.py`. No migration.  
What changed: Evolved B1's mode reference contract into backwards-compatible `ModeRequestContract` with exact provider endpoint, fixed/range duration, resolution options, mode-specific aspect-ratio behavior, explicit audio parameter/default, output-format support and canonical media-field mapping. Added current verified Kling 2.5 Turbo Pro, Seedance 2.5 and Seedance 2.0 T2V/I2V profiles. Auto routing now applies hard capability filtering before scoring. Balanced/economy generic video remains Kling; quality can select Seedance 2.5; >10s selects a capable long-duration model; native audio routes away from Kling; explicit 1080p/4K routes to Seedance 2.0. START+END canonical roles already cause the router to exclude Kling and select a first/last-frame-capable Seedance mode, while persistence/upload of END_IMAGE remains C1/C2.  
Provider compilation: New jobs persist exact `provider_model`; Seedance 2.5/2.0 receive only audited mode-specific fields. Seedance audio is explicitly set false unless requested, preventing provider default `generate_audio=true` from violating Content Engine intent. Seedance 2.5 T2V sends supported aspect ratio; 2.5 I2V deliberately sends no aspect-ratio field. Existing jobs retain the legacy root+mode fallback. Estimate and paid submit reuse the same compiled body/path. Current Kling body remains only `prompt + duration`.  
Prompt compilation: Added `seedance_structured` using current official section guidance (GLOBAL STYLE, SCENE, optional FIRST FRAME/BLOCKING, CAMERA, PHYSICS, LIGHTING, AUDIO, BRAND CONTEXT) without adding scroll-specific continuity rules prematurely.  
Tests added: balanced 8s→Kling/10s normalization; economy→Kling; quality 8s→Seedance 2.5/exact 8s; 20s→Seedance 2.5; native audio→Seedance; explicit 4K→Seedance 2.0; disabled preferred model fallback; unsupported 4K+4:5 fails before provider; canonical START+END routes only to an END_IMAGE-capable model; exact Seedance endpoint/range metadata; I2V START/END field mapping; resolution/audio parsing; Seedance T2V estimate payload; Seedance I2V source upload with no unsupported aspect ratio; audio true only when requested; Seedance 2.0 4K; estimate/paid-submit body identity; existing Kling submit JSON regression.  
Static/branch verification: PR #38 is mergeable. Branch-head code review checked registry contracts, route decisions, compiler paths, legacy fallback and safe UI diagnostics. A too-broad Seedance 2.0 `output_format` assumption was caught against the B2 audit and removed before closeout. Container could not clone the private repository because this runtime has no external DNS/network; no false local Django-pass claim is made.  
Official/provider evidence: `docs/2026-09-23-higgsfield-seedance-model-audit.md`, sourced from current Higgsfield model-specific API docs/help-center/prompt guide and shared estimate contract. Public capability evidence is still distinct from the dedicated Golfkuponger server account.  
Live verification: intentionally deferred. No Render deploy and no provider estimate/generation in B3. D2 remains the first authenticated account-scoped non-billable provider verification.  
Known limitations: Actual END_IMAGE persistence/upload is C1/C2. Seedance Reference-to-Video and Kling O3 remain disabled. Expert model override is B4. Full Django/PostgreSQL suite must be rerun when GitHub Actions billing is restored.  
PR: #38  
Deploy: none  
Next exact task: C1

---

## Task B4 — Expert model override

- [x] Add `Model: Auto` as default.
- [x] Add advanced override for verified eligible models.
- [x] Expose only controls supported by selected model.
- [x] Prevent invalid duration/resolution/reference combinations locally.
- [x] Add same override capability to MCP in a bounded safe form.
- [x] Persist manual override provenance.

### Acceptance criteria

- Normal user never needs to choose a model.
- Expert user can force a valid verified model.
- Invalid override cannot reach paid submit.
- Auto behavior remains unchanged when no override is supplied.

### Tests

- UI form validation,
- MCP validation,
- ownership/security unchanged,
- explicit override provenance.

### Closeout

Status: DONE — B4 shipped with F3 using the existing single Creative Director/router. Auto remains default; manual override is allow-listed to verified request-compatible models and fails before provider calls for invalid reference/duration/resolution/aspect/audio combinations.  
Tests: included in CI `36011305597` across Creative Director, Media/AI Studio, MCP and Sequence paths; normal + PostgreSQL suites green.  
Commit: `c70775797ce57e348fb78ad1caf3a19122296307`  
Deploy: `dep-daqj1d0u01pc738blq5g` — live  
Evidence: `docs/2026-09-24-sequence-workspace-f3-clip-controls-plan.md`; current Higgsfield model contracts rechecked 2026-09-24.

---

# 4. Phase C — Canonical media reference system

Goal: evolve beyond one `source_asset` without breaking existing I2V.

## Task C1 — Design/add canonical MediaGenerationReference relation

Recommended shape: additive relation rather than multiplying provider-specific columns.

- [x] Add canonical reference roles:
  - START_IMAGE
  - END_IMAGE
  - PRODUCT_REFERENCE
  - CHARACTER_REFERENCE
  - LOCATION_REFERENCE
  - STYLE_REFERENCE
  - VIDEO_REFERENCE
  - AUDIO_REFERENCE
- [x] Add ordered references where a model supports multiple refs.
- [x] Validate all assets belong to the same company.
- [x] Preserve `MediaGeneration.source_asset` compatibility for old jobs/current code.
- [x] Backfill or compatibility-map START_IMAGE from `source_asset` without destructive migration.
- [x] Provider-specific field names stay in provider adapter only.

### Acceptance criteria

- Existing source-image jobs still render and poll correctly.
- A new job can persist multiple typed references.
- Cross-company asset injection is impossible.
- Old generation rows require no destructive rewrite.

### Tests

- migration,
- unique/order constraints,
- company ownership,
- compatibility with source_asset,
- serialization.

### Closeout

Status: DONE — canonical provider-neutral generation references implemented and verified against both the normal Django suite and PostgreSQL suite.  
Files changed: `engine/models.py`, `engine/media_references.py`, `engine/media.py`, `engine/mcp_operations.py`, `engine/migrations/0014_media_generation_references.py`, `engine/test_media.py`, `engine/test_mcp_media.py`.  
What changed: Added additive `MediaGenerationReference` rows keyed by generation + canonical role + ordered position. References retain safe `asset_snapshot` provenance even if a terminal unused preview later expires. Active reference assets are protected from cleanup. New legacy `source_asset` jobs are mirrored to canonical START_IMAGE, migration 0014 backfills historical source assets non-destructively, and runtime fallback still supports rows without a canonical reference. Provider field names remain confined to the existing provider/model contracts; C1 does not change provider payloads.  
Tests: CI run `35971227154` passed full `python manage.py test` plus full `python manage.py test engine operator_bridge --settings=engine.postgres_test_settings`. The same run also passed `makemigrations --check --dry-run`, migration apply/check, Django checks, static collection and MCP import. Focused coverage includes source→START_IMAGE mirroring, multiple ordered references, immutable occupied slots, database uniqueness, cross-company rejection through service and direct model save, active-reference cleanup protection, terminal snapshot preservation, legacy source fallback and safe MCP serialization without storage keys.  
Baseline note: Initial C1 CI exposed two pre-existing regressions from the prior multi-model merge. They were isolated and fixed separately in PR #41, whose full normal + PostgreSQL CI run `35970925974` passed before C1 was rerun.  
Security/ownership: Same-company validation exists in both service-level creation and model validation; START/END require non-logo images; VIDEO_REFERENCE requires video; AUDIO_REFERENCE remains reserved until `MediaAsset` supports audio.  
Live/provider verification: Not applicable to C1 provider behavior; no provider payload changed, no paid call made and no Render deployment is claimed. C2 will wire END_IMAGE into UI/MCP/planning/provider payloads.  
Commit before checklist closeout: `1c0a67794e204890c155574a78cf1466c7f09f07`.  
PR: #40  
Deploy: none  
Known limitation: Typed references are now persisted, but only START_IMAGE is automatically created by the current job flow. END_IMAGE and other roles become user/job inputs in C2.  
Next exact task: C2 — End-frame support end-to-end.

---

## Task C2 — End-frame support end-to-end

- [x] AI Studio can select/display/remove an END_IMAGE.
- [x] MCP preview/generate can accept an end asset id.
- [x] End asset is company-scoped.
- [x] CreativeBrief/plan sees END_IMAGE capability requirement.
- [x] Router chooses only compatible models.
- [x] Estimate uploads/includes the actual end image.
- [x] Paid submit reuses the reviewed exact inputs.
- [x] Provenance includes start/end asset IDs and hashes where safe.
- [x] Job review page clearly shows both anchors.

### Acceptance criteria

A non-billable preview for a start→end job shows:

- selected recipe,
- selected model,
- exact start asset,
- exact end asset,
- duration/resolution,
- compiled prompt,
- provider estimate or explicit provider preflight failure.

No paid job is started merely by previewing.

### Tests

- UI,
- MCP,
- provider body,
- estimate,
- paid-start immutable reviewed inputs,
- unsupported model rejection,
- cross-company reference rejection.

### Closeout

Status: DONE — generic end-frame support is implemented end-to-end on top of C1 canonical references.  
Files changed: `engine/creative_director.py`, `engine/creative_registry.py`, `engine/media_references.py`, `engine/media.py`, `engine/media_providers.py`, `engine/media_views.py`, `engine/operator_media.py`, `engine/mcp_server.py`, `templates/engine/media.html`, `templates/engine/media_asset.html`, `templates/engine/media_job.html`, `engine/test_media.py`, `engine/test_mcp_media.py`.  
What changed: AI Studio and MCP/operator flows now accept a company-scoped END_IMAGE together with START_IMAGE. CreativeBrief stores the canonical END_IMAGE role, capability routing excludes models without verified first/last-frame support, Seedance provider contracts map START_IMAGE→`image_url` and END_IMAGE→`end_image_url`, and the review page displays the exact anchor pair. Seedance prompt compilation adds an explicit END FRAME section when a reviewed end frame exists.  
Paid-start safety: preview stores a SHA-256 signature over the reviewed canonical reference set (role, position, asset id, content hash, availability). `start_reviewed_job` fails closed if the anchor set differs before paid start, so reviewed start/end frames cannot silently change between estimate and submission. Existing ten-minute review expiry, approved max USD and at-most-once paid submit protections remain intact.  
Provenance: start/end asset IDs and hashes are available through safe canonical reference diagnostics without storage keys or provider upload URLs.  
Tests: CI run `35973388785` passed the full normal Django suite and full PostgreSQL suite after the end-frame prompt fix. The run also passed `makemigrations --check --dry-run`, migration apply/check, Django checks, static collection and MCP import. Focused tests cover start+end routing, canonical persistence, same-company validation, provider `image_url`+`end_image_url` body, review-signature mutation blocking, AI Studio selection/submission/review and operator/MCP end-frame flow.  
Provider behavior: no paid generation was performed. Provider mapping is verified by contract/unit tests; live non-billable provider preflight remains D2.  
CI note: first C2 run `35972272306` had one focused failure: the end frame was routed correctly but the compiled Seedance prompt lacked the explicit `END FRAME:` section. That was corrected by declaring/compiling the END_FRAME prompt section and the complete rerun passed.  
Commit before checklist closeout: `1ab21376316e0690d1bbf7a1a6d5b2d76a2e1a47`.  
PR: #42  
Deploy: none yet  
Known limitation: C2 provides generic end-frame infrastructure only. It does not yet impose scroll-specific continuity/no-cut rules; those belong to D1.  
Next exact task: D1 — implement the trusted `scroll_transition_bridge` recipe.

---

# 5. Phase D — First proven continuity workflow

Goal: prove the new architecture with the smallest useful cinematic feature before building a timeline.

## Task D1 — Implement `scroll_transition_bridge` recipe

- [x] Trusted recipe exists.
- [x] Requires START_IMAGE + END_IMAGE.
- [x] Enforces one continuous shot.
- [x] Includes continuity constraints.
- [x] Uses model-specific prompt profile rather than one universal prompt.
- [x] Prioritizes continuity over spectacle.
- [x] No hard cuts/morphing/new objects unless explicitly requested.
- [x] Appropriate audio default is explicit.

### Acceptance criteria

Compiled prompt is materially different and model-appropriate compared with generic video generation.

### Tests

- recipe requirements,
- compiled prompt structure,
- negative constraints,
- no raw Prompt Library injection,
- correct router capability requirement.

### Closeout

Status: DONE — trusted evidence-backed `scroll_transition_bridge` is implemented and isolated from generic video behavior.  
Files changed: `engine/creative_recipes.py`, `engine/creative_director.py`, `engine/media.py`, `engine/test_creative_core.py`, `engine/test_media.py`.  
What changed: Added recipe v1.0.0 with required START_IMAGE+END_IMAGE, continuity-first camera/motion policy, explicit no-cut/single-shot format mode, reverse-scrub coherence, continuity/geometry/lighting constraints, no morphing/object duplication/disappearance/new-object rules, draft→final metadata and official evidence URLs verified 2026-09-24. `create_job(..., recipe_id=...)` can now invoke a trusted recipe while generic jobs remain on `generic_video`.  
Model behavior: Recipe routing still uses the existing single router. Current verified capabilities select Seedance first/last-frame I2V; the recipe does not hard-code a provider endpoint. Seedance compilation emits model-specific FORMAT MODE, FIRST FRAME, END FRAME, CAMERA, PHYSICS/CONTINUITY/FORBID and explicit AUDIO sections.  
Generic isolation: Bridge policy is only added when the bridge recipe is selected. Generic Seedance video retains previous camera and `Avoid:` behavior and does not inherit FORMAT MODE or CONTINUITY sections.  
Prompt Library boundary: Raw Prompt Library text remains untrusted inspiration and cannot select/replace trusted recipe policy or inject raw instructions.  
Official/provider evidence: Rechecked 2026-09-24 against Higgsfield Seedance prompting guide, Seedance help center and Seedance 2.5 I2V API. Higgsfield explicitly recommends first/last-frame generation to bridge jerky cuts and prototyping at short 720p before final quality.  
Tests: Latest full CI run `35975587712` passed both normal Django and PostgreSQL suites. The same head passed schema/migration checks, Django checks, static collection and MCP import. Focused tests cover required reference roles, official recipe evidence, Seedance selection, start/end provider field mapping, no-cut/continuity/negative constraints, explicit silent audio, provenance persistence, Prompt Library isolation and generic-video isolation.  
Earlier CI note: initial D1 run failed only because a test expected lowercase `official` while the established enum serializes `OFFICIAL`; the test was corrected to use the canonical enum value.  
Commit before checklist closeout: `b54a8c57785bda750d4efcd04ae2f8df48afdea4`.  
PR: #43  
Deploy: none yet  
Known limitation: D1 is an explicit trusted recipe; automatic loose-prompt recipe selection remains A2. Production provider estimate remains D2.  
Next exact task: D2 — deploy current code and run one non-billable production start→end estimate.

---

## Task D2 — Non-billable production preflight for start→end

- [x] Deploy current code to Render.
- [x] Verify dedicated GK Higgsfield server credential works for estimate.
- [x] Verify actual provider accepts the selected model + both references for estimate.
- [x] Record exact returned model path and safe estimate metadata.
- [x] Do not substitute Jonas personal Higgsfield workspace.
- [x] Do not run paid generation merely to test credentials.

### Acceptance criteria

One production job reaches a valid reviewed/queued state with a real provider estimate and no provider generation id.

### Closeout

Status: DONE — production start→end preflight completed successfully without starting provider generation.  
Production commit: `2718f3e30df7a90a8dcf30388091f3002302de7c`.  
Render service: `content-engine-mcp`, branch `feature/chatgpt-content-engine-mcp`, Frankfurt.  
Credential isolation: Production code accepts only `HIGGSFIELD_API_KEY_GK` (+ optional GK secret). Generic/personal Higgsfield variables are ignored and readiness fails closed without the GK credential.  
Live provider evidence: Render emitted `D2_PREFLIGHT_OK` at 2026-09-24 09:34:59Z for token `d2-2026-09-24-4`. The real provider estimate selected `bytedance/seedance-2.5` with provider path `bytedance/seedance-2.5/image-to-video`, canonical references `START_IMAGE` + `END_IMAGE`, recipe `scroll_transition_bridge`, and safe estimate metadata `usd=1.6180`.  
Non-billable proof: job status remained `queued` and `provider_id_present=false`; no `start_reviewed_job`/generation submit occurred.  
Provider compatibility fix: Live diagnostics showed current Seedance 2.5 pricing is returned in the provider's token-based pricing shape rather than the previously assumed shape. PR #48 updated safe parsing for that current contract before the successful preflight.  
Operational hook: PR #45 added an env-gated one-time production preflight command that creates temporary anchors, uses the real `create_job → preview_job` path, logs only safe metadata, and removes its temporary run/assets. After the successful proof, `D2_HIGGSFIELD_PREFLIGHT_TOKEN` was set to `0` so future deploys do not repeat the preflight.  
Earlier diagnostics: PR #46 and PR #47 added safe diagnostics to identify the live estimate shape without exposing credentials or starting generation.  
Paid generation: none.  
Next paid gate: D3 remains BLOCKED until explicit authorization of the exact reviewed job and price.  
Next non-paid implementation task: E1 — Sequence domain/schema.

---

## Task D3 — One authorized paid continuity smoke test

- [ ] Only run after explicit user authorization of the exact reviewed job and price.
- [ ] Submit exactly once.
- [ ] Poll/reconcile through existing lifecycle.
- [ ] Persist output to R2.
- [ ] Verify generated asset is viewable.
- [ ] Confirm no duplicate provider request.
- [ ] Record actual provider/model/cost/result.

### Acceptance criteria

A real START_IMAGE → END_IMAGE clip completes through the production pipeline.

### Closeout

Status: BLOCKED UNTIL EXPLICIT PAID APPROVAL  
Commit: —  
Deploy: —  
Provider request: —  
Actual cost: —  
Result: —

---

# 6. Phase E — General Cinematic Sequence Engine

Goal: add a reusable project layer for reels, ads, product films and scroll experiences.

## Task E1 — Sequence domain/schema

Execution ledger: `docs/2026-09-24-sequence-engine-e1-implementation-plan.md`

- [x] Add `SequenceProject`.
- [x] Add `SequenceAnchor`.
- [x] Add `SequenceClip`.
- [x] Add clip/candidate version representation.
- [x] Link generated assets through existing `MediaAsset`.
- [x] Link generation jobs through existing `MediaGeneration`.
- [x] Company ownership enforced everywhere.
- [x] Non-destructive versioning.
- [x] No duplicated media storage system.

### Acceptance criteria

Can persist:

`K0 → Clip1 → K1 → Clip2 → K2`

with canonical shared K1.

### Tests

- schema constraints,
- ownership,
- delete/protect semantics,
- version promotion,
- existing media compatibility.

### Closeout

Status: DONE — E1 is implemented, fully CI-verified and live on Render.  
Migration: `0015_sequence_engine_e1`  
CI: `35988142066` — normal + PostgreSQL suites green.  
PR: #50  
Commit: `65909657c1709af2411798dc8bb9de08a1bd1326`  
Deploy: `dep-daqfqu0u01pc73811is0` — migration applied, new instance healthy and live.  
Evidence: see the dedicated E1 execution ledger for schema, ownership, versioning and deletion/protection proof.

---

## Task E2 — Anchor Chain mode

Execution ledger: `docs/2026-09-24-sequence-engine-e2-anchor-chain-plan.md`

- [x] Canonical anchor can be start of one clip and end of previous clip.
- [x] Same exact asset identity is preserved.
- [x] Regenerating a clip does not mutate anchors.
- [x] Locked anchors cannot be silently replaced.

### Acceptance criteria

Regenerate Clip2 without changing Clip1, K1 or K2.

### Closeout

Status: DONE — non-destructive Anchor Chain execution is implemented and live.  
CI: `35995732844` — full normal + PostgreSQL suites green (299 tests).  
PR: #52  
Commit: `b883b2febb85a907d0cc7f34da523bb7f520bcee`  
Deploy: `dep-daqgvd67bikc738g27dg` — new instance healthy/live.  
Evidence: see the dedicated E2 execution ledger for exact K1 identity, idempotency, stale-anchor safety and provider-free prepare proof.

---

## Task E3 — Output Chain mode

Execution ledger: `docs/2026-09-24-sequence-engine-e3-output-chain-plan.md`

- [x] User can explicitly promote a generated final frame into the next start anchor.
- [x] System labels this as output-chain behavior.
- [x] It never silently replaces canonical anchors.
- [x] Provenance records source clip/frame.

### Closeout

Status: DONE — explicit Output Chain promotion is implemented and live.  
Migration: `0016_sequence_output_chain_provenance`  
CI: `35996836039` — full normal + PostgreSQL suites green.  
PR: #54  
Commit: `468b26e534ac69ed83332a876a5164e813b219ed`  
Deploy: `dep-daqh4rc9v7es73d5p03g` — migration applied, new instance healthy/live.  
Evidence: see the dedicated E3 ledger for final-frame extraction, provenance, downstream safety and provider-free promotion proof.

---

## Task E4 — Transition Bridge mode

Execution ledger: `docs/2026-09-24-sequence-engine-e4-transition-bridge-plan.md`

- [x] User can select an existing clip end/opening anchor pair.
- [x] System creates a bridge segment using the continuity recipe.
- [x] Existing clips remain untouched.

### Closeout

Status: DONE — separate Transition Bridge orchestration is implemented and live.  
Migration: `0017_sequence_transition_bridge`  
CI: `35998901727` — full normal + PostgreSQL suites green.  
PR: #56  
Commit: `820455e21f0a07c13c682e02b9588ed468fd4bb2`  
Deploy: `dep-daqhe1e7bikc738hg58g` — migration applied, new instance healthy/live.  
Evidence: see the dedicated E4 ledger for clip isolation, typed anchors, versioning, stale-anchor safety and provenance constraints.

---

# 7. Phase F — Sequence workspace / timeline UX

## Task F1 — Project workspace

Execution ledger: `docs/2026-09-24-sequence-workspace-f1-plan.md`

- [x] Dedicated sequence project page/workspace.
- [x] Visible anchor/clip order.
- [x] Clear locked/unlocked state.
- [x] Generation status per clip.
- [x] Candidate/version count.
- [x] No hidden destructive regeneration.

### Closeout

Status: DONE — read-safe Sequence project workspace is implemented and live.  
Migration: none  
CI: `36000378816` — full normal + PostgreSQL suites green.  
PR: #58  
Commit: `6a309fc1f461068eaa9a0e8f3bd1029994dc59c3`  
Deploy: `dep-daqhko3tqb8s73eh5rgg` — new instance healthy/live.  
Evidence: see the dedicated F1 ledger for navigation, ownership, timeline, version/status and read-safe UI proof.

---

## Task F2 — Anchor controls

Execution ledger: `docs/2026-09-24-sequence-workspace-f2-anchor-controls-plan.md`

- [x] Upload anchor.
- [x] Choose existing MediaAsset.
- [x] Generate anchor with AI.
- [x] Replace anchor.
- [x] Lock anchor.
- [x] Duplicate/version anchor where appropriate.
- [x] Show provenance.

### Closeout

Status: DONE — explicit, revisioned Anchor Controls are implemented and live.  
Migration: `0018_sequence_anchor_controls_f2`  
CI: `36004141029` — full normal + PostgreSQL suites green after PostgreSQL row-lock hardening.  
PR: #60  
Commit: `7c2568982e29f8aa449301a1734ed3585ffd3426`  
Deploy: `dep-daqi56gu01pc7388oqfg` — migration applied, new instance `g2ht2` healthy/live.  
Evidence: see the dedicated F2 ledger for revision history, stale invalidation, Media/upload/AI controls and paid-start reuse proof.

---

## Task F3 — Clip controls

Execution ledger: `docs/2026-09-24-sequence-workspace-f3-clip-controls-plan.md`

- [x] Generate one clip.
- [x] Regenerate one clip.
- [x] Compare versions.
- [x] Promote selected version.
- [x] Cancel current job safely.
- [x] Advanced model override per clip.
- [x] Show recipe/model/prompt/cost diagnostics.

### Closeout

Status: DONE — non-destructive V1/V2/V3 clip controls are implemented and live on the existing reviewed MediaGeneration lifecycle.  
Migration: none  
CI: `36011305597` — full normal + PostgreSQL suites green, including B4/F3/MCP/media regressions.  
PR: #62  
Commit: `c70775797ce57e348fb78ad1caf3a19122296307`  
Deploy: `dep-daqj1d0u01pc738blq5g` — new instance `rwbm5` healthy/live.  
Evidence: see the dedicated F3 ledger for candidate lifecycle, comparison, selection, cancellation, diagnostics and B4 override proof.

---

## Task F4 — Responsive/accessibility verification

- [x] Desktop visual review.
- [x] Mobile visual review.
- [x] Keyboard interaction.
- [x] No horizontal overflow.
- [x] Status and destructive actions accessible.
- [x] Existing AI Studio remains usable.

### Closeout

Status: DONE — responsive/accessibility hardening is merged and live without changing provider/payment behavior. Zero paid generations were started.

Files changed: `templates/engine/sequence_workspace.html`, `engine/static/css/sequence-screen.css`, `engine/test_sequence_ui.py`.

What changed: Mobile status rows now reflow into labeled cards instead of requiring a 660 px horizontal table; anchor actions span the mobile card; Sequence links/buttons/disclosures have an explicit visible keyboard focus ring; mobile Sequence controls use a minimum 44 px target; clip candidate/version/action semantics have contextual accessible labels and list/status structure; cancel is explicitly presented as a destructive action. Existing F3 generation/review/start/cancel/idempotency behavior was not changed.

Tests: Real Chromium audit run `36015265268` passed on branch head `22751ddc864c4fd87864e599b6dd420a7b2224e8` at 1440×1100 desktop and 390×844 mobile. It verified no document/body horizontal overflow, no mobile status-table horizontal scroll, anchor actions remaining inside the mobile card, visible keyboard focus with a 3 px outline, visible mobile Sequence controls at least 44 px high, and an AI Studio mobile smoke check. Screenshots were captured in artifact `10814551984` (`sequence-f4-screenshots`) and visually reviewed before merge. The temporary Playwright workflow/harness was removed before PR.

Full regression: PR #64 / GitHub Actions run `36015760333` passed both required jobs on exact head `70773d1f2f3ecec1dfc595818a5d9dcb3d76156c`: standard `verify` ran 367 tests in 31.854s, `OK (skipped=2)`; PostgreSQL ran 367 tests in 19.831s, `OK`. Migration drift, migrations, Django checks, MCP checks, collectstatic and import/compile gates also passed.

Official/accessibility evidence: W3C WCAG 2.2 Focus Visible and Target Size (Minimum) were rechecked for the F4 interaction baseline: https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html and https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html. F4 changes no provider contract, so no Higgsfield/provider revalidation was required.

Live verification: PR #64 was squash-merged as `0c15ae6077fbb4422e1869ea5a40cc1816ee26c7`. `feature/chatgpt-content-engine-mcp` was fast-forwarded to the same code commit. Render deploy `dep-daqjil17lnhs73d84qhg` for `content-engine-mcp` completed `live` on that exact commit. Render reported build success, `No migrations to apply`, `StreamableHTTP session manager started`, `Application startup complete`, and the new instance `srv-daj9cfgae00c7392t5c0-n6r7p` returned repeated `GET /healthz ... 200 OK` responses. Post-deploy log review found no `error` or `critical` entries.

Known limitations: F4 validates a deterministic seeded Sequence workspace plus AI Studio smoke behavior; it intentionally does not submit provider media or exercise a paid generation.

Commit: `0c15ae6077fbb4422e1869ea5a40cc1816ee26c7`  
PR: #64  
Deploy: `dep-daqjil17lnhs73d84qhg`  
Next exact task: G1 — Sequence planner.

---

# 8. Phase G — Automatic storyboard + anchor planning

Goal: make a loose prompt powerful enough for non-experts.

## Task G1 — Sequence planner

- [x] Loose brief can produce proposed:
  - number of scenes,
  - narrative progression,
  - recipe per scene/transition,
  - anchor descriptions,
  - required references,
  - model capability requirements,
  - draft/final plan.
- [x] Company facts remain grounded in current verified context.
- [x] User can edit before any paid media generation.

### Acceptance criteria

“Create a premium 4-scene Golfkuponger scroll story” creates a useful editable plan without requiring model knowledge.

### Closeout

Status: DONE — a versioned, editable and media-provider-free Sequence planning layer is merged and live.

Files changed: `engine/models.py`, `engine/migrations/0019_sequence_planner_g1.py`, new `engine/sequence_planner.py`, `engine/sequence_views.py`, `engine/urls.py`, `templates/engine/sequence_workspace.html`, `engine/static/css/sequence-screen.css`, and new `engine/test_sequence_g1.py`.

What changed: `SequenceProject` now persists a structured plan, revision number, text-planner usage metadata and generated timestamp. A loose project brief is converted into an editable Draft blueprint containing scene count, narrative progression, canonical anchor descriptions, scene purposes/narratives/durations, transition intent, trusted recipe metadata, required reference roles, verified model-capability requirements and currently eligible verified model ids. The text model proposes only story structure; trusted recipes, references and model eligibility are compiled locally from the existing Creative Recipe registry and existing single model-routing/capability architecture. No second router was added. Users can edit the structured plan and explicitly mark it Draft or Final before any media production. Trusted recipe/model fields are not accepted from edits and are rebuilt locally. Stale concurrent edits fail closed.

Grounding: The planner receives current `Company.profile` and `Company.current` as reference-only fact sources. Any explicit company fact reference returned by the planner must quote the corresponding current field verbatim; an unverified quote fails the whole plan before persistence. If the factual source is insufficient, the prompt instructs the planner to remain visual/generic and record an assumption instead of inventing a claim.

Tests: Final clean PR CI run `36063147228` passed on exact head `3d6b796f850738b395f86b8eb8e64a30bc7e3e1e`: standard `verify` ran 376 tests in 33.229s, `OK (skipped=2)`; PostgreSQL ran 376 tests in 20.804s, `OK`. Migration drift, migration execution, Django checks, MCP checks, collectstatic and import/compile gates also passed. G1 regression coverage verifies the required 4-scene/5-anchor acceptance example, exact fact-reference grounding, fail-closed scene-count mismatch, trusted-metadata preservation/recomputation on edit, optimistic revision locking, company scoping, editable UI and zero `MediaGeneration` creation/provider-media calls from planning.

UI verification: Real Chromium run `36062886046` passed on audit head `b9020502ccbd2dec8de8fa7e284a0e5ed3bf96a9` at 1440×1100 desktop and 390×844 mobile. It verified 4 scenes + 5 anchors, planner placement before production controls, no document/body horizontal overflow, one-column mobile scene reflow, 44 px primary mobile actions, and a real edit flow from Draft V1 to Final V2 after reload. Screenshot artifact: `10835271530` (`sequence-g1-screenshots`). The temporary Playwright workflow/harness was removed before the final clean CI run.

Official/provider evidence: G1 changes no image/video provider contract and enables no new media model, so no new Higgsfield contract verification was required. It reuses the existing trusted Creative Recipe/model capability registries and the existing structured OpenRouter text adapter. Provider media estimate/submit code is never called by the planner.

Live verification: PR #65 was squash-merged as `8324fd96c49ef3050ff940a05aee3fe045c530fb`. `feature/chatgpt-content-engine-mcp` was fast-forwarded to the same code commit and Render deploy `dep-daqpjhvlk1mc73ekupl0` completed `live` on that exact commit. Render reported build success; new instance `srv-daj9cfgae00c7392t5c0-8mr4k` applied `engine.0019_sequence_planner_g1... OK`, started the StreamableHTTP session manager and Uvicorn successfully, and returned `GET /healthz ... 200 OK`. Post-startup log review found no `error` or `critical` entries. Zero paid media generations or media-provider estimates were started for G1.

Known limitations: G1 stores and edits the production blueprint only; it intentionally does not materialize proposed anchors or create clips. AI anchor materialization is G2. The planner's trusted recipe policy is deterministic from Sequence format for this workflow; broader automatic semantic recipe selection from arbitrary loose media briefs remains the separate A2 task. Company fact references are mechanically source-validated, while the planner prompt is also responsible for avoiding unsupported factual claims elsewhere in purely visual narrative text.

Commit: `8324fd96c49ef3050ff940a05aee3fe045c530fb`  
PR: #65  
Deploy: `dep-daqpjhvlk1mc73ekupl0`  
Next exact task: G2 — AI anchor generation.

---

## Task G2 — AI anchor generation

- [x] Generate proposed anchors using existing image-generation pipeline.
- [x] Preserve company/product references when required.
- [x] Allow user replacement/upload.
- [x] Do not start video generation until required anchors exist.

### Closeout

Status: DONE — G1 blueprint anchors can now be materialized safely at exact canonical K positions through the existing Media/image lifecycle, and Sequence video is fail-closed until all anchors required by the current plan exist.

Files changed: `engine/models.py`, `engine/migrations/0020_sequence_ai_anchors_g2.py`, `engine/sequence_planner.py`, `engine/sequence.py`, `engine/sequence_views.py`, `engine/media.py`, `engine/urls.py`, `templates/engine/sequence_workspace.html`, `templates/engine/media_job.html`, `templates/engine/media_asset.html`, `engine/static/css/sequence-screen.css`, and new `engine/test_sequence_g2.py`.

What changed: Planned anchors are materialized by exact `target_position` rather than the old next-free-position behavior. Planned AI targets persist the plan revision and a complete anchor snapshot, so a target created for one K position or an older blueprint cannot later be applied to a different/current anchor. Idempotency tokens are also bound to planned position, plan revision, snapshot and source reference. Manual Media selection and upload reuse the existing canonical anchor replacement/revision/stale-history behavior. The workspace shows per-K materialization status and exposes explicit AI review, Media and upload actions.

Reference preservation: G1 anchor proposals can now declare bounded `company` and/or `product` exact-reference requirements plus an editable reference note. Product-preservation requires a real company-scoped image reference and reuses the existing image-to-image source path while storing typed `PRODUCT_REFERENCE` provenance. Company identity reuses the official deterministic logo path when available; otherwise a company reference image is required. A combined company+product exact requirement without an official logo fails closed because one untyped source image must not silently stand in for two distinct exact references. Typed reference changes refresh the non-billable review signature before any paid start.

Video gate: `prepare_anchor_chain_version()` now refuses to prepare Sequence video while any current planned K position is missing. The same readiness check is also enforced centrally inside `start_reviewed_job()` immediately before a reviewed Sequence video could reach the provider, and the exact canonical clip references are rechecked there. UI disablement is therefore only an ergonomic layer, not the security/cost boundary.

Tests: Final clean PR CI run `36105689204` passed on exact head `95d9c2dc60409d3539a231efc0662bc503d724f6`: standard `verify` ran 386 tests in 33.515s, `OK (skipped=2)`; PostgreSQL ran 386 tests in 20.764s, `OK`. Migration drift, `0020` migration execution, Django checks, MCP checks, collectstatic and compile/import gates also passed. G2 regression coverage includes exact out-of-order K materialization, required product reference + typed provenance, official-logo company preservation, stale-plan apply rejection, exact planned AI apply, position-scoped idempotency, cross-company project/asset rejection, pre-generation video blocking and a second central paid-start readiness check.

UI verification: Real Chromium run `36105335619` passed with desktop 1440×1100 and mobile 390×844. The audit seeded K0/K1 plus a missing K2 and verified `2/3 klara`, the explicit video lock, disabled clip preparation, no horizontal overflow and one-column mobile materialization cards with ≥44 px disclosure targets. It then selected an existing Media image for K2 in the browser, reloaded, verified `Alla 3 anchors klara`, canonical K2 preview, removal of the video lock and enabled clip preparation. Screenshot artifact: `10850399992` (`sequence-g2-screenshots`), digest `sha256:7cc128d05084b144e79519958606562bde9894c23402dc5e5b1810e7f8d61d87`. The audit asserted zero `MediaGeneration` records and the temporary Playwright workflow/harness was removed before final clean CI.

Official/provider evidence: G2 changes no OpenAI/Higgsfield request contract and enables no model. It deliberately reuses the existing reviewed image pipeline, existing image-to-image source behavior, deterministic official-logo composition and existing typed reference model. No paid provider call was needed or authorized for this task.

Live verification: PR #66 was squash-merged as `3e5f308ae3b2e6a62ffa25e2574ca3e41a8ae5ff`. `feature/chatgpt-content-engine-mcp` was fast-forwarded to that exact code commit and Render deploy `dep-dar1q97avr4c73ff2dtg` completed `live`. Render explicitly checked out `3e5f308ae3b2e6a62ffa25e2574ca3e41a8ae5ff`; build succeeded; new instance `srv-daj9cfgae00c7392t5c0-xqjzg` applied `engine.0020_sequence_ai_anchors_g2... OK`, started StreamableHTTP/Uvicorn successfully and returned `GET /healthz ... 200 OK` before the prior instance shut down. Post-startup review found no `error` or `critical` entries.

Known limitations: G2 prepares AI anchor image jobs for human review but no paid image generation was submitted during verification, so provider-side visual fidelity is intentionally untested here. Manual Media/upload materialization is an explicit human override and can satisfy a planned K position even when the planner suggested a reference requirement. G2 materializes anchors only; broader reusable scroll production methods are H1.

Commit: `3e5f308ae3b2e6a62ffa25e2574ca3e41a8ae5ff`  
PR: #66  
Deploy: `dep-dar1q97avr4c73ff2dtg`  
Next exact task: H1 — Scroll recipe family.

---

# 9. Phase H — Recipe library expansion

Goal: build reusable proven creative production methods, not one-off prompts.

## Task H1 — Scroll recipe family

- [x] `scroll_orbit_hero`
- [x] `scroll_dolly_reveal`
- [x] `scroll_macro_flythrough`
- [x] `scroll_exploded_reveal`
- [x] `scroll_environment_transition`
- [x] `scroll_transition_bridge`
- [x] `scroll_product_showcase`
- [x] `scroll_landscape_flythrough`

Each recipe must have:

- official/internal evidence,
- compatible model capabilities,
- negative constraints,
- model-specific compilation tests,
- clear intended good/bad result.

### Closeout

Status: DONE — all eight trusted H1 scroll recipes are implemented, regression-tested, merged and live. The family is capability-gated rather than hard-coded to a model id: H1 requires canonical START_IMAGE + END_IMAGE plus verified `reference_animation`, `single_continuous_shot` and `first_last_frame` capabilities. No paid media generation was run.

Files changed: `engine/creative_core.py`, `engine/creative_recipes.py`, `engine/creative_director.py`, `engine/creative_registry.py`, new `engine/test_scroll_recipes_h1.py`, focused expectation updates in `engine/test_creative_core.py` and `engine/test_media.py`, plus new evidence/production-method record `docs/2026-09-25-scroll-recipe-family-h1.md`. No database migration.

What changed: Added distinct trusted production methods for orbit hero, dolly reveal, macro flythrough, exploded reveal, environment transition, transition bridge, product showcase and landscape flythrough. Every recipe has camera/motion/continuity policy, negative constraints, evaluation rules, explicit good-result criteria and bad-result signals. `CreativeRecipe` now carries provider-neutral `required_model_capabilities` and outcome criteria. The existing single `route_model()` remains authoritative and now rejects models missing a recipe's verified capabilities. Current Kling 2.5 Turbo Pro is therefore excluded from H1 first/last-frame work while current verified Seedance 2.5 and 2.0 qualify. Generic image/video defaults remain unchanged. The compiler applies the trusted scroll/scrub contract through both Seedance structured and ordered-motion strategies while respecting the existing 1,800-character provider safety ceiling. During H1, current Seedance 2.0 API evidence exposed that its verified I2V contract supports `end_image_url` but its prompt profile lacked `END_FRAME`; H1 corrected and versioned that profile. Creative model/compiler/recipe provenance is now version `2026-09-25.1`.

Tests: Final clean CI run `36108113243` passed. Standard Django: 393 tests in 20.230s, `OK (skipped=2)`. PostgreSQL: 393 tests in 15.519s, `OK`. Migration drift, migrate/check, Django check, MCP settings/import, collectstatic and py_compile gates passed. New H1 coverage verifies all eight registry entries, required capability filtering, START/END role requirements, current Seedance 2.5 and 2.0 eligibility, current Kling exclusion, recipe-specific prompt differentiation, exact provider I2V endpoint/reference-field compilation, audio-off semantics and backwards-compatible generic video behavior. H1 changed no UI, so a Chromium visual audit was not applicable.

Official/provider evidence: Current Higgsfield Seedance help-center guidance, Seedance 2.5 prompting guide and current Seedance 2.5/2.0 image-to-video API references were rechecked on 2026-09-25 and recorded in `docs/2026-09-25-scroll-recipe-family-h1.md`. Evidence supports the current camera vocabulary, first-and-last-frame continuity method, current duration/resolution ranges and optional `end_image_url`. A read-only Higgsfield plugin catalog check still returned workspace error 423; this is not account-availability evidence. Dedicated Content Engine account availability remains authenticated estimate/preflight truth.

Live verification: Render explicitly deployed code commit `4a6afde2d65bab700387edf7b066758627ac0808` as deploy `dep-dar27q7f3r2c73asju9g`. Build was successful, startup reported no migrations to apply, instance `srv-daj9cfgae00c7392t5c0-9zwrh` started the StreamableHTTP session manager and Uvicorn successfully, and the new instance returned `GET /healthz 200 OK`. Render marked the service live. No post-startup error/critical logs were found.

Known limitations: H1 defines and compiles the trusted recipe family but does not yet automatically choose among these recipes from arbitrary loose briefs; A2 remains the separate semantic recipe-selection task. G1's current scroll planner policy still deterministically uses `scroll_transition_bridge` for planned scroll segments rather than automatically selecting the richer H1 family. H1 makes no aesthetic/output-quality claim because no explicitly authorized paid generation was performed. Account-level Higgsfield model availability continues to be verified at non-billable estimate/preflight time.

Commit: `4a6afde2d65bab700387edf7b066758627ac0808`  
PR: #67 — squash merged  
Deploy: `dep-dar27q7f3r2c73asju9g` — live  
Next exact task: H2 — General ad/reel/product recipe family.

---

## Task H2 — General ad/reel/product recipe family

Initial targets should include evidence-backed versions of:

- [ ] Premium Product Reveal
- [ ] Product Showcase
- [ ] Hyper Motion Product
- [ ] Before/After
- [ ] UGC Testimonial
- [ ] UGC Product Demo
- [ ] Problem/Solution Paid Ad
- [ ] Curiosity Hook Paid Ad
- [ ] Landscape/Environment Hero
- [ ] Luxury Brand Film

Do not add a recipe just to increase recipe count. Each must have a reproducible production method.

### Closeout

Status: NOT STARTED

---

# 10. Phase I — Draft → Select → Final orchestration

Goal: spend cheaply while exploring and reserve premium settings for selected directions.

## Task I1 — Draft policy engine

- [ ] Recipe/model can define draft strategy.
- [ ] Draft plan uses cheaper verified settings when appropriate.
- [ ] Preview clearly labels draft quality/model/cost.
- [ ] User can explicitly skip draft stage.

### Closeout

Status: NOT STARTED

---

## Task I2 — Candidate comparison

- [ ] Multiple candidates belong to one creative decision.
- [ ] User can compare and promote a winner.
- [ ] Rejected candidates remain provenance/history.
- [ ] Rejection alone is editorial feedback, not measured performance.

### Closeout

Status: NOT STARTED

---

## Task I3 — Final promotion/render

- [ ] Selected concept can be re-rendered with final model/settings.
- [ ] Final generation preserves recipe, references and chosen creative direction.
- [ ] New provider cost is reviewed before paid submit.
- [ ] Draft and final provenance are linked.

### Closeout

Status: NOT STARTED

---

# 11. Phase J — Generated-media QA

Goal: catch obvious technical/continuity failures before the human spends time evaluating them.

## Task J1 — QA schema and recipe-specific checks

- [ ] Add structured QA result attached to candidate/generation.
- [ ] Recipe defines applicable checks.
- [ ] Human can override QA recommendation.

Continuity checks should include where technically feasible:

- [ ] start-anchor adherence,
- [ ] end-anchor adherence,
- [ ] subject/geometry stability,
- [ ] lighting continuity,
- [ ] camera smoothness,
- [ ] unexpected object appearance/disappearance,
- [ ] obvious morphing,
- [ ] transition coherence.

Product checks:

- [ ] product fidelity,
- [ ] label/logo fidelity when reference-preservation is requested,
- [ ] framing/visibility,
- [ ] reference consistency.

### Closeout

Status: NOT STARTED

---

# 12. Phase K — Creative-media learning extension

Goal: extend, never replace, the current leakage-safe performance learning.

## Task K1 — Persist media-production provenance for learning

- [ ] recipe id/version,
- [ ] model/profile version,
- [ ] compiled prompt/compiler version,
- [ ] reference roles/assets,
- [ ] draft/final stage,
- [ ] candidate selection,
- [ ] manual overrides,
- [ ] estimated/actual cost,
- [ ] published asset linkage.

### Closeout

Status: NOT STARTED

---

## Task K2 — Connect published outcomes to recipe/model provenance

- [ ] Measured own outcomes can be joined to selected media recipe/model.
- [ ] Editorial selection/rejection remains distinct from performance evidence.
- [ ] Competitor data never becomes own-performance labels.
- [ ] Historical claims never become current company facts.

### Closeout

Status: NOT STARTED

---

## Task K3 — Safe recipe/model learning guidance

Only after enough real data:

- [ ] identify repeated stronger/weaker recipe patterns,
- [ ] identify model reliability/cost patterns,
- [ ] influence Auto routing conservatively,
- [ ] keep shadow mode before production influence,
- [ ] store confidence/sample size/evidence.

### Acceptance criteria

No routing change is promoted from one anecdotal result.

### Closeout

Status: NOT STARTED

---

# 13. Phase L — Frame extraction and scroll export

## Task L1 — Frame extraction

- [ ] Extract first frame.
- [ ] Extract last frame.
- [ ] Extract user-selected frame/time.
- [ ] Save extracted frame as normal `MediaAsset`.
- [ ] Store source video/time provenance.
- [ ] Promote frame to SequenceAnchor.

### Closeout

Status: NOT STARTED

---

## Task L2 — Scroll-ready asset export

Later-stage feature:

- [ ] extract ordered frame sequence,
- [ ] deterministic naming,
- [ ] compression/quality policy,
- [ ] dimensions/manifest,
- [ ] web-ready asset package,
- [ ] no impact on canonical source video/assets.

### Closeout

Status: NOT STARTED

---

# 14. Cross-cutting release gates

These gates apply throughout the program.

## Security/ownership gate

- [ ] No cross-company MediaAsset/reference access.
- [ ] No provider credentials exposed to client/signed storage destination.
- [ ] Prompt Library remains untrusted.
- [ ] External references cannot override system/company safety constraints.

## Cost/idempotency gate

- [ ] Non-billable preview never starts paid work.
- [ ] Fresh estimate/review required before paid start.
- [ ] No automatic retry after ambiguous paid submit.
- [ ] Existing UNKNOWN behavior remains fail-closed.
- [ ] Sequence regeneration cannot accidentally duplicate paid jobs.

## Regression gate

- [ ] Existing image generation works.
- [ ] Existing Kling flow remains readable/compatible.
- [ ] Existing media library works.
- [ ] Existing MCP operations work.
- [ ] Existing Postiz flow works.
- [ ] Existing learning flow works.

## Documentation gate

- [ ] This checklist updated after every logical task.
- [ ] DELTA spec updated if architecture materially changes.
- [ ] README updated only for current operational truth.
- [ ] Official model evidence dates updated when models change.

---

# 15. Recommended first implementation sprint

Do these in this order:

1. **A1** — CreativeRecipe domain/registry.
2. **B1** — richer model prompt/reference profile.
3. **B2** — current official Higgsfield/Seedance contract audit.
4. **B3** — add real multi-model routing.
5. **C1** — canonical reference relation.
6. **C2** — END_IMAGE end-to-end.
7. **D1** — `scroll_transition_bridge`.
8. **B4** — expert model override.
9. **D2** — live non-billable production preflight.
10. **D3** — one explicitly authorized paid smoke test.

Only after D1/D2 prove the architecture should the project/timeline work in Phase E begin.

---

# 16. Current next exact task

> **Task H2 — General ad/reel/product recipe family.**

Expand the trusted Creative Recipe registry with evidence-backed general commercial/social production methods: Premium Product Reveal, Product Showcase, Hyper Motion Product, Before/After, UGC Testimonial, UGC Product Demo, Problem/Solution Paid Ad, Curiosity Hook Paid Ad, Landscape/Environment Hero and Luxury Brand Film. Add a recipe only when it has a reproducible production method, clear good/bad result, compatible verified model capabilities, negative constraints and appropriate evidence. Reuse the existing recipe registry/compiler/router and preserve the Prompt Library safety boundary.

