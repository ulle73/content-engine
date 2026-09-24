# Sequence Engine E2 — Anchor Chain Execution Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until all release gates pass.  
**Depends on:** E1 live Sequence Engine schema.

> E2 makes clips executable from canonical anchors. It must reuse the existing MediaGeneration pipeline and must not introduce a second provider, billing or storage path.

## E2.1 Canonical execution

- [ ] Prepare a clip version using only `SequenceClip.start_anchor.asset` and `end_anchor.asset`.
- [ ] Persist those exact assets as canonical START_IMAGE and END_IMAGE generation references.
- [ ] Adjacent clips may share the exact same anchor/asset identity.
- [ ] Caller cannot substitute arbitrary start/end asset IDs into an existing clip.
- [ ] Store sequence project/clip/anchor provenance on the generated MediaGeneration.
- [ ] Reuse the trusted recipe id/version already stored on SequenceClip.
- [ ] Reuse existing Creative Director/model router/provider adapter.

## E2.2 Internal ContentRun compatibility

- [ ] Reuse existing `ContentRun → MediaGeneration` ownership instead of adding another generation model.
- [ ] Create a bounded internal sequence ContentRun per generation attempt.
- [ ] Tag the run context with sequence project/clip/anchor identity.
- [ ] Project/company ownership must be inherited from the SequenceProject.
- [ ] Failed prepare rolls back the internal run/job/version atomically.

## E2.3 Non-destructive regeneration

- [ ] Regenerating Clip2 creates a new SequenceClipVersion.
- [ ] Previous clip versions remain stored.
- [ ] Existing selected version remains selected until an explicit later selection.
- [ ] Clip1 is untouched when Clip2 is regenerated.
- [ ] K1/K2 rows and asset IDs are untouched when Clip2 is regenerated.
- [ ] Locked anchors are read-only inputs, never silently rewritten.

## E2.4 Review and stale-anchor safety

- [ ] Prepare step performs no provider call.
- [ ] Optional preview uses existing non-billable `preview_job()`.
- [ ] Preview refreshes safe estimate/reference/usage snapshots on SequenceClipVersion.
- [ ] Preview keeps MediaGeneration queued and without provider_id.
- [ ] If a canonical anchor changed after prepare, the old prepared version fails closed before provider preview.
- [ ] Existing D2 reviewed-reference signature remains the paid-start safety layer later.
- [ ] E2 itself never calls `start_reviewed_job()`.

## E2.5 Determinism / idempotency

- [ ] Same idempotency token for same clip returns the same version.
- [ ] Same token cannot be reused across different clips.
- [ ] Duration target is compiled into the media brief.
- [ ] Aspect-ratio target is compiled into the media brief.
- [ ] Manual model override fails closed until B4 implements verified override behavior.

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

- [ ] No migration required.
- [ ] `makemigrations --check --dry-run` passes.
- [ ] Full normal Django suite passes.
- [ ] Full PostgreSQL suite passes.
- [ ] Focused E2 tests pass.
- [ ] Existing media/recipe/end-frame tests remain green.
- [ ] Merge to main.
- [ ] Sync Render deploy branch.
- [ ] Deploy and verify healthy startup.
- [ ] Update master plan with PR/commit/CI/deploy evidence.

## Closeout

Status: NOT STARTED  
CI: —  
PR: —  
Main commit: —  
Deploy: —  
Provider calls: none required for release; tests must remain provider-free.  
Next exact task after E2: **E3 — Output Chain mode.**
