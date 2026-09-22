import uuid

from django.conf import settings
from django.db import models


class RunState(models.Model):
    """Operator-only concurrency and delivery metadata for an existing ContentRun."""

    run = models.OneToOneField("engine.ContentRun", on_delete=models.CASCADE, related_name="operator_state")
    revision = models.PositiveIntegerField(default=0)
    delivery_mode = models.CharField(max_length=10, blank=True, default="")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    synced_hash = models.CharField(max_length=64, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)


class MediaProvenance(models.Model):
    """Where an asset came from without changing the existing MediaAsset contract."""

    asset = models.OneToOneField("engine.MediaAsset", on_delete=models.CASCADE, related_name="operator_provenance")
    source = models.CharField(max_length=30)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class OperatorAction(models.Model):
    """Durable exactly-once reservation for MCP writes and paid/external side effects."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="operator_actions")
    run = models.ForeignKey(
        "engine.ContentRun", null=True, blank=True, on_delete=models.PROTECT, related_name="operator_actions"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, default="started")
    result = models.JSONField(default=dict)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "key"], name="unique_operator_action_company_key")
        ]
        indexes = [
            models.Index(fields=["company", "status", "created_at"], name="operator_action_status_idx")
        ]
