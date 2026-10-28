# Golf photo realism — production guide (2026-10-28)

Scope: optional photographic golf image creation for Golfkuponger. This is an extension of `skills/golfkuponger-brand/SKILL.md`, not a replacement for brand directions, the trusted Creative Recipe registry, model contracts or user instructions.

Source: user-provided research report `deep-research-report (1).md`, "Hyperrealistiska AI-bilder för golf: evidens, promptteknik och praktiska A/B-tester" (2026-10-24). These are evidence-informed working hypotheses, **not tested improvements within Content Engine**.

## Core workflow

1. Specify visible subject, pose/action phase, relation between hands/equipment/ground, camera/viewpoint, turf zone, lighting and intended image use. Structure only if complexity warrants it. Avoid empty quality words ("8K", "masterpiece", "perfect anatomy").
2. Minimize simultaneous spatial constraints; one golfer and one club where possible. If inspecting a club, show the grip→shaft→hosel→head chain unobstructed; for high-stakes product identity, supply a real reference.
3. For realistic course photos, distinguish green, collar, fairway, semi-rough and rough. Subtle Nordic seasonal variation, real terrain, natural non-neon colors. Grains/blades visible only at plausible camera distances; distant turf must merge into photographic texture.
4. Prefer ordinary editorial/candid golf photography over generic cinematic, glossy or over-retouched aesthetics unless user explicitly asks otherwise. Use camera descriptors as appearance cues, not guarantees of exact optics or geometry.
5. If a structural defect remains after 2–3 attempts, stop making the text prompt longer. Use a verified reference, targeted edit or compositing when supported. **Do not imply Content Engine currently provides mask-based inpainting or multiple-image editing.** Current OpenAI image adapter accepts one source image; new capabilities require implementation and provider validation.
6. Keep output resolution, quality and model parameters separate from prompt text. Preserve existing brand rule: official logos/wordmarks are never synthesized; add them from real assets afterward. For actual named clubs, use genuine club photographs rather than claiming a synthetic view is documentary evidence.

## Five optional photo templates (use to enrich, never override the user's brief)

### 1. Golfer — natural editorial
Subject: [ONE GOLFER], [STATIC ADDRESS/PUTTING OR CLEAR ACTIVITY], [SWEDISH COURSE]. Show natural hands visibly gripping **one** club, anatomically consistent wrists/forearms, credible shoes and ground contact. Equipment: one coherent grip, shaft, hosel and correct clubhead type. Frame: [THREE-QUARTER/OTHER RELEVANT VIEW], enough depth of field to inspect important interactions. Natural Nordic light; restrained retouching.

### 2. Golf swing — exact action phase
Subject: one golfer at [ADDRESS/BACKSWING/EARLY FOLLOW-THROUGH/FINISH]. State ball before/after impact appropriately, realistic torso/hips/arms/lead and trail foot positions, hands on one grip, one continuous shaft, plausible clubhead. Full silhouette visible, natural divot or turf disturbance only where appropriate. Sports-shutter impression; do not request mutually contradictory poses.

### 3. Nordic course — turf and terrain
Scene: [TEE/FAIRWAY/GREEN] in [REGION, SEASON]. Describe the visible turf zones separately (putting green shortest, collar slightly longer, fairway closely mown, rough longer), natural mowing contour and gentle topographic variation. Foreground can show grass texture; middle and far distance should merge. Mixed Nordic vegetation, believable muted seasonal colors and natural exposure. Never claim an invented view depicts a particular real course.

### 4. Equipment — physical topology
Object: one [DRIVER/IRON/PUTTER/STAND BAG/PUSH TROLLEY] from a three-quarter inspection angle. Detail mechanically coherent visible parts and connection points: club grip→straight shaft→hosel/neck→head; stand bag has two correctly attached support legs; a three-wheel push trolley has one front, two rear wheels, a frame and bag attachment. Real contact shadows and material response. For an exact product, require a genuine product image reference.

### 5. Believable commercial golf image
A clean professional but plausible golf photograph for [CAMPAIGN]. [SUBJECT] in [SETTING], naturally engaged rather than staged; physically plausible golf equipment and terrain. Camera framing [SHOT/ANGLE] with clean negative space for externally overlaid text. Soft real light and coherent shadows; restrained saturation and sharpening; no invented logos/text. Keep verified Golfkuponger facts and final creative copy outside image generation.

## Review: separate visual appeal from correctness

Score 1–5, individually: photographic credibility; human anatomy; golf equipment geometry; turf/ground; prompt adherence; physical integration (shadows, scale, contacts). Do not substitute one blended aesthetic score. **Hard fail**: visibly impossible central club, major hand/anatomy error, or central referenced product not matching the reference. Inspect at 100% zoom, not just thumbnail.

Record attempts, local edits, model/version, resolution, runtime, cost, accepted/rejected, reason and **cost per accepted image** if/when the existing workflow supports that reporting. Never fabricate scores or improvements.

## Validation before promotion to global defaults

Use a small paired pilot: 4 representative scenarios × baseline/structured variant × 3 generations = 24 images, same model version, aspect, quality and reference inputs within each pair. Blind-review outcomes and record hard fails separately. Optional follow-up: reference+edit as a separate C arm. No provider generations have been run by adding this guide.

## Integration boundaries

- `skills/golfkuponger-brand/SKILL.md`: brand consistency, not a universal prompt system.
- `engine/creative_recipes.py`: trusted, versioned operational production recipes; do not paste external report as executable policy without tests.
- `engine/assistant/templates.py`: user-selectable assistant templates, scoped to company context.
- `engine/prompt_library.py`: inspirational untrusted prompt storage, not trusted production constraints.
- `engine/creative_director.py`: actual compiled provider prompts; merely saving a template in Prompt Library does not automatically enforce this guide.
