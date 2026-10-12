"""Quality gate for a finished cloud cut: decides whether it goes to the owner's Discord review as finished.

A cut is held back ("behöver omtag") when the AI critique (engine/edit/critic.py) scores it below EDIT_GATE_MIN_SCORE
(default 7, the critic's "good enough to publish") or when more than EDIT_GATE_MAX_STILL_SHARE (default 0.5) of the
scene time is still images. The owner has rejected still images with graphics on top; moving film comes first.
A critique that was skipped or failed does not hold the cut back: the gate only judges what it can see.
EDIT_QUALITY_GATE=0 turns the gate off. A held-back cut can still be sent with service.send_anyway.
"""

from __future__ import annotations

import os

from django.utils import timezone

VERSION = "cut-gate/1"


def enabled() -> bool:
    return os.environ.get("EDIT_QUALITY_GATE", "1").strip() not in {"0", "false", "off", ""}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def min_score() -> int:
    return int(_env_float("EDIT_GATE_MIN_SCORE", 7))


def max_still_share() -> float:
    return _env_float("EDIT_GATE_MAX_STILL_SHARE", 0.5)


def still_share(spec: dict) -> float:
    """Share of the scene time (end card and outro excluded) that is still images, 0–1."""
    total = still = 0.0
    for scene in spec.get("scenes") or []:
        duration = float(scene.get("duration_s") or 0)
        total += duration
        if scene.get("asset_kind") == "image":
            still += duration
    return round(still / total, 3) if total else 0.0


def assess(spec: dict, critique: dict | None) -> dict:
    """{"passed", "reasons" (Swedish), "score", "still_share", limits, "version", "checked_at"}."""
    now = timezone.now().isoformat()
    if not enabled():
        return {"passed": True, "skipped": True, "reasons": [], "version": VERSION, "checked_at": now}
    lowest, max_share = min_score(), max_still_share()
    share = still_share(spec)
    reasons = []
    score = critique.get("score") if isinstance(critique, dict) and critique.get("status") == "done" else None
    if isinstance(score, int) and score < lowest:
        reasons.append(f"AI-granskningen gav {score}/10 (gränsen är {lowest}).")
    if share > max_share:
        reasons.append(f"{round(share * 100)} % av scentiden är stillbilder (högst {round(max_share * 100)} %). "
                       "Byt stillbilder mot filmklipp.")
    return {"passed": not reasons, "reasons": reasons, "score": score, "still_share": share, "min_score": lowest,
            "max_still_share": max_share, "version": VERSION, "checked_at": now}


def held_back(job) -> bool:
    gate = job.quality_gate if isinstance(job.quality_gate, dict) else {}
    return gate.get("passed") is False and not gate.get("override")


def status_line(job) -> str:
    """Swedish next step for a held-back cut, with the critique's first fix when there is one."""
    gate = job.quality_gate or {}
    line = "Behöver omtag, inte skickad till Discord: " + " ".join(gate.get("reasons") or [])
    fix = next(iter((job.ai_critique or {}).get("fixes") or []), None)
    if fix:
        line += f" Först: {fix['fix']}"
    return line + " Rätta och rendera igen, eller skicka ändå med send_cut_for_review."
