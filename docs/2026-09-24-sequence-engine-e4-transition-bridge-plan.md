# Sequence Engine E4 — Transition Bridge Execution Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Depends on:** E1 schema, E2 Anchor Chain and E3 Output Chain live.

> E4 creates an extra continuity segment between two existing clips. It must never rewrite, replace or repurpose either source clip.

## E4.1 Domain model

- [x] Add `SequenceBridge` as a separate project-scoped segment.
- [x] Add `SequenceBridgeVersion` for non-destructive candidates.
- [x] Bridge points to left clip + right clip.
- [x] Bridge START anchor is exactly `left_clip.end_anchor`.
- [x] Bridge END anchor is exactly `right_clip.start_anchor`.
- [x] Bridge requires two distinct anchors.
- [x] Left clip must precede right clip.
- [x] One logical bridge exists per project + left/right clip pair.
- [x] Bridge recipe is fixed to trusted `scroll_transition_bridge`.
- [x] Bridge versions point to existing `MediaGeneration`.
- [x] One MediaGeneration cannot be shared between clip and bridge provenance.

## E4.2 Non-destructive prepare/regenerate

- [x] `create_transition_bridge()` creates/reuses only bridge metadata.
- [x] `prepare_transition_bridge_version()` uses canonical bridge anchors only.
- [x] Prepare reuses existing ContentRun → MediaGeneration → typed-reference pipeline.
- [x] START_IMAGE is the exact left clip end-anchor asset.
- [x] END_IMAGE is the exact right clip start-anchor asset.
- [x] Prepare performs no provider request.
- [x] Regeneration creates V2/V3 without deleting previous candidates.
- [x] Existing selected bridge candidate remains selected until explicit replacement.
- [x] Existing clips, clip versions and anchors remain unchanged.

## E4.3 Review / selection

- [x] `preview_transition_bridge_version()` reuses existing non-billable preview.
- [x] Preview refreshes safe recipe/model/reference/usage/cost provenance.
- [x] Preview leaves MediaGeneration queued and provider_id empty.
- [x] Stale anchor assets fail closed before provider access.
- [x] `select_transition_bridge_version()` selects only completed bridge candidates.
- [x] Candidate from another bridge cannot be selected.

## E4.4 Snapshot / future workspace support

- [x] `sequence_snapshot()` exposes bridge IDs, clip pair, anchors, recipe and selected version.
- [x] Bridge remains distinct from ordinary clips for timeline/workspace rendering.
- [x] Deleting project removes bridge metadata but preserves underlying MediaGeneration history.
- [x] No provider-specific bridge table or storage path is added.

## Acceptance proof

Given:

```text
K0 → Clip A → K1     K2 → Clip B → K3
```

Create:

```text
K0 → Clip A → K1 → Bridge → K2 → Clip B → K3
```

Then prove:

1. Bridge START_IMAGE == K1 asset.
2. Bridge END_IMAGE == K2 asset.
3. Clip A and Clip B primary keys/status/versions are unchanged.
4. K1 and K2 primary keys/assets/lock state are unchanged.
5. Bridge generation uses `scroll_transition_bridge`.
6. Regenerating bridge creates V2 while V1 remains.
7. Existing selected bridge V1 remains selected until explicit change.
8. Preview is non-billable.
9. No paid generation is started.

## Release gates

- [x] Migration is deterministic and `makemigrations --check --dry-run` passes.
- [x] Full normal Django suite passes.
- [x] Full PostgreSQL suite passes.
- [x] Existing E1/E2/E3/media/provider tests remain green.
- [x] Focused E4 isolation/versioning/stale-anchor tests pass.
- [x] Merge to main.
- [x] Sync Render deploy branch.
- [x] Production migration applies successfully.
- [x] New Render instance returns `/healthz` 200 and deploy is live.
- [x] Master plan updated with exact PR/commit/CI/deploy evidence.

## Closeout

Status: DONE — non-destructive Transition Bridge orchestration is implemented, fully tested and live.  
Architecture: `SequenceBridge` and `SequenceBridgeVersion` are separate from ordinary clips. A bridge is bound to one existing left/right clip pair and derives its immutable logical inputs as `left_clip.end_anchor → right_clip.start_anchor`. Existing clip rows, versions and anchor rows are never rewritten by bridge prepare/regenerate.  
Recipe/model path: every bridge is fixed to trusted `scroll_transition_bridge`; prepare reuses the existing Creative Director/router/MediaGeneration/typed-reference pipeline, so provider behavior is not duplicated.  
Versioning: bridge V1/V2/... candidates are non-destructive; selecting a candidate changes bridge selection only and does not change source clips.  
Safety: bridge pair/project/order/anchor binding is model-validated; duplicate logical pair is DB-constrained; stale anchor assets fail before preview; one MediaGeneration cannot be reused across clip and bridge provenance in either direction.  
Snapshot: `sequence_snapshot()` now exposes bridge identity, left/right clip IDs, anchor IDs, recipe/version and selected bridge version separately from ordinary clips.  
CI: run `35998901727` passed `makemigrations --check --dry-run`, migration apply/check, Django/system/static/MCP gates, full normal Django suite and full PostgreSQL suite.  
PR: #56  
Main commit: `820455e21f0a07c13c682e02b9588ed468fd4bb2`  
Migration: `0017_sequence_transition_bridge`  
Deploy: `dep-daqhe1e7bikc738hg58g`; production log shows `Applying engine.0017_sequence_transition_bridge... OK`, new instance `nlzxh` startup complete, `/healthz` 200 and deploy status `live`.  
Provider calls: none required for release; no paid generation was started.  
Next exact task after E4: **F1 — Sequence project workspace.**
