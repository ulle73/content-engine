"""Bridge between Remotion/Motion templates and AdBrief.

Convention used by the registered templates: a scene with id `x` reads
`x_asset_id` and `x_text`; the final end card reads `end_text` and `cta`.
That lets the conversation design scenes freely while production stays a
deterministic, schema-validated template fill.
"""

from __future__ import annotations

import uuid

from engine.motion.ad_templates import AD_TEMPLATES
from engine.motion.planner import compile_template, template_schema

from .brief import AdBrief

PROOF_IDS = {"proof", "montage"}


def _purpose(scene_id: str, component: str) -> str:
    if scene_id == "hook":
        return "hook"
    if component == "end-card" or scene_id == "end":
        return "cta"
    if scene_id in PROOF_IDS:
        return "proof"
    return "how"


def blueprint(template_id: str) -> dict:
    """Scene skeleton the assistant fills in: ids, timing, asset slots, text slots."""
    schema = template_schema(template_id)
    props = schema.get("properties", {})
    dummy = {name: str(uuid.uuid4()) for name in schema.get("required", []) if name.endswith("_asset_id")}
    for name in schema.get("required", []):
        if name.endswith("_text") and name not in dummy:
            dummy[name] = "X"
    spec = compile_template(template_id, dummy)
    fps = spec["fps"]
    defined = {s["id"]: s for s in AD_TEMPLATES.get(template_id, {}).get("scenes", [])}
    scenes = []
    for scene in spec["scenes"]:
        sid = scene["id"]
        scenes.append(
            {
                "id": sid,
                "purpose": defined[sid]["purpose"] if sid in defined else _purpose(sid, scene["component"]),
                "duration_s": (scene["duration_frames"] - scene["transition_frames"]) / fps,
                "component": scene["component"],
                "title": defined.get(sid, {}).get("title", ""),
                "needs_asset": f"{sid}_asset_id" in dummy,
                "asset_kind": "real screen recording" if scene["component"] == "device" else "footage/image",
                "text_field": f"{sid}_text" if f"{sid}_text" in props else ("end_text" if sid == "end" else None),
                "default_text_not_verified": "" if template_id in AD_TEMPLATES else scene.get("props", {}).get("headline", ""),
                "text_max_chars": props.get(f"{sid}_text", props.get("end_text", {})).get("maxLength"),
            }
        )
    meta = AD_TEMPLATES.get(template_id, {})
    return {
        "template_id": template_id,
        "tone": meta.get("tone", "informativ"),
        "tempo": meta.get("tempo", "balanserad"),
        "when": meta.get("when", "Friskvård med riktiga skärminspelningar av köpvägen."),
        "aspect_ratio": spec["aspect_ratio"],
        "duration_s": sum(s["duration_s"] for s in scenes),
        "scenes": scenes,
        "rules": [
            "Använd exakt dessa scen-id och tider i AdBrief.scenes.",
            "Varje scen med text_field måste få on_screen_text i briefen. Mallens standardtexter används aldrig, "
            "eftersom de innehåller overifierade påståenden.",
            "Scener med needs_asset kräver ett asset_id ur briefens assets.",
            "Skärminspelningar (device) ska vara riktiga filer, aldrig AI-genererade.",
        ],
    }


def template_fields(brief: AdBrief) -> dict:
    """Locked brief -> validated template fields. Raises ValueError with a clear reason."""
    if not brief.engine or not brief.engine.remotion_template_id:
        raise ValueError("Briefen har ingen Remotion-mall.")
    template_id = brief.engine.remotion_template_id
    bp = blueprint(template_id)
    by_id = {s.id: s for s in brief.scenes}
    expected = [s["id"] for s in bp["scenes"]]
    if list(by_id) != expected:
        raise ValueError(f"Mallen {template_id} kräver scenerna {expected} i den ordningen, briefen har {list(by_id)}.")

    fields: dict = {}
    for slot in bp["scenes"]:
        scene = by_id[slot["id"]]
        if abs(scene.duration_s - slot["duration_s"]) > 0.01:
            raise ValueError(f"Scen '{scene.id}' ska vara {slot['duration_s']:g} s i mallen {template_id}.")
        if slot["needs_asset"]:
            if not scene.asset_id:
                raise ValueError(f"Scen '{scene.id}' saknar bild/video.")
            fields[f"{scene.id}_asset_id"] = scene.asset_id
        if slot["text_field"]:
            if not scene.on_screen_text:
                raise ValueError(f"Scen '{scene.id}' saknar text. Mallens standardtext används inte.")
            fields[slot["text_field"]] = scene.on_screen_text.replace(" / ", "\n")
    fields["cta"] = brief.copy_.landing_url.removeprefix("https://").removeprefix("http://").rstrip("/") or "Golfkuponger.se"
    return fields


def compile_brief(brief: AdBrief) -> dict:
    fields = template_fields(brief)
    return compile_template(
        brief.engine.remotion_template_id,
        fields,
        aspect_ratio=brief.formats[0] if brief.formats else "9:16",
        brand_id=brief.brand_preset,
    )
