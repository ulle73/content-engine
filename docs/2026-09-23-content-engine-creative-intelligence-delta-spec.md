# Content Engine — Creative Intelligence DELTA Spec

**Date:** 2026-09-23  
**Purpose:** Add only the missing capabilities needed to reach the agreed Creative Engine end-state.  
**Do not use this document as a rewrite plan. Existing working architecture must be preserved and extended.**

**Execution checklist:** `docs/2026-09-23-content-engine-creative-intelligence-implementation-plan.md` — this is the active task ledger and must be updated/checkmarked only after implementation and verification.

---

## 0. Verified current baseline

This spec was written after reading the current live Content Engine, not the older 2026-09-21 design plan.

### Source/deploy snapshot

- Repository: `ulle73/content-engine`
- Baseline commit before this documentation update: `780468c9e96dcba046054668cbca2a834373f241`
- At baseline, `main` and `feature/chatgpt-content-engine-mcp` pointed at the same commit.
- Render service: `content-engine-mcp`
- Render branch: `feature/chatgpt-content-engine-mcp`
- Baseline live deploy: `dep-dapt2d6gekts73f3uvh0`
- Baseline live commit: `780468c9e96dcba046054668cbca2a834373f241`
- Baseline deploy status: `live`

The previous README statement saying that `main` had not been merged was stale and was corrected together with this document.

---

# 1. End goal

Content Engine's end goal is:

> Automatically create the strongest possible content for the selected company, using evidence-backed creative methods, current official model/provider guidance, model-specific best practices and measured company learning — while allowing the user to take full manual control whenever desired.

The engine must support:

- loose natural-language requests,
- highly automated creative production,
- full expert control,
- images,
- ads,
- reels,
- product films,
- cinematic sequences,
- scroll-website assets,
- future creative formats.

Scroll websites are **one recipe/use case**, not the product architecture.

---

# 2. Important: what is ALREADY implemented

Do not rebuild the following.

## 2.1 Provider-neutral Creative Engine planning

Already implemented in:

- `engine/creative_core.py`
- `engine/creative_director.py`
- `engine/creative_registry.py`

Current system already has:

- `CreativeBrief`
- `CreativeContext`
- `Complexity`
- `ModelSelection`
- `CreativePlan`
- preflight issues
- versioned compiler/registry identifiers
- deterministic intent parsing
- complexity analysis
- model routing
- parameter normalization
- prompt compilation
- provider-neutral planning

This is the foundation to extend.

## 2.2 Automatic model routing architecture

Already implemented:

`route_model()` selects from verified models using:

- quality preference,
- speed preference,
- budget preference,
- complexity,
- reference-media need,
- audio need.

The architecture therefore already supports automatic routing conceptually.

### Current limitation

The registry currently contains only one enabled verified video route:

`kling-video/v2.5-turbo/pro`

So the router exists, but for video it does not yet have a meaningful model choice.

**Do not build a second router. Expand the existing router and registry.**

## 2.3 Versioned verified model registry

Already implemented in:

`engine/creative_registry.py`

Current `ModelIntelligence` already stores:

- provider
- model id
- content kind
- modes
- enabled
- evidence level
- verified date
- source
- durations
- resolution metadata
- reference support
- audio support
- quality/speed/cost tiers
- prompt strategy

This is already close to the desired future ModelGuide concept.

Do not replace it blindly. Extend it where structured model-specific guidance is missing.

## 2.4 Prompt Library

Already implemented:

- exact immutable original
- editable working copy
- company ownership
- favorites
- tags
- archive/restore
- generation provenance
- bounded search/retrieval
- safe/untrusted inspiration handling
- UI
- MCP tools
- bulk handling

Current generation deliberately uses Prompt Library only as bounded inspiration mechanisms.

That safety model is correct.

Do not turn raw saved prompts into trusted instructions.

## 2.5 Model-specific prompt compilation

Already implemented in `creative_director.py`.

The compiler currently changes behavior between OpenAI still images and Higgsfield video.

It already understands:

