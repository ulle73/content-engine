"""Versioned, allow-listed model intelligence for Creative Engine.

Only entries whose current contract has been verified may be selected
automatically. Public documentation proves capability, not account availability;
provider estimate/preflight remains the final account-scoped gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.conf import settings

from .creative_core import EvidenceLevel, ReferenceRole, REGISTRY_VERSION


AspectBehavior = Literal["explicit", "prompt_only", "derived", "none"]


@dataclass(frozen=True)
class ModeRequestContract:
    """Exact request contract for one provider model mode/endpoint."""

    mode: str
    endpoint: str = ""
    required_reference_roles: tuple[ReferenceRole, ...] = ()
    optional_reference_roles: tuple[ReferenceRole, ...] = ()
    reference_fields: tuple[tuple[ReferenceRole, str], ...] = ()
    durations: tuple[int, ...] = ()
    duration_range: tuple[int, int] | None = None
    resolutions: tuple[str, ...] = ()
    aspect_ratio_behavior: AspectBehavior = "none"
    aspect_ratios: tuple[str, ...] = ()
    audio_parameter: str = ""
    audio_default: bool | None = None
    output_formats: tuple[str, ...] = ()
    prompt_required: bool = True

    @property
    def supported_reference_roles(self) -> tuple[ReferenceRole, ...]:
        return tuple(dict.fromkeys((*self.required_reference_roles, *self.optional_reference_roles)))

    def provider_field(self, role: ReferenceRole) -> str | None:
        return next((field for candidate, field in self.reference_fields if candidate == role), None)

    def supports_duration(self, duration: int) -> bool:
        if self.durations:
            return duration in self.durations
        if self.duration_range:
            return self.duration_range[0] <= duration <= self.duration_range[1]
        return False

    def normalize_duration(self, duration: int) -> int:
        if self.durations:
            return min(self.durations, key=lambda item: (abs(item - duration), -item))
        if self.duration_range:
            return min(max(duration, self.duration_range[0]), self.duration_range[1])
        raise ValueError("The verified model mode has no duration contract.")


# Backwards-compatible name used by B1 tests/imports. New code should use
# ModeRequestContract because the contract now includes the full request shape.
ModeReferenceContract = ModeRequestContract


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
    reference_contracts: tuple[ModeRequestContract, ...] = ()
    aspect_ratio_behavior: AspectBehavior = "none"
    prompt_sections: tuple[str, ...] = ()
    negative_prompt_support: bool = False
    known_constraints: tuple[str, ...] = ()
    recipe_capabilities: tuple[str, ...] = ()

    def request_contract(self, mode: str) -> ModeRequestContract | None:
        return next((item for item in self.reference_contracts if item.mode == mode), None)

    def reference_contract(self, mode: str) -> ModeRequestContract | None:
        return self.request_contract(mode)

    def supports_reference_role(self, mode: str, role: ReferenceRole) -> bool:
        contract = self.request_contract(mode)
        return bool(contract and role in contract.supported_reference_roles)


SEEDANCE_RATIOS = ("16:9", "4:3", "1:1", "3:4", "9:16", "21:9")


def registry() -> tuple[ModelIntelligence, ...]:
    """Trusted current model profiles.

    Public-doc availability is deliberately separate from the authenticated
    Content Engine account check done through Higgsfield estimate/preflight.
    """
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
            profile_version="2026-09-23.2",
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
                ModeRequestContract(mode="text-to-image"),
                ModeRequestContract(
                    mode="image-to-image",
                    required_reference_roles=(ReferenceRole.start_image,),
                    reference_fields=((ReferenceRole.start_image, "image"),),
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
            model_id="kling-video/v2.5-turbo/pro",
            kind="video",
            modes=("text-to-video", "image-to-video"),
            enabled=True,
            evidence_level=EvidenceLevel.official,
            verified_date="2026-09-23",
            source="https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-image-to-video",
            profile_version="2026-09-23.2",
            profile_status="verified",
            evidence_version="kling-2.5-turbo-pro-api-2026-09-23",
            sources=(
                "https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-text-to-video",
                "https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-image-to-video",
            ),
            durations=(5, 10),
            reference_support=True,
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
                "The current Pro endpoints expose no sound field.",
                "The current Pro endpoints expose no aspect_ratio field.",
                "Image-to-video requires image_url.",
            ),
            recipe_capabilities=("general_video", "reference_animation", "single_continuous_shot"),
            reference_contracts=(
                ModeRequestContract(
                    mode="text-to-video",
                    endpoint="kling-video/v2.5-turbo/pro/text-to-video",
                    durations=(5, 10),
                    aspect_ratio_behavior="prompt_only",
                ),
                ModeRequestContract(
                    mode="image-to-video",
                    endpoint="kling-video/v2.5-turbo/pro/image-to-video",
                    required_reference_roles=(ReferenceRole.start_image,),
                    reference_fields=((ReferenceRole.start_image, "image_url"),),
                    durations=(5, 10),
                    aspect_ratio_behavior="prompt_only",
                ),
            ),
            aspect_ratio_behavior="prompt_only",
        ),
        ModelIntelligence(
            provider="higgsfield",
            model_id="bytedance/seedance-2.5",
            kind="video",
            modes=("text-to-video", "image-to-video"),
            enabled=True,
            evidence_level=EvidenceLevel.official,
            verified_date="2026-09-25",
            source="https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference",
            profile_version="2026-09-25.2",
            profile_status="verified",
            evidence_version="seedance-2.5-commercial-profile-2026-09-25",
            sources=(
                "https://open.higgsfield.ai/models/bytedance/seedance-2.5/text-to-video/api-reference",
                "https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference",
                "https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance",
                "https://higgsfield.ai/blog/seedance-2-5-prompting-guide",
            ),
            reference_support=True,
            audio_support=True,
            quality_tier=4,
            speed_tier=2,
            cost_tier=4,
            prompt_strategy="seedance_structured",
            prompt_sections=(
                "GLOBAL_STYLE",
                "SCENE",
                "LOCATION",
                "FIRST_FRAME_BLOCKING",
                "END_FRAME",
                "CAMERA",
                "PHYSICS",
                "LIGHTING",
                "AUDIO",
                "BRAND_CONTEXT",
            ),
            known_constraints=(
                "Current API duration is 4-30 seconds.",
                "Current API exposes 480p and 720p.",
                "Image-to-video requires image_url and optionally accepts end_image_url.",
                "Provider defaults generate_audio=true; Content Engine must set it explicitly.",
            ),
            recipe_capabilities=("general_video", "reference_animation", "single_continuous_shot", "first_last_frame", "native_audio"),
            reference_contracts=(
                ModeRequestContract(
                    mode="text-to-video",
                    endpoint="bytedance/seedance-2.5/text-to-video",
                    duration_range=(4, 30),
                    resolutions=("480p", "720p"),
                    aspect_ratio_behavior="explicit",
                    aspect_ratios=SEEDANCE_RATIOS,
                    audio_parameter="generate_audio",
                    audio_default=True,
                    output_formats=("mp4", "mov"),
                ),
                ModeRequestContract(
                    mode="image-to-video",
                    endpoint="bytedance/seedance-2.5/image-to-video",
                    required_reference_roles=(ReferenceRole.start_image,),
                    optional_reference_roles=(ReferenceRole.end_image,),
                    reference_fields=(
                        (ReferenceRole.start_image, "image_url"),
                        (ReferenceRole.end_image, "end_image_url"),
                    ),
                    duration_range=(4, 30),
                    resolutions=("480p", "720p"),
                    aspect_ratio_behavior="derived",
                    audio_parameter="generate_audio",
                    audio_default=True,
                    output_formats=("mp4", "mov"),
                    prompt_required=False,
                ),
            ),
        ),
        ModelIntelligence(
            provider="higgsfield",
            model_id="bytedance/seedance-2.0",
            kind="video",
            modes=("text-to-video", "image-to-video"),
            enabled=True,
            evidence_level=EvidenceLevel.official,
            verified_date="2026-09-25",
            source="https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference",
            profile_version="2026-09-25.2",
            profile_status="verified",
            evidence_version="seedance-2.0-commercial-profile-2026-09-25",
            sources=(
                "https://open.higgsfield.ai/models/bytedance/seedance-2.0/text-to-video/api-reference",
                "https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference",
                "https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance",
            ),
            reference_support=True,
            audio_support=True,
            quality_tier=4,
            speed_tier=1,
            cost_tier=5,
            prompt_strategy="seedance_structured",
            prompt_sections=(
                "GLOBAL_STYLE",
                "SCENE",
                "LOCATION",
                "FIRST_FRAME_BLOCKING",
                "END_FRAME",
                "CAMERA",
                "PHYSICS",
                "LIGHTING",
                "AUDIO",
                "BRAND_CONTEXT",
            ),
            known_constraints=(
                "Current API duration is 4-15 seconds.",
                "Current API exposes 480p, 720p, 1080p and 4k.",
                "Image-to-video requires image_url and optionally accepts end_image_url.",
                "Provider defaults generate_audio=true; Content Engine must set it explicitly.",
            ),
            recipe_capabilities=("general_video", "reference_animation", "single_continuous_shot", "first_last_frame", "high_resolution", "native_audio"),
            reference_contracts=(
                ModeRequestContract(
                    mode="text-to-video",
                    endpoint="bytedance/seedance-2.0/text-to-video",
                    duration_range=(4, 15),
                    resolutions=("480p", "720p", "1080p", "4k"),
                    aspect_ratio_behavior="explicit",
                    aspect_ratios=SEEDANCE_RATIOS,
                    audio_parameter="generate_audio",
                    audio_default=True,
                ),
                ModeRequestContract(
                    mode="image-to-video",
                    endpoint="bytedance/seedance-2.0/image-to-video",
                    required_reference_roles=(ReferenceRole.start_image,),
                    optional_reference_roles=(ReferenceRole.end_image,),
                    reference_fields=(
                        (ReferenceRole.start_image, "image_url"),
                        (ReferenceRole.end_image, "end_image_url"),
                    ),
                    duration_range=(4, 15),
                    resolutions=("480p", "720p", "1080p", "4k"),
                    aspect_ratio_behavior="derived",
                    audio_parameter="generate_audio",
                    audio_default=True,
                    prompt_required=False,
                ),
            ),
        ),
    )


def _verified_profile(item: ModelIntelligence) -> bool:
    contracts = list(item.reference_contracts)
    modes = [contract.mode for contract in contracts]
    references_are_valid = all(
        not (set(contract.required_reference_roles) & set(contract.optional_reference_roles))
        for contract in contracts
    )
    fields_are_valid = all(
        len({role for role, _ in contract.reference_fields}) == len(contract.reference_fields)
        and len({field for _, field in contract.reference_fields}) == len(contract.reference_fields)
        and set(contract.supported_reference_roles) <= {role for role, _ in contract.reference_fields}
        for contract in contracts
    )
    video_contracts_are_valid = all(
        (
            bool(contract.endpoint)
            and bool(contract.durations) != bool(contract.duration_range)
            and (contract.aspect_ratio_behavior != "explicit" or bool(contract.aspect_ratios))
            and (not contract.audio_parameter or contract.audio_default is not None)
        )
        for contract in contracts
    ) if item.kind == "video" else True
    return (
        item.profile_status == "verified"
        and bool(item.profile_version)
        and bool(item.verified_date)
        and bool(item.source)
        and bool(item.sources)
        and bool(item.evidence_version)
        and item.prompt_strategy in {"natural_scene", "ordered_motion", "seedance_structured"}
        and bool(item.prompt_sections)
        and len(modes) == len(set(modes))
        and set(modes) == set(item.modes)
        and references_are_valid
        and fields_are_valid
        and video_contracts_are_valid
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
    "ModeRequestContract",
    "ModeReferenceContract",
    "ModelIntelligence",
    "REGISTRY_VERSION",
    "registry",
    "verified_models",
    "get_model",
]
