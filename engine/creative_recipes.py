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
    reasons = ["trusted_recipe_registry", "explicit_recipe" if explicit else "compatibility_default"]
    return recipe, RecipeSelection(
        recipe_id=recipe.recipe_id,
        version=recipe.version,
        reason_codes=reasons,
        evidence_level=recipe.evidence_level,
        registry_version=RECIPE_REGISTRY_VERSION,
    )


__all__ = ["registry", "get_recipe", "resolve_recipe", "RECIPE_REGISTRY_VERSION"]