- preservation,
- allowed changes,
- forbidden changes,
- camera instructions,
- format intent,
- company-context safety.

The missing work is to make this substantially richer per model/recipe, not to create the concept from zero.

## 2.6 Start-image image-to-video

Already implemented.

Current UI allows selecting a source/start image.

Current pipeline:

- validates company ownership,
- stores source on `MediaGeneration.source_asset`,
- uploads it to Higgsfield,
- sends it as `image_url` for I2V.

Do not rebuild start-image support.

## 2.7 Media generation lifecycle and safety

Already implemented:

- queued preview
- non-billable video price preflight
- explicit reviewed start
- 10-minute review window
- approved max USD
- server cost ceiling
- no blind retry after ambiguous paid POST
- UNKNOWN handling
- provider polling
- webhook as untrusted wake-up hint
- authenticated reconciliation
- R2 storage
- output validation
- cancellation
- recovery
- company ownership
- MCP integration

This production infrastructure must remain unless an additive extension requires a carefully tested change.

## 2.8 AI Studio UI

Already implemented:

- Image / Video modes
- natural-language brief
- start image
- format selector
- quality/balanced/economy priority
- media library
- upload
- generation history
- preflight/review page
- model/parameter diagnostics

The UI already communicates the correct direction:

> “Beskriv vad du vill skapa — motorn väljer modell och inställningar”

## 2.9 Closed-loop content learning

Added 2026-09-23 and live.

Already implemented:

- verified own-performance outcomes
- separate editorial preference signals
- strong/weak historical examples
- leakage-safe cutoffs
- current-facts separation
- minimum evidence rules
- shadow learning model infrastructure
- generator guidance
- UI explanation of learning confidence

Relevant code:

- `engine/learning.py`
- `engine/generation.py`
- `templates/engine/learning_panel.html`

The generator already uses measured own performance to influence future ideas and copy.

Do not build another general content-learning loop.

### Current limitation

This learning is primarily about:

- ideas,
- copy,
- editorial selection,
- post outcomes.

It is not yet a complete creative-media recipe/model learning loop.

---

# 3. What is ACTUALLY missing

Everything below is additive work.

## 3.1 Evidence-backed Creative Recipes

### Gap

Content Engine currently has:

- CreativeBrief
- router
- compiler
- Prompt Library

But it does not have a first-class structured concept describing:

> “This is the proven workflow for producing this specific type of creative result.”

Examples:

- cinematic product reveal
- premium orbit hero
- scroll transition bridge
- UGC product demonstration
- premium golf-course flythrough
- Meta problem/solution ad
- hyper-motion product showcase

### Required addition

Introduce a `CreativeRecipe` layer between brief interpretation and model-specific compilation.

Conceptual flow:

```text
CreativeBrief
    ↓
CreativeRecipe selection
    ↓
Model routing
    ↓
Model-specific compilation
```

A recipe should contain structured production logic, not only raw prompt text.

Suggested fields:

```text
id
version
name
description
goal_tags
format_tags
required_reference_roles
optional_reference_roles
preferred_motion
camera_strategy
continuity_strategy
negative_constraints
default_duration_intent
default_format_intent
draft_policy
evaluation_rules
supported_model_families
evidence_sources
verified_at
confidence
```

## 3.2 Official-guide / best-practice knowledge must become first-class

Every important production recipe should prefer evidence in this order:

1. official model documentation,
2. official Higgsfield/provider guides,
3. official published examples/presets,
4. internal verified tests,
5. external reproducible guidance only when official evidence is insufficient.

`ModelIntelligence.source` and `verified_date` already exist, but the engine needs a richer structured representation of **how the model should be prompted for different use cases**.

Extend the current registry/compiler architecture rather than replacing it.

Possible extension:

```text
ModelIntelligence
  capabilities
  evidence
  prompt_profiles
  reference_roles
  recipe_compatibility
  known_failure_modes
```

or an adjacent `ModelPromptProfile`.

The required behavior matters more than the exact class name.

## 3.3 Add Seedance and other verified models to the existing router

### Current state

