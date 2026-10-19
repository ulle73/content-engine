"""Persist approved techniques and staged suggestions alongside the static Content Library."""
import uuid

from django.conf import settings
from django.db import models


class TechniqueImport(models.Model):
    """One link, its AI-derived suggestions, and the human review decision."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="technique_imports")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    source_url = models.URLField(max_length=2000)
    source_kind = models.CharField(max_length=10, choices=[("page", "Webbsida"), ("video", "Video")])
    source_title = models.CharField(max_length=300, blank=True)
    reference = models.ForeignKey("engine.ReferenceVideo", null=True, blank=True, on_delete=models.SET_NULL)
    suggestions = models.JSONField(default=list)
    status = models.CharField(max_length=12, default="review", choices=[("review", "Granskas"), ("approved", "Godkänd")])
    approved_indices = models.JSONField(default=list)
    analysis_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["company", "source_url"], name="unique_company_technique_source")]


class StoredTechnique(models.Model):
    """Approved overlay to library/catalog.json, scoped to one company."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="stored_techniques")
    batch = models.ForeignKey(TechniqueImport, on_delete=models.PROTECT, related_name="saved")
    key = models.SlugField(max_length=120)
    data = models.JSONField(default=dict)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-approved_at"]
        constraints = [models.UniqueConstraint(fields=["company", "key"], name="unique_company_technique_key")]
