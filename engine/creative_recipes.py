"""Trusted Creative Recipe registry.

Prompt Library entries are deliberately excluded from this module. A recipe is
executable Creative Engine policy and may only come from this versioned,
reviewed registry.
"""
from __future__ import annotations

from .creative_core import (
    CreativeBrief,
    CreativeRecipe,
    EvidenceLevel,
    ReferenceRole,
    RecipeSelection,
    RECIPE_REGISTRY_VERSION,
)


_SCROLL_OFFICIAL_EVIDENCE = (
    "https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance",
    "https://higgsfield.ai/blog/seedance-2-5-prompting-guide",
    "https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference",
    "https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference",
)
_SCROLL_INTERNAL_EVIDENCE = "docs/2026-09-25-scroll-recipe-family-h1.md"
_SCROLL_REQUIRED_CAPABILITIES = (
    "reference_animation",
    "single_continuous_shot",
    "first_last_frame",
)
_SCROLL_FORMAT_TAGS = ("scroll", "single_continuous_shot", "scrub_friendly")
_SCROLL_BASE_NEGATIVE = (
    "hard cuts",
    "unexplained scene resets",
    "perspective teleporting",
    "random object creation",
    "unrequested object disappearance",
    "subject geometry drift",
    "lighting resets",
    "intermediate-frame incoherence",
)


def _scroll_recipe(
    *,
    recipe_id: str,
    name: str,
    description: str,
    goal_tags: tuple[str, ...],
    camera_strategy: tuple[str, ...],
    motion_strategy: tuple[str, ...],
    continuity_strategy: tuple[str, ...],
    extra_negative: tuple[str, ...],
    evaluation_rules: tuple[str, ...],
    good_result_criteria: tuple[str, ...],
    bad_result_signals: tuple[str, ...],
    default_duration_intent: int = 5,
    evidence_level: EvidenceLevel = EvidenceLevel.verified,
) -> CreativeRecipe:
    negative = tuple(dict.fromkeys((*_SCROLL_BASE_NEGATIVE, *extra_negative)))
    return CreativeRecipe(
        recipe_id=recipe_id,
        version="1.0.0",
        name=name,
        description=description,
        kinds=("video",),
        supported_modes=("image-to-video",),
        goal_tags=("scroll", "cinematic_sequence", *goal_tags),
        format_tags=_SCROLL_FORMAT_TAGS,
        required_reference_roles=(ReferenceRole.start_image, ReferenceRole.end_image),
        camera_strategy=camera_strategy,
        motion_strategy=motion_strategy,
        continuity_strategy=continuity_strategy,
        negative_constraints=negative,
        default_duration_intent=default_duration_intent,
        default_format_intent="anchor_to_anchor",
        draft_policy="draft_then_final",
        evaluation_rules=evaluation_rules,
        supported_model_families=("higgsfield",),
        required_model_capabilities=_SCROLL_REQUIRED_CAPABILITIES,
        good_result_criteria=good_result_criteria,
        bad_result_signals=bad_result_signals,
        evidence_sources=(*_SCROLL_OFFICIAL_EVIDENCE, _SCROLL_INTERNAL_EVIDENCE),
        verified_at="2026-09-25",
        evidence_level=evidence_level,
    )


