"""Reviewed provider profiles, shared by routing, UI and price planning.

No remote catalog is trusted to enable paid endpoints automatically. Add a profile
with mode-specific contracts and source links, then verify it with the contract
tests. Planning prices are conservative public hints, never account quotations.
"""
import json
from functools import lru_cache
from pathlib import Path

from .creative_core import EvidenceLevel, ReferenceRole

CATALOG_VERSION = "2026-10-03.1"


@lru_cache(maxsize=1)
def profiles():
    document = json.loads(Path(__file__).with_name("higgsfield_video_profiles.json").read_text(encoding="utf-8"))
    return {item["id"]: item for item in document["models"]}


def additional_video_models():
    from .creative_registry import ModelIntelligence, ModeRequestContract

    models = []
    for item in profiles().values():
        contracts = []
        for mode in item["contracts"]:
            start, end = mode["start_field"], mode["end_field"]
            fields = []
            if start:
                fields.append((ReferenceRole.start_image, start))
            if end:
                fields.append((ReferenceRole.end_image, end))
            contracts.append(ModeRequestContract(
                mode=mode["mode"], endpoint=mode["endpoint"],
                required_reference_roles=(ReferenceRole.start_image,) if start else (),
                optional_reference_roles=(ReferenceRole.end_image,) if end else (),
                reference_fields=tuple(fields), durations=tuple(mode["durations"]),
                duration_range=tuple(mode["duration_range"]) if mode["duration_range"] else None,
                resolutions=tuple(mode["resolutions"]),
                aspect_ratio_behavior="explicit" if mode["aspect_ratios"] else "derived" if start else "prompt_only",
                aspect_ratios=tuple(mode["aspect_ratios"]), audio_parameter=mode["audio_parameter"],
                audio_default=mode["audio_default"] in (True, "on") if mode["audio_parameter"] else None,
                audio_type=mode["audio_type"] or "boolean", request_fields=tuple(mode["request_fields"]),
                defaults=tuple(mode["defaults"].items()),
            ))
        capabilities = ["general_video", "reference_animation", "single_continuous_shot"]
        if any(c.supports_duration(10) and ReferenceRole.end_image in c.supported_reference_roles for c in contracts):
            capabilities.append("first_last_frame")
        if any(c.audio_parameter for c in contracts):
            capabilities.append("native_audio")
        if any("4k" in c.resolutions for c in contracts):
            capabilities.append("high_resolution")
        models.append(ModelIntelligence(
            provider="higgsfield", model_id=item["id"], kind="video", modes=tuple(c.mode for c in contracts),
            enabled=True, evidence_level=EvidenceLevel.official, verified_date=item["verified_date"],
            source=item["sources"][0], sources=tuple(item["sources"]), profile_version=item["profile_version"],
            evidence_version=CATALOG_VERSION, profile_status="verified", reference_support=True,
            audio_support="native_audio" in capabilities, quality_tier=item["quality_tier"],
            speed_tier=item["speed_tier"], cost_tier=item["cost_tier"], prompt_strategy="cinematic_scene",
            prompt_sections=("GLOBAL_STYLE", "SCENE", "LOCATION", "FIRST_FRAME_BLOCKING", "END_FRAME",
                             "CAMERA", "PHYSICS", "LIGHTING", "AUDIO", "BRAND_CONTEXT"),
            reference_contracts=tuple(contracts), recipe_capabilities=tuple(capabilities),
            label=item["label"], summary=item["summary"], preview=item["preview"],
        ))
    return tuple(models)


def model_label(model_id):
    from .creative_controls import MODEL_LABELS
    return profiles().get(model_id, {}).get("label") or MODEL_LABELS.get(model_id, model_id)


def planning_rate(model_id, resolution):
    """Use the largest published rate across modes; no temporary discounts."""
    from decimal import Decimal
    profile = profiles().get(model_id)
    if not profile:
        return None
    if profile.get("resolution_rates"):
        value = profile["resolution_rates"].get(resolution)
        return Decimal(value) if value else None
    values = [Decimal(item["max_usd_per_second"]) for item in profile["planning_prices"].values()
              if item.get("max_usd_per_second")]
    return max(values) if values else None


def price_source(model_id):
    return profiles().get(model_id, {}).get("sources", [""])[0]
