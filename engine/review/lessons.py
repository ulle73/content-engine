"""Turn feedback into lessons and lessons into behaviour (library ranking + production prompts)."""

from __future__ import annotations

from collections import defaultdict

from django.db.models import F

from .manifest import all_items
from .models import Lesson, Review

ASPECTS = {"hook", "pacing", "music", "sound", "text", "logo", "cta", "color", "voice", "model", "person",
           "product", "length", "format", "humor", "story", "other"}
MULTIPLIER = {"avoid": 0.15, "prefer": 1.8, "adjust": 1.0}


def remember(company, *, target_type, target_id, target_label, polarity, rule, adjustment=None, source=None) -> Lesson:
    """Create a lesson or strengthen the existing one for the same target and direction."""
    lesson, created = Lesson.objects.get_or_create(
        company=company, target_type=target_type, target_id=target_id[:200], polarity=polarity,
        defaults={"target_label": target_label[:200], "rule": rule, "adjustment": adjustment or {}, "source": source},
    )
    if not created:
        Lesson.objects.filter(pk=lesson.pk).update(
            evidence=F("evidence") + 1, rule=rule, active=True, source=source or lesson.source,
            adjustment={**lesson.adjustment, **(adjustment or {})})
        lesson.refresh_from_db()
    # A new verdict in the opposite direction weakens the old one instead of keeping both alive.
    opposite = {"avoid": "prefer", "prefer": "avoid"}.get(polarity)
    if opposite:
        Lesson.objects.filter(company=company, target_type=target_type, target_id=target_id, polarity=opposite,
                              active=True).update(active=False)
    return lesson


def active(company):
    return Lesson.objects.filter(company=company, active=True)


def for_prompt(company, limit=15) -> list[str]:
    """Plain rules to put in front of every brief/production for this company."""
    out = []
    for lesson in active(company)[:limit]:
        label = f" ({lesson.target_label})" if lesson.target_label and lesson.target_label not in lesson.rule else ""
        weight = f" [{lesson.evidence}×]" if lesson.evidence > 1 else ""
        out.append(f"{lesson.get_polarity_display()}: {lesson.rule}{label}{weight}")
    return out


def item_ratings(company) -> dict[str, float]:
    """Average 1–10 rating of the videos each library item appeared in (weak evidence, needs no comment)."""
    totals = defaultdict(list)
    for review in Review.objects.filter(company=company, rating__isnull=False).only("manifest", "rating"):
        for item in all_items(review.manifest or {}):
            totals[item["id"]].append(review.rating)
    return {item_id: sum(r) / len(r) for item_id, r in totals.items()}


def library_feedback(company) -> dict[str, dict]:
    """item_id → {"multiplier", "notes"} for Content Library search."""
    out: dict[str, dict] = {}
    for item_id, average in item_ratings(company).items():
        out[item_id] = {"multiplier": 0.6 + average / 10 * 0.8, "notes": [f"Snittbetyg {average:.1f}/10 i våra videor"]}
    for lesson in active(company).filter(target_type="library"):
        entry = out.setdefault(lesson.target_id, {"multiplier": 1.0, "notes": []})
        entry["multiplier"] *= MULTIPLIER[lesson.polarity] ** min(lesson.evidence, 3)
        entry["notes"].insert(0, f"{lesson.get_polarity_display()}: {lesson.rule}")
        if lesson.adjustment:
            entry["adjustment"] = lesson.adjustment
    return out


def serialize(lesson: Lesson) -> dict:
    return {"lesson_id": lesson.pk, "target_type": lesson.target_type, "target_id": lesson.target_id,
            "target_label": lesson.target_label, "polarity": lesson.polarity, "rule": lesson.rule,
            "adjustment": lesson.adjustment, "evidence": lesson.evidence, "active": lesson.active}
