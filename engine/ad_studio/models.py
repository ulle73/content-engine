import uuid

from django.conf import settings
from django.db import models


class AdDraft(models.Model):
    """One ad being designed in conversation. `brief` is an AdBrief as JSON."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="ad_drafts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    title = models.CharField(max_length=160, blank=True)
    brief = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=12,
        default="draft",
        choices=[("draft", "Utkast"), ("locked", "Låst"), ("producing", "Produceras"), ("archived", "Arkiverad")],
    )
    lock_hash = models.CharField(max_length=64, blank=True)
    motion_project = models.ForeignKey(
        "engine.MotionProject", null=True, blank=True, on_delete=models.SET_NULL, related_name="ad_drafts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class AssetTags(models.Model):
    """Searchable description of a media asset, written after looking at it.

    Tags are written by the assistant (which can see the image via view_media)
    or by a human, and corrected by a human. `verified` marks human-checked tags.
    """

    asset = models.OneToOneField("engine.MediaAsset", on_delete=models.CASCADE, related_name="ad_tags")
    description = models.CharField(max_length=500, blank=True)
    tags = models.JSONField(default=list)
    roles = models.JSONField(default=list)  # hook, footage, screen, product, proof, end_card, logo
    theme = models.CharField(max_length=60, blank=True)  # friskvard, kampanj, bana, app ...
    season = models.CharField(max_length=20, blank=True)
    mood = models.CharField(max_length=60, blank=True)
    source = models.CharField(max_length=200, blank=True)  # e.g. "Epassi-portal", "eget foto"
    verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def search_text(self) -> str:
        parts = [self.description, self.theme, self.season, self.mood, self.source, *self.tags, *self.roles]
        return " ".join(p for p in parts if p).casefold()
