# Sequence Engine E2 — Anchor Chain Execution Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Depends on:** E1 live Sequence Engine schema.

> E2 makes clips executable from canonical anchors. It must reuse the existing MediaGeneration pipeline and must not introduce a second provider, billing or storage path.

## E2.1 Canonical execution

- [x] Prepare a clip version using only `SequenceClip.start_anchor.asset` and `end_anchor.asset`.
- [x] Persist those exact assets as canonical START_IMAGE and END_IMAGE generation references.
- [x] Adjacent clips may share the exact same anchor/asset identity.
- [x] Caller cannot substitute arbitrary start/end asset IDs into an existing clip.
- [x] Store sequence project/clip/anchor provenance on the generated MediaGeneration.
- [x] Reuse the trusted recipe id/version already stored on SequenceClip.
- [x] Reuse existing Creative Director/model router/provider adapter.

## E2.2 Internal ContentRun compatibility

- [x] Reuse existing `ContentRun → MediaGeneration` ownership instead of adding another generation model.
- [x] Create a bounded internal sequence ContentRun per generation attempt.
- [x] Tag the run context with sequence project/clip/anchor identity.
- [x] Project/company ownership must be inherited from the SequenceProject.
- [x] Failed prepare rolls back the internal run/job/version atomically.

## E2.3 Non-destructive regeneration

- [x] Regenerating Clip2 creates a new SequenceClipVersion.
- [x] Previous clip versions remain stored.
- [x] Existing selected version remains selected until an explicit later selection.
- [x] Clip1 is untouched when Clip2 is regenerated.
- [x] K1/K2 rows and asset IDs are untouched when Clip2 is regenerated.
- [x] Locked anchors are read-only inputs, never silently rewritten.

## E2.4 Review and stale-anchor safety

- [x] Prepare step performs no provider call.
- [x] Optional preview uses existing non-billable `preview_job()`.
- [x] Preview refreshes safe estimate/reference/usage snapshots on SequenceClipVersion.
- [x] Preview keeps MediaGeneration queued and without provider_id.
- [x] If a canonical anchor changed after prepare, the old prepared version fails closed before provider preview.
- [x] Existing D2 reviewed-reference signature remains the paid-start safety layer later.
- [x] E2 itself never calls `start_reviewed_job()`.

## E2.5 Determinism / idempotency

- [x] Same idempotency token for same clip returns the same version.
- [x] Same token cannot be reused across different clips.
- [x] Duration target is compiled into the media brief.
- [x] Aspect-ratio target is compiled into the media brief.
- [x] Manual model override fails closed until B4 implements verified override behavior.

## Acceptance proof

Persist and prepare:

```text
K0 → Clip1 → K1 → Clip2 → K2
```

Then prove:

1. Clip1 END_IMAGE asset == K1 asset.
2. Clip2 START_IMAGE asset == K1 asset.
3. Regenerating Clip2 creates V2.
4. Clip1 is unchanged.
5. K1 and K2 are unchanged.
6. Clip2 V1 is retained and remains selected if it was selected.
7. No provider call occurs merely by preparing V2.

## Release gates

- [x] No migration required.
- [x] `makemigrations --check --dry-run` passes.
- [x] Full normal Django suite passes.
- [x] Full PostgreSQL suite passes.
- [x] Focused E2 tests pass.
- [x] Existing media/recipe/end-frame tests remain green.
- [x] Merge to main.
- [x] Sync Render deploy branch.
- [x] Deploy and verify healthy startup.
- [x] Update master plan with PR/commit/CI/deploy evidence.

## Closeout

Status: DONE — Anchor Chain execution is implemented, fully CI-verified and live.  
Implementation: `prepare_anchor_chain_version()` creates a provider-free review candidate from only the clip's canonical START/END anchors; `regenerate_anchor_chain_clip()` creates another non-destructive candidate; `preview_anchor_chain_version()` reuses the existing non-billable media preview/estimate path and fails closed if canonical anchor assets changed after prepare.  
Canonical proof: focused tests verify Clip1.END_IMAGE == K1.asset and Clip2.START_IMAGE == the exact same K1.asset/anchor identity.  
Regeneration proof: regenerating Clip2 creates V2 while preserving Clip2 V1 and its selected state, and leaves Clip1, K1 and K2 unchanged. Locked anchors are inputs only and are never silently replaced.  
Compatibility: existing `ContentRun → MediaGeneration → MediaGenerationReference` ownership/routing/provider lifecycle is reused. Sequence provenance is persisted on MediaGeneration and SequenceClipVersion. No parallel media/generation system was added.  
Idempotency: same token/same clip returns the same candidate; token reuse across clips fails closed.  
Targets: clip duration and aspect ratio are compiled into the existing Creative Director brief. Manual model override fails closed until B4 rather than being silently ignored.  
CI: run `35995732844` passed the full normal Django suite (299 tests), full PostgreSQL suite, `makemigrations --check --dry-run`, migration/check/static/MCP gates and all existing regression tests. No migration was added for E2.  
CI hardening found and fixed before merge: PostgreSQL rejected `FOR UPDATE` across nullable joins for `selected_version` and `project.author`; both optional joins were removed from the locked query while preserving the SequenceClip row lock. A missing `ContentRun` import was also caught before the final green run.  
PR: #52  
Main commit: `b883b2febb85a907d0cc7f34da523bb7f520bcee`  
Deploy: `dep-daqgvd67bikc738g27dg` on `content-engine-mcp`; commit matched, startup reported no migrations to apply, new instance `qtrbc` returned `/healthz` 200 and Render marked the deploy `live`.  
Provider calls: none required for E2 release; no paid generation was started.  
Next exact task after E2: **E3 — Output Chain mode.**
