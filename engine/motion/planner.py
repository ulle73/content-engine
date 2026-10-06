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
from .ad_templates import AD_TEMPLATES, compile_scenes, field_schema
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
    "hook_text": {"type": "string", "title": "1 · Hooktext", "maxLength": 120},
    "portal_text": {"type": "string", "title": "2 · Portaltext", "maxLength": 120},
    "purchase_text": {"type": "string", "title": "3 · Köptext", "maxLength": 120},
    "app_text": {"type": "string", "title": "4 · Apptext", "maxLength": 120},
    "proof_text": {"type": "string", "title": "5 · Bevis / 300+ klubbar", "maxLength": 120},
    "website_text": {"type": "string", "title": "2 · Webbtext", "maxLength": 120},
    "receipt_text": {"type": "string", "title": "3 · Kvittotext", "maxLength": 120},
    "montage_text": {"type": "string", "title": "4 · Banmontage", "maxLength": 120},
    "end_text": {"type": "string", "title": "Slutbudskap", "maxLength": 120},
    "hook_asset_id": {"type": "string", "format": "uuid", "title": "1 · Banbild / hook"},
    "portal_asset_id": {"type": "string", "format": "uuid", "title": "2 · Förmånsportal"},
    "purchase_asset_id": {"type": "string", "format": "uuid", "title": "3 · Belopp / köp"},
    "app_asset_id": {"type": "string", "format": "uuid", "title": "4 · Golfkuponger-appen"},
    "proof_asset_id": {"type": "string", "format": "uuid", "title": "5 · Banbild / 300+ klubbar"},
    "website_asset_id": {"type": "string", "format": "uuid", "title": "2 · Golfkuponger.se"},
    "receipt_asset_id": {"type": "string", "format": "uuid", "title": "3 · Kvitto / mejl"},
    "montage_asset_id": {"type": "string", "format": "uuid", "title": "4 · Banmontage"},
}


def template_schema(template_id):
    template = get_item(template_id, kinds={"template"})
    if template_id in AD_TEMPLATES:
        return {
            "type": "object",
            "required": template["required_props"],
            "additionalProperties": False,
            "properties": field_schema(template_id),
        }
    fields = set(
        template["required_props"] + template["optional_props"] + ["headline", "body", "cta", "end_card_asset_id"]
    )
    if template_id == "monthly-wrapped":
        fields = set(template["required_props"] + ["cta", "end_card_asset_id"])
    elif template_id in {"friskvard-portal-ad", "friskvard-direct-ad"}:
        fields = set(template["required_props"] + template["optional_props"])
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
        ("friskvard-direct-ad", ["ingen förmånsportal", "direktköp", "kvitto från golfkuponger"]),
        ("friskvard-portal-ad", ["förmånsportal", "benify", "benifex", "epassi", "söderberg & partners"]),
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
    elif template not in {"friskvard-portal-ad", "friskvard-direct-ad"}:
        fields["headline"] = brief.strip().split("\n")[0][:240]
    required = get_item(template, kinds={"template"})["required_props"]
    return {
        "template_id": template,
        "fields": fields,
        "missing_fields": [key for key in required if not fields.get(key) and fields.get(key) != 0],
        "reason": "En registrerad mall matchar inneh\u00e5llet. Endast uttryckligen angivna fakta fylls i.",
        "source_rules": [SOURCE + "/references/house-style.md", SOURCE + "/references/video-composition.md"],
    }


SCREEN_AD_TEMPLATES = {"friskvard-portal-ad", "friskvard-direct-ad"}


def _screen_scene(scene_id, component, asset_id, headline, duration_frames):
    return {
        "id": scene_id,
        "component": component,
        "props": {"asset_id": asset_id, "headline": headline},
        "duration_frames": duration_frames,
        "background": "solid",
        "transition": "cut",
        "transition_frames": 0,
        "effects": [],
        "sfx": [],
    }


