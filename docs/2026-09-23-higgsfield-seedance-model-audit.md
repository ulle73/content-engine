# Higgsfield Video Model Audit — Seedance / Continuity Candidates

**Date:** 2026-09-23  
**Task:** B2 from `docs/2026-09-23-content-engine-creative-intelligence-implementation-plan.md`  
**Scope:** Public/current provider-contract audit only. No model is enabled by this document and no paid generation is performed.

---

## 1. Source priority

Higgsfield's shared API documentation explicitly says:

1. discover models from the current Higgsfield catalog/console,
2. treat the selected model's model-specific API documentation as the authoritative request contract,
3. use shared docs for lifecycle/authentication/errors/billing,
4. treat supplementary OpenAPI as non-authoritative for model availability,
5. distinguish documented availability from availability verified with the authenticated account.

Content Engine must therefore not infer server-account access merely because a public model page exists.

Primary shared source:

- https://docs.higgsfield.ai/docs/llms.txt

Billing/estimate source:

- https://docs.higgsfield.ai/docs/concepts/billing-and-retention

The estimate contract remains:

`POST /estimate/{exact-model-path}`

with the same request body that would be used for generation. The authenticated estimate response contains `credits` and `usd`; the authenticated estimate is the authoritative amount.

---

# 2. Current Seedance API contracts

## 2.1 Seedance 2.5 — Text-to-Video

**Exact model path**

`bytedance/seedance-2.5/text-to-video`

**Official API page**

https://open.higgsfield.ai/models/bytedance/seedance-2.5/text-to-video/api-reference

**Current request contract**

- `prompt`: required
- `duration`: integer, 4–30 seconds, default 5
- `resolution`: 480p or 720p, default 720p
- `aspect_ratio`: 16:9, 4:3, 1:1, 3:4, 9:16, 21:9; default 16:9
- `output_format`: mp4 or mov, default mp4
- `generate_audio`: boolean, default **true**

### Important Content Engine consequence

The current Content Engine defaults `audio_intent` to `none`.

Therefore Seedance 2.5 T2V must **not** be enabled by merely adding it to the registry while leaving the current generic Higgsfield payload unchanged. If `generate_audio` is omitted, the provider default is true, which would violate Content Engine's current intent.

B3 must explicitly compile:

`generate_audio=false`

unless audio was requested.

---

## 2.2 Seedance 2.5 — Image-to-Video

**Exact model path**

`bytedance/seedance-2.5/image-to-video`

**Official API page**

https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference

**Current request contract**

- `prompt`: optional
- `duration`: integer, 4–30 seconds, default 5
- `image_url`: required
- `resolution`: 480p or 720p, default 720p
- `end_image_url`: optional
- `output_format`: mp4 or mov, default mp4
- `generate_audio`: boolean, default **true**

### Continuity relevance

This is a direct fit for canonical:

- START_IMAGE → `image_url`
- END_IMAGE → `end_image_url`

It is therefore a primary candidate for Content Engine's future Anchor Chain and `scroll_transition_bridge` workflows.

### Important aspect-ratio detail

The current Seedance 2.5 I2V API page does **not** expose `aspect_ratio`, unlike its T2V endpoint.

Content Engine must therefore model aspect-ratio behavior per mode/endpoint rather than assuming one global behavior for the whole model family.

---

## 2.3 Seedance 2.5 — Reference-to-Video

**Exact model path**

`bytedance/seedance-2.5/reference-to-video`

**Official API page**

https://open.higgsfield.ai/models/bytedance/seedance-2.5/reference-to-video/api-reference

**Current request contract includes**

- prompt
- duration 4–30
- `audio_urls[]`
- `image_urls[]`
- `video_urls[]`
- resolution 480p/720p
- explicit aspect ratio
- output format
- audio generation

### Content Engine ruling

Do **not** enable this route before C1 introduces canonical persisted multi-reference roles.

The current single `source_asset` relation is not sufficient to represent this endpoint honestly.

---

# 3. Seedance 2.0 API contracts

## 3.1 Seedance 2.0 — Text-to-Video

**Exact model path**

`bytedance/seedance-2.0/text-to-video`

