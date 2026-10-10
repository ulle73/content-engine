"""AI critique of a finished cloud cut: ~8 small frames + the review manifest + the recipe → one cheap vision call.

Runs once per EditJob when the renderer delivers (engine/edit/service.complete), before the Discord card is posted,
and is fail-open: no key, a provider error, an undecodable video or EDIT_AI_CRITIC=0 only stores a status on the job.
Delivery is never blocked. The result is stored in EditJob.ai_critique, shown as one line on the Discord card and
returned by get_cut_job.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time

from django.utils import timezone
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

FRAMES = 8
FRAME_PX = 512
DECODE_BUDGET_S = 20.0
VERSION = "cut-critic/1"


class Fix(BaseModel):
    scene_id: str = Field(description="Scen-id ur manifestet, t.ex. s1, eller 'global'")
    item_id: str = Field(default="", description="Biblioteks-id eller asset-id ur manifestet som ska ändras, annars tomt")
    fix: str = Field(description="Konkret ändring på svenska, en mening")


class Aspect(BaseModel):
    score: int = Field(ge=1, le=10)
    note: str = Field(description="En kort mening på svenska")


class CutCritique(BaseModel):
    score: int = Field(ge=1, le=10, description="Helhetsbetyg 1–10 som färdig reklamvideo")
    summary: str = Field(description="En mening på svenska: det viktigaste att veta")
    hook: Aspect = Field(description="Krokens styrka de första 2 sekunderna")
    legibility: Aspect = Field(description="Läsbarhet för text i mobil (storlek, kontrast, säkra zoner, tid på skärm)")
    pacing: Aspect = Field(description="Tempo och klipprytm")
    brand_fit: Aspect = Field(description="Passar varumärket och känns premium")
    fixes: list[Fix] = Field(default_factory=list, max_length=3, description="Max 3 konkreta rättningar, viktigast först")


SYSTEM = (
    "Du är en erfaren klippare och reklamgranskare för korta sociala videor (Reels/TikTok). Du får bildrutor ur en "
    "färdig video (med tidpunkt och scen-id), videons manifest (scener med exakt vilka biblioteksobjekt och "
    "mediefiler som användes) och ibland receptet den byggdes från. Bedöm som färdig annons: krokens styrka de "
    "första 2 sekunderna, textens läsbarhet i mobil, tempo och klipprytm samt varumärkespassning. Var ärlig och "
    "konkret; 7 betyder bra nog att publicera. Föreslå högst 3 rättningar som pekar på scen-id och, när det går, "
    "på item_id exakt ur manifestet. Hitta inte på detaljer du inte ser. Skriv på svenska."
)


def enabled() -> bool:
    return os.environ.get("EDIT_AI_CRITIC", "1").strip() not in {"0", "false", "off", ""}


def _scene_at(manifest: dict, t: float) -> str:
    for scene in manifest.get("scenes") or []:
        if float(scene.get("start", 0)) <= t < float(scene.get("end", 0)):
            return str(scene.get("id"))
    return ""


def frame_times(duration: float, count: int = FRAMES) -> list[float]:
    """Two frames inside the hook (first 2 s), the rest spread evenly over the remainder."""
    duration = max(0.2, float(duration or 0))
    hook = [t for t in (0.3, 1.5) if t < duration]
    rest = max(0, count - len(hook))
    start = min(2.0, duration)
    span = max(0.0, duration - start)
    times = hook + [start + span * (i + 0.5) / rest for i in range(rest)] if rest and span > 0.2 else hook
    return [round(t, 2) for t in times][:count]


def extract_frames(data: bytes, times: list[float], *, size: int = FRAME_PX,
                   budget_s: float = DECODE_BUDGET_S) -> list[tuple[float, bytes]]:
    """JPEG frames (longest side `size`) at the given times. One sequential pass that skips non-reference frames
    (a frame near each time is enough) and stops after `budget_s` seconds with the frames it has, so a slow server
    never holds up delivery for long."""
    import av
    from PIL import Image

    out: list[tuple[float, bytes]] = []
    wanted = sorted(times)
    deadline = time.monotonic() + budget_s
    with av.open(io.BytesIO(data)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        stream.codec_context.skip_frame = "NONREF"
        index = 0
        for frame in container.decode(stream):
            if index >= len(wanted) or time.monotonic() > deadline:
                break
            t = float(frame.pts * frame.time_base) if frame.pts is not None and frame.time_base else 0.0
            if t + 1e-3 < wanted[index]:
                continue
            image = frame.to_image().convert("RGB")
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=72)
            while index < len(wanted) and wanted[index] <= t + 1e-3:
                index += 1
            out.append((round(t, 2), buffer.getvalue()))
    return out


def _video_duration(data: bytes) -> float:
    import av

    with av.open(io.BytesIO(data)) as container:
        if container.duration:
            return container.duration / av.time_base
        stream = container.streams.video[0]
        return float(stream.duration * stream.time_base) if stream.duration else 0.0


def _recipe(recipe_id: str) -> dict | None:
    from . import planner

    if not recipe_id:
        return None
    try:
        recipe = planner.load_recipe(recipe_id)
    except (planner.PlanError, ValueError, OSError):
        return None
    keys = ("id", "title", "type", "hook", "why_it_works", "duration_s", "qa")
    return {**{k: recipe.get(k) for k in keys},
            "scenes": [{k: s.get(k) for k in ("id", "purpose", "duration_s", "text", "camera")} for s in recipe["scenes"]]}


def critique(job, video: bytes) -> dict:
    """Ask the vision tier for a critique. Raises on any failure; use run() for the fail-open wrapper."""
    from engine.openrouter import structured_analysis

    from .service import build_manifest

    manifest = build_manifest(job.cut_spec)
    duration = float(job.cut_spec.get("render", {}).get("duration_s") or 0) or _video_duration(video) \
        or float(manifest.get("duration_s") or 0)
    frames = extract_frames(video, frame_times(duration))
    if not frames:
        raise ValueError("Inga bildrutor kunde läsas ur videon.")
    images = ["data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii") for _, jpeg in frames]
    payload = {
        "title": job.cut_spec.get("title", ""), "format": job.cut_spec.get("format"), "duration_s": round(duration, 2),
        "company": job.company.name,
        "frames": [{"image": i + 1, "t": t, "scene_id": _scene_at(manifest, t)} for i, (t, _) in enumerate(frames)],
        "manifest": manifest, "recipe": _recipe(job.recipe_id),
    }
    result, meta = structured_analysis(system=SYSTEM, payload=payload, schema=CutCritique, operation="cut_critique",
                                       max_tokens=1200, images=images)
    known = {str(s["id"]) for s in manifest.get("scenes", [])} | {"global"}
    items = {str(i["id"]) for s in manifest.get("scenes", []) for i in s.get("items", [])} \
        | {str(i["id"]) for i in manifest.get("global", [])}
    fixes = []
    for fix in result.fixes[:3]:
        fixes.append({"scene_id": fix.scene_id if fix.scene_id in known else "global",
                      "item_id": fix.item_id if fix.item_id in items else "", "fix": fix.fix[:300]})
    return {
        "status": "done", "version": VERSION, "score": result.score, "summary": result.summary[:300],
        "hook": result.hook.model_dump(), "legibility": result.legibility.model_dump(),
        "pacing": result.pacing.model_dump(), "brand_fit": result.brand_fit.model_dump(), "fixes": fixes,
        "frames": len(frames), "model": meta.get("model"), "cost_usd": meta.get("cost_usd"),
        "created_at": timezone.now().isoformat(),
    }


def run(job, video: bytes | None) -> dict:
    """Fail-open: always returns a dict for EditJob.ai_critique and never raises."""
    now = timezone.now().isoformat()
    if not enabled():
        return {"status": "skipped", "reason": "AI-granskningen är avstängd (EDIT_AI_CRITIC=0).", "created_at": now}
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        return {"status": "skipped", "reason": "OPENROUTER_API_KEY saknas.", "created_at": now}
    if not video:
        return {"status": "skipped", "reason": "Ingen video att granska.", "created_at": now}
    try:
        return critique(job, video)
    except Exception as exc:  # noqa: BLE001 - the critic must never block delivery
        log.warning("AI critique for edit job %s failed: %s", job.pk, exc)
        return {"status": "failed", "error": str(exc)[:300], "created_at": now}


def card_line(data: dict | None) -> str:
    """One line for the Discord card, or "" when there is no finished critique."""
    if not isinstance(data, dict) or data.get("status") != "done":
        return ""
    line = f"🤖 **AI-granskning {data.get('score')}/10:** {data.get('summary', '')}".strip()
    fix = next(iter(data.get("fixes") or []), None)
    if fix:
        line += f" Först: {fix['fix']}" + (f" ({fix['scene_id']})" if fix.get("scene_id") not in {"", "global"} else "")
    return line[:600]
