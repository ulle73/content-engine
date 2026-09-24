# Sequence Engine E4 — Transition Bridge Execution Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until all release gates pass.  
**Depends on:** E1 schema, E2 Anchor Chain and E3 Output Chain live.

> E4 creates an extra continuity segment between two existing clips. It must never rewrite, replace or repurpose either source clip.

## E4.1 Domain model

- [ ] Add `SequenceBridge` as a separate project-scoped segment.
- [ ] Add `SequenceBridgeVersion` for non-destructive candidates.
- [ ] Bridge points to left clip + right clip.
- [ ] Bridge START anchor is exactly `left_clip.end_anchor`.
- [ ] Bridge END anchor is exactly `right_clip.start_anchor`.
- [ ] Bridge requires two distinct anchors.
- [ ] Left clip must precede right clip.
- [ ] One logical bridge exists per project + left/right clip pair.
- [ ] Bridge recipe is fixed to trusted `scroll_transition_bridge`.
- [ ] Bridge versions point to existing `MediaGeneration`.
- [ ] One MediaGeneration cannot be shared between clip and bridge provenance.

## E4.2 Non-destructive prepare/regenerate

- [ ] `create_transition_bridge()` creates/reuses only bridge metadata.
- [ ] `prepare_transition_bridge_version()` uses canonical bridge anchors only.
- [ ] Prepare reuses existing ContentRun → MediaGeneration → typed-reference pipeline.
- [ ] START_IMAGE is the exact left clip end-anchor asset.
- [ ] END_IMAGE is the exact right clip start-anchor asset.
- [ ] Prepare performs no provider request.
- [ ] Regeneration creates V2/V3 without deleting previous candidates.
- [ ] Existing selected bridge candidate remains selected until explicit replacement.
- [ ] Existing clips, clip versions and anchors remain unchanged.

## E4.3 Review / selection

- [ ] `preview_transition_bridge_version()` reuses existing non-billable preview.
- [ ] Preview refreshes safe recipe/model/reference/usage/cost provenance.
- [ ] Preview leaves MediaGeneration queued and provider_id empty.
- [ ] Stale anchor assets fail closed before provider access.
- [ ] `select_transition_bridge_version()` selects only completed bridge candidates.
- [ ] Candidate from another bridge cannot be selected.

## E4.4 Snapshot / future workspace support

- [ ] `sequence_snapshot()` exposes bridge IDs, clip pair, anchors, recipe and selected version.
- [ ] Bridge remains distinct from ordinary clips for timeline/workspace rendering.
- [ ] Deleting project removes bridge metadata but preserves underlying MediaGeneration history.
- [ ] No provider-specific bridge table or storage path is added.

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

- [ ] Migration is deterministic and `makemigrations --check --dry-run` passes.
- [ ] Full normal Django suite passes.
- [ ] Full PostgreSQL suite passes.
- [ ] Existing E1/E2/E3/media/provider tests remain green.
- [ ] Focused E4 isolation/versioning/stale-anchor tests pass.
- [ ] Merge to main.
- [ ] Sync Render deploy branch.
- [ ] Production migration applies successfully.
- [ ] New Render instance returns `/healthz` 200 and deploy is live.
- [ ] Master plan updated with exact PR/commit/CI/deploy evidence.

## Closeout

Status: NOT STARTED  
Migration: `0017_sequence_transition_bridge`  
CI: —  
PR: —  
Main commit: —  
Deploy: —  
Provider calls: none required for release.  
Next exact task after E4: **F1 — Sequence project workspace.**
