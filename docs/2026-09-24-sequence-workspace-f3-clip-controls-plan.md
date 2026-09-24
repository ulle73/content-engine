# Sequence Workspace F3 — Clip Controls Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Depends on:** E1–E4, F1–F2 live.  
**Prerequisite implemented in this change:** B4 verified expert model override.

> F3 must remain a thin UI over the existing Sequence + MediaGeneration lifecycle. Preparing or regenerating a candidate may perform the existing non-billable estimate, but it must never perform a paid submit. Paid start remains the existing reviewed Media job action.

## B4 prerequisite — verified model override

Official contracts rechecked 2026-09-24:
- Seedance 2.5 I2V: https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference
- Seedance 2.0 I2V: https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference
- Kling 2.5 Turbo Pro I2V: https://open.higgsfield.ai/models/kling-video/v2.5-turbo/pro/image-to-video/api-reference

- [x] Auto remains the default route.
- [x] Manual override uses only enabled verified registry entries.
- [x] Exact reference-role compatibility is checked before provider calls.
- [x] Manual duration override must be exactly supported rather than silently normalized.
- [x] Existing resolution/aspect/audio hard capability validation remains active.
- [x] Manual override provenance is persisted in CreativePlan/MediaGeneration.
- [x] AI Studio exposes Auto + verified mode-compatible override list.
- [x] MCP preview_media accepts a bounded model_override and reuses the same validation.
- [x] F3 anchor-to-anchor UI lists only models supporting START_IMAGE + END_IMAGE.
- [x] Current START+END choices exclude Kling 2.5 Turbo Pro and allow compatible Seedance modes.
- [x] No provider/account availability is inferred from public documentation.

## F3.1 Generate/regenerate

- [x] Each clip exposes a prepare/generate control.
- [x] First prepare creates V1 without paid submit.
- [x] Regenerate creates V2/V3 etc without mutating prior candidates.
- [x] Existing selected candidate remains selected while a new candidate is prepared/generated.
- [x] Exact canonical START_IMAGE + END_IMAGE are reused for every candidate.
- [x] Non-billable estimate/review uses existing preview_anchor_chain_version → preview_job path.
- [x] Review redirects to the existing Media job page.
- [x] Media job page links back to exact Sequence project/candidate.

## F3.2 Shared reviewed lifecycle

- [x] Paid start remains only start_reviewed_job().
- [x] Polling/status never starts a queued job.
- [x] Sequence candidate snapshot syncs after preview/start/status/cancel/provider refresh.
- [x] Active generation can be canceled only through existing cancel_job safety.
- [x] queued cancel causes no provider cancel call.
- [x] ambiguous/unknown lifecycle behavior remains fail-closed.
- [x] No duplicate paid submit path is introduced.

## F3.3 Candidate comparison + winner

- [x] Workspace shows all versions for each clip.
- [x] Completed video assets can be previewed in candidate cards.
- [x] Candidate card shows version status + MediaGeneration status.
- [x] Candidate shows selected model + exact provider path.
- [x] Candidate shows reviewed cost estimate/usage snapshot.
- [x] Candidate diagnostics show route reasons, manual/Auto, generation ID, provider prompt and canonical reference snapshot.
- [x] Completed non-stale candidate can be selected as winner.
- [x] Previous winner remains historical and is not deleted.
- [x] Stale/rejected/failed candidate cannot be selected.
- [x] stale status survives a later provider completion sync.

## F3.4 Ownership/UI boundaries

- [x] All actions require authenticated company ownership.
- [x] Cross-company project/clip/version actions 404/fail closed.
- [x] F3 does not mutate anchors.
- [x] F3 does not introduce a second timeline/domain model.
- [x] F3 reuses existing six-primary-navigation contract.
- [x] Responsive final visual/keyboard verification remains F4.

## Release gates

- [x] No migration required and makemigrations --check --dry-run passes.
- [x] Focused B4 route/media tests pass.
- [x] Focused F3 service/UI/lifecycle tests pass.
- [x] Full normal Django suite passes.
- [x] Full PostgreSQL suite passes.
- [x] Existing media safety/idempotency tests remain green.
- [x] Existing E1–E4/F1–F2 tests remain green.
- [x] MCP checks/schema load remain green.
- [x] Merge to main.
- [x] Sync Render deploy branch.
- [x] Production starts without migration changes.
- [x] New instance returns /healthz 200 and deploy is live.
- [x] Master checklist updated with exact evidence.

## Closeout

Status: DONE — reviewed, non-destructive clip controls and the B4 verified model override are implemented and live.  
B4: Auto remains default. Manual override is routed through the existing Creative Director and must match an enabled, verified, exact request-compatible model before a MediaGeneration can be created. START/END capability, duration, resolution, aspect and audio constraints remain fail-closed. Manual selection is persisted in `parameters.model_override` and `creative.selection.manual_override/reason_codes`. AI Studio and MCP reuse the same path; MCP override length is bounded to 120 characters.  
Official model evidence rechecked 2026-09-24: Higgsfield Seedance 2.5 I2V and Seedance 2.0 I2V still expose optional end-frame input; Kling 2.5 Turbo Pro I2V exposes start-image input but not END_IMAGE. Public docs were used only for capability contracts, never as proof of Golfkuponger's account availability.  
F3 generation: each prepare/regenerate action creates an independent V1/V2/V3 candidate from the current canonical START_IMAGE + END_IMAGE. Workspace prepare runs the existing non-billable `preview_anchor_chain_version → preview_job` path and redirects to the existing Media job review page. No paid-start path was added to Sequence workspace.  
F3 lifecycle: paid submit remains `start_reviewed_job()`; status/polling never starts queued jobs; cancel reuses `cancel_job()`; Sequence candidate snapshots sync after preview/start/status/cancel/provider refresh. `stale` and `rejected` states are preserved even if the provider later reports completion.  
F3 comparison: workspace shows all candidate versions, completed video previews, version/generation status, model, exact provider path, estimate, recipe, routing reason, Auto/manual provenance, generation id, compiled provider prompt and canonical reference snapshot. Completed valid candidates can be selected as winner without deleting prior versions.  
Security/ownership: project/clip/version actions remain company-scoped; invalid cross-company access fails closed. No anchor mutation, second timeline model, second provider path or second billing path was introduced.  
Migration: none. Production startup reported `No migrations to apply.`  
CI: run `36011305597` — full normal Django suite, full PostgreSQL suite, `makemigrations --check --dry-run`, migration/check/static/MCP gates all green.  
PR: #62  
Main commit: `c70775797ce57e348fb78ad1caf3a19122296307`  
Deploy: `dep-daqj1d0u01pc738blq5g`; new instance `rwbm5` completed startup, returned `/healthz` 200 and Render marked the deploy `live`.  
Paid generation: none was started during implementation or release verification.  
Next exact task after F3: **F4 — Responsive/accessibility verification.**
