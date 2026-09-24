# Sequence Workspace F3 — Clip Controls Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until all release gates pass.  
**Depends on:** E1–E4, F1–F2 live.  
**Prerequisite implemented in this change:** B4 verified expert model override.

> F3 must remain a thin UI over the existing Sequence + MediaGeneration lifecycle. Preparing or regenerating a candidate may perform the existing non-billable estimate, but it must never perform a paid submit. Paid start remains the existing reviewed Media job action.

## B4 prerequisite — verified model override

Official contracts rechecked 2026-09-24:
- Seedance 2.5 I2V: https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference
- Seedance 2.0 I2V: https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference
- Kling 2.5 Turbo Pro I2V: https://open.higgsfield.ai/models/kling-video/v2.5-turbo/pro/image-to-video/api-reference

- [ ] Auto remains the default route.
- [ ] Manual override uses only enabled verified registry entries.
- [ ] Exact reference-role compatibility is checked before provider calls.
- [ ] Manual duration override must be exactly supported rather than silently normalized.
- [ ] Existing resolution/aspect/audio hard capability validation remains active.
- [ ] Manual override provenance is persisted in CreativePlan/MediaGeneration.
- [ ] AI Studio exposes Auto + verified mode-compatible override list.
- [ ] MCP preview_media accepts a bounded model_override and reuses the same validation.
- [ ] F3 anchor-to-anchor UI lists only models supporting START_IMAGE + END_IMAGE.
- [ ] Current START+END choices exclude Kling 2.5 Turbo Pro and allow compatible Seedance modes.
- [ ] No provider/account availability is inferred from public documentation.

## F3.1 Generate/regenerate

- [ ] Each clip exposes a prepare/generate control.
- [ ] First prepare creates V1 without paid submit.
- [ ] Regenerate creates V2/V3 etc without mutating prior candidates.
- [ ] Existing selected candidate remains selected while a new candidate is prepared/generated.
- [ ] Exact canonical START_IMAGE + END_IMAGE are reused for every candidate.
- [ ] Non-billable estimate/review uses existing preview_anchor_chain_version → preview_job path.
- [ ] Review redirects to the existing Media job page.
- [ ] Media job page links back to exact Sequence project/candidate.

## F3.2 Shared reviewed lifecycle

- [ ] Paid start remains only start_reviewed_job().
- [ ] Polling/status never starts a queued job.
- [ ] Sequence candidate snapshot syncs after preview/start/status/cancel/provider refresh.
- [ ] Active generation can be canceled only through existing cancel_job safety.
- [ ] queued cancel causes no provider cancel call.
- [ ] ambiguous/unknown lifecycle behavior remains fail-closed.
- [ ] No duplicate paid submit path is introduced.

## F3.3 Candidate comparison + winner

- [ ] Workspace shows all versions for each clip.
- [ ] Completed video assets can be previewed in candidate cards.
- [ ] Candidate card shows version status + MediaGeneration status.
- [ ] Candidate shows selected model + exact provider path.
- [ ] Candidate shows reviewed cost estimate/usage snapshot.
- [ ] Candidate diagnostics show route reasons, manual/Auto, generation ID, provider prompt and canonical reference snapshot.
- [ ] Completed non-stale candidate can be selected as winner.
- [ ] Previous winner remains historical and is not deleted.
- [ ] Stale/rejected/failed candidate cannot be selected.
- [ ] stale status survives a later provider completion sync.

## F3.4 Ownership/UI boundaries

- [ ] All actions require authenticated company ownership.
- [ ] Cross-company project/clip/version actions 404/fail closed.
- [ ] F3 does not mutate anchors.
- [ ] F3 does not introduce a second timeline/domain model.
- [ ] F3 reuses existing six-primary-navigation contract.
- [ ] Responsive final visual/keyboard verification remains F4.

## Release gates

- [ ] No migration required and makemigrations --check --dry-run passes.
- [ ] Focused B4 route/media tests pass.
- [ ] Focused F3 service/UI/lifecycle tests pass.
- [ ] Full normal Django suite passes.
- [ ] Full PostgreSQL suite passes.
- [ ] Existing media safety/idempotency tests remain green.
- [ ] Existing E1–E4/F1–F2 tests remain green.
- [ ] MCP checks/schema load remain green.
- [ ] Merge to main.
- [ ] Sync Render deploy branch.
- [ ] Production starts without migration changes.
- [ ] New instance returns /healthz 200 and deploy is live.
- [ ] Master checklist updated with exact evidence.

## Closeout

Status: NOT STARTED  
Migration: none expected  
CI: —  
PR: —  
Main commit: —  
Deploy: —  
Paid generation: none required for implementation/release verification.  
Next exact task after F3: **F4 — Responsive/accessibility verification.**
