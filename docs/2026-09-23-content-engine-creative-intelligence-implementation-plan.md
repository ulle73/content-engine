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

- [ ] Add only currently verified compatible models.
- [ ] Keep Kling if still valid.
- [ ] Update scoring to consider:
  - recipe compatibility,
  - required reference roles,
  - quality,
  - speed,
  - cost,
  - audio,
  - complexity.
- [ ] Preserve current `route_model()` as the single Auto router.
- [ ] Add reason codes showing why a model won.

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

Status: NOT STARTED  
Commit: —  
Deploy: —  
Evidence: —

---

## Task B4 — Expert model override

- [ ] Add `Model: Auto` as default.
- [ ] Add advanced override for verified eligible models.
- [ ] Expose only controls supported by selected model.
- [ ] Prevent invalid duration/resolution/reference combinations locally.
- [ ] Add same override capability to MCP in a bounded safe form.
- [ ] Persist manual override provenance.

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

Status: NOT STARTED  
Commit: —  
Deploy: —  
Evidence: —

---

# 4. Phase C — Canonical media reference system

Goal: evolve beyond one `source_asset` without breaking existing I2V.

## Task C1 — Design/add canonical MediaGenerationReference relation

Recommended shape: additive relation rather than multiplying provider-specific columns.

- [ ] Add canonical reference roles:
  - START_IMAGE
  - END_IMAGE
  - PRODUCT_REFERENCE
  - CHARACTER_REFERENCE
  - LOCATION_REFERENCE
  - STYLE_REFERENCE
  - VIDEO_REFERENCE
  - AUDIO_REFERENCE
- [ ] Add ordered references where a model supports multiple refs.
- [ ] Validate all assets belong to the same company.
- [ ] Preserve `MediaGeneration.source_asset` compatibility for old jobs/current code.
- [ ] Backfill or compatibility-map START_IMAGE from `source_asset` without destructive migration.
- [ ] Provider-specific field names stay in provider adapter only.

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

Status: NOT STARTED  
Commit: —  
Deploy: —  
Evidence: —

---

## Task C2 — End-frame support end-to-end

- [ ] AI Studio can select/display/remove an END_IMAGE.
- [ ] MCP preview/generate can accept an end asset id.
- [ ] End asset is company-scoped.
- [ ] CreativeBrief/plan sees END_IMAGE capability requirement.
- [ ] Router chooses only compatible models.
- [ ] Estimate uploads/includes the actual end image.
- [ ] Paid submit reuses the reviewed exact inputs.
- [ ] Provenance includes start/end asset IDs and hashes where safe.
- [ ] Job review page clearly shows both anchors.

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

Status: NOT STARTED  
Commit: —  
Deploy: —  
Evidence: —

---

# 5. Phase D — First proven continuity workflow

Goal: prove the new architecture with the smallest useful cinematic feature before building a timeline.

## Task D1 — Implement `scroll_transition_bridge` recipe

- [ ] Trusted recipe exists.
- [ ] Requires START_IMAGE + END_IMAGE.
- [ ] Enforces one continuous shot.
- [ ] Includes continuity constraints.
- [ ] Uses model-specific prompt profile rather than one universal prompt.
- [ ] Prioritizes continuity over spectacle.
- [ ] No hard cuts/morphing/new objects unless explicitly requested.
- [ ] Appropriate audio default is explicit.

### Acceptance criteria

Compiled prompt is materially different and model-appropriate compared with generic video generation.

### Tests

- recipe requirements,
- compiled prompt structure,
- negative constraints,
- no raw Prompt Library injection,
- correct router capability requirement.

### Closeout

Status: NOT STARTED  
Commit: —  
Deploy: —  
Evidence: —

---

## Task D2 — Non-billable production preflight for start→end

- [ ] Deploy current code to Render.
- [ ] Verify dedicated GK Higgsfield server credential works for estimate.
- [ ] Verify actual provider accepts the selected model + both references for estimate.
- [ ] Record exact returned model path and safe estimate metadata.
- [ ] Do not substitute Jonas personal Higgsfield workspace.
- [ ] Do not run paid generation merely to test credentials.

### Acceptance criteria

One production job reaches a valid reviewed/queued state with a real provider estimate and no provider generation id.

### Closeout

Status: NOT STARTED  
Commit: —  
Deploy: —  
Live evidence: —

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

- [ ] Add `SequenceProject`.
- [ ] Add `SequenceAnchor`.
- [ ] Add `SequenceClip`.
- [ ] Add clip/candidate version representation.
- [ ] Link generated assets through existing `MediaAsset`.
- [ ] Link generation jobs through existing `MediaGeneration`.
- [ ] Company ownership enforced everywhere.
- [ ] Non-destructive versioning.
- [ ] No duplicated media storage system.

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

