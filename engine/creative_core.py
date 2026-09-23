"""Typed domain objects for Creative Engine planning.

These objects contain no provider credentials and make no external calls. They are
safe to persist inside MediaGeneration.parameters as diagnostics/provenance.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


REGISTRY_VERSION = "2026-09-23.2"
COMPILER_VERSION = "2026-09-23.1"
BRIEF_VERSION = "2026-09-22.1"
RECIPE_REGISTRY_VERSION = "2026-09-23.1"


class Complexity(str, Enum):
    simple = "simple"
    medium = "medium"
    advanced = "advanced"


class EvidenceLevel(str, Enum):
    official = "OFFICIAL"
    verified = "VERIFIED"
    heuristic = "HEURISTIC"


class ReferenceRole(str, Enum):
    start_image = "START_IMAGE"
    end_image = "END_IMAGE"
    product_reference = "PRODUCT_REFERENCE"
    character_reference = "CHARACTER_REFERENCE"
    location_reference = "LOCATION_REFERENCE"
    style_reference = "STYLE_REFERENCE"
    video_reference = "VIDEO_REFERENCE"
    audio_reference = "AUDIO_REFERENCE"


class CreativeRecipe(BaseModel):
    """Trusted, versioned production method selected from the internal registry.

    Recipes are executable Creative Engine policy, unlike Prompt Library entries,
    which remain untrusted inspiration data.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    recipe_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_]{2,79}$")
    version: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    kinds: tuple[Literal["image", "video"], ...]
    supported_modes: tuple[
        Literal["text-to-image", "image-to-image", "text-to-video", "image-to-video"], ...
    ]
    goal_tags: tuple[str, ...] = ()
    format_tags: tuple[str, ...] = ()
    required_reference_roles: tuple[ReferenceRole, ...] = ()
    optional_reference_roles: tuple[ReferenceRole, ...] = ()
    camera_strategy: tuple[str, ...] = ()
    motion_strategy: tuple[str, ...] = ()
    continuity_strategy: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()
    default_duration_intent: int | None = Field(default=None, ge=1, le=120)
    default_format_intent: str = "auto"
    draft_policy: Literal["single_pass", "draft_then_final"] = "single_pass"
    evaluation_rules: tuple[str, ...] = ()
    supported_model_families: tuple[str, ...] = ()
    evidence_sources: tuple[str, ...] = ()
    verified_at: str
    evidence_level: EvidenceLevel


class RecipeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    version: str
    reason_codes: list[str]
    evidence_level: EvidenceLevel
    registry_version: str = RECIPE_REGISTRY_VERSION


class CreativeBrief(BaseModel):
    """Provider-neutral interpretation of the human request.

    Keep the schema permissive enough for future models while constraining the
    fields that influence billing/routing.
    """

    model_config = ConfigDict(extra="forbid")

    version: str = BRIEF_VERSION
    user_intent: str = Field(min_length=1, max_length=6000)
    kind: Literal["image", "video"]
    mode: Literal["text-to-image", "image-to-image", "text-to-video", "image-to-video"]
    purpose: str = "social content"
    platform: str = "auto"
    campaign: str = ""
    subject: str = ""
    environment: str = ""
    visual_style: list[str] = Field(default_factory=list)
    realism: str = ""
    camera_movement: list[str] = Field(default_factory=list)
    camera_position: str = ""
    framing: str = ""
    shot_type: str = ""
    lens_look: str = ""
    composition: str = ""
    lighting: str = ""
    subject_motion: list[str] = Field(default_factory=list)
    environmental_motion: list[str] = Field(default_factory=list)
    pacing: str = ""
    temporal_sequence: list[str] = Field(default_factory=list)
    transition_intent: str = ""
    duration_seconds: int | None = Field(default=None, ge=1, le=120)
    aspect_ratio: str = "auto"
    resolution: str = "auto"
    audio_intent: str = "none"
    dialogue: str = ""
    reference_media: list[str] = Field(default_factory=list)
    preserve: list[str] = Field(default_factory=list)
    allow_change: list[str] = Field(default_factory=list)
    forbid: list[str] = Field(default_factory=list)
    visible_text: list[str] = Field(default_factory=list)
    factual_constraints: list[str] = Field(default_factory=list)
    company_constraints: list[str] = Field(default_factory=list)
    quality_preference: Literal["quality", "balanced", "economy"] = "balanced"
    speed_preference: Literal["fast", "balanced", "quality"] = "balanced"
    budget_preference: Literal["economy", "balanced", "quality"] = "balanced"


class CreativeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str
    profile: str = ""
    voice: str = ""
    current_facts: str = ""
    idea_title: str = ""
    idea_angle: str = ""
    caption: str = ""
    channel: str = ""
    campaign: str = ""


class PreflightIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["warning", "error"]
    message: str
    auto_fixed: bool = False


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["openai", "higgsfield"]
    model_id: str
    mode: str
    reason_codes: list[str]
    evidence_level: EvidenceLevel
    profile_version: str = ""
    evidence_version: str = ""
    registry_version: str = REGISTRY_VERSION


class CreativePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: CreativeBrief
    context: CreativeContext
    complexity: Complexity
    selection: ModelSelection
    recipe: RecipeSelection
    prompt: str
    parameters: dict
    inspiration_ids: list[str] = Field(default_factory=list)
    preflight: list[PreflightIssue] = Field(default_factory=list)
    compiler_version: str = COMPILER_VERSION
    registry_version: str = REGISTRY_VERSION
    recipe_registry_version: str = RECIPE_REGISTRY_VERSION
