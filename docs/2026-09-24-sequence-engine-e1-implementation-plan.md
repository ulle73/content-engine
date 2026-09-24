# Sequence Engine E1 — Implementation Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Parent plan:** `docs/2026-09-23-content-engine-creative-intelligence-implementation-plan.md`

> E1 builds only the durable sequence domain/schema. It does not build timeline UI, automatic storyboards, paid generation orchestration or provider-specific sequence code.

## Architecture rule

Sequence Engine orchestrates existing objects:

```text
SequenceProject
  K0 (SequenceAnchor -> MediaAsset)
   ↓
  Clip1 (SequenceClip)
   └─ V1/V2/... (SequenceClipVersion -> MediaGeneration)
   ↓
  K1 (same exact SequenceAnchor/MediaAsset)
   ↓
  Clip2
   ↓
  K2
```

No duplicate media table and no duplicate generation lifecycle may be introduced.

## E1.1 Schema

- [x] Add `SequenceProject`.
- [x] Add `SequenceAnchor`.
- [x] Add `SequenceClip`.
- [x] Add `SequenceClipVersion`.
- [x] Project owns ordered anchors and clips.
- [x] Anchor points to existing `MediaAsset`.
- [x] ClipVersion points one-to-one to existing `MediaGeneration`.
- [x] Clip stores trusted recipe id/version, optional model override and target metadata.
- [x] Clip stores one selected version without deleting rejected/older candidates.
- [x] Blueprint id/version hooks exist but no Blueprint Engine is built in E1.

## E1.2 Integrity and ownership

- [x] Anchor positions are unique within a project.
- [x] Clip positions are unique within a project.
- [x] Clip-version numbers are unique within a clip and start at 1.
- [x] START anchor must precede END anchor.
- [x] Both clip anchors must belong to the clip project.
- [x] Anchor MediaAsset must belong to the project company.
- [x] Anchor must be a non-logo image.
- [x] ClipVersion MediaGeneration must belong to the project company.
- [x] ClipVersion MediaGeneration must be video.
- [x] One MediaGeneration cannot be reused as two different clip-version provenance records.
- [x] A selected version must belong to the same clip.
- [x] Anchor assets are protected from normal media deletion.
- [x] A MediaGeneration referenced by sequence provenance is protected from deletion.
- [x] Deleting a SequenceProject removes sequence metadata, not the underlying MediaAsset/MediaGeneration.

## E1.3 Service layer

- [x] `create_sequence_project()`
- [x] `add_anchor()`
- [x] `replace_anchor_asset()`
- [x] `set_anchor_locked()`
- [x] `create_clip()`
- [x] `attach_generation_to_clip()`
- [x] `select_clip_version()`
- [x] `reject_clip_version()`
- [x] `sequence_snapshot()`
- [x] Trusted recipe validation is reused from current CreativeRecipe registry.
- [x] Version provenance snapshots recipe/model/prompt/references/usage/cost without provider calls.

## E1.4 Acceptance proof

The test suite must prove this exact graph can persist:

```text
K0 → Clip1 → K1 → Clip2 → K2
```

and that Clip1.END and Clip2.START reference the **same K1 primary key**.

Additional proof:

- [x] Two versions can exist on Clip1.
- [x] Selecting V2 preserves V1 and simply changes selection.
- [x] Locked K1 cannot silently change asset.
- [x] Cross-company asset/generation injection fails.
- [x] Existing normal MediaAsset and MediaGeneration rows survive project deletion.
- [x] No provider request is made by E1.

## E1.5 Release gates

Do not mark E1 complete until:

- [x] `makemigrations --check --dry-run` passes.
- [x] migration applies on CI.
- [x] full normal Django suite passes.
- [x] full PostgreSQL suite passes.
- [x] model/system checks pass.
- [x] focused Sequence Engine tests pass.
- [x] migration deploys successfully on Render.
- [x] Render health check returns healthy after migration.
- [x] master implementation plan is updated with commit/PR/deploy evidence.

## Closeout

Status: DONE — E1 Sequence Engine domain/schema is implemented, fully tested and live.  
Files changed: `engine/models.py`, `engine/sequence.py`, `engine/media.py`, `engine/migrations/0015_sequence_engine_e1.py`, `engine/test_sequence.py`, this ledger and the master implementation plan.  
Architecture delivered: `SequenceProject` owns ordered `SequenceAnchor` and `SequenceClip` rows; anchors point to existing `MediaAsset`; clip candidates use `SequenceClipVersion` and point one-to-one to existing `MediaGeneration`. No second media store or provider lifecycle was added.  
Integrity delivered: company isolation for anchor assets and generations, non-logo image anchors, forward-only clip anchors, unique project positions, version numbering, one generation per clip-version provenance row, same-clip selected-version validation, locked-anchor replacement protection, anchor MediaAsset deletion protection and MediaGeneration provenance protection.  
Versioning delivered: multiple clip candidates remain intact; selecting a new winner changes `selected_version` and candidate status without deleting the prior version.  
Acceptance proof: focused tests persist `K0 → Clip1 → K1 → Clip2 → K2` and verify that Clip1.END and Clip2.START use the exact same K1 primary key. Tests also cover cross-company injection, DB uniqueness, locked anchors, delete/protect semantics, version selection and provenance snapshots.  
Initial CI fix: first run exposed that empty JSON provenance snapshots were valid but Django `full_clean()` rejected them. `reference_snapshot`, `usage_snapshot` and `cost_snapshot` were corrected to `blank=True`; service validation was also normalized to `SequenceError`.  
Migration: `engine.0015_sequence_engine_e1`.  
CI: run `35988142066` passed `makemigrations --check --dry-run`, migration apply/check, Django/system checks, MCP import, the full normal Django test suite and the full PostgreSQL suite.  
PR: #50  
Main commit: `65909657c1709af2411798dc8bb9de08a1bd1326`  
Render deploy: `dep-daqfqu0u01pc73811is0` on `content-engine-mcp`; production log shows `Applying engine.0015_sequence_engine_e1... OK`, new instance startup complete, `/healthz` 200 and deploy status `live`.  
Provider impact: none. E1 makes no provider call and starts no paid generation.  
Known limitations: E2 Anchor Chain execution, E3 Output Chain, E4 Transition Bridge orchestration and all timeline/blueprint UI remain intentionally out of E1.  
Next exact task after E1: **E2 — Anchor Chain mode.**
