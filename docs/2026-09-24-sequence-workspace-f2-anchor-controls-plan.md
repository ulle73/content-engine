# Sequence Workspace F2 — Anchor Controls Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until every release gate passes.  
**Depends on:** E1–E4 + F1 live.

> F2 makes canonical anchors editable without making sequence history destructive. All replacements are explicit, revisioned and stale-aware. AI anchors reuse the existing MediaGeneration review/start gate.

## F2.1 Anchor revision model

- [ ] Add non-destructive `SequenceAnchorRevision`.
- [ ] Seed revision 1 for every existing anchor during migration.
- [ ] Every newly created anchor receives revision 1.
- [ ] Every replacement/restore creates a new revision number.
- [ ] Historical revision assets are deletion-protected.
- [ ] Revision stores asset, source type, source clip provenance, source metadata, reason and actor.
- [ ] Restore creates a new revision; history is never rewound/deleted.

## F2.2 Stale safety

- [ ] Add explicit `stale` candidate status for clips and bridges.
- [ ] Compute clip/bridge versions impacted by an anchor change.
- [ ] Anchor replacement with affected versions requires explicit confirmation.
- [ ] Confirmed change preserves those versions and marks them stale.
- [ ] Selected stale clip/bridge candidates are explicitly unselected and parent segment returns to review.
- [ ] Stale candidates cannot be re-selected.
- [ ] Locked anchor cannot be replaced or restored until explicitly unlocked.
- [ ] Existing E2 stale-reference checks remain an additional fail-closed layer.

## F2.3 Existing MediaAsset + upload controls

- [ ] Add new anchor from an existing company-scoped image.
- [ ] Add new anchor from JPEG/PNG/WebP upload.
- [ ] Replace unlocked anchor from existing company-scoped image.
- [ ] Replace unlocked anchor via upload.
- [ ] Upload is not persisted if stale confirmation is still missing.
- [ ] Applied/generated anchor assets are retained permanently.
- [ ] Cross-company, video and logo assets fail closed.
- [ ] Current provenance is visible in workspace.

## F2.4 AI anchor generation

- [ ] Add explicit `SequenceAnchorGenerationTarget`.
- [ ] AI job is bound to project + create/replace anchor intent.
- [ ] AI prepare reuses existing `ContentRun → MediaGeneration → Creative Director` image pipeline.
- [ ] Prepare performs no paid provider generation.
- [ ] Existing Media job review page is reused.
- [ ] Paid image generation can only start through existing `start_reviewed_job()`.
- [ ] Completed alternatives show “Use as anchor” on the existing job page.
- [ ] Applying result validates exact generation ownership and image kind.
- [ ] Create-mode AI result appends a new canonical anchor.
- [ ] Replace-mode AI result passes the same lock/stale/revision controls as every other replacement.
- [ ] AI target/job links back to Sequence workspace.

## F2.5 Workspace controls

- [ ] Add project-level controls for Media / upload / AI new anchor.
- [ ] Add per-anchor lock/unlock.
- [ ] Add per-anchor replace from Media.
- [ ] Add per-anchor upload replacement.
- [ ] Add per-anchor AI replacement.
- [ ] Show revision history and restore action.
- [ ] Show stale-impact warning before replacement.
- [ ] Show recent AI anchor jobs.
- [ ] F2 does not expose clip regenerate/start controls; those remain F3.

## Release gates

- [ ] Migration is deterministic and `makemigrations --check --dry-run` passes.
- [ ] Full normal Django suite passes.
- [ ] Full PostgreSQL suite passes.
- [ ] Focused revision/stale/upload/AI-target tests pass.
- [ ] Existing E1–E4/F1/media/provider tests remain green.
- [ ] Existing six-primary-navigation contract remains green.
- [ ] Merge to main.
- [ ] Sync Render deploy branch.
- [ ] Production migration applies successfully.
- [ ] New Render instance returns `/healthz` 200 and deploy is live.
- [ ] Master plan updated with exact CI/PR/deploy evidence.

## Closeout

Status: NOT STARTED  
Migration: `0018_sequence_anchor_controls_f2`  
CI: —  
PR: —  
Main commit: —  
Deploy: —  
Paid generation: none required for release.  
Next exact task after F2: **F3 — Clip controls.**