Status: NOT STARTED  
Commit: —  
Deploy: —

---

## Task E2 — Anchor Chain mode

- [ ] Canonical anchor can be start of one clip and end of previous clip.
- [ ] Same exact asset identity is preserved.
- [ ] Regenerating a clip does not mutate anchors.
- [ ] Locked anchors cannot be silently replaced.

### Acceptance criteria

Regenerate Clip2 without changing Clip1, K1 or K2.

### Closeout

Status: NOT STARTED

---

## Task E3 — Output Chain mode

- [ ] User can explicitly promote a generated final frame into the next start anchor.
- [ ] System labels this as output-chain behavior.
- [ ] It never silently replaces canonical anchors.
- [ ] Provenance records source clip/frame.

### Closeout

Status: NOT STARTED

---

## Task E4 — Transition Bridge mode

- [ ] User can select an existing clip end/opening anchor pair.
- [ ] System creates a bridge segment using the continuity recipe.
- [ ] Existing clips remain untouched.

### Closeout

Status: NOT STARTED

---

# 7. Phase F — Sequence workspace / timeline UX

## Task F1 — Project workspace

- [ ] Dedicated sequence project page/workspace.
- [ ] Visible anchor/clip order.
- [ ] Clear locked/unlocked state.
- [ ] Generation status per clip.
- [ ] Candidate/version count.
- [ ] No hidden destructive regeneration.

### Closeout

Status: NOT STARTED

---

## Task F2 — Anchor controls

- [ ] Upload anchor.
- [ ] Choose existing MediaAsset.
- [ ] Generate anchor with AI.
- [ ] Replace anchor.
- [ ] Lock anchor.
- [ ] Duplicate/version anchor where appropriate.
- [ ] Show provenance.

### Closeout

Status: NOT STARTED

---

## Task F3 — Clip controls

- [ ] Generate one clip.
- [ ] Regenerate one clip.
- [ ] Compare versions.
- [ ] Promote selected version.
- [ ] Cancel current job safely.
- [ ] Advanced model override per clip.
- [ ] Show recipe/model/prompt/cost diagnostics.

### Closeout

Status: NOT STARTED

---

## Task F4 — Responsive/accessibility verification

- [ ] Desktop visual review.
- [ ] Mobile visual review.
- [ ] Keyboard interaction.
- [ ] No horizontal overflow.
- [ ] Status and destructive actions accessible.
- [ ] Existing AI Studio remains usable.

### Closeout

Status: NOT STARTED

---

# 8. Phase G — Automatic storyboard + anchor planning

Goal: make a loose prompt powerful enough for non-experts.

## Task G1 — Sequence planner

- [ ] Loose brief can produce proposed:
  - number of scenes,
  - narrative progression,
  - recipe per scene/transition,
  - anchor descriptions,
  - required references,
  - model capability requirements,
  - draft/final plan.
- [ ] Company facts remain grounded in current verified context.
- [ ] User can edit before any paid media generation.

### Acceptance criteria

“Create a premium 4-scene Golfkuponger scroll story” creates a useful editable plan without requiring model knowledge.

### Closeout

Status: NOT STARTED

---

## Task G2 — AI anchor generation

- [ ] Generate proposed anchors using existing image-generation pipeline.
- [ ] Preserve company/product references when required.
- [ ] Allow user replacement/upload.
- [ ] Do not start video generation until required anchors exist.

### Closeout

Status: NOT STARTED

---

# 9. Phase H — Recipe library expansion

Goal: build reusable proven creative production methods, not one-off prompts.

## Task H1 — Scroll recipe family

- [ ] `scroll_orbit_hero`
- [ ] `scroll_dolly_reveal`
- [ ] `scroll_macro_flythrough`
- [ ] `scroll_exploded_reveal`
- [ ] `scroll_environment_transition`
- [ ] `scroll_transition_bridge`
- [ ] `scroll_product_showcase`
- [ ] `scroll_landscape_flythrough`

Each recipe must have:

- official/internal evidence,
- compatible model capabilities,
- negative constraints,
- model-specific compilation tests,
- clear intended good/bad result.

### Closeout

Status: NOT STARTED

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

> **Task B3 — Make Higgsfield request compilation mode-aware and add verified Seedance 2.5/2.0 to the existing Auto router without breaking current Kling behavior.**

Do not begin by building the timeline UI.