_RECIPES: tuple[CreativeRecipe, ...] = (
    CreativeRecipe(
        recipe_id="generic_image",
        version="1.0.0",
        name="Generic image",
        description="Compatibility recipe for the existing still-image Creative Engine path.",
        kinds=("image",),
        supported_modes=("text-to-image", "image-to-image"),
        goal_tags=("general",),
        format_tags=("image",),
        optional_reference_roles=(ReferenceRole.start_image,),
        draft_policy="single_pass",
        evaluation_rules=("prompt_adherence", "brand_safety"),
        supported_model_families=("openai",),
        evidence_sources=("docs/2026-09-22-creative-audit.md",),
        verified_at="2026-09-23",
        evidence_level=EvidenceLevel.verified,
    ),
    _scroll_recipe(
        recipe_id="scroll_orbit_hero",
        name="Scroll orbit hero",
        description="A restrained cinematic arc around a hero subject while the subject remains geometrically stable between canonical anchors.",
        goal_tags=("hero", "orbit", "product_or_subject_reveal"),
        camera_strategy=(
            "Use a controlled arc or orbital camera move around the primary subject; prefer a modest arc over an unnecessary full revolution.",
            "Keep orbit radius, camera height and lens character stable unless the supplied anchors explicitly require a change.",
            "Create parallax through real camera travel rather than rotating the subject in place.",
        ),
        motion_strategy=(
            "Keep the hero subject visually stable while background and foreground parallax reveal depth.",
            "Use smooth angular acceleration and ease naturally into the target anchor.",
        ),
        continuity_strategy=(
            "Treat both anchors as exact subject-orientation, scale, placement, material and lighting constraints.",
            "Maintain stable three-dimensional geometry and texture attachment through every intermediate frame.",
        ),
        extra_negative=(
            "subject spinning in place instead of camera orbit",
            "orbit radius jumps",
            "camera crossing through the subject",
            "unrequested full 360-degree spin",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "subject_consistency",
            "geometry_stability",
            "camera_smoothness",
            "parallax_coherence",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "One smooth readable arc reveals depth while the hero subject keeps the same identity and geometry.",
            "The first and last frames match their anchors and the move remains coherent when scrubbed in either direction.",
        ),
        bad_result_signals=(
            "The subject rotates or morphs instead of the camera moving around it.",
            "Perspective, orbit radius, geometry or lighting jumps between intermediate frames.",
        ),
    ),
    _scroll_recipe(
        recipe_id="scroll_dolly_reveal",
        name="Scroll dolly reveal",
        description="A controlled push, pull or lateral dolly that reveals the next composition through real parallax and occlusion.",
        goal_tags=("reveal", "dolly", "parallax"),
        camera_strategy=(
            "Use a physically plausible dolly, push, pull or truck move with stable horizon and lens character.",
            "Reveal the target through changing parallax and natural occlusion rather than a digital zoom or sudden reframing.",
            "Keep screen direction consistent from the opening anchor to the closing anchor.",
        ),
        motion_strategy=(
            "Move foreground, subject and background at depth-appropriate relative speeds.",
            "Keep subject motion secondary unless the anchors explicitly encode subject action.",
        ),
        continuity_strategy=(
            "Preserve spatial layout while newly revealed areas enter frame progressively.",
            "Arrive at the end anchor without a late snap, crop jump or scene reset.",
        ),
        extra_negative=(
            "zoom-only reveal",
            "teleporting occluders",
            "horizon jumps",
            "late framing snap",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "parallax_coherence",
            "camera_smoothness",
            "spatial_continuity",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "The reveal comes from genuine camera translation with convincing foreground/background parallax.",
            "The target composition emerges progressively and lands naturally on the closing anchor.",
        ),
        bad_result_signals=(
            "The move reads as a digital zoom, crop animation or teleport instead of camera travel.",
            "Occluders, horizon or target framing jump discontinuously.",
        ),
    ),
    _scroll_recipe(
        recipe_id="scroll_macro_flythrough",
        name="Scroll macro flythrough",
        description="A close-range cinematic traversal along or through real visible gaps in a subject or environment without breaking scale or surface continuity.",
        goal_tags=("macro", "detail", "flythrough"),
        camera_strategy=(
            "Use a slow macro tracking move along surfaces or through a clearly visible real opening, keeping plausible camera clearance.",
            "Let depth of field and parallax evolve continuously with camera distance instead of changing scale abruptly.",
            "Keep camera orientation legible so the viewer can understand the path between anchors.",
        ),
        motion_strategy=(
            "Preserve fine surface texture attachment and physically plausible depth cues throughout the close-range move.",
            "Use restrained motion blur and focus transitions that follow the actual camera path.",
        ),
        continuity_strategy=(
            "Maintain consistent material, scale and topology between the macro start and end anchors.",
            "Any passage through an opening must remain spatially possible in every intermediate frame.",
        ),
        extra_negative=(
            "camera clipping through solid surfaces",
            "texture swimming",
            "impossible scale changes",
            "focus teleporting",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "surface_stability",
            "scale_consistency",
            "camera_path_plausibility",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "The viewer can follow one continuous close-range camera path with stable scale, texture and depth.",
            "Focus and parallax change naturally as the camera advances toward the end anchor.",
        ),
        bad_result_signals=(
            "The camera passes through solid geometry or the object changes size without spatial cause.",
            "Fine textures swim, smear or detach from the surface during motion.",
        ),
    ),
    _scroll_recipe(
        recipe_id="scroll_exploded_reveal",
        name="Scroll exploded reveal",
        description="A reversible exploded-view transition in which known components separate cleanly between assembled and exploded anchor states.",
        goal_tags=("product", "exploded_view", "mechanical_reveal"),
        camera_strategy=(
            "Keep a stable hero angle or a very restrained dolly so component motion remains easy to read.",
            "Do not hide part movement behind aggressive camera motion; the exploded structure is the primary event.",
        ),
        motion_strategy=(
            "Move each visible component along a clear mechanically plausible axis while preserving part identity, count, shape and material.",
            "Use staggered, smooth separation with no collisions, melting or spontaneous replacement parts.",
            "Make the motion visually reversible so backward scroll reads as a clean reassembly.",
        ),
        continuity_strategy=(
            "Treat the supplied anchors as authoritative assembled and exploded states.",
            "Keep the relationship between every visible component stable across the entire move.",
        ),
        extra_negative=(
            "new unanchored components",
            "melting or stretching parts",
            "component identity swaps",
            "part collisions",
            "parts vanishing behind no occluder",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "part_count_stability",
            "part_identity_stability",
            "geometry_stability",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "Every visible component separates along a clear path and remains recognizably the same part throughout.",
            "Forward scroll reads as controlled disassembly and backward scroll as equally clean reassembly.",
        ),
        bad_result_signals=(
            "Parts appear, disappear, merge, melt or change identity during the reveal.",
            "Camera motion obscures the mechanism or the final arrangement misses the closing anchor.",
        ),
    ),
    _scroll_recipe(
        recipe_id="scroll_environment_transition",
        name="Scroll environment transition",
        description="A continuous camera move that connects two environment anchors without a cut, reset or unexplained spatial teleport.",
        goal_tags=("environment", "transition", "world_reveal"),
        camera_strategy=(
            "Travel continuously through the environment with a stable screen direction and understandable spatial path.",
            "Use foreground occlusion, depth and camera travel to motivate the transition rather than resetting the scene.",
            "Allow gradual change in viewpoint, atmosphere or lighting only when the end anchor requires it.",
        ),
        motion_strategy=(
            "Keep environmental motion secondary and physically plausible while the camera carries the transition.",
            "Blend atmospheric and lighting changes gradually across space instead of switching them in one frame.",
        ),
        continuity_strategy=(
            "Preserve persistent landmarks and spatial relationships for as long as they remain visible.",
            "Make every intermediate frame a believable location on one continuous route between anchors.",
        ),
        extra_negative=(
            "portal-like scene replacement unless explicitly anchored",
            "background teleporting",
            "instant weather swap",
            "landmark duplication",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "environment_geometry_stability",
            "lighting_continuity",
            "camera_path_plausibility",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "The viewer can infer a continuous route from the first environment to the second with no hidden scene reset.",
            "Landmarks, atmosphere and lighting evolve gradually and remain coherent while scrubbed.",
        ),
        bad_result_signals=(
            "The environment swaps or teleports while the camera pretends to continue moving.",
            "Persistent landmarks duplicate, vanish or change geometry without occlusion.",
        ),
    ),
    _scroll_recipe(
        recipe_id="scroll_transition_bridge",
        name="Scroll transition bridge",
        description="Continuity-first single-shot bridge between two canonical anchor frames for scrub-friendly cinematic sequences.",
        goal_tags=("continuity", "transition"),
        camera_strategy=(
            "Use the simplest physically plausible continuous camera move between the supplied anchor compositions.",
            "Keep camera speed and acceleration controlled and smooth.",
            "Maintain natural multi-plane parallax without perspective teleporting.",
        ),
        motion_strategy=(
            "Prefer stable physically plausible motion over spectacle.",
            "Do not introduce a separate creative event during the bridge.",
            "Ease naturally into the end-frame composition with minimal residual motion.",
        ),
        continuity_strategy=(
            "Preserve subject identity, geometry, proportions, materials, colors, environment and lighting continuity.",
            "Every intermediate frame must remain visually coherent when scrubbed forward or backward.",
            "Treat the supplied start and end frames as locked visual anchors.",
        ),
        extra_negative=(
            "morphing",
            "duplicated objects",
            "identity changes",
            "sudden perspective jumps",
            "sudden acceleration",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "subject_consistency",
            "geometry_stability",
            "camera_smoothness",
            "lighting_continuity",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "The bridge feels like one uneventful physically plausible shot connecting the exact two anchor compositions.",
            "Nothing important changes identity and every intermediate frame remains usable during forward or backward scrub.",
        ),
        bad_result_signals=(
            "The model invents a cut, spectacle event, new object, morph or lighting reset between anchors.",
            "The shot reaches the end anchor through a late snap, perspective jump or sudden acceleration.",
        ),
        evidence_level=EvidenceLevel.official,
    ),
    _scroll_recipe(
        recipe_id="scroll_product_showcase",
        name="Scroll product showcase",
        description="A continuity-first premium product move that reveals shape and material while keeping the anchored product identity exact.",
        goal_tags=("product", "showcase", "commercial"),
        camera_strategy=(
            "Use a restrained arc, dolly or push that keeps the product readable and heroically framed.",
            "Move the camera around the product rather than rotating the product unless the anchors explicitly show product rotation.",
            "Favor clean silhouette separation and controlled parallax over dramatic lens changes.",
        ),
        motion_strategy=(
            "Keep the product itself stable; allow only requested articulation and physically plausible environmental motion.",
            "Preserve material response and reflections consistently as camera angle changes.",
        ),
        continuity_strategy=(
            "Treat product silhouette, proportions, colors, labels, logos and visible text present in the anchors as identity constraints.",
            "Maintain the same product instance and surface details throughout the shot.",
        ),
        extra_negative=(
            "label hallucination",
            "logo mutation",
            "product shape drift",
            "unrequested product rotation",
            "material swapping",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "product_fidelity",
            "label_logo_fidelity",
            "geometry_stability",
            "material_consistency",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "The product remains recognizably identical while camera motion reveals premium form, depth and materials.",
            "Labels, logos and proportions visible in the anchors stay fixed and readable enough to remain the same product.",
        ),
        bad_result_signals=(
            "The product changes shape, materials, branding, text or identity while the camera moves.",
            "The product spins unnaturally or the camera move sacrifices readable product framing.",
        ),
    ),
    _scroll_recipe(
        recipe_id="scroll_landscape_flythrough",
        name="Scroll landscape flythrough",
        description="A smooth cinematic glide through a landscape that preserves terrain, horizon and landmark continuity between canonical anchors.",
        goal_tags=("landscape", "flythrough", "environment"),
        camera_strategy=(
            "Use a smooth forward glide, crane or low aerial-style travel that follows the terrain without abrupt altitude or heading changes.",
            "Keep the horizon stable and maintain a readable relationship between foreground, midground and distant landmarks.",
            "Choose a route with plausible clearance above terrain and visible obstacles.",
        ),
        motion_strategy=(
            "Use multi-plane parallax appropriate to landscape depth and keep environmental motion subtle.",
            "Maintain physically plausible travel speed and smooth acceleration for comfortable scroll scrubbing.",
        ),
        continuity_strategy=(
            "Preserve terrain topology, horizon, vegetation, architecture and major landmarks while they remain visible.",
            "Arrive at the closing landscape anchor without rebuilding the world near the end of the shot.",
        ),
        extra_negative=(
            "terrain morphing",
            "horizon bending",
            "camera clipping into terrain",
            "new buildings or landmarks",
            "abrupt altitude jumps",
        ),
        evaluation_rules=(
            "start_anchor_adherence",
            "end_anchor_adherence",
            "terrain_stability",
            "horizon_stability",
            "landmark_consistency",
            "camera_smoothness",
            "reverse_scrub_coherence",
        ),
        good_result_criteria=(
            "The camera glides through one stable landscape with convincing depth and persistent landmarks.",
            "Terrain and horizon remain coherent from the opening anchor through the closing anchor in either scrub direction.",
        ),
        bad_result_signals=(
            "Terrain, horizon or landmarks morph, duplicate or jump while the camera travels.",
            "The camera clips through terrain or changes altitude or heading without a smooth physical path.",
        ),
    ),
    CreativeRecipe(
        recipe_id="generic_video",
        version="1.0.0",
        name="Generic video",
        description="Compatibility recipe for the existing Higgsfield video Creative Engine path.",
        kinds=("video",),
        supported_modes=("text-to-video", "image-to-video"),
        goal_tags=("general",),
        format_tags=("video", "social"),
        optional_reference_roles=(ReferenceRole.start_image,),
        draft_policy="single_pass",
        evaluation_rules=("prompt_adherence", "subject_consistency", "motion_coherence"),
        supported_model_families=("higgsfield",),
        evidence_sources=("docs/2026-09-22-creative-audit.md",),
        verified_at="2026-09-23",
        evidence_level=EvidenceLevel.verified,
    ),
)

