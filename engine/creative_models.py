"""Additive Creative Engine tables; media stays in the existing media models."""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PromptQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if set(kwargs) & {"original_text", "original_hash", "company", "company_id"}:
            raise ValidationError("Original prompt and company cannot be changed.")
        return super().update(**kwargs)


class PromptEntry(models.Model):
    objects = PromptQuerySet.as_manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="prompts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    original_text = models.TextField(editable=False)
    original_hash = models.CharField(max_length=64, editable=False)
    text = models.TextField()
    title = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict)
    source_url = models.URLField(max_length=2000, blank=True)
    notes = models.TextField(blank=True)
    origin = models.CharField(max_length=20, default="manual")
    favorite = models.BooleanField(default=False)
    generation = models.ForeignKey("engine.MediaGeneration", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="saved_prompts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous = type(self).objects.filter(pk=self.pk).values("original_text", "original_hash", "company_id").first()
            if previous and any(getattr(self, field) != value for field, value in previous.items()):
                raise ValidationError("Original prompt and company cannot be changed.")
        super().save(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "original_hash"], name="unique_company_prompt_original")]
        indexes = [models.Index(fields=["company", "archived_at", "-created_at"], name="prompt_company_recent_idx")]
        ordering = ["-created_at", "-id"]


class PromptTerm(models.Model):
    """Indexed multilingual concept/word lookup; never scan every prompt per request."""
    prompt = models.ForeignKey(PromptEntry, on_delete=models.CASCADE, related_name="terms")
    value = models.CharField(max_length=80)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["prompt", "value"], name="unique_prompt_term")]
        indexes = [models.Index(fields=["value", "prompt"], name="prompt_term_lookup_idx")]
