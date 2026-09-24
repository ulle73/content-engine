# Sequence Engine E3 — Output Chain Execution Ledger

**Date:** 2026-09-24  
**Status:** DONE — implemented, CI-verified and deployed 2026-09-24.  
**Depends on:** E1 schema + E2 Anchor Chain live.

> E3 is an explicit operation. It may replace the shared end/next-start anchor only after the user has selected a completed source clip version and explicitly unlocked that anchor. It never runs automatically.

## E3.1 Final-frame extraction

- [x] Decode the final display frame from an existing stored video MediaAsset locally with PyAV.
- [x] Do not call Higgsfield/OpenAI/another provider for frame extraction.
- [x] Persist the derived PNG through the existing MediaAsset/R2 storage model.
- [x] Derived image keeps source MediaGeneration/provider provenance.
- [x] Expired/unreadable source video fails closed.
- [x] Only deterministic final-frame extraction is supported in E3.

## E3.2 Explicit output-chain promotion

- [x] Source SequenceClipVersion must be explicitly selected.
- [x] Source MediaGeneration must be completed.
- [x] Source generation must have exactly one stored video output.
- [x] Target is derived from the source clip's canonical end anchor; caller cannot substitute another anchor.
- [x] Target anchor must also be the start anchor of a following clip.
- [x] Locked target anchor fails closed until explicitly unlocked.
- [x] Existing selected downstream clip fails closed rather than silently becoming stale.
- [x] Promotion changes the shared anchor asset, not the anchor identity.
- [x] Previous canonical anchor asset is preserved.
- [x] Promotion is idempotent for the same source version.

## E3.3 Structured provenance

- [x] Add explicit `output_chain` anchor source type.
- [x] Add structured anchor source metadata.
- [x] Record source project, clip, clip version and generation IDs.
- [x] Record source video asset ID/hash.
- [x] Record previous anchor asset ID.
- [x] Record derived image asset ID/hash.
- [x] Record frame selector, frame index, timestamp/PTS when available.
- [x] Keep `source_clip_version` FK as structured sequence provenance.
- [x] Model validation rejects incomplete output-chain provenance.

## E3.4 Downstream safety

- [x] Existing unselected downstream candidates are not deleted.
- [x] Those candidates become stale naturally because their START_IMAGE no longer matches the canonical anchor.
- [x] E2 stale-anchor check blocks preview of stale candidates before provider access.
- [x] New downstream E2 candidates use the newly promoted canonical frame.
- [x] Promotion makes no paid or non-billable provider request.

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

- [x] Migration is deterministic and `makemigrations --check --dry-run` passes.
- [x] Full normal Django suite passes.
- [x] Full PostgreSQL suite passes.
- [x] Existing E1/E2/media/provider tests remain green.
- [x] Focused frame-extraction/output-chain tests pass.
- [x] Merge to main.
- [x] Sync Render deploy branch.
- [x] Production migration applies successfully.
- [x] New Render instance returns `/healthz` 200 and deploy is live.
- [x] Master plan updated with exact PR/commit/CI/deploy evidence.

## Closeout

Status: DONE — explicit Output Chain final-frame promotion is implemented, fully tested and live.  
Implementation: selected completed clip versions can explicitly promote their real stored video's final decoded frame into the shared end/next-start anchor. The anchor primary key is preserved; only its MediaAsset changes.  
Frame extraction: local PyAV decode only; no provider request. The final display frame is saved as a normal generated MediaAsset through existing storage with generation/provider provenance.  
Safety: source version must be selected and completed; target must be the source clip's own end anchor and also start a following clip; locked target fails closed; selected downstream clip fails closed; old downstream unselected candidates remain and E2 stale-anchor checks block them before preview.  
Provenance: `source_type=output_chain`, `source_clip_version` FK and structured `source_metadata` capture project/clip/version/generation IDs, source video ID/hash, previous anchor asset, derived asset ID/hash and final-frame selector/index/timestamp/PTS.  
Idempotency: re-promoting the same selected version returns the already promoted anchor without creating another frame asset.  
Migration: `0016_sequence_output_chain_provenance`.  
CI: run `35996836039` passed `makemigrations --check --dry-run`, migration/check/static/MCP gates, full normal Django suite and full PostgreSQL suite, including real H.264 frame-extraction tests.  
PR: #54  
Main commit: `468b26e534ac69ed83332a876a5164e813b219ed`  
Deploy: `dep-daqh4rc9v7es73d5p03g`; production log shows `Applying engine.0016_sequence_output_chain_provenance... OK`, new instance `9fjhr` startup complete, `/healthz` 200 and deploy status `live`.  
Provider calls: none; no paid or estimate request is part of Output Chain promotion.  
Next exact task after E3: **E4 — Transition Bridge mode.**