_RECIPE_BY_ID = {item.recipe_id: item for item in _RECIPES}
if len(_RECIPE_BY_ID) != len(_RECIPES):
    raise RuntimeError("Creative Recipe registry contains duplicate recipe ids.")

for _recipe in _RECIPES:
    if _recipe.recipe_id.startswith("scroll_"):
        if not _recipe.negative_constraints:
            raise RuntimeError(f"{_recipe.recipe_id} is missing negative constraints.")
        if not _recipe.required_model_capabilities:
            raise RuntimeError(f"{_recipe.recipe_id} is missing model-capability requirements.")
        if not _recipe.good_result_criteria or not _recipe.bad_result_signals:
            raise RuntimeError(f"{_recipe.recipe_id} is missing explicit good/bad result criteria.")
        if not _recipe.evidence_sources:
            raise RuntimeError(f"{_recipe.recipe_id} is missing evidence sources.")


def registry() -> tuple[CreativeRecipe, ...]:
    """Return trusted recipes available to the planning layer."""
    return _RECIPES


def get_recipe(recipe_id: str) -> CreativeRecipe | None:
    return _RECIPE_BY_ID.get(recipe_id)


def _default_recipe_id(brief: CreativeBrief) -> str:
    return "generic_image" if brief.kind == "image" else "generic_video"


