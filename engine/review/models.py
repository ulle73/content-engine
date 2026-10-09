import uuid

from django.db import models


class Review(models.Model):
    """One version of a finished video waiting for (or given) a human verdict."""

    STATUSES = [
        ("pending", "Väntar"), ("approved", "Godkänd"), ("rejected", "Nej"),
        ("changes", "Ändras"), ("superseded", "Ersatt"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="reviews")
    asset = models.ForeignKey("engine.MediaAsset", on_delete=models.PROTECT, related_name="reviews")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="revisions")
    ad_draft = models.ForeignKey("engine.AdDraft", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews")
    title = models.CharField(max_length=200)
    caption = models.TextField(blank=True)
    # What the video is made of, scene by scene, so feedback can point at the exact effect/template/model.
    manifest = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    discord_channel_id = models.CharField(max_length=32, blank=True)
    discord_message_id = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ReviewFeedback(models.Model):
    KINDS = [("approve", "👍"), ("reject", "👎"), ("rating", "Betyg"), ("comment", "Kommentar"), ("change", "Ändra")]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="feedback")
    kind = models.CharField(max_length=10, choices=KINDS)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    text = models.TextField(blank=True)
    interpreted = models.JSONField(default=dict, blank=True)
    reviewer_id = models.CharField(max_length=32, blank=True)
    reviewer_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Lesson(models.Model):
    """Something the system learned from feedback. Steers library ranking and every new production."""

    POLARITIES = [("avoid", "Undvik"), ("prefer", "Mer av"), ("adjust", "Justera")]

    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="lessons")
    # target_type: library (catalog item id), aspect (hook/pacing/music/text/logo/cta/color/voice/model/other)
    target_type = models.CharField(max_length=12)
    target_id = models.CharField(max_length=200)
    target_label = models.CharField(max_length=200, blank=True)
    polarity = models.CharField(max_length=8, choices=POLARITIES)
    rule = models.TextField()
    adjustment = models.JSONField(default=dict, blank=True)
    evidence = models.PositiveIntegerField(default=1)
    source = models.ForeignKey(ReviewFeedback, null=True, blank=True, on_delete=models.SET_NULL, related_name="lessons")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-evidence", "-updated_at"]
        constraints = [models.UniqueConstraint(fields=["company", "target_type", "target_id", "polarity"],
                                               name="unique_lesson_target")]
