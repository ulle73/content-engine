import uuid

from django.db import models


class EditJob(models.Model):
    """One cut spec (cut/v1) waiting for, or rendered by, the cloud edit worker (edit-renderer/ on GitHub Actions)."""

    STATUSES = [
        ("queued", "I kö"), ("claimed", "Hämtad av renderaren"), ("rendering", "Renderas"),
        ("done", "Klar"), ("failed", "Misslyckades"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="edit_jobs")
    recipe_id = models.CharField(max_length=100, blank=True)
    cut_spec = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUSES, default="queued")
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True)
    # Catalog ids the template skipped and other non-fatal notes (Swedish), from validation and from the renderer.
    warnings = models.JSONField(default=list, blank=True)
    progress = models.FloatField(default=0)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatch_error = models.CharField(max_length=300, blank=True)
    # Full-quality master (what gets published) and, when the master is above Discord's upload limit, a preview.
    output_asset = models.ForeignKey("engine.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="edit_outputs")
    preview_asset = models.ForeignKey("engine.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="edit_previews")
    review = models.ForeignKey("engine.Review", null=True, blank=True, on_delete=models.SET_NULL, related_name="edit_jobs")
    discord_error = models.CharField(max_length=300, blank=True)
    # Cheap vision critique of the finished cut (engine/edit/critic.py): {"status": done/skipped/failed, "score", …}.
    ai_critique = models.JSONField(default=dict, blank=True)
    # Quality gate (engine/edit/gate.py): {"passed", "reasons", "score", "still_share", "override"?, …}.
    quality_gate = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="edit_job_status_created")]
