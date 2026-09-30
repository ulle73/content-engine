"""HyperFrames-informed beat planning -> registered templates -> closed MotionSpec.

This is an explicit creative rule layer, not a second renderer. The rules are
adapted from HyperFrames creative house-style, video-composition and animation:
one focal claim, larger video typography, legible holds, grouped stagger,
restrained transition vocabulary, persistent context, deliberate sonic accents.
No factual claim or arbitrary React/CSS is generated here.
"""

from __future__ import annotations
import math
import re
from .catalog import get_item
from .schema import validate_spec

SOURCE = "heygen-com/hyperframes@9a27b9f934:skills/hyperframes-creative"
FIELDS = {
    "headline": {"type": "string", "title": "Rubrik", "maxLength": 240},
    "body": {"type": "string", "title": "Kort beskrivning", "maxLength": 500},
    "month": {"type": "string", "title": "M\u00e5nad", "maxLength": 40},
    "count": {"type": "integer", "title": "Antal inl\u00f6sen", "minimum": 0, "maximum": 1000000000},
    "total": {"type": "number", "title": "Totalt inl\u00f6st, kr", "minimum": 0, "maximum": 1000000000000},
    "area": {"type": "string", "title": "Popul\u00e4raste omr\u00e5det", "maxLength": 100},
    "items": {
        "type": "array",
        "title": "Punkter eller nyckeltal",
        "minItems": 1,
        "maxItems": 12,
        "items": {
            "type": "object",
            "required": ["label"],
            "properties": {"label": {"type": "string", "maxLength": 100}, "value": {"type": "number"}},
            "additionalProperties": False,
        },
    },
    "cta": {"type": "string", "title": "Uppmaning", "maxLength": 100},
    "attribution": {"type": "string", "title": "Avs\u00e4ndare / k\u00e4lla", "maxLength": 160},
    "asset_id": {"type": "string", "format": "uuid", "title": "Bild eller video fr\u00e5n Media"},
    "secondary_asset_id": {"type": "string", "format": "uuid", "title": "Andra bilden"},
    "end_card_asset_id": {"type": "string", "format": "uuid", "title": "Slutvideo p\u00e5 svart bakgrund"},
}


def template_schema(template_id):
    template = get_item(template_id, kinds={"template"})
    fields = set(
        template["required_props"] + template["optional_props"] + ["headline", "body", "cta", "end_card_asset_id"]
    )
    return {
        "type": "object",
        "required": template["required_props"],
        "additionalProperties": False,
        "properties": {key: FIELDS[key] for key in FIELDS if key in fields},
    }


def _number(text):
    return float(re.sub(r"[\s\u00a0\u202f]", "", text).replace(",", "."))


def recommend(brief):
    """Resolve explicit intent/data without making up missing metrics or claims."""
    if not isinstance(brief, str) or len(brief) > 6000:
        raise ValueError("Beskrivningen f\u00e5r vara h\u00f6gst 6000 tecken.")
    lower = brief.casefold()
    fields = {}
    template = "custom-storyboard"
    routes = [
        ("monthly-wrapped", ["wrapped", "inl\u00f6sen", "m\u00e5nadens siffror"]),
        ("facility-spotlight", ["golfklubb", "anl\u00e4ggning"]),
        ("friskvard-explainer", ["friskv\u00e5rd"]),
        ("gift-card-promo", ["presentkort", "ge bort"]),
        ("new-partner", ["ny partner"]),
        ("feature-announcement", ["ny funktion", "appvisning"]),
        ("product-launch", ["lansering"]),
        ("top-three", ["topp 3", "top 3", "ranking"]),
        ("before-after-story", ["f\u00f6re och efter", "before and after"]),
        ("quote-testimonial", ["citat", "omd\u00f6me"]),
        ("kpi-recap", ["nyckeltal", "kpi"]),
        ("logo-end-card", ["logotyp", "logo"]),
        ("product-offer", ["erbjudande", "annons"]),
        ("kinetic-text", ["kinetisk", "kinetic"]),
    ]
    for name, words in routes:
        if any(word in lower for word in words):
            template = name
            break
    if template == "monthly-wrapped":
        for month in [
            "januari",
            "februari",
            "mars",
            "april",
            "maj",
            "juni",
            "juli",
            "augusti",
            "september",
            "oktober",
            "november",
            "december",
        ]:
            if re.search(r"\b" + month + r"\b", lower):
                fields["month"] = month.capitalize()
                break
        count = re.search(r"([\d][\d\s\u00a0\u202f]*?)\s*(?:st\.?\s*)?inl\u00f6sen", lower)
        total = re.search(r"([\d][\d\s\u00a0\u202f]*(?:[,\.]\d{1,2})?)\s*(?:kr|sek)\b", lower)
        if count:
            fields["count"] = int(_number(count[1]))
        if total:
            fields["total"] = _number(total[1])
        area = re.search(
            r"([A-Z\u00c5\u00c4\u00d6][A-Za-z\u00e5\u00e4\u00f6\u00c5\u00c4\u00d6 -]{1,60}?)\s+som\s+popul\u00e4raste\s+omr\u00e5de",
            brief,
        )
        if area:
            fields["area"] = area[1].strip()
    else:
        fields["headline"] = brief.strip().split("\n")[0][:240]
    required = get_item(template, kinds={"template"})["required_props"]
    return {
        "template_id": template,
        "fields": fields,
        "missing_fields": [key for key in required if not fields.get(key) and fields.get(key) != 0],
        "reason": "En registrerad mall matchar inneh\u00e5llet. Endast uttryckligen angivna fakta fylls i.",
        "source_rules": [SOURCE + "/references/house-style.md", SOURCE + "/references/video-composition.md"],
    }


