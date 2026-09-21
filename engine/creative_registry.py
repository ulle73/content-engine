"""Versioned, allow-listed model intelligence for Creative Engine.

Only entries whose contract has been verified may be selected automatically.
Prompt-library metadata never changes provider capabilities in this registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.conf import settings

from .creative_core import EvidenceLevel, REGISTRY_VERSION


@dataclass(frozen=True)
class ModelIntelligence:
    provider: Literal["openai", "higgsfield"]
    model_id: str
    kind: Literal["image", "video"]
    modes: tuple[str, ...]
    enabled: bool
    evidence_level: EvidenceLevel
    verified_date: str
    source: str
    durations: tuple[int, ...] = ()
    explicit_aspect_ratio: bool = False
    resolutions: tuple[str, ...] = ()
    reference_support: bool = False
    audio_support: bool = False
    quality_tier: int = 2
    speed_tier: int = 2
    cost_tier: int = 2
    prompt_strategy: str = "natural"


# Deliberately small. Availability in documentation is not the same as account
# availability; Higgsfield estimate/preflight remains the final fail-closed gate.
def registry() -> tuple[ModelIntelligence, ...]:
    return (
        ModelIntelligence(
            provider="openai",
            model_id=settings.OPENAI_IMAGE_MODEL,
            kind="image",
            modes=("text-to-image", "image-to-image"),
            enabled=settings.OPENAI_IMAGE_MODEL == "gpt-image-2",
            evidence_level=EvidenceLevel.official,
            verified_date="2026-09-21",
            source="https://platform.openai.com/docs/models",
            resolutions=("1024x1024", "1024x1536", "1536x1024"),
            reference_support=True,
            quality_tier=3,
            speed_tier=2,
            cost_tier=2,
            prompt_strategy="natural_scene",
        ),
        ModelIntelligence(
            provider="higgsfield",
            model_id=settings.HIGGSFIELD_VIDEO_MODEL,
            kind="video",
            modes=("text-to-video", "image-to-video"),
            enabled=settings.HIGGSFIELD_VIDEO_MODEL == "kling-video/v2.5-turbo/pro",
            evidence_level=EvidenceLevel.verified,
            verified_date="2026-09-21",
            source="https://docs.higgsfield.ai/docs",
            durations=(5, 10),
            # The existing verified request schema does not send a separate
            # aspect-ratio parameter. Preserve format intent in the compiled
            # prompt instead of inventing an API field.
            explicit_aspect_ratio=False,
            reference_support=True,
            quality_tier=3,
            speed_tier=2,
            cost_tier=2,
            prompt_strategy="ordered_motion",
        ),
    )


def verified_models(kind: str, mode: str) -> list[ModelIntelligence]:
    return [
        item for item in registry()
        if item.enabled
        and item.kind == kind
        and mode in item.modes
        and item.evidence_level in {EvidenceLevel.official, EvidenceLevel.verified}
    ]


def get_model(provider: str, model_id: str) -> ModelIntelligence | None:
    return next((item for item in registry() if item.provider == provider and item.model_id == model_id), None)


__all__ = ["ModelIntelligence", "REGISTRY_VERSION", "registry", "verified_models", "get_model"]