def _brief_reference_roles(brief: CreativeBrief) -> set[ReferenceRole]:
    aliases = {
        "source_asset": ReferenceRole.start_image,
        "start_image": ReferenceRole.start_image,
        ReferenceRole.start_image.value: ReferenceRole.start_image,
        "end_image": ReferenceRole.end_image,
        ReferenceRole.end_image.value: ReferenceRole.end_image,
        "product_reference": ReferenceRole.product_reference,
        ReferenceRole.product_reference.value: ReferenceRole.product_reference,
        "character_reference": ReferenceRole.character_reference,
        ReferenceRole.character_reference.value: ReferenceRole.character_reference,
        "location_reference": ReferenceRole.location_reference,
        ReferenceRole.location_reference.value: ReferenceRole.location_reference,
        "style_reference": ReferenceRole.style_reference,
        ReferenceRole.style_reference.value: ReferenceRole.style_reference,
        "video_reference": ReferenceRole.video_reference,
        ReferenceRole.video_reference.value: ReferenceRole.video_reference,
        "audio_reference": ReferenceRole.audio_reference,
        ReferenceRole.audio_reference.value: ReferenceRole.audio_reference,
    }
    return {aliases[value] for value in brief.reference_media if value in aliases}


def resolve_recipe(brief: CreativeBrief, *, recipe_id: str | None = None) -> tuple[CreativeRecipe, RecipeSelection]:
    """Resolve only trusted recipes and verify compatibility before model routing."""
    explicit = recipe_id is not None
    requested = recipe_id or _default_recipe_id(brief)
    recipe = get_recipe(requested)
    if recipe is None:
        raise ValueError("Unknown or untrusted creative recipe.")
    if brief.kind not in recipe.kinds or brief.mode not in recipe.supported_modes:
        raise ValueError(
            f"Creative recipe {recipe.recipe_id} does not support {brief.kind}/{brief.mode}."
        )
    available_roles = _brief_reference_roles(brief)
    missing_roles = set(recipe.required_reference_roles) - available_roles
    unsupported_roles = available_roles - (
        set(recipe.required_reference_roles) | set(recipe.optional_reference_roles)
    )
    if missing_roles:
        raise ValueError(
            "Creative recipe requires reference role: "
            + ", ".join(sorted(role.value for role in missing_roles))
            + "."
        )
    if unsupported_roles and recipe.recipe_id != _default_recipe_id(brief):
        raise ValueError(
            "Creative recipe does not accept reference role: "
            + ", ".join(sorted(role.value for role in unsupported_roles))
            + "."
        )
    reasons = ["trusted_recipe_registry", "explicit_recipe" if explicit else "compatibility_default"]
    return recipe, RecipeSelection(
        recipe_id=recipe.recipe_id,
        version=recipe.version,
        reason_codes=reasons,
        evidence_level=recipe.evidence_level,
        registry_version=RECIPE_REGISTRY_VERSION,
    )


__all__ = ["registry", "get_recipe", "resolve_recipe", "RECIPE_REGISTRY_VERSION"]
