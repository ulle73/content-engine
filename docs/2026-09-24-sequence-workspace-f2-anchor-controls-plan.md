# Sequence Workspace F2 — Anchor Controls Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Depends on:** E1–E4 + F1 live.

> F2 makes canonical anchors editable without making sequence history destructive. All replacements are explicit, revisioned and stale-aware. AI anchors reuse the existing MediaGeneration review/start gate.

## F2.1 Anchor revision model

- [x] Add non-destructive `SequenceAnchorRevision`.
- [x] Seed revision 1 for every existing anchor during migration.
- [x] Every newly created anchor receives revision 1.
- [x] Every replacement/restore creates a new revision number.
- [x] Historical revision assets are deletion-protected.
- [x] Revision stores asset, source type, source clip provenance, source metadata, reason and actor.
- [x] Restore creates a new revision; history is never rewound/deleted.

## F2.2 Stale safety

- [x] Add explicit `stale` candidate status for clips and bridges.
- [x] Compute clip/bridge versions impacted by an anchor change.
- [x] Anchor replacement with affected versions requires explicit confirmation.
- [x] Confirmed change preserves those versions and marks them stale.
- [x] Selected stale clip/bridge candidates are explicitly unselected and parent segment returns to review.
- [x] Stale candidates cannot be re-selected.
- [x] Locked anchor cannot be replaced or restored until explicitly unlocked.
- [x] Existing E2 stale-reference checks remain an additional fail-closed layer.

## F2.3 Existing MediaAsset + upload controls

- [x] Add new anchor from an existing company-scoped image.
- [x] Add new anchor from JPEG/PNG/WebP upload.
- [x] Replace unlocked anchor from existing company-scoped image.
- [x] Replace unlocked anchor via upload.
- [x] Upload is not persisted if stale confirmation is still missing.
- [x] Applied/generated anchor assets are retained permanently.
- [x] Cross-company, video and logo assets fail closed.
- [x] Current provenance is visible in workspace.

## F2.4 AI anchor generation

- [x] Add explicit `SequenceAnchorGenerationTarget`.
- [x] AI job is bound to project + create/replace anchor intent.
- [x] AI prepare reuses existing `ContentRun → MediaGeneration → Creative Director` image pipeline.
- [x] Prepare performs no paid provider generation.
- [x] Existing Media job review page is reused.
- [x] Paid image generation can only start through existing `start_reviewed_job()`.
- [x] Completed alternatives show “Use as anchor” on the existing job page.
- [x] Applying result validates exact generation ownership and image kind.
- [x] Create-mode AI result appends a new canonical anchor.
- [x] Replace-mode AI result passes the same lock/stale/revision controls as every other replacement.
- [x] AI target/job links back to Sequence workspace.

## F2.5 Workspace controls

- [x] Add project-level controls for Media / upload / AI new anchor.
- [x] Add per-anchor lock/unlock.
- [x] Add per-anchor replace from Media.
- [x] Add per-anchor upload replacement.
- [x] Add per-anchor AI replacement.
- [x] Show revision history and restore action.
- [x] Show stale-impact warning before replacement.
- [x] Show recent AI anchor jobs.
- [x] F2 does not expose clip regenerate/start controls; those remain F3.

## Release gates

- [x] Migration is deterministic and `makemigrations --check --dry-run` passes.
- [x] Full normal Django suite passes.
- [x] Full PostgreSQL suite passes.
- [x] Focused revision/stale/upload/AI-target tests pass.
- [x] Existing E1–E4/F1/media/provider tests remain green.
- [x] Existing six-primary-navigation contract remains green.
- [x] Merge to main.
- [x] Sync Render deploy branch.
- [x] Production migration applies successfully.
- [x] New Render instance returns `/healthz` 200 and deploy is live.
- [x] Master plan updated with exact CI/PR/deploy evidence.

## Closeout

Status: DONE — explicit, versioned Anchor Controls are implemented, fully CI-verified and live.  
Revision model: `SequenceAnchorRevision` preserves every canonical anchor asset/provenance state. Migration `0018` seeds revision 1 for existing anchors; create/replace/restore/output-chain changes append history rather than rewinding it. Historical assets are protected from cleanup.  
Stale safety: anchor impact is computed across dependent clip/bridge versions. Replacements with existing candidates require explicit confirmation; confirmed changes preserve those candidates as `stale`, clear any affected selected version and return the parent segment to review. Locked anchors fail closed until explicitly unlocked.  
Media/upload controls: users can add anchors from company Media, upload JPEG/PNG/WebP, replace unlocked anchors from Media/upload and restore prior revisions. Upload replacement checks stale confirmation before storing the new asset, avoiding orphan uploads.  
AI anchors: `SequenceAnchorGenerationTarget` binds an existing image MediaGeneration to a create/replace anchor intent. Preparation reuses the normal ContentRun → Creative Director → MediaGeneration path and does not start paid generation. The existing media-job review/start page remains the only paid-start gate. Completed alternatives can then be explicitly applied back to the exact bound project/anchor with the same lock/stale/revision rules.  
Workspace: F2 controls expose add-from-Media, upload, AI proposal, lock/unlock, replace, revision restore, current provenance, stale-impact warnings and recent AI anchor jobs. Clip-generation controls remain out of F2.  
Initial CI finding: run `36003901835` passed the full normal suite but PostgreSQL exposed `FOR UPDATE cannot be applied to the nullable side of an outer join` in F2 anchor mutation locking. Nullable `source_clip_version`, `target_anchor` and `applied_anchor` joins were removed from locked queries without changing row-lock semantics.  
CI: rerun `36004141029` passed `makemigrations --check --dry-run`, migration apply/check, Django/system/static/MCP gates, the full normal Django suite and the full PostgreSQL suite.  
Migration: `0018_sequence_anchor_controls_f2`  
PR: #60  
Main commit: `7c2568982e29f8aa449301a1734ed3585ffd3426`  
Deploy: `dep-daqi56gu01pc7388oqfg`; production log shows `Applying engine.0018_sequence_anchor_controls_f2... OK`, new instance `g2ht2` completed startup, returned `/healthz` 200 and Render marked the deploy `live`.  
Paid generation: none was started during implementation or release verification.  
Next exact task after F2: **F3 — Clip controls.**
