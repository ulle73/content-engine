"""Send a finished video for review and handle verdicts, 1–10 ratings and comments."""

from __future__ import annotations

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from pydantic import BaseModel

from ..openrouter import OpenRouterError, structured_analysis
from . import lessons
from .manifest import all_items, candidates, clean
from .models import Review, ReviewFeedback

SIGNER = signing.Signer(salt="review-video")


class ReviewError(ValueError):
    pass


def video_link(review: Review) -> str:
    """Long-lived, unguessable link to the video (redirects to a fresh storage URL on every open)."""
    token = SIGNER.sign(str(review.pk))
    return settings.APP_URL.rstrip("/") + reverse("engine_review_video", kwargs={"token": token})


def review_from_token(token: str) -> Review:
    try:
        return Review.objects.select_related("asset").get(pk=SIGNER.unsign(token))
    except (signing.BadSignature, Review.DoesNotExist, ValueError) as exc:
        raise ReviewError("Länken är ogiltig.") from exc


def create(company, asset, *, title, caption="", manifest=None, ad_draft=None, parent=None) -> Review:
    if asset.company_id != company.pk or asset.kind != "video":
        raise ReviewError("Välj en video från bolagets mediabank.")
    version = parent.version + 1 if parent else 1
    with transaction.atomic():
        if parent:
            Review.objects.filter(pk=parent.pk).update(status="superseded")
        return Review.objects.create(
            company=company, asset=asset, title=title[:200], caption=caption, manifest=clean(manifest or {}),
            ad_draft=ad_draft or (parent.ad_draft if parent else None), parent=parent, version=version)


def _feedback(review, kind, reviewer, **fields) -> ReviewFeedback:
    return ReviewFeedback.objects.create(review=review, kind=kind, reviewer_id=reviewer.get("id", ""),
                                         reviewer_name=reviewer.get("name", "")[:100], **fields)


def decide(review: Review, verdict: str, reviewer: dict) -> str:
    if verdict not in {"approve", "reject"}:
        raise ReviewError("Okänt beslut.")
    _feedback(review, verdict, reviewer)
    review.status = "approved" if verdict == "approve" else "rejected"
    review.decided_at = timezone.now()
    review.save(update_fields=["status", "decided_at"])
    if verdict == "reject":
        return "👎 Sparat. Tryck **Kommentar** och berätta varför, så lär jag mig."
    if review.company.postiz_ciphertext:
        return "👍 Godkänd. Den läggs i publiceringskön."
    return "👍 Godkänd. Postiz är inte kopplat än, så ladda ner videon från länken och publicera själv."


def rate(review: Review, rating: int, reviewer: dict) -> str:
    if not 1 <= int(rating) <= 10:
        raise ReviewError("Betyget ska vara 1–10.")
    _feedback(review, "rating", reviewer, rating=int(rating))
    review.rating = int(rating)
    review.save(update_fields=["rating"])
    hint = " Skriv gärna en kommentar om vad som drog ner den." if rating <= 6 else ""
    return f"Betyg **{rating}/10** sparat för v{review.version}.{hint}"


class Point(BaseModel):
    target_type: str  # library | aspect
    target_id: str
    target_label: str
    polarity: str  # avoid | prefer | adjust
    rule: str
    adjustment: dict = {}
    fix_now: str = ""


class Interpretation(BaseModel):
    points: list[Point]
    clarification: str = ""
    summary: str


SYSTEM = (
    "Du tolkar en marknadschefs feedback på en reklamvideo. Du får videons manifest (scener med tider och exakt "
    "vilka biblioteksobjekt som användes: effekter, övergångar, mallar, textbehandlingar, ljud, AI-modeller) och "
    "kommentaren. Svara med punkter. För varje sak i kommentaren: peka ut objektet med target_type 'library' och "
    "target_id EXAKT från manifestets id:n, eller target_type 'aspect' med target_id något av: "
    + ", ".join(sorted(lessons.ASPECTS)) + ". polarity: avoid (sluta använda), prefer (mer av), adjust (behåll men "
    "ändra, beskriv ändringen i adjustment som parameter→värde, t.ex. {\"duration_s\": 0.3, \"intensity\": \"låg\"}). "
    "rule: en generell regel på svenska för framtida videor. fix_now: vad som ska ändras i just denna video. "
    "Om det är oklart vilket objekt som avses, gissa inte: lämna points tom och skriv en kort fråga i clarification "
    "som nämner kandidaterna. summary: en mening på svenska om vad du uppfattade."
)