**Official API page**

https://open.higgsfield.ai/models/bytedance/seedance-2.0/text-to-video/api-reference

**Current request contract**

- `prompt`: required
- `duration`: integer, 4–15 seconds
- `resolution`: 480p, 720p, 1080p, 4k
- explicit aspect ratio: 16:9, 4:3, 1:1, 3:4, 9:16, 21:9
- `generate_audio`: boolean, default true

### Initial routing value

Seedance 2.0 is especially relevant where higher API output resolution matters.

---

## 3.2 Seedance 2.0 — Image-to-Video

**Exact model path**

`bytedance/seedance-2.0/image-to-video`

**Official API page**

https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference

**Current request contract**

- `prompt`: optional
- `duration`: integer, 4–15 seconds
- `image_url`: required
- `resolution`: 480p, 720p, 1080p, 4k
- `end_image_url`: optional
- `generate_audio`: boolean, default true

### Initial routing value

This provides the same first/last-frame primitive as Seedance 2.5 but supports higher documented API resolutions.

Potential future routing:

- continuity/longer clips → Seedance 2.5 candidate
- high-resolution final up to 4K, <=15 s → Seedance 2.0 candidate

This must remain evidence-driven rather than hard-coded as an aesthetic winner.

---

## 3.3 Seedance 2.0 — Reference-to-Video

**Exact model path**

`bytedance/seedance-2.0/reference-to-video`

**Official API page**

https://open.higgsfield.ai/models/bytedance/seedance-2.0/reference-to-video/api-reference

It supports image/video/audio reference arrays, 4–15 seconds, aspect ratio and up to 4K.

### Content Engine ruling

Defer until C1 typed multi-reference storage is implemented.

---

# 4. Higgsfield's official Seedance usage guidance

Official help-center guidance:

https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance

Important findings:

- Seedance 2.5 supports longer clips than 2.0.
- Seedance 2.0 is positioned for maximum quality / higher resolution.
- Higgsfield recommends starting new prompts at 720p, validating motion/composition first, then increasing final quality.
- Recommended prompting order: subject/action → setting/lighting → camera move → mood/style.
- Specific camera vocabulary includes dolly in, truck left, arc shot, push in, pull back wide, handheld follow, crane up and orbital move.
- For a jerky transition, Higgsfield specifically recommends using the final frame of one clip and opening frame of the next as references, then generating a first-and-last-frame transition.
- Resolution and duration are major cost drivers.

This directly supports Content Engine's planned:

`Draft → Select → Final`

and:

`K0 → Clip1 → K1 → Clip2 → K2`

architecture.

---

# 5. Seedance 2.5 prompt-structure evidence

Official Higgsfield guide:

https://higgsfield.ai/blog/seedance-2-5-prompting-guide

It recommends structured prompts using concepts such as:

- GLOBAL STYLE
- SCENE
- CHARACTERS
- LOCATION
- FIRST FRAME AND BLOCKING
- shot/action breakdown
- OPTICS
- CAMERA
- PHYSICS
- LIGHTING
- AUDIO

This should later become a Seedance-specific prompt profile/compiler strategy.

Do not copy one giant static prompt across every recipe.

---

# 6. Important API-vs-web resolution discrepancy

Higgsfield's Creator Hub says Seedance 2.5 can reach up to 1080p on certain web plans.

However, the **current model-specific Seedance 2.5 API pages** expose only:

- 480p
- 720p

for the API endpoints audited above.

Content Engine is an API integration.

Therefore:

> Use the model-specific API contract for server routing. Do not expose 1080p for Seedance 2.5 in Content Engine unless the model-specific API contract itself later exposes it and is reverified.

Seedance 2.0's API currently documents 1080p and 4K.

---

# 7. Other current continuity candidate: Kling O3

Current API page:

https://open.higgsfield.ai/models/kling-video/o3/first-last-frame/api-reference

**Exact model path**

`kling-video/o3/first-last-frame`

Current request contract includes:

- `mode`: std / pro / 4k
- `sound`: on / off
- `prompt`
- duration 3–15 seconds
- aspect ratio 16:9 / 9:16 / 1:1
- `first_frame_url`
- `last_frame_url`
- optional multi-shot/multi-prompt controls