def _compile_screen_ad(template_id, fields, fps):
    if template_id == "friskvard-portal-ad":
        return [
            _screen_scene(
                "hook",
                "footage",
                fields["hook_asset_id"],
                fields.get("hook_text", "DITT FRISKVÅRDSBIDRAG\nBRINNER INNE 31/12"),
                2 * fps,
            ),
            _screen_scene(
                "portal",
                "device",
                fields["portal_asset_id"],
                fields.get("portal_text", "SÖK GOLFKUPONGER\nI DIN PORTAL"),
                3 * fps,
            ),
            _screen_scene(
                "purchase",
                "device",
                fields["purchase_asset_id"],
                fields.get("purchase_text", "VÄLJ BELOPP"),
                3 * fps,
            ),
            _screen_scene(
                "app",
                "device",
                fields["app_asset_id"],
                fields.get("app_text", "KODEN LÄGGS IN\nI APPEN"),
                3 * fps,
            ),
            _screen_scene(
                "proof",
                "footage",
                fields["proof_asset_id"],
                fields.get("proof_text", "GOLF PÅ 300+ KLUBBAR\nHELA NÄSTA SÄSONG"),
                2 * fps,
            ),
            {
                "id": "end",
                "component": "end-card",
                "props": {
                    "headline": fields.get("end_text", "MER GOLF. NÄR DET PASSAR DIG."),
                    "cta": fields.get("cta", "Golfkuponger.se"),
                },
                "duration_frames": 2 * fps,
                "background": "solid",
                "transition": "cut",
                "transition_frames": 0,
                "effects": [],
                "sfx": [],
            },
        ]

    return [
        _screen_scene(
            "hook",
            "footage",
            fields["hook_asset_id"],
            fields.get("hook_text", "INGEN FÖRMÅNSPORTAL?"),
            2 * fps,
        ),
        _screen_scene(
            "website",
            "device",
            fields["website_asset_id"],
            fields.get("website_text", "VÄLJ BELOPP PÅ\nGOLFKUPONGER.SE"),
            3 * fps,
        ),
        _screen_scene(
            "receipt",
            "device",
            fields["receipt_asset_id"],
            fields.get("receipt_text", "KVITTOT KOMMER\nDIREKT PÅ MEJL"),
            3 * fps,
        ),
        _screen_scene(
            "montage",
            "footage",
            fields["montage_asset_id"],
            fields.get("montage_text", "300+ KLUBBAR"),
            3 * fps,
        ),
        {
            "id": "end",
            "component": "end-card",
            "props": {
                "headline": fields.get("end_text", "GOLF PÅ DINA VILLKOR."),
                "cta": fields.get("cta", "Golfkuponger.se"),
            },
            "duration_frames": 3 * fps,
            "background": "solid",
            "transition": "cut",
            "transition_frames": 0,
            "effects": [],
            "sfx": [],
        },
    ]


def _template_motion_preset(template_id: str) -> str:
    if template_id in AD_TEMPLATES:
        tempo = AD_TEMPLATES[template_id]["tempo"]
        return "snappy" if tempo == "snabb" else "weighty" if tempo == "lugn" else "soft"
    if template_id in SCREEN_AD_TEMPLATES:
        return "soft"
    return "legacy"


def _beat_frames(bpm: float, fps: int, total_frames: int, offset_frames: int = 0) -> list[int]:
    step = fps * 60 / bpm
    frames, index = [], 0
    while len(frames) < 512:
        frame = round(offset_frames + index * step)
        if frame >= total_frames:
            break
        if frame >= 0 and (not frames or frames[-1] != frame):
            frames.append(frame)
        index += 1
    return frames


