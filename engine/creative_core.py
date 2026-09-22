"""Typed domain objects for Creative Engine planning.

These objects contain no provider credentials and make no external calls. They are
safe to persist inside MediaGeneration.parameters as diagnostics/provenance.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


REGISTRY_VERSION = "2026-09-21.1"
COMPILER_VERSION = "2026-09-22.1"
BRIEF_VERSION = "2026-09-22.1"


class Complexity(str, Enum):
    simple = "simple"
    medium = "medium"
    advanced = "advanced"


class EvidenceLevel(str, Enum):
    official = "OFFICIAL"
    verified = "VERIFIED"
    heuristic = "HEURISTIC"


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
    registry_version: str = REGISTRY_VERSION


class CreativePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: CreativeBrief
    context: CreativeContext
    complexity: Complexity
    selection: ModelSelection
    prompt: str
    parameters: dict
    inspiration_ids: list[str] = Field(default_factory=list)
    preflight: list[PreflightIssue] = Field(default_factory=list)
    compiler_version: str = COMPILER_VERSION
    registry_version: str = REGISTRY_VERSION