def interpret(review: Review, text: str) -> Interpretation:
    manifest = review.manifest or {}
    payload = {"comment": text, "rating": review.rating, "manifest": manifest,
               "likely_targets": candidates(manifest, text)}
    result = structured_analysis(system=SYSTEM, payload=payload, schema=Interpretation, operation="review_feedback",
                                 max_tokens=1500)
    known = {item["id"]: item for item in all_items(manifest)}
    points = []
    for point in result.points:
        if point.polarity not in lessons.MULTIPLIER:
            continue
        if point.target_type == "library" and point.target_id not in known:
            continue
        if point.target_type == "aspect" and point.target_id not in lessons.ASPECTS:
            point.target_id = "other"
        if point.target_type not in {"library", "aspect"}:
            continue
        if point.target_type == "library":
            point.target_label = known[point.target_id]["label"]
        points.append(point)
    result.points = points
    return result


def comment(review: Review, text: str, reviewer: dict, *, change=False) -> str:
    text = (text or "").strip()[:2000]
    if not text:
        raise ReviewError("Kommentaren är tom.")
    feedback = _feedback(review, "change" if change else "comment", reviewer, text=text)
    if change:
        review.status = "changes"
        review.save(update_fields=["status"])
    try:
        result = interpret(review, text)
    except OpenRouterError:
        feedback.interpreted = {"pending": True}
        feedback.save(update_fields=["interpreted"])
        return "Kommentaren är sparad. Tolkningen misslyckades just nu och görs om automatiskt i natt."
    return _apply(review, feedback, result)


def _apply(review, feedback, result: Interpretation) -> str:
    feedback.interpreted = result.model_dump()
    feedback.save(update_fields=["interpreted"])
    if result.clarification and not result.points:
        return f"🤔 {result.clarification}\n(Svara med en ny kommentar så sparar jag rätt.)"
    lines = [f"Uppfattat: {result.summary}"]
    for point in result.points:
        lesson = lessons.remember(review.company, target_type=point.target_type, target_id=point.target_id,
                                  target_label=point.target_label, polarity=point.polarity, rule=point.rule,
                                  adjustment=point.adjustment, source=feedback)
        where = f"**{point.target_label or point.target_id}**"
        lines.append(f"• {lesson.get_polarity_display()} {where}: {point.rule}"
                     + (f" ({lesson.evidence}:e gången)" if lesson.evidence > 1 else ""))
    if feedback.kind == "change":
        lines.append("✏️ Ändringen ligger i kön. Nästa version postas här när den är klar.")
    return "\n".join(lines)


def interpret_pending(limit=25) -> int:
    done = 0
    for feedback in ReviewFeedback.objects.filter(interpreted__pending=True).select_related("review__company")[:limit]:
        try:
            _apply(feedback.review, feedback, interpret(feedback.review, feedback.text))
            done += 1
        except OpenRouterError:
            break
    return done


def serialize(review: Review) -> dict:
    return {
        "review_id": str(review.pk), "title": review.title, "version": review.version, "status": review.status,
        "rating": review.rating, "asset_id": str(review.asset_id), "video_link": video_link(review),
        "parent_id": str(review.parent_id) if review.parent_id else None,
        "feedback": [{"kind": f.kind, "rating": f.rating, "text": f.text, "by": f.reviewer_name,
                      "interpreted": f.interpreted, "at": f.created_at.isoformat()} for f in review.feedback.all()],
    }
