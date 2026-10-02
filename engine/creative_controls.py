"""Human-facing controls compiled into the existing CreativeBrief.

The trusted recipe/model registries remain the only capability source.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .creative_core import CreativeBrief, ReferenceRole
from .creative_recipes import registry as recipe_registry
from .creative_registry import registry as model_registry
from .creative_registry import verified_models

CONTROL_VERSION = "2026-09-30.1"
CAMERAS = {
    "auto": ("F\u00f6lj min id\u00e9", ""),
    "push_in": ("N\u00e4rma sig motivet", "slow push-in"),
    "orbit": ("R\u00f6ra sig runt motivet", "smooth orbit around the subject"),
    "follow": ("F\u00f6lja motivet", "smooth tracking shot following the subject"),
    "static": ("St\u00e5 stilla", "static"),
}
MOTIONS = {
    "auto": ("F\u00f6lj min id\u00e9", ""),
    "still": ("Vara stilla", "Keep the subject stationary"),
    "rotate": ("Rotera", "The subject rotates slowly around its own axis"),
    "lift": ("Lyfta", "The subject lifts smoothly, retaining its shape and details"),
    "forward": ("R\u00f6ra sig fram\u00e5t", "The subject moves forward along one continuous path"),
}
ENDINGS = {
    "auto": ("F\u00f6lj min id\u00e9", ""),
    "close_up": ("Avsluta i n\u00e4rbild", "Finish in a clear close-up of the same subject"),
    "hero": ("L\u00e5t motivet st\u00e5 i fokus", "Settle on a clean hero composition of the same subject"),
    "match_end": ("Matcha slutbilden", "Arrive naturally at the supplied end image and hold the closing composition"),
}
# Presentation names only. Production methods and capabilities remain in recipes.
TEMPLATE_LABELS = {
    "premium_product_reveal": ("Filmisk reveal", "Visa fram produkten med lugn r\u00f6relse och stabila detaljer."),
    "product_showcase": ("Produkt i fokus", "Utg\u00e5 fr\u00e5n din produktbild och visa det viktiga."),
    "before_after": ("F\u00f6re och efter", "En tydlig f\u00f6r\u00e4ndring mellan dina tv\u00e5 bilder."),
    "scroll_transition_bridge": ("Mjuk \u00f6verg\u00e5ng", "Bind ihop dina tv\u00e5 bilder i en sammanh\u00e4ngande r\u00f6relse."),
    "landscape_environment_hero": ("Golfbana och milj\u00f6", "En lugn filmisk f\u00e4rd genom platsen du beskriver."),
    "luxury_brand_film": ("Lugn varum\u00e4rkesfilm", "Avskalad k\u00e4nsla, genomt\u00e4nkt ljus och f\u00e5 distraktioner."),
}
MODEL_LABELS = {
    "kling-video/v2.5-turbo/pro": "Kling 2.5 Turbo",
    "bytedance/seedance-2.5": "Seedance 2.5",
    "bytedance/seedance-2.0": "Seedance 2.0",
}


class CreativeControls(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_seconds: int | None = Field(default=None, ge=1, le=120)
    camera: Literal["auto", "push_in", "orbit", "follow", "static"] = "auto"
    subject_motion: Literal["auto", "still", "rotate", "lift", "forward"] = "auto"
    ending: Literal["auto", "close_up", "hero", "match_end"] = "auto"
    audio: Literal["auto", "none", "native"] = "auto"
    resolution: Literal["auto", "480p", "720p", "1080p", "4k"] = "auto"


def _explicit_subject_motion(text):
    # Match directions tied to the subject, not camera or environmental movement.
    subject = r"(?:motivet|produkten|golfbollen|bollen|objektet|föremålet|flaskan|bilen|personen|subject|product|golf ball|ball|object|bottle|car|person)"
    modifiers = r"(?:(?:ska|skall|bör|kan|långsamt|sakta|lugnt|mjukt|will|should|must|slowly|gently|smoothly)\s+){0,4}"
    stationary = (
        rf"\b{subject}\s+{modifiers}(?:stå(?:r)?\s+still(?:a)?|(?:är|vara)\s+stilla|förbli(?:r)?\s+stilla|"
        r"rör\s+sig\s+inte|lyfter\s+inte|roterar\s+inte|inte\s+(?:röra\s+sig|lyfta|rotera)|"
        r"(?:does\s+not|not)\s+(?:move|rise|rotate)|"
        r"(?:stays?|remains?|is)\s+(?:still|stationary))\b"
    )
    moving = (
        rf"\b{subject}\s+{modifiers}(?:lyft(?:er|a)?|sväv(?:ar|a)|rotera(?:r)?|snurra(?:r)?|rulla(?:r)?|flyg(?:er|a)|"
        r"rör(?:a)?\s+sig|förflytta(?:r)?\s+sig|lifts?|rises?|rotates?|spins?|rolls?|flies|moves?)\b"
        r"(?!\s+(?:inte|not)\b)"
    )
    still = bool(re.search(stationary, text)) or bool(re.search(
        rf"\b(?:håll|keep)\s+(?:the\s+)?{subject}\s+(?:stilla|still|stationary)\b", text))
    motion = bool(re.search(moving, text)) or bool(re.search(
        rf"(?<!not )\b(?:lyft|rotera|snurra|flytta|lift|rotate|spin|move)\s+(?:the\s+)?{subject}\b", text))
    return still, motion


def apply_controls(brief: CreativeBrief, values: dict | CreativeControls | None) -> CreativeBrief:
    options = values if isinstance(values, CreativeControls) else CreativeControls.model_validate(values or {})
    if brief.kind == "image":
        if options != CreativeControls():
            raise ValueError("R\u00f6relse, l\u00e4ngd och ljud kan bara v\u00e4ljas f\u00f6r video.")
        return brief
    changes = {}
    text = brief.user_intent.casefold()
    explicit_duration = re.search(r"\b(\d{1,3})[\s-]*(?:s|sek|sekunder(?:s)?|seconds?)\b", text)
    if options.duration_seconds is not None and explicit_duration and brief.duration_seconds != options.duration_seconds:
        raise ValueError("Texten och valet av l\u00e4ngd skiljer sig. V\u00e4lj Auto f\u00f6r att f\u00f6lja texten eller justera beskrivningen.")
    if options.resolution != "auto" and brief.resolution != "auto" and options.resolution != brief.resolution:
        raise ValueError("Texten och valet av uppl\u00f6sning skiljer sig. V\u00e4lj Auto eller justera beskrivningen.")
    explicit_audio = re.search(r"utan ljud|no audio|silent|muted|ljudl\u00f6s|med ljud|with audio|ljudeffekt|sound effect|sfx|bakgrundsljud|dialog|voice\s?over", text)
    if options.audio != "auto" and explicit_audio and options.audio != brief.audio_intent:
        raise ValueError("Texten och ljudvalet s\u00e4ger emot varandra. V\u00e4lj F\u00f6lj min id\u00e9 eller justera beskrivningen.")
    if options.duration_seconds is not None:
        changes["duration_seconds"] = options.duration_seconds
    if options.resolution != "auto":
        changes["resolution"] = options.resolution
    if options.audio != "auto":
        changes["audio_intent"] = options.audio
    camera = CAMERAS[options.camera][1]
    if camera:
        if brief.camera_movement and ((camera == "static") != ("static" in brief.camera_movement)):
            raise ValueError("Kameravalet och texten s\u00e4ger emot varandra: v\u00e4lj stilla eller r\u00f6rlig kamera.")
        changes["camera_movement"] = list(dict.fromkeys([*brief.camera_movement, camera]))
    motion = MOTIONS[options.subject_motion][1]
    if options.subject_motion != "auto":
        still, moving = _explicit_subject_motion(text)
        if (options.subject_motion == "still" and moving) or (options.subject_motion != "still" and still):
            raise ValueError(
                "Texten och motivets rörelseval säger emot varandra. "
                "Välj Följ min idé eller justera beskrivningen."
            )
    ending = ENDINGS[options.ending][1]
    if options.ending == "match_end" and ReferenceRole.end_image.value not in brief.reference_media:
        raise ValueError("V\u00e4lj en slutbild f\u00f6r att matcha slutbilden.")
    if motion:
        changes["subject_motion"] = [*brief.subject_motion, motion]
        changes["allow_change"] = [*brief.allow_change, motion]
    if ending:
        changes["temporal_sequence"] = [*brief.temporal_sequence, ending]
    return brief.model_copy(update=changes)


def creation_catalog(kind: str) -> dict:
    from .creative_budget import known_video_cost
    models = []
    for model in model_registry():
        for mode in model.modes:
            if model not in verified_models(kind, mode):
                continue
            contract = model.request_contract(mode)
            durations = list(contract.durations)
            if contract.duration_range:
                durations = list(range(contract.duration_range[0], contract.duration_range[1] + 1))
            models.append({
                "id": model.model_id, "label": model.label or MODEL_LABELS.get(model.model_id, model.model_id),
                "mode": mode, "roles": [r.value for r in contract.supported_reference_roles],
                "required": [r.value for r in contract.required_reference_roles],
                "durations": durations, "resolutions": list(contract.resolutions),
                "ratios": list(contract.aspect_ratios), "aspect_behavior": contract.aspect_ratio_behavior,
                "audio": bool(model.audio_support and contract.audio_parameter),
                "capabilities": list(model.recipe_capabilities),
                "summary": model.summary, "preview": model.preview, "verified_date": model.verified_date,
                "rates": {resolution: str(rate) for resolution in (contract.resolutions or ("",))
                          if (rate := known_video_cost(model.model_id, 1, resolution)) is not None} if kind == "video" else {},
            })
    recipes = []
    for recipe in recipe_registry():
        if recipe.recipe_id not in TEMPLATE_LABELS or kind not in recipe.kinds:
            continue
        label, description = TEMPLATE_LABELS[recipe.recipe_id]
        recipes.append({"id": recipe.recipe_id, "label": label, "description": description,
                        "modes": list(recipe.supported_modes),
                        "required": [r.value for r in recipe.required_reference_roles],
                        "roles": [r.value for r in (*recipe.required_reference_roles, *recipe.optional_reference_roles)],
                        "capabilities": list(recipe.required_model_capabilities)})
    return {"models": models, "recipes": recipes, "version": CONTROL_VERSION}
