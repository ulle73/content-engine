"""Ad templates with a tone, composed only from registered Motion components.

Pure data + one compile function, no Django imports, so the catalog generator,
the planner and Ad Studio share one definition.

Conventions (used by engine.ad_studio.blueprints):
- scene `x` reads `x_text` (required) and, if it shows media, `x_asset_id` (required)
- the end card reads `end_text` (required) and `cta` (optional)
- no default copy anywhere: every word on screen comes from the brief

Tone is a creative contract for the assistant (see skills/golfkuponger-brand).
"""

from __future__ import annotations

TEXT_MAX = 80

AD_TEMPLATES: dict[str, dict] = {
    "golf-fracka": {
        "name": "Golf · rolig och fräck",
        "description": "12 s, högt tempo: kaxig hook, vändning på riktig bild, punchline, bevis och slutkort.",
        "tone": "fräck",
        "tempo": "snabb",
        "when": "Lekfull eller kaxig ton, ett överraskande påstående, sociala flöden där man måste sticka ut.",
        "scenes": [
            {"id": "hook", "component": "split-flap", "seconds": 2, "purpose": "hook", "background": "mesh",
             "title": "1 · Kaxig hook (max 6 ord)"},
            {"id": "twist", "component": "footage", "seconds": 3, "purpose": "problem", "media": True,
             "title": "2 · Vändningen (riktig bild/video)"},
            {"id": "punch", "component": "word-highlight", "seconds": 2, "purpose": "solution", "background": "radial",
             "transition": "flash", "title": "3 · Punchline"},
            {"id": "proof", "component": "spotlight", "seconds": 3, "purpose": "proof", "media": True,
             "transition": "whip", "title": "4 · Bevis / banbild"},
            {"id": "end", "component": "end-card", "seconds": 2, "purpose": "cta", "transition": "fade",
             "title": "Slutkort"},
        ],
    },
    "golf-sista-chansen": {
        "name": "Golf · sista chansen",
        "description": "10 s med nedräkning 3–2–1: brådska, problemet, lösningen på riktig bild, slutkort.",
        "tone": "brådskande",
        "tempo": "snabb",
        "when": "Deadline- och sista chansen-budskap, t.ex. bidrag som brinner inne eller kampanj som tar slut.",
        "scenes": [
            {"id": "hook", "component": "countdown", "seconds": 3, "purpose": "hook", "background": "radial",
             "props": {"value": 3}, "title": "1 · Text ovanför nedräkningen"},
            {"id": "problem", "component": "mask-rise", "seconds": 2, "purpose": "problem", "background": "solid",
             "transition": "wipe", "title": "2 · Problemet"},
            {"id": "solution", "component": "footage", "seconds": 3, "purpose": "solution", "media": True,
             "title": "3 · Lösningen (riktig bild/video)"},
            {"id": "end", "component": "end-card", "seconds": 2, "purpose": "cta", "transition": "fade",
             "title": "Slutkort"},
        ],
    },
    "golf-premium": {
        "name": "Golf · lugn premium",
        "description": "15 s, lugnt tempo: banbild, ett skarpt påstående, detaljbild och långt slutkort.",
        "tone": "lugn premium",
        "tempo": "lugn",
        "when": "Varumärke, säsongsstart, presentkort och B2B, där trovärdighet går före brådska.",
        "scenes": [
            {"id": "hook", "component": "footage", "seconds": 4, "purpose": "hook", "media": True,
             "title": "1 · Öppningsbild"},
            {"id": "statement", "component": "blur-reveal", "seconds": 3, "purpose": "solution", "background": "radial",
             "transition": "fade", "title": "2 · Påståendet"},
            {"id": "detail", "component": "spotlight", "seconds": 4, "purpose": "proof", "media": True,
             "transition": "fade", "title": "3 · Detalj / bevis"},
            {"id": "end", "component": "end-card", "seconds": 4, "purpose": "cta", "transition": "fade",
             "title": "Slutkort"},
        ],
    },
}

TRANSITION_FRAMES = 8  # ~0.27 s at 30 fps; short and deliberate


def scene_frames(scene: dict, fps: int) -> tuple[int, int]:
    """(duration_frames, transition_frames). Effective length stays `seconds`."""
    transition = scene.get("transition", "cut")
    overlap = 0 if transition == "cut" else TRANSITION_FRAMES
    return scene["seconds"] * fps + overlap, overlap


def total_seconds(template_id: str) -> int:
    return sum(s["seconds"] for s in AD_TEMPLATES[template_id]["scenes"])


def field_names(template_id: str) -> tuple[list[str], list[str]]:
    required, optional = [], ["cta", "end_card_asset_id"]
    for scene in AD_TEMPLATES[template_id]["scenes"]:
        if scene["id"] == "end":
            required.append("end_text")
            continue
        if scene.get("media"):
            required.append(f"{scene['id']}_asset_id")
        required.append(f"{scene['id']}_text")
    return required, optional


def field_schema(template_id: str) -> dict:
    out = {"cta": {"type": "string", "title": "Uppmaning", "maxLength": 100},
           "end_card_asset_id": {"type": "string", "format": "uuid", "title": "Slutvideo på svart bakgrund"},
           "end_text": {"type": "string", "title": "Slutbudskap", "minLength": 1, "maxLength": TEXT_MAX}}
    for scene in AD_TEMPLATES[template_id]["scenes"]:
        if scene["id"] == "end":
            continue
        out[f"{scene['id']}_text"] = {"type": "string", "title": scene["title"], "minLength": 1, "maxLength": TEXT_MAX}
        if scene.get("media"):
            out[f"{scene['id']}_asset_id"] = {"type": "string", "format": "uuid", "title": scene["title"]}
    return out


def compile_scenes(template_id: str, fields: dict, fps: int) -> list[dict]:
    scenes = []
    for index, scene in enumerate(AD_TEMPLATES[template_id]["scenes"]):
        duration, overlap = scene_frames(scene, fps)
        transition = scene.get("transition", "cut") if index else "cut"
        if index == 0:
            duration, overlap = scene["seconds"] * fps, 0
        if scene["id"] == "end":
            props = {"headline": fields["end_text"], "cta": fields.get("cta", "Golfkuponger.se")}
        else:
            props = {"headline": fields[f"{scene['id']}_text"], **scene.get("props", {})}
            if scene.get("media"):
                props["asset_id"] = fields[f"{scene['id']}_asset_id"]
        scenes.append({
            "id": scene["id"],
            "component": scene["component"],
            "props": props,
            "duration_frames": duration,
            "background": scene.get("background", "solid"),
            "transition": transition,
            "transition_frames": overlap,
            "effects": [],
            "sfx": [],
        })
    return scenes


def catalog_entries() -> list[dict]:
    entries = []
    for template_id, spec in AD_TEMPLATES.items():
        required, optional = field_names(template_id)
        components = [s["component"] for s in spec["scenes"]]
        entries.append({
            "id": template_id,
            "name": spec["name"],
            "description": spec["description"],
            "kind": "template",
            "category": "ads",
            "tags": [template_id, "ads", spec["name"].lower(), spec["tone"], spec["tempo"], *components],
            "version": 1,
            "aspect_ratios": ["9:16", "1:1", "16:9"],
            "required_props": required,
            "optional_props": optional,
            "source": "content-engine/ad-studio templates; HyperFrames-informed pacing",
            "license": "Repository LICENSE (original implementation)",
            "status": "candidate",
            "preview": None,
            "scene_components": components,
            "typical_seconds": total_seconds(template_id),
        })
    return entries