Video registry currently auto-enables only:

`kling-video/v2.5-turbo/pro`

The UI explicitly states that priority does not yet change the video model.

### Required addition

Verify and add current officially supported models such as appropriate Seedance variants.

The router should then make a real selection based on the job.

Example:

```text
scroll continuity
+ start frame
+ end frame
+ one continuous shot

→ prefer verified model with first/last-frame support
```

Do not hard-code “Seedance is always best”.

Use capability-driven routing.

## 3.4 Canonical media-reference roles

### Current state

The generation database currently has one first-class reference relation:

`MediaGeneration.source_asset`

That is sufficient for current image editing / start-image I2V.

It is not sufficient for the long-term goal.

### Required addition

Support normalized reference roles such as:

```text
START_IMAGE
END_IMAGE
PRODUCT_REFERENCE
CHARACTER_REFERENCE
LOCATION_REFERENCE
STYLE_REFERENCE
VIDEO_REFERENCE
AUDIO_REFERENCE
```

Provider adapters translate canonical roles to provider-specific fields.

Example:

```text
START_IMAGE
→ Seedance image_url

END_IMAGE
→ Seedance end_image_url
```

Do not leak provider field names into general business/UI logic.

## 3.5 End-frame support

This is one of the most immediate concrete gaps.

Current Higgsfield video payload is effectively:

```text
prompt
duration
image_url (when source_asset exists)
```

There is no general first-class `end_image` path.

### Required behavior

The user must be able to:

- select an optional end image,
- see it visibly in the UI,
- have it ownership-validated,
- include it in preflight,
- include it in cost estimation,
- persist its provenance,
- send it through the provider adapter only when the selected model supports it.

The router must reject or choose another model when the requested reference combination is unsupported.

## 3.6 Expert model override

### Current state

Normal user mode automatically chooses the model.

That should remain default.

### Missing

Advanced users cannot currently force:

- a specific verified video model,
- exact advanced model parameters,
- exact reference role behavior.

### Required UX

Default:

`Model: Auto`

Advanced panel:

- model override
- valid duration
- resolution
- audio
- model-specific supported controls

Invalid combinations must fail before spend.

## 3.7 Cinematic Sequence Engine

This is the main new architectural capability.

The current app is generation-job based.

For connected films, reels and scroll experiences, add a project-level sequence model.

Required concepts:

```text
SequenceProject
SequenceAnchor
SequenceClip
SequenceClipVersion
```

Example:

```text
K0
↓
Clip 1
↓
K1
↓
Clip 2
↓
K2
↓
Clip 3
↓
K3
```

This must be general enough for:

- ads
- reels
- product films
- brand films
- scroll websites

## 3.8 Canonical anchor workflow

For quality-oriented continuity:

```text
Clip 1 = K0 → K1
Clip 2 = K1 → K2
Clip 3 = K2 → K3
```

The exact canonical `K1` must be reusable as:

- Clip 1 target/end anchor
- Clip 2 start anchor

Do not automatically propagate accumulated generation drift unless the user explicitly chooses an output-chain workflow.

Support:

### Anchor Chain
Preferred high-quality workflow.

### Output Chain
Use actual generated final frame as next input for rapid experimentation.

### Transition Bridge
Generate a dedicated connection between an existing clip end and next clip opening.

## 3.9 Sequence/timeline UI

The project UI should allow:

- view all anchors,
- create AI anchor,
- upload anchor,
- replace anchor,
- lock anchor,
- create clip between two anchors,
- regenerate only one clip,
- retain earlier versions,
- compare candidate versions,
- promote a winner,
- extend the sequence,
- generate a bridge,
- override model/prompt on one clip.

One failed/regenerated segment must not destroy the rest of the sequence.

## 3.10 Automatic storyboard and anchor generation

The system should also work from a loose request.

Example:

> “Create a premium four-scene Golfkuponger cinematic scroll story.”

Content Engine should be able to propose:

- narrative structure,
- recipe per segment,
- anchor descriptions,
- required reference assets,
- model plan,
- draft cost plan.