def compile_template(
    template_id,
    fields,
    *,
    aspect_ratio="9:16",
    brand_id="golfkuponger",
    audio=True,
    tempo="balanced",
    end_card_seconds=5,
):
    from jsonschema import Draft202012Validator

    template = get_item(template_id, kinds={"template"})
    schema = template_schema(template_id)
    errors = list(Draft202012Validator(schema).iter_errors(fields))
    if errors:
        raise ValueError("Kontrollera mallens f\u00e4lt: " + "; ".join(e.message[:140] for e in errors[:3]))
    if tempo not in {"calm", "balanced", "energetic"}:
        raise ValueError("Ogiltigt tempo.")
    fps = 30
    scenes = []
    transitions = ["cut", "fade", "wipe", "push", "fade"]
    backgrounds = ["orbits", "solid", "topography", "radial", "solid"]
    for i, component in enumerate(template["scene_components"]):
        props = {
            key: fields[key]
            for key in ["headline", "body", "items", "asset_id", "secondary_asset_id", "cta", "attribution"]
            if key in fields
        }
        if template_id == "monthly-wrapped":
            month = fields["month"]
            count = fields["count"]
            total = fields["total"]
            area = fields["area"]
            props = [
                {
                    "eyebrow": "GOLFKUPONGER / " + month.upper(),
                    "headline": month + "\nmed Golfkuponger",
                    "body": "M\u00e5naden i siffror.",
                },
                {
                    "eyebrow": month.upper(),
                    "headline": "Inl\u00f6sen",
                    "value": count,
                    "body": "Till golf hos v\u00e5ra anslutna anl\u00e4ggningar.",
                },
                {
                    "eyebrow": month.upper(),
                    "headline": "Totalt inl\u00f6st",
                    "value": total,
                    "unit": "kr",
                    "body": "Till golf, tr\u00e4ning och spel.",
                },
                {
                    "eyebrow": month.upper(),
                    "headline": "Popul\u00e4raste omr\u00e5det",
                    "items": [{"label": area, "value": 0}],
                },
                {"headline": "Mer golf.", "cta": fields.get("cta", "Golfkuponger.se")},
            ][i]
        if component == "offer" and "total" in fields:
            props.update(value=fields["total"], unit="kr")
        # A reader needs time after the entrance. Templates share motion grammar, not layouts.
        chars = len(str(props.get("headline", ""))) + len(str(props.get("body", "")))
        hold = max(3.3, min(7.0, chars / 19 + 1.0))
        if component in {"counter", "currency", "ranking"}:
            hold = max(hold, 4.3)
        if tempo == "calm":
            hold *= 1.2
        if tempo == "energetic":
            hold *= 0.87
        duration = math.ceil(hold * fps)
        sfx = []
        if audio:
            if component in {"counter", "currency"}:
                sfx = [{"kind": "tick", "frame": frame, "gain": 0.32} for frame in [12, 20, 28, 36, 45, 55]]
                sfx.append({"kind": "chime", "frame": 62, "gain": 0.4})
            elif component in {"logo-sting", "end-card"}:
                sfx = [{"kind": "sting", "frame": 12, "gain": 0.55}]
            elif i:
                sfx = [{"kind": "whoosh", "frame": 0, "gain": 0.25}]
        scenes.append(
            {
                "id": f"beat-{i + 1:02d}",
                "component": component,
                "props": props,
                "duration_frames": duration,
                "background": backgrounds[i % len(backgrounds)],
                "transition": transitions[i % len(transitions)] if i else "cut",
                "transition_frames": 0 if not i or transitions[i % len(transitions)] == "cut" else 12,
                "effects": ["grain"] if i % 2 == 0 else [],
                "sfx": sfx,
            }
        )
    end_id = fields.get("end_card_asset_id")
    if end_id:
        scenes[-1].update(
            component="end-card",
            background="solid",
            effects=[],
            sfx=[],
            duration_frames=max(12, min(900, math.floor(end_card_seconds * fps))),
            transition="cut",
            transition_frames=0,
        )
    spec = validate_spec(
        {
            "version": 1,
            "template_id": template_id,
            "template_version": template["version"],
            "aspect_ratio": aspect_ratio,
            "fps": fps,
            "seed": 42,
            "brand_id": brand_id,
            "scenes": scenes,
            "audio": {
                "enabled": audio,
                "gain": 0.7,
                "music": "bed",
                "music_asset_id": None,
                "fade_frames": 18,
                "ducking": 0.3,
            },
            "end_card_asset_id": end_id,
        }
    )
    return spec
