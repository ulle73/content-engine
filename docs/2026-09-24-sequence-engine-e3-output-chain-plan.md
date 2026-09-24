# Sequence Engine E3 — Output Chain Execution Ledger

**Date:** 2026-09-24  
**Status:** ACTIVE until every release gate passes.  
**Depends on:** E1 schema + E2 Anchor Chain live.

> E3 is an explicit operation. It may replace the shared end/next-start anchor only after the user has selected a completed source clip version and explicitly unlocked that anchor. It never runs automatically.

## E3.1 Final-frame extraction

- [ ] Decode the final display frame from an existing stored video MediaAsset locally with PyAV.
- [ ] Do not call Higgsfield/OpenAI/another provider for frame extraction.
- [ ] Persist the derived PNG through the existing MediaAsset/R2 storage model.
- [ ] Derived image keeps source MediaGeneration/provider provenance.
- [ ] Expired/unreadable source video fails closed.
- [ ] Only deterministic final-frame extraction is supported in E3.

## E3.2 Explicit output-chain promotion

- [ ] Source SequenceClipVersion must be explicitly selected.
- [ ] Source MediaGeneration must be completed.
- [ ] Source generation must have exactly one stored video output.
- [ ] Target is derived from the source clip's canonical end anchor; caller cannot substitute another anchor.
- [ ] Target anchor must also be the start anchor of a following clip.
- [ ] Locked target anchor fails closed until explicitly unlocked.
- [ ] Existing selected downstream clip fails closed rather than silently becoming stale.
- [ ] Promotion changes the shared anchor asset, not the anchor identity.
- [ ] Previous canonical anchor asset is preserved.
- [ ] Promotion is idempotent for the same source version.

## E3.3 Structured provenance

- [ ] Add explicit `output_chain` anchor source type.
- [ ] Add structured anchor source metadata.
- [ ] Record source project, clip, clip version and generation IDs.
- [ ] Record source video asset ID/hash.
- [ ] Record previous anchor asset ID.
- [ ] Record derived image asset ID/hash.
- [ ] Record frame selector, frame index, timestamp/PTS when available.
- [ ] Keep `source_clip_version` FK as structured sequence provenance.
- [ ] Model validation rejects incomplete output-chain provenance.

## E3.4 Downstream safety

- [ ] Existing unselected downstream candidates are not deleted.
- [ ] Those candidates become stale naturally because their START_IMAGE no longer matches the canonical anchor.
- [ ] E2 stale-anchor check blocks preview of stale candidates before provider access.
- [ ] New downstream E2 candidates use the newly promoted canonical frame.
- [ ] Promotion makes no paid or non-billable provider request.

## Acceptance proof

Starting from:

```text
K0 → Clip1(selected completed V1) → K1 → Clip2 → K2
```

Explicitly unlock K1 and promote Clip1 V1 final frame.

Then prove:

1. K1 primary key is unchanged.
2. K1 MediaAsset becomes a newly derived image of Clip1's real final video frame.
3. Clip1.end_anchor and Clip2.start_anchor still reference the exact same K1.
4. K1 is labeled `output_chain`.
5. K1 source provenance identifies Clip1 V1, the generation, source video and exact final frame.
6. Original K1 MediaAsset still exists.
7. Old unselected Clip2 candidates still exist but fail stale-anchor preview before provider access.
8. No provider API call occurs during promotion.

## Release gates

- [ ] Migration is deterministic and `makemigrations --check --dry-run` passes.
- [ ] Full normal Django suite passes.
- [ ] Full PostgreSQL suite passes.
- [ ] Existing E1/E2/media/provider tests remain green.
- [ ] Focused frame-extraction/output-chain tests pass.
- [ ] Merge to main.
- [ ] Sync Render deploy branch.
- [ ] Production migration applies successfully.
- [ ] New Render instance returns `/healthz` 200 and deploy is live.
- [ ] Master plan updated with exact PR/commit/CI/deploy evidence.

## Closeout

Status: NOT STARTED  
Migration: `0016_sequence_output_chain_provenance`  
CI: —  
PR: —  
Main commit: —  
Deploy: —  
Provider calls: none.  
Next exact task after E3: **E4 — Transition Bridge mode.**
