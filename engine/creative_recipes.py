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
        CreativeRecipe(
            recipe_id="scroll_transition_bridge",
            version="1.0.0",
            name="Scroll transition bridge",
            description="Continuity-first single-shot bridge between two canonical anchor frames for scrub-friendly cinematic sequences.",
            kinds=("video",),
            supported_modes=("image-to-video",),
            goal_tags=("continuity", "transition", "scroll", "cinematic_sequence"),
            format_tags=("single_continuous_shot", "scrub_friendly"),
            required_reference_roles=(ReferenceRole.start_image, ReferenceRole.end_image),
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
            negative_constraints=(
                "hard cuts",
                "scene changes",
                "morphing",
                "duplicated objects",
                "disappearing objects",
                "unrequested new objects",
                "identity changes",
                "lighting resets",
                "sudden perspective jumps",
                "sudden acceleration",
            ),
            default_duration_intent=5,
            default_format_intent="anchor_to_anchor",
            draft_policy="draft_then_final",
            evaluation_rules=(
                "start_anchor_adherence",
                "end_anchor_adherence",
                "subject_consistency",
                "geometry_stability",
                "camera_smoothness",
                "lighting_continuity",
                "reverse_scrub_coherence",
            ),
            supported_model_families=("higgsfield",),
            evidence_sources=(
                "https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance",
                "https://higgsfield.ai/blog/seedance-2-5-prompting-guide",
                "https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference",
            ),
            verified_at="2026-09-24",
            evidence_level=EvidenceLevel.official,
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


def registry() -> tuple[CreativeRecipe, ...]:
    """Return trusted recipes available to the planning layer.

    A1 intentionally starts with compatibility recipes only. Automatic semantic
    recipe selection is added in A2; these defaults preserve all existing media
    behavior while establishing provenance and a trusted extension point.
    """
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