This is a serious future candidate for continuity/bridge comparisons.

### Why it should not be added blindly in B3

Its endpoint and parameter vocabulary differ materially from the current Content Engine convention:

`{model_root}/{text-to-video|image-to-video}`

It should be represented through an explicit mode/endpoint request contract rather than special-cased string logic.

---

# 8. Required architecture adjustments discovered by B2

B1 introduced model profiles, but this audit exposes additional needs for B3.

## 8.1 Duration ranges

Current registry primarily models discrete duration tuples.

Seedance uses continuous integer ranges:

- 2.5: 4–30
- 2.0: 4–15
- Kling O3 First/Last: 3–15

B3 should add explicit `duration_range` support rather than enumerating every integer.

---

## 8.2 Mode-specific request contracts

One global model-family profile is insufficient for all request behavior.

Example Seedance 2.5:

- T2V exposes explicit aspect ratio
- I2V currently does not
- I2V requires START_IMAGE
- I2V optionally accepts END_IMAGE

B3 should evolve the mode contract beyond references to include:

- exact endpoint/model path
- prompt required/optional
- duration contract
- resolution options
- aspect-ratio behavior/options
- audio parameter/default behavior
- output-format options
- canonical → provider media-field mapping

This remains one model router; it is not a second routing system.

---

## 8.3 Explicit audio behavior

Seedance defaults `generate_audio=true`.

Content Engine defaults audio intent to none.

Therefore the model-specific provider payload must explicitly map intent:

- NONE → `generate_audio=false`
- requested native audio → `generate_audio=true`

Never rely on provider defaults when they conflict with Content Engine semantics.

---

## 8.4 Exact endpoint paths

Do not assume every Higgsfield model follows:

`model_root + "/" + brief.mode`

Seedance happens to have matching T2V/I2V endpoint names.

Kling O3 First/Last Frame does not.

The mode/request profile should supply the exact provider path.

---

# 9. Initial B3 enablement recommendation

For the first real multi-model router iteration, keep scope controlled.

## Enable after B3 adapter support

1. Existing `kling-video/v2.5-turbo/pro`
2. `bytedance/seedance-2.5` T2V + I2V
3. `bytedance/seedance-2.0` T2V + I2V

This creates meaningful Auto choice without prematurely adding every catalog model.

## Keep audited but disabled initially

- Seedance 2.5 Reference-to-Video
- Seedance 2.0 Reference-to-Video
- Kling O3 First/Last Frame
- Kling O3 Image Reference
- other reference-heavy/video-edit endpoints

These become natural candidates after C1/C2.

---

# 10. Cost/estimate behavior

Shared official billing docs state:

- exact price depends on model + parameters,
- call `POST /estimate/{model-path}` using the same parameters before generation,
- response includes `credits` and `usd`,
- the authenticated estimate is authoritative.

Informational current catalog pricing observed during this audit includes broad per-second ranges, but those values must **not** replace authenticated preflight.

Content Engine's existing reviewed-estimate → explicit paid start design remains correct.

---

# 11. Account availability evidence

A read-only Higgsfield MCP catalog lookup for `seedance` was attempted during B2.

It failed with:

`FNF API GET /mcp/workspaces failed (423)`

This is a Higgsfield MCP workspace-access failure.

It is **not** evidence that Seedance is unavailable to the dedicated Golfkuponger Content Engine server credential.

Conversely, the public docs are not evidence that the Golfkuponger API account can use the models.

The correct account-scoped check remains Content Engine's own authenticated non-billable estimate/preflight after B3 supports the request contract.

---

# 12. B2 decision

The model-contract audit is sufficient to proceed to B3.

B3 must **not** merely append Seedance IDs to the existing registry.

It must first make provider request compilation mode-aware so that:

- exact endpoint path is explicit,
- ranges are normalized correctly,
- Seedance audio defaults cannot leak through,
- aspect ratio is only sent where documented,
- resolution is only sent where documented,
- current Kling behavior remains backwards compatible.

No new paid generation is necessary for B3 implementation/tests.
