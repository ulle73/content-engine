import uuid

from django.conf import settings
from django.db import models


class SmsFilmJob(models.Model):
    """One SMS film made in the dashboard (Generera video → SMS-film), rendered by .github/workflows/sms-film-render.yml.

    `conversation` is the template's conversation.json with uploaded images referenced as assets/upload/<asset id>.<ext>;
    those ids are listed in `image_asset_ids` so the worker may download exactly them.
    """

    KINDS = [("sms", "SMS-film"), ("slutmall", "Slutmall"), ("mall", "Mall")]
    STATUSES = [
        ("queued", "I kö"), ("claimed", "Hämtad av renderaren"), ("rendering", "Renderas"),
        ("done", "Klar"), ("failed", "Misslyckades"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="sms_film_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="sms_film_jobs")
    title = models.CharField(max_length=200, blank=True)
    # "slutmall": an end card from library/templates/golfkuponger-slutmallar (swing logo + two text lines);
    # form holds {mall, rad1, rad2} and conversation/image_asset_ids stay empty.
    kind = models.CharField(max_length=10, choices=KINDS, default="sms")
    # The form as submitted (to reopen and tweak it) and the conversation.json built from it.
    form = models.JSONField(default=dict, blank=True)
    conversation = models.JSONField(default=dict)
    image_asset_ids = models.JSONField(default=list, blank=True)
    # Dashboard templates (mall/v1, library/templates/<mall_id>/mall.json; docs/designs/mallmotor.md). `varden` holds
    # every control value, frozen with the template's defaults when the job was created (format-dependent defaults
    # are left out and resolved per format by the page). ormats lists the formats one job renders.
    mall_id = models.CharField(max_length=64, blank=True)
    varden = models.JSONField(default=dict, blank=True)
    formats = models.JSONField(default=list, blank=True)
    # The commit that rendered the files, for tracing only.
    render_commit = models.CharField(max_length=40, blank=True)
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


class SmsFilmOutput(models.Model):
    """One file a job produced (a template can give several: e.g. 9:16 and 4:5). The job's output_asset still points
    at the 9:16 file so the job list and an SMS film's end keep working."""

    TYPER = [("bild", "Bild"), ("video", "Video")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(SmsFilmJob, on_delete=models.CASCADE, related_name="outputs")
    typ = models.CharField(max_length=10, choices=TYPER)
    format = models.CharField(max_length=10)
    variant = models.CharField(max_length=20, blank=True)
    bredd = models.PositiveIntegerField(default=0)
    hojd = models.PositiveIntegerField(default=0)
    langd = models.FloatField(null=True, blank=True)
    asset = models.ForeignKey("engine.MediaAsset", on_delete=models.PROTECT, related_name="sms_film_files")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["job", "format", "variant"]
        constraints = [models.UniqueConstraint(fields=["job", "typ", "format", "variant"], name="sms_film_output_unique")]
