# H2 General Commercial Recipe Family — Evidence and Production Contract

**Date:** 2026-09-25  
**Task:** H2 from `docs/2026-09-23-content-engine-creative-intelligence-implementation-plan.md`  
**Scope:** Trusted commercial/social recipe methods and compiler/routing constraints only. No paid generation is required or authorized.

## 1. Current evidence rechecked

Current Higgsfield sources reviewed for H2:

- https://higgsfield.ai/blog/seedance-2-5-prompting-guide
- https://higgsfield.ai/blog/ai-product-videos-no-studio
- https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming
- https://higgsfield.ai/blog/most-reliable-ai-video-generators-2026
- https://higgsfield.ai/blog/cinema-studio-3.0
- current read-only Higgsfield Marketing Studio video-format catalog on 2026-09-25

Relevant current provider findings:

- Marketing Studio exposes dedicated modes for UGC, Selfie Testimonial, Product Showcase, Hyper Motion, Before and After, Tutorial, Unboxing, TV Spot and several hook-driven formats.
- Current UGC and testimonial examples are generally 12–15 seconds, creator/phone-camera framed and use generated audio.
- The current Product Showcase mode is explicitly product-centered.
- Hyper Motion is positioned as high-energy product motion.
- Before and After is explicitly a transformation/results format.
- Seedance 2.5 prompting guidance supports structured shot/action/camera/audio direction and authentic UGC-style framing.
- Current Seedance 2.5 and 2.0 Content Engine API profiles already expose explicit `generate_audio`; H2 records this as the verified `native_audio` recipe capability.
- A direct read-only Higgsfield model-catalog query again returned workspace error 423. This is not evidence that Content Engine's dedicated server credential lacks the models; account availability remains authenticated estimate/preflight truth.

Marketing Studio is evidence for production patterns only. H2 does **not** introduce Marketing Studio as a second Content Engine provider pipeline.

## 2. Recipe family

| Recipe | Reproducible production method | Key capability |
| --- | --- | --- |
| `premium_product_reveal` | partial/detail opening → controlled reveal → clean hero payoff | reference animation |
| `product_showcase` | whole product → useful detail(s) → clean packshot | reference animation |
| `hyper_motion_product` | immediate kinetic hook → escalating motion → readable product payoff | reference animation |
| `before_after` | establish before → legible transformation → hold anchored after | first/last frame |
| `ugc_testimonial` | relatable opening → one approved experience/benefit → natural close | native audio |
| `ugc_product_demo` | product in hand → approved feature demo → short creator reaction/CTA | reference animation + native audio |
| `problem_solution_paid_ad` | problem → product/mechanism solution → proof/packshot/CTA | general video |
| `curiosity_hook_paid_ad` | unanswered visual question → brief delay → relevant reveal/payoff | general video |
| `landscape_environment_hero` | establish scale → defining environmental reveal → hero composition | single continuous shot |
| `luxury_brand_film` | anticipation → tactile/material reveal → composed premium payoff | general video |

## 3. Reference and truth rules

Product-led H2 recipes that promise reference fidelity require a canonical START_IMAGE. They may accept END_IMAGE when the user explicitly supplies a closing anchor; the existing router then automatically restricts eligibility to models whose verified request contract supports END_IMAGE.

`before_after` requires both START_IMAGE and END_IMAGE. The model must not invent an after-result.

UGC recipes do not silently turn on sound. They fail closed unless the brief explicitly requests approved dialogue, voiceover or audio. This keeps audio cost and generated speech intentional.

UGC Testimonial specifically forbids invented personal experience, statistics, outcomes or testimonial claims. The existing Creative Engine factual safety remains authoritative.

The current Content Engine cannot yet send separate product + creator references through the standard Seedance I2V endpoint. Therefore `ugc_product_demo` uses a canonical pre-composed START_IMAGE containing the creator/product staging when visual identity needs to be locked. H2 does not fake multi-reference support that the current provider adapter does not possess.

## 4. Compiler behavior

H2 adds trusted `narrative_strategy` to `CreativeRecipe`.

The model prompt receives:

- the original user brief,
- the trusted narrative production method,
- one concise format directive,
- recipe camera/motion/continuity strategy,
- recipe negative constraints,
- existing factual/company safety.

Format directives distinguish:

- creator-style UGC,
- before/after proof,
- paid social,
- product-led commercial,
- environment hero,
- luxury brand film,
- existing H1 scroll mode.

The existing 1,800-character Higgsfield prompt ceiling remains fail-closed.

## 5. Capability routing

H2 does not add a second model router.

Recipes declare only capabilities supported by the current verified Content Engine profiles:

- `general_video`
- `reference_animation`
- `single_continuous_shot`
- `first_last_frame`
- `native_audio`

Current Seedance 2.5 and 2.0 gain `native_audio` because their already-audited request contracts expose explicit `generate_audio` and the current prompt profiles support an AUDIO section.

Kling remains eligible for recipes it can honestly satisfy, such as one-reference product reveals and environment hero shots, but is excluded from native-audio and first/last-frame recipes.

## 6. Good vs bad outcomes

Every H2 recipe stores explicit:

- good result criteria,
- bad result signals,
- negative constraints,
- evaluation rules.

This is production metadata for later QA/learning. It is not an aesthetic performance claim.

No paid sample was generated in H2, so H2 validates recipe contracts, routing and compilation rather than claiming one recipe/model produces superior real-world ad performance.
