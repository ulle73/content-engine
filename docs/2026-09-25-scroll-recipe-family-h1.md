# H1 Scroll Recipe Family — Evidence and Production Contract

**Date:** 2026-09-25  
**Task:** H1 from `docs/2026-09-23-content-engine-creative-intelligence-implementation-plan.md`  
**Scope:** Trusted recipe methods and compiler/routing constraints only. No paid media generation is required or authorized by this task.

## 1. Current provider evidence rechecked

H1 rechecked the current official Higgsfield/Seedance material on 2026-09-25.

Primary sources:

- https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance
- https://higgsfield.ai/blog/seedance-2-5-prompting-guide
- https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference
- https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference

Current findings relevant to scroll recipes:

- Higgsfield recommends structured prompts that separate subject/action, setting/lighting, camera movement and mood/style.
- Current Seedance guidance explicitly recognizes camera vocabulary including dolly, truck, arc, push, pull, crane and orbital movement.
- For jerky transitions, Higgsfield recommends supplying the final frame of one clip and the opening frame of the next and using first-and-last-frame generation.
- Seedance 2.5 I2V currently requires a start image and accepts an optional end image, duration 4–30 seconds, 480p/720p, optional output format and explicit audio generation.
- Seedance 2.0 I2V currently requires a start image and accepts an optional end image, duration 4–15 seconds, resolutions through 4K and explicit audio generation.
- The model-specific API pages remain the request-contract source of truth. Creator Hub/web-plan resolution statements do not override API endpoint fields.
- A read-only Higgsfield plugin model-catalog query was attempted during H1 and again returned workspace error `423`. This does not prove model unavailability for Content Engine's dedicated server credential. Account availability remains authenticated estimate/preflight truth.

## 2. Shared scroll contract

Every H1 scroll recipe is:

- video-only,
- image-to-video,
- anchor-to-anchor,
- `START_IMAGE + END_IMAGE` required,
- single continuous shot,
- scrub-friendly forward and backward,
- compatible only with verified models that expose:
  - `reference_animation`,
  - `single_continuous_shot`,
  - `first_last_frame`.

This deliberately excludes current Kling 2.5 Turbo Pro from H1 scroll recipes because its verified Content Engine I2V contract has no END_IMAGE / first-last-frame capability. Current Seedance 2.5 and Seedance 2.0 profiles satisfy the required capability set.

Shared forbidden failure modes include:

- hard cuts,
- unexplained scene resets,
- perspective teleporting,
- random object creation,
- unrequested object disappearance,
- subject geometry drift,
- lighting resets,
- incoherent intermediate frames.

The compiler injects the scroll format contract from trusted recipe metadata, not from user Prompt Library text.

## 3. Recipe intent

| Recipe | Intended production method | Good result | Bad result |
| --- | --- | --- | --- |
| `scroll_orbit_hero` | restrained arc/orbit around a stable hero | camera moves around stable subject with continuous parallax and exact anchor landing | subject spins/morphs, orbit radius jumps, perspective teleports |
| `scroll_dolly_reveal` | push/pull/truck reveal through real parallax/occlusion | target emerges progressively through camera translation | digital zoom, crop jump, teleporting occluder |
| `scroll_macro_flythrough` | macro tracking along surfaces or through real visible openings | stable scale/texture/depth along a plausible close camera path | camera clips solids, texture swims, impossible scale shift |
| `scroll_exploded_reveal` | reversible component separation between assembled/exploded anchors | fixed part identities separate on clean paths and reassemble under reverse scrub | parts appear/disappear/melt/swap identity or collide |
| `scroll_environment_transition` | continuous spatial travel between environment anchors | one understandable route with gradual atmosphere/light evolution | hidden scene reset, background teleport, instant world swap |
| `scroll_transition_bridge` | simplest continuity-first bridge between two fixed anchors | uneventful smooth connection with coherent intermediate frames | spectacle event, morph, new object, late snap to end anchor |
| `scroll_product_showcase` | restrained premium arc/dolly around an anchored product | exact product identity/materials remain stable while camera reveals form | label/logo/shape/material mutation or unnecessary product spin |
| `scroll_landscape_flythrough` | smooth forward/crane/low-aerial travel through stable terrain | persistent terrain/horizon/landmarks with convincing depth | terrain morph, horizon bend, landmark duplication, terrain clipping |

## 4. Why these are recipes, not model hard-codes

The recipe registry declares capabilities, references, camera/motion/continuity method, forbidden failures and evaluation criteria.

The existing single `route_model()` remains authoritative. A recipe never names a provider as an execution shortcut. It may constrain provider family for the current trusted architecture, while exact eligibility is decided by verified model capabilities and request contracts.

This means a future verified model can become H1-compatible by truthfully exposing the required capabilities without rewriting eight recipes.

## 5. Verification target

H1 is complete only when:

- all eight recipe IDs exist in the trusted registry,
- every recipe has evidence, negative constraints, model-capability requirements and explicit good/bad criteria,
- current incompatible Kling is excluded from H1 scroll eligibility,
- current verified Seedance 2.5 and Seedance 2.0 are eligible for anchor-to-anchor requests,
- both Seedance compilers receive each recipe's format/camera/motion/continuity/negative constraints,
- model-specific request compilation still emits the exact audited I2V endpoint and START/END provider fields,
- generic image/video behavior remains unchanged,
- full SQLite + PostgreSQL CI passes.

No visual output-quality claim is made without an explicitly authorized paid generation. H1 validates production-method contracts and compilation, not aesthetic superiority.