Then generate anchors before generating final connected clips.

The user can edit/lock/replace anything.

## 3.11 Draft → Select → Final for MEDIA generation

### Current state

Content Engine already has:

- priority selection,
- cost preview,
- explicit approval.

For still images, priority changes image quality.

For video, priority currently does not change the model.

### Missing

There is no complete automatic media-production strategy such as:

```text
cheap draft
→ compare
→ select
→ expensive final
```

### Required addition

Add orchestration policy:

#### Draft stage
Prefer:
- 720p or provider-equivalent draft,
- short valid duration,
- lower-cost suitable model when evidence supports it.

#### Selection stage
Compare output candidates.

#### Final stage
Only spend premium settings on selected creative direction.

Do not confuse **price preflight** with a **visual draft generation**. They are different.

## 3.12 Output evaluation for generated media

Current learning/evaluation is strong for posts and content outcomes, but generated creative media does not yet have a recipe-specific QA layer.

Add recipe-specific checks.

Examples for continuity:

- start anchor adherence,
- end anchor adherence,
- geometry stability,
- identity stability,
- camera smoothness,
- lighting continuity,
- unwanted object introduction,
- morphing,
- transition coherence.

Examples for product work:

- product fidelity,
- label fidelity,
- framing,
- visibility,
- reference consistency.

Automated evaluation should assist selection, not pretend to be a universal aesthetic truth.

Human selection remains authoritative.

## 3.13 Creative-media learning loop

Do not duplicate the existing content-performance loop.

Extend learning with media-production provenance.

Store/link:

```text
recipe_id
recipe_version
model
model_profile_version
compiled_prompt_version
references
draft/final stage
cost
candidate count
selected candidate
rejected candidates
manual overrides
published asset
measured post/ad outcome
```

Long term this lets the system learn questions such as:

- Which recipe works best for Golfkuponger reels?
- Which model follows product references most reliably?
- Which camera strategy fails often?
- Which expensive model actually adds measurable value?
- Which creative recipe correlates with better paid performance?

Only measured outcomes may become performance evidence.

## 3.14 Scroll Website recipe family

Scroll Website should be implemented on top of the general Sequence Engine.

Initial recipes:

- `scroll_orbit_hero`
- `scroll_dolly_reveal`
- `scroll_macro_flythrough`
- `scroll_exploded_reveal`
- `scroll_environment_transition`
- `scroll_transition_bridge`
- `scroll_product_showcase`
- `scroll_landscape_flythrough`

Scroll-specific constraints:

```text
single continuous shot
no hard cuts
no perspective teleport
no unexplained scene reset
no random object creation/disappearance
stable subject geometry
stable lighting continuity
smooth physically plausible movement
intermediate frames coherent during forward/backward scrub
```

## 3.15 Frame extraction / anchor capture

For scroll and sequence workflows, add tools to:

- extract first frame,
- extract final frame,
- extract selected frame,
- save extracted frame as MediaAsset,
- promote extracted frame to canonical anchor.

This should use existing media storage rather than introducing a separate storage system.

## 3.16 Scroll asset export

Later phase.

After a sequence is approved, allow preparing it for scroll implementation:

- frame extraction,
- ordered frame naming,
- compression,
- dimensions,
- metadata/manifest,
- optional web-ready asset bundle.

This should be separate from the core generation pipeline.

---

# 4. Recommended implementation order

Do not start by building the full timeline.

## Phase A — Recipe and model intelligence extension

1. Add structured `CreativeRecipe`.
2. Extend current model intelligence with model-specific prompt guidance.
3. Add provenance/evidence/versioning.
4. Keep Prompt Library separate and untrusted.

## Phase B — Real multi-model video routing

1. Verify current official Higgsfield/API contracts.
2. Add Seedance or other suitable verified models.
3. Extend capability routing.
4. Add advanced model override.

## Phase C — Reference-role foundation

1. Introduce canonical reference-role abstraction.
2. Preserve backward compatibility with `source_asset`.
3. Add `END_IMAGE`.
4. Update provider estimate and submit adapters.
5. Add UI and MCP fields.

