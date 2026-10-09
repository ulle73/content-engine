"""What a video is made of, scene by scene, so feedback ("effekten vid 0:07 är billig") can find the exact item.

Shape:
    {"duration_s": 24.0,
     "global": [{"id": "hf.template.x", "type": "template", "label": "…"}],          # template, music, grade, model
     "scenes": [{"id": "s1", "start": 0.0, "end": 3.0, "purpose": "hook", "text": "…",
                 "items": [{"id": "animate.effect.boil-line", "type": "effect", "label": "…", "params": {}}]}]}
"""

from __future__ import annotations

import re

ITEM_TYPES = {"template", "scene", "effect", "transition", "text", "caption", "grade", "background", "sound",
              "music", "model", "prompt", "motion", "voice", "asset", "product", "other"}


def _item(raw) -> dict | None:
    if isinstance(raw, str):
        raw = {"id": raw}
    if not isinstance(raw, dict) or not str(raw.get("id", "")).strip():
        return None
    kind = str(raw.get("type") or "other").lower()
    return {
        "id": str(raw["id"]).strip()[:200],
        "type": kind if kind in ITEM_TYPES else "other",
        "label": str(raw.get("label") or raw.get("name") or raw["id"])[:200],
        "params": raw.get("params") if isinstance(raw.get("params"), dict) else {},
    }


def clean(manifest) -> dict:
    """Validate a manifest coming from Claude/ChatGPT or a renderer. Unknown keys are dropped."""
    manifest = manifest if isinstance(manifest, dict) else {}
    scenes, clock = [], 0.0
    for index, raw in enumerate(manifest.get("scenes") or []):
        if not isinstance(raw, dict):
            continue
        start = float(raw.get("start", clock) or 0)
        end = float(raw.get("end") or start + float(raw.get("duration_s") or 0))
        clock = max(end, start)
        scenes.append({
            "id": str(raw.get("id") or f"s{index + 1}")[:40],
            "start": round(start, 2), "end": round(max(end, start), 2),
            "purpose": str(raw.get("purpose") or "")[:40], "text": str(raw.get("text") or "")[:300],
            "items": [i for i in map(_item, raw.get("items") or []) if i][:20],
        })
    return {
        "duration_s": round(float(manifest.get("duration_s") or clock), 2),
        "global": [i for i in map(_item, manifest.get("global") or []) if i][:20],
        "scenes": scenes[:40],
    }


def from_brief(brief: dict) -> dict:
    """Manifest from an Ad Studio AdBrief: template, per-scene text, motion and transitions."""
    engine = brief.get("engine") or {}
    global_items = []
    if engine.get("remotion_template_id"):
        global_items.append({"id": engine["remotion_template_id"], "type": "template"})
    if engine.get("engine"):
        global_items.append({"id": f"engine:{engine['engine']}", "type": "model", "label": engine["engine"]})
    scenes, clock = [], 0.0
    for scene in brief.get("scenes") or []:
        duration = float(scene.get("duration_s") or 0)
        items = []
        if scene.get("transition_in"):
            items.append({"id": scene["transition_in"], "type": "transition"})
        if scene.get("motion"):
            items.append({"id": f"motion:{scene['motion']}"[:200], "type": "motion", "label": scene["motion"]})
        if scene.get("asset_id"):
            items.append({"id": str(scene["asset_id"]), "type": "asset"})
        scenes.append({"id": scene.get("id"), "start": clock, "end": clock + duration, "purpose": scene.get("purpose"),
                       "text": scene.get("on_screen_text") or "", "items": items})
        clock += duration
    return clean({"global": global_items, "scenes": scenes, "duration_s": clock})


def all_items(manifest: dict) -> list[dict]:
    seen, out = set(), []
    for item in [*manifest.get("global", []), *(i for s in manifest.get("scenes", []) for i in s["items"])]:
        if item["id"] not in seen:
            seen.add(item["id"])
            out.append(item)
    return out


def _seconds(text: str) -> list[float]:
    found = [int(m) * 60 + int(s) for m, s in re.findall(r"\b(\d{1,2}):(\d{2})\b", text)]
    found += [float(n.replace(",", ".")) for n in re.findall(r"\b(\d{1,3}(?:[.,]\d)?)\s*(?:s|sek|sekunder)\b", text.lower())]
    return found


def candidates(manifest: dict, comment: str) -> list[dict]:
    """Items the comment most likely points at: by time stamp, then by words matching the label/id/type."""
    times = _seconds(comment)
    words = {w for w in re.split(r"[^\wåäö]+", comment.lower()) if len(w) > 3}
    scored = []
    for scene in manifest.get("scenes", []):
        in_time = any(scene["start"] - 0.5 <= t <= scene["end"] + 0.5 for t in times)
        for item in scene["items"]:
            text = f"{item['label']} {item['id']} {item['type']}".lower()
            score = (3 if in_time else 0) + sum(1 for w in words if w in text)
            if score:
                scored.append((score, dict(item, scene=scene["id"], at=f"{scene['start']:.1f}–{scene['end']:.1f}s")))
    for item in manifest.get("global", []):
        text = f"{item['label']} {item['id']} {item['type']}".lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, dict(item, scene="hela videon")))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored[:8]]
