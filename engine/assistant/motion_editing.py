"""Closed scene edits preserve media, branding, effects and immutable revisions."""
from copy import deepcopy
from decimal import ROUND_CEILING, Decimal

from engine.motion.schema import validate_spec


def apply_scene_edits(spec, edits):
    result = deepcopy(spec)
    scenes = {scene["id"]: scene for scene in result["scenes"]}
    seen = set()
    for edit in edits:
        values = edit.model_dump(mode="json", exclude_none=True) if hasattr(edit, "model_dump") else {key: value for key, value in edit.items() if value is not None}
        scene_id = values["scene_id"]
        if scene_id not in scenes or scene_id in seen:
            raise ValueError("Välj en befintlig scen en gång per ändring.")
        seen.add(scene_id)
        scene = scenes[scene_id]
        for key in ("headline", "body", "cta"):
            if key in values:
                scene["props"][key] = values[key]
        if "duration_seconds" in values:
            if scene["component"] == "footage":
                raise ValueError("Videoklippets längd ändras i filmsteget, så att originalmaterialet bevaras.")
            scene["duration_frames"] = int((Decimal(str(values["duration_seconds"])) * result["fps"]).to_integral_value(rounding=ROUND_CEILING))
    try:
        return validate_spec(result)
    except ValueError as exc:
        raise ValueError("Ändringen ger en ogiltig tidslinje. Ge texten, övergångarna och ljudet mer tid eller ändra texten.") from exc


def scene_context(spec):
    """Bounded authoring context for timestamped comments; never arbitrary code."""
    from engine.motion.schema import timeline
    times = {row["id"]: row for row in timeline(spec)}
    return [{"scene_id": scene["id"], "start_seconds": times[scene["id"]]["start"] / spec["fps"],
             "end_seconds": times[scene["id"]]["end"] / spec["fps"],
             **{key: scene["props"].get(key, "") for key in ("headline", "body", "cta")}} for scene in spec["scenes"]]


def scene_changes(before, after):
    changes = []
    originals = {scene["id"]: scene for scene in before["scenes"]}
    for index, scene in enumerate(after["scenes"], 1):
        old = originals[scene["id"]]
        for key, label in (("headline", "Rubrik"), ("body", "Beskrivning"), ("cta", "Uppmaning"), ("duration_seconds", "Sekunder")):
            previous = old["duration_frames"] / before["fps"] if key == "duration_seconds" else old["props"].get(key, "")
            current = scene["duration_frames"] / after["fps"] if key == "duration_seconds" else scene["props"].get(key, "")
            if previous != current:
                changes.append({"scene": index, "field": label, "before": previous, "after": current})
    return changes
