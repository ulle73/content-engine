"""Deterministic MotionSpec quality checks and bounded safe improvements.

This critic evaluates properties the spec can prove. Visual fidelity and aesthetic
finish remain an explicit human/vision review; this module never pretends a JSON
spec proves those qualities.
"""

from __future__ import annotations

import copy
import math

from .schema import validate_spec


CRITIC_VERSION = "motion-critic/1"
VISUAL_REVIEW_CHECKLIST = ["ui_product_fidelity", "brand_finish", "visual_artifacts"]


def _words(scene: dict) -> int:
    props = scene["props"]
    return len((props.get("headline", "") + " " + props.get("body", "") + " " + props.get("cta", "")).split())


def _effective_seconds(scene: dict, fps: int) -> float:
    return (scene["duration_frames"] - scene["transition_frames"]) / fps


def _score(identifier: str, value: int, reason: str) -> dict:
    return {"id": identifier, "score": value, "max": 2, "reason": reason}


def critique_spec(spec: dict, *, storyboard_scene_ids: list[str] | None = None) -> dict:
    data = validate_spec(spec)
    scenes, fps = data["scenes"], data["fps"]
    first = scenes[0]
    first_seconds = _effective_seconds(first, fps)
    first_words = _words(first)
    hook = 2 if first_seconds <= 3 and first_words <= 8 else 1 if first_seconds <= 4.5 and first_words <= 12 else 0

    readable = []
    for scene in scenes:
        seconds = max(0.5, _effective_seconds(scene, fps))
        words = _words(scene)
        readable.append(words <= max(8, math.floor(seconds * 3.5)))
    readability = 2 if all(readable) else 1 if sum(readable) >= max(1, len(readable) - 1) else 0

    durations = [_effective_seconds(scene, fps) for scene in scenes]
    average = sum(durations) / len(durations)
    tempo = 2 if 1.5 <= average <= 5.5 else 1 if 1 <= average <= 7.5 else 0

    animated = [
        scene for scene in scenes
        if scene["component"] != "footage" and scene.get("motion_preset", "legacy") != "legacy"
    ]
    candidates = [scene for scene in scenes if scene["component"] != "footage"]
    motion = 2 if candidates and len(animated) == len(candidates) else 1 if animated else 0

    components = {scene["component"] for scene in scenes}
    backgrounds = {scene["background"] for scene in scenes}
    variation = 2 if len(components) >= 3 or (len(components) >= 2 and len(backgrounds) >= 2) else 1 if len(components) >= 2 else 0

    brand = 2 if data["brand_id"] == "golfkuponger" else 1
    beat = data.get("beat_map") or {}
    if not data["audio"]["enabled"] or data["audio"]["music"] == "none":
        audio_sync = 2
        audio_reason = "Audio is intentionally disabled."
    elif beat.get("enabled") and beat.get("beat_frames"):
        audio_sync = 2
        audio_reason = "A deterministic beat map is present."
    else:
        audio_sync = 1
        audio_reason = "Audio exists but there is no explicit beat map."

    last = scenes[-1]
    has_cta = bool(last["props"].get("cta")) or last["component"] in {"cta", "end-card"}
    cta = 2 if has_cta else 1 if last["props"].get("headline") else 0

    scores = [
        _score("hook", hook, "Opening length and on-screen word count."),
        _score("readability", readability, "Words are bounded by effective scene duration."),
        _score("tempo", tempo, f"Average effective scene duration is {average:.2f}s."),
        _score("motion", motion, "Non-footage scenes use allow-listed motion presets."),
        _score("visual_variation", variation, "Scene components/backgrounds provide structural variation."),
        _score("brand", brand, "Brand snapshot is explicit in the MotionSpec."),
        _score("audio_sync", audio_sync, audio_reason),
        _score("cta", cta, "Final scene contains a clear end-card/CTA signal." if has_cta else "Final scene lacks a CTA."),
    ]
    if storyboard_scene_ids is not None:
        expected = [scene["id"] for scene in scenes]
        if storyboard_scene_ids != expected:
            scores.append(_score("render_integrity", 0, "Storyboard keyframes do not match the current scene order."))
        else:
            scores.append(_score("render_integrity", 2, "Storyboard keyframes match every current scene."))

    return {
        "version": CRITIC_VERSION,
        "score": sum(item["score"] for item in scores),
        "max_score": sum(item["max"] for item in scores),
        "scores": scores,
        "visual_review_required": True,
        "visual_review_checklist": VISUAL_REVIEW_CHECKLIST,
        "safe_auto_fix_available": any(item["id"] in {"motion", "audio_sync"} and item["score"] < 2 for item in scores),
    }


def _frames_for_bpm(bpm: float, fps: int, total_frames: int) -> list[int]:
    step = fps * 60 / bpm
    frames, index = [], 0
    while len(frames) < 512:
        frame = round(index * step)
        if frame >= total_frames:
            break
        if not frames or frames[-1] != frame:
            frames.append(frame)
        index += 1
    return frames


def improve_spec(spec: dict) -> tuple[dict, list[dict]]:
    """Apply only mechanical, reversible MotionSpec improvements."""
    data = copy.deepcopy(validate_spec(spec))
    changes: list[dict] = []
    profile = data.get("reference_profile") or {}
    fallback = profile.get("motion_preset") or "soft"

    for scene in data["scenes"]:
        if scene["component"] == "footage":
            continue
        if scene.get("motion_preset", "legacy") == "legacy":
            scene["motion_preset"] = fallback
            changes.append({"scene_id": scene["id"], "field": "motion_preset", "to": fallback})

    beat = data.get("beat_map") or {}
    if (
        data["audio"]["enabled"]
        and data["audio"]["music"] == "pulse"
        and not beat.get("enabled")
    ):
        total_frames = sum(scene["duration_frames"] - scene["transition_frames"] for scene in data["scenes"])
        bpm = 120.0
        data["beat_map"] = {
            "enabled": True,
            "bpm": bpm,
            "offset_frames": 0,
            "beat_frames": _frames_for_bpm(bpm, data["fps"], total_frames),
            "source": "built-in-pulse",
        }
        changes.append({"field": "beat_map", "to": "built-in-pulse@120bpm"})

    return validate_spec(data), changes
