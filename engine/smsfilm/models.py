import uuid

from django.conf import settings
from django.db import models


class SmsFilmJob(models.Model):
    """One SMS film made in the dashboard (Generera video → SMS-film), rendered by .github/workflows/sms-film-render.yml.

    `conversation` is the template's conversation.json with uploaded images referenced as assets/upload/<asset id>.<ext>;
    those ids are listed in `image_asset_ids` so the worker may download exactly them.
    """

    STATUSES = [
        ("queued", "I kö"), ("claimed", "Hämtad av renderaren"), ("rendering", "Renderas"),
        ("done", "Klar"), ("failed", "Misslyckades"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="sms_film_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="sms_film_jobs")
    title = models.CharField(max_length=200, blank=True)
    # The form as submitted (to reopen and tweak it) and the conversation.json built from it.
    form = models.JSONField(default=dict, blank=True)
    conversation = models.JSONField(default=dict)
    image_asset_ids = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="queued")
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True)
    warnings = models.JSONField(default=list, blank=True)
    progress = models.FloatField(default=0)
    stage = models.CharField(max_length=40, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatch_error = models.CharField(max_length=300, blank=True)
    duration_s = models.FloatField(null=True, blank=True)
    output_asset = models.ForeignKey("engine.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="sms_film_outputs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="sms_film_status_created")]
