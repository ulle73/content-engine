import uuid

from django.db import models


class ReferenceVideo(models.Model):
    """A video someone else made (a monitored ad or post, or any URL) that we study to make our own version.

    The file is stored in our own storage the moment it is fetched, because ad-library and CDN links expire. It is
    never a MediaAsset: reference footage, people, claims and logos are someone else's and must not end up in our
    media bank or in a cut. Only its grammar (hook, structure, rhythm, camera, sound) is reused.
    """

    STATUSES = [("fetched", "Hämtad"), ("measured", "Uppmätt"), ("analyzed", "Nedbruten"), ("failed", "Misslyckades")]
    KINDS = [("url", "Länk"), ("meta_ad", "Meta-annons"), ("instagram", "Instagram-inlägg")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="reference_videos")
    source_kind = models.CharField(max_length=10, choices=KINDS, default="url")
    source_url = models.URLField(max_length=2000)
    competitor_ad = models.ForeignKey("engine.CompetitorAd", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="reference_videos")
    competitor_post = models.ForeignKey("engine.CompetitorPost", null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name="reference_videos")
    author = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="fetched")
    error = models.TextField(blank=True)

    storage_backend = models.CharField(max_length=10)
    storage_key = models.CharField(max_length=300)
    proxy_key = models.CharField(max_length=300, blank=True)  # small H.264 copy that the vision model watches
    sheet_key = models.CharField(max_length=300, blank=True)  # contact sheet: one frame per measured scene
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveBigIntegerField(default=0)
    duration_s = models.FloatField(null=True)
    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)

    # Exact, free measurements (engine/references/measure.py): cuts, motion, tempo, loudness, silence.
    measurements = models.JSONField(default=dict, blank=True)
    # The chosen breakdown, and every model run kept for comparison: [{model, cost_usd, created_at, breakdown}].
    breakdown = models.JSONField(default=dict, blank=True)
    analyses = models.JSONField(default=list, blank=True)
    # "Our version" plans made from the breakdown: [{id, created_at, model, cost_usd, angle, plan}].
    adaptations = models.JSONField(default=list, blank=True)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["company", "sha256"], name="unique_reference_video_file")]

    def __str__(self):
        return self.title or self.source_url