def _apply_motion_harness(spec: dict, *, template_id: str, reference_profile: dict | None) -> dict:
    data = validate_spec(spec)
    profile = dict(reference_profile) if reference_profile else None
    preset = profile.get("motion_preset") if profile else _template_motion_preset(template_id)
    family = profile.get("transition_family", "mixed") if profile else "mixed"
    dynamic = ("whip", "flash", "push")

    for index, scene in enumerate(data["scenes"]):
        # Source footage already has authored movement. Do not add a second camera move.
        scene["motion_preset"] = "legacy" if scene["component"] == "footage" else preset
        if not index or scene["component"] == "footage":
            scene["transition"], scene["transition_frames"] = "cut", 0
        elif family == "cuts":
            scene["transition"], scene["transition_frames"] = "cut", 0
        elif family == "soft":
            scene["transition"], scene["transition_frames"] = "fade", min(8, scene["duration_frames"] // 3)
        elif family == "dynamic":
            scene["transition"] = dynamic[(index - 1) % len(dynamic)]
            scene["transition_frames"] = min(8, scene["duration_frames"] // 3)

    total_frames = sum(scene["duration_frames"] - scene["transition_frames"] for scene in data["scenes"])
    bpm = profile.get("bpm") if profile else None
    source = "profile" if bpm else "none"
    if bpm is None and data["audio"]["enabled"] and data["audio"]["music"] == "pulse":
        bpm, source = 120.0, "built-in-pulse"
    if bpm:
        data["beat_map"] = {
            "enabled": True,
            "bpm": float(bpm),
            "offset_frames": 0,
            "beat_frames": _beat_frames(float(bpm), data["fps"], total_frames),
            "source": source,
        }
    if profile:
        data["reference_profile"] = profile
    return validate_spec(data)


def compile_template(
    template_id,
    fields,
    *,
    aspect_ratio="9:16",
    brand_id="golfkuponger",
    audio=True,
    tempo="balanced",
    end_card_seconds=5,
    reference_profile=None,
):
    from jsonschema import Draft202012Validator

    if template_id == "sequence-film":
        raise ValueError("Skapa filmen från en sekvens för att bevara material och ordning.")

    template = get_item(template_id, kinds={"template"})
    schema = template_schema(template_id)
    errors = list(Draft202012Validator(schema).iter_errors(fields))
    if errors:
        raise ValueError("Kontrollera mallens f\u00e4lt: " + "; ".join(e.message[:140] for e in errors[:3]))
    if tempo not in {"calm", "balanced", "energetic"}:
        raise ValueError("Ogiltigt tempo.")
    fps = 30
    if template_id in AD_TEMPLATES:
        return _apply_motion_harness(
            {
                "version": 1,
                "template_id": template_id,
                "template_version": template["version"],
                "aspect_ratio": aspect_ratio,
                "fps": fps,
                "seed": 42,
                "brand_id": brand_id,
                "scenes": compile_scenes(template_id, fields, fps),
                "audio": {
                    "enabled": audio,
                    "gain": 0.7,
                    "music": "pulse" if AD_TEMPLATES[template_id]["tempo"] == "snabb" else "bed",
                    "music_asset_id": None,
                    "fade_frames": 18,
                    "ducking": 0.3,
                },
                "end_card_asset_id": fields.get("end_card_asset_id"),
            },
            template_id=template_id,
            reference_profile=reference_profile,
        )
    if template_id in SCREEN_AD_TEMPLATES:
        return _apply_motion_harness(
            {
                "version": 1,
                "template_id": template_id,
                "template_version": template["version"],
                "aspect_ratio": aspect_ratio,
                "fps": fps,
                "seed": 42,
                "brand_id": brand_id,
                "scenes": _compile_screen_ad(template_id, fields, fps),
                "audio": {
                    "enabled": audio,
                    "gain": 0.7,
                    "music": "bed",
                    "music_asset_id": None,
                    "fade_frames": 18,
                    "ducking": 0.3,
                },
                "end_card_asset_id": fields.get("end_card_asset_id"),
            },
            template_id=template_id,
            reference_profile=reference_profile,
        )
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
    return _apply_motion_harness(spec, template_id=template_id, reference_profile=reference_profile)
