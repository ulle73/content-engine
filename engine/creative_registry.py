"""Versioned, allow-listed model intelligence for Creative Engine.

Only entries whose contract has been verified may be selected automatically.
Prompt-library metadata never changes provider capabilities in this registry.
Public documentation proves capability, not account availability; provider
estimate/preflight remains the final account-scoped gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.conf import settings

from .creative_core import EvidenceLevel, ReferenceRole, REGISTRY_VERSION


@dataclass(frozen=True)
class ModeReferenceContract:
    mode: str
    required_reference_roles: tuple[ReferenceRole, ...] = ()
    optional_reference_roles: tuple[ReferenceRole, ...] = ()

    @property
    def supported_reference_roles(self) -> tuple[ReferenceRole, ...]:
        return tuple(dict.fromkeys((*self.required_reference_roles, *self.optional_reference_roles)))


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
    profile_version: str = ""
    profile_status: Literal["verified", "stale"] = "stale"
    evidence_version: str = ""
    sources: tuple[str, ...] = ()
    reference_contracts: tuple[ModeReferenceContract, ...] = ()
    aspect_ratio_behavior: Literal["explicit", "prompt_only", "derived", "none"] = "none"
    prompt_sections: tuple[str, ...] = ()
    negative_prompt_support: bool = False
    known_constraints: tuple[str, ...] = ()
    recipe_capabilities: tuple[str, ...] = ()

    def reference_contract(self, mode: str) -> ModeReferenceContract | None:
        return next((item for item in self.reference_contracts if item.mode == mode), None)

    def supports_reference_role(self, mode: str, role: ReferenceRole) -> bool:
        contract = self.reference_contract(mode)
        return bool(contract and role in contract.supported_reference_roles)


# Deliberately small. Availability in documentation is not the same as account
# availability; provider estimate/preflight remains the final fail-closed gate.
def registry() -> tuple[ModelIntelligence, ...]:
    return (
        ModelIntelligence(
            provider="openai",
            model_id=settings.OPENAI_IMAGE_MODEL,
            kind="image",
            modes=("text-to-image", "image-to-image"),
            enabled=settings.OPENAI_IMAGE_MODEL == "gpt-image-2",
            evidence_level=EvidenceLevel.official,
            verified_date="2026-09-23",
            source="https://developers.openai.com/api/docs/models/gpt-image-2",
            profile_version="2026-09-23.1",
            profile_status="verified",
            evidence_version="gpt-image-2-2026-04-21",
            sources=(
                "https://developers.openai.com/api/docs/models/gpt-image-2",
                "https://developers.openai.com/api/docs/guides/image-generation",
            ),
            resolutions=("1024x1024", "1024x1536", "1536x1024"),
            explicit_aspect_ratio=False,
            aspect_ratio_behavior="derived",
            reference_support=True,
            reference_contracts=(
                ModeReferenceContract(mode="text-to-image"),
                ModeReferenceContract(
                    mode="image-to-image",
                    required_reference_roles=(ReferenceRole.start_image,),
                ),
            ),
            audio_support=False,
            quality_tier=3,
            speed_tier=2,
            cost_tier=2,
            prompt_strategy="natural_scene",
            prompt_sections=(
                "USER_INTENT",
                "BRAND_RENDERING",
                "VISUAL_DIRECTION",
                "FORMAT",
                "PRESERVE",
                "AVOID",
                "INSPIRATION",
                "SAFETY",
                "COMPANY_CONTEXT",
            ),
            negative_prompt_support=False,
            known_constraints=(
                "GPT-Image-2 image inputs are processed at high fidelity; input_fidelity is not configurable.",
                "Content Engine intentionally allow-lists the three recommended 1K output sizes.",
                "The current Content Engine adapter accepts one source image for image editing.",
            ),
            recipe_capabilities=("general_image", "reference_edit"),
        ),
        ModelIntelligence(
            provider="higgsfield",
            model_id=settings.HIGGSFIELD_VIDEO_MODEL,
            kind="video",
            modes=("text-to-video", "image-to-video"),
            enabled=settings.HIGGSFIELD_VIDEO_MODEL == "kling-video/v2.5-turbo/pro",
            evidence_level=EvidenceLevel.official,
            verified_date="2026-09-23",
            source="https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-image-to-video",
            profile_version="2026-09-23.1",
            profile_status="verified",
            evidence_version="kling-2.5-turbo-pro-api-2026-09-23",
            sources=(
                "https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-text-to-video",
                "https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-image-to-video",
            ),
            durations=(5, 10),
            # Official current API exposes no aspect_ratio field for these endpoints.
            explicit_aspect_ratio=False,
            aspect_ratio_behavior="prompt_only",
            reference_support=True,
            reference_contracts=(
                ModeReferenceContract(mode="text-to-video"),
                ModeReferenceContract(
                    mode="image-to-video",
                    required_reference_roles=(ReferenceRole.start_image,),
                ),
            ),
            audio_support=False,
            quality_tier=3,
            speed_tier=2,
            cost_tier=2,
            prompt_strategy="ordered_motion",
            prompt_sections=(
                "SCENE",
                "CAMERA",
                "FORMAT_INTENT",
                "PRESERVE_EXACTLY",
                "ALLOW_MOTION_CHANGE",
                "FORBID",
                "INSPIRATION_MECHANISMS",
                "SAFETY",
                "BRAND_CONTEXT",
            ),
            negative_prompt_support=True,
            known_constraints=(
                "Duration is limited to 5 or 10 seconds.",
                "The current Pro text-to-video and image-to-video endpoints expose no sound field.",
                "The current Pro endpoints expose no aspect_ratio field.",
                "Image-to-video requires image_url.",
            ),
            recipe_capabilities=("general_video", "reference_animation", "single_continuous_shot"),
        ),
    )


def _verified_profile(item: ModelIntelligence) -> bool:
    contracts = [contract.mode for contract in item.reference_contracts]
    contract_set = set(contracts)
    references_are_valid = all(
        not (set(contract.required_reference_roles) & set(contract.optional_reference_roles))
        for contract in item.reference_contracts
    )
    return (
        item.profile_status == "verified"
        and bool(item.profile_version)
        and bool(item.verified_date)
        and bool(item.source)
        and bool(item.sources)
        and bool(item.evidence_version)
        and item.prompt_strategy in {"natural_scene", "ordered_motion"}
        and bool(item.prompt_sections)
        and len(contracts) == len(contract_set)
        and contract_set == set(item.modes)
        and references_are_valid
    )


def verified_models(kind: str, mode: str) -> list[ModelIntelligence]:
    return [
        item for item in registry()
        if item.enabled
        and item.kind == kind
        and mode in item.modes
        and item.evidence_level in {EvidenceLevel.official, EvidenceLevel.verified}
        and _verified_profile(item)
    ]


def get_model(provider: str, model_id: str) -> ModelIntelligence | None:
    return next((item for item in registry() if item.provider == provider and item.model_id == model_id), None)


__all__ = [
    "ModeReferenceContract",
    "ModelIntelligence",
    "REGISTRY_VERSION",
    "registry",
    "verified_models",
    "get_model",
]