## Phase D — First useful continuity recipe

Implement:

`scroll_transition_bridge`

This is the smallest feature that proves:

- two anchors,
- correct model selection,
- start/end-frame transmission,
- model-specific prompt compilation,
- cost preflight,
- generation.

## Phase E — Sequence Engine

Add:

- projects,
- anchors,
- clips,
- versions,
- non-destructive regeneration,
- timeline UI.

## Phase F — Automatic storyboard

Loose prompt → proposed multi-scene sequence.

## Phase G — Draft/select/final orchestration

Cost-efficient creative iteration.

## Phase H — Creative-media evaluation + learning

Connect creative provenance to real performance without corrupting existing learning safeguards.

---

# 5. Things that must NOT be rebuilt

Explicitly preserve:

- current `CreativeBrief`
- current `CreativeContext`
- current `CreativePlan`
- current `route_model()` architecture
- current provider-neutral planning concept
- current MediaGeneration lifecycle
- current paid-submit safety
- current cost preflight
- current R2 media storage
- current ownership isolation
- current Prompt Library safety boundary
- current MCP/OAuth setup
- current UI/media library
- current content-performance learning
- current editorial-vs-performance separation

Refactor only when necessary and with backwards-compatible migrations/tests.

---

# 6. Definition of a good implementation

A good implementation:

- extends existing architecture,
- adds no duplicate router,
- adds no duplicate media database,
- uses current MediaAsset storage,
- uses current cost/preflight safety,
- adds models only after current official verification,
- keeps Auto mode simple,
- adds expert override progressively,
- can generate a start→end continuity clip,
- can later scale naturally into multi-clip sequencing,
- keeps recipe/model provenance,
- creates measurable learning data.

---

# 7. Definition of a bad implementation

A bad implementation:

- rewrites Creative Director from scratch,
- creates a second model router,
- creates another Prompt Library,
- creates an unrelated media storage layer,
- hard-codes Seedance throughout the application,
- treats one giant prompt string as a recipe system,
- bypasses current cost approval,
- removes UNKNOWN paid-request protection,
- invents undocumented model parameters,
- makes scroll logic impossible to reuse for ads/reels/product films,
- mixes editorial feedback with measured performance labels,
- propagates generated drift across clips without canonical anchors,
- requires users to know provider API field names.

---

# 8. Immediate acceptance target

The first meaningful extension should prove all of the following:

1. Existing Content Engine still works unchanged for normal images/video.
2. A new verified video model can coexist with Kling.
3. Router can genuinely select between models.
4. User can optionally force a verified model.
5. A generation can have a canonical start image.
6. A generation can have a canonical end image.
7. Provider adapter maps those roles correctly.
8. A structured continuity recipe compiles a model-specific prompt.
9. Estimate/preflight includes the real inputs.
10. Paid start still uses the existing reviewed-start safety.
11. Result is stored as normal MediaAsset.
12. Full provenance is retained.
13. Existing tests stay green and new tests cover the extension.

Only after that foundation is proven should the full Sequence Project UI be built.

---

# 9. Verified current-app references

Current production code reviewed:

- `engine/creative_core.py`
- `engine/creative_director.py`
- `engine/creative_registry.py`
- `engine/creative_models.py`
- `engine/prompt_library.py`
- `engine/media.py`
- `engine/media_providers.py`
- `engine/media_views.py`
- `engine/models.py`
- `engine/generation.py`
- `engine/learning.py`
- `engine/mcp_server.py`
- `templates/engine/media.html`
- `templates/engine/learning_panel.html`

Historical implementation/audit evidence reviewed:

- `docs/2026-09-21-higgsfield-creative-engine-progress.md`
- `docs/2026-09-22-creative-audit.md`

Baseline production source commit reviewed:

`780468c9e96dcba046054668cbca2a834373f241`

---

# 10. One-line implementation rule

> **Build the missing creative intelligence on top of the existing Creative Engine; do not rebuild capabilities that are already implemented and live.**
