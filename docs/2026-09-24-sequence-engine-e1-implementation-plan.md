# Sequence Engine E1 — Implementation Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until every acceptance gate below is verified.  
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

- [ ] Add `SequenceProject`.
- [ ] Add `SequenceAnchor`.
- [ ] Add `SequenceClip`.
- [ ] Add `SequenceClipVersion`.
- [ ] Project owns ordered anchors and clips.
- [ ] Anchor points to existing `MediaAsset`.
- [ ] ClipVersion points one-to-one to existing `MediaGeneration`.
- [ ] Clip stores trusted recipe id/version, optional model override and target metadata.
- [ ] Clip stores one selected version without deleting rejected/older candidates.
- [ ] Blueprint id/version hooks exist but no Blueprint Engine is built in E1.

## E1.2 Integrity and ownership

- [ ] Anchor positions are unique within a project.
- [ ] Clip positions are unique within a project.
- [ ] Clip-version numbers are unique within a clip and start at 1.
- [ ] START anchor must precede END anchor.
- [ ] Both clip anchors must belong to the clip project.
- [ ] Anchor MediaAsset must belong to the project company.
- [ ] Anchor must be a non-logo image.
- [ ] ClipVersion MediaGeneration must belong to the project company.
- [ ] ClipVersion MediaGeneration must be video.
- [ ] One MediaGeneration cannot be reused as two different clip-version provenance records.
- [ ] A selected version must belong to the same clip.
- [ ] Anchor assets are protected from normal media deletion.
- [ ] A MediaGeneration referenced by sequence provenance is protected from deletion.
- [ ] Deleting a SequenceProject removes sequence metadata, not the underlying MediaAsset/MediaGeneration.

## E1.3 Service layer

- [ ] `create_sequence_project()`
- [ ] `add_anchor()`
- [ ] `replace_anchor_asset()`
- [ ] `set_anchor_locked()`
- [ ] `create_clip()`
- [ ] `attach_generation_to_clip()`
- [ ] `select_clip_version()`
- [ ] `reject_clip_version()`
- [ ] `sequence_snapshot()`
- [ ] Trusted recipe validation is reused from current CreativeRecipe registry.
- [ ] Version provenance snapshots recipe/model/prompt/references/usage/cost without provider calls.

## E1.4 Acceptance proof

The test suite must prove this exact graph can persist:

```text
K0 → Clip1 → K1 → Clip2 → K2
```

and that Clip1.END and Clip2.START reference the **same K1 primary key**.

Additional proof:

- [ ] Two versions can exist on Clip1.
- [ ] Selecting V2 preserves V1 and simply changes selection.
- [ ] Locked K1 cannot silently change asset.
- [ ] Cross-company asset/generation injection fails.
- [ ] Existing normal MediaAsset and MediaGeneration rows survive project deletion.
- [ ] No provider request is made by E1.

## E1.5 Release gates

Do not mark E1 complete until:

- [ ] `makemigrations --check --dry-run` passes.
- [ ] migration applies on CI.
- [ ] full normal Django suite passes.
- [ ] full PostgreSQL suite passes.
- [ ] model/system checks pass.
- [ ] focused Sequence Engine tests pass.
- [ ] migration deploys successfully on Render.
- [ ] Render health check returns healthy after migration.
- [ ] master implementation plan is updated with commit/PR/deploy evidence.

## Closeout

Status: NOT STARTED  
Files changed: —  
Migration: —  
CI: —  
PR: —  
Main commit: —  
Render deploy: —  
Known limitations: E2 Anchor Chain execution, E3 Output Chain, E4 Transition Bridge orchestration and all timeline/blueprint UI remain intentionally out of E1.  
Next exact task after E1: **E2 — Anchor Chain mode.**
