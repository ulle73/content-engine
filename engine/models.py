import base64
import hashlib
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class SetupState(models.Model):
    """Single transaction lock for first-admin registration."""

    completed = models.BooleanField(default=False)


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    profile = models.TextField(blank=True)
    voice = models.TextField(blank=True)
    current = models.TextField(blank=True)
    source = models.CharField(max_length=500, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    postiz_ciphertext = models.TextField(blank=True, default="")
    postiz_channels = models.JSONField(default=list)

    @staticmethod
    def cipher():
        key = hashlib.sha256(settings.POSTIZ_ENCRYPTION_SECRET.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    @property
    def postiz_key(self):
        return self.cipher().decrypt(self.postiz_ciphertext.encode()).decode() if self.postiz_ciphertext else ""

    @postiz_key.setter
    def postiz_key(self, value):
        self.postiz_ciphertext = self.cipher().encrypt(value.encode()).decode() if value else ""


class ContentRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Company, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    context = models.JSONField()
    ideas = models.JSONField(default=list)
    selected = models.PositiveSmallIntegerField(null=True)
    draft = models.JSONField(default=dict)
    model = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, default="draft")
    delivery_result = models.JSONField(default=list)
    media_asset = models.ForeignKey("MediaAsset", null=True, blank=True, on_delete=models.PROTECT, related_name="content_runs")

    @property
    def title(self):
        return (
            self.ideas[self.selected]["title"]
            if self.selected is not None and self.selected < len(self.ideas)
            else "Sparat utkast"
        )

    @property
    def influencing_signal(self):
        if self.selected is None or self.selected >= len(self.ideas):
            return None
        signal_id = self.ideas[self.selected].get("signal_id")
        return next((s for s in self.context.get("competitor_signals", []) if s["id"] == signal_id), None)


class Competitor(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="competitors")
    name = models.CharField(max_length=200)
    username = models.CharField(max_length=30)
    active = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "username"], name="unique_company_competitor")]

    @property
    def url(self):
        return f"https://www.instagram.com/{self.username}/"


class CompetitorImport(models.Model):
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name="imports")
    actor = models.CharField(max_length=100)
    actor_run_id = models.CharField(max_length=100, unique=True, null=True)
    dataset_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default="starting")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    item_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    requested_limit = models.PositiveIntegerField(default=100)
    error = models.CharField(max_length=500, blank=True)
    fallback_of = models.ForeignKey("self", null=True, on_delete=models.SET_NULL)


class CompetitorPost(models.Model):
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name="posts")
    shortcode = models.CharField(max_length=100)
    instagram_id = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=500)
    published_at = models.DateTimeField(db_index=True)
    caption = models.TextField(blank=True)
    format = models.CharField(
        max_length=20, choices=[("image", "Bild"), ("carousel", "Carousel"), ("reel", "Reel/video")]
    )
    duration_seconds = models.FloatField(null=True)
    slide_count = models.PositiveSmallIntegerField(null=True)
    classification = models.JSONField(default=dict)
    classification_hash = models.CharField(max_length=64, blank=True)
    classified_at = models.DateTimeField(null=True)
    classifier_model = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["competitor", "shortcode"], name="unique_competitor_post")]


class CompetitorSnapshot(models.Model):
    post = models.ForeignKey(CompetitorPost, on_delete=models.CASCADE, related_name="snapshots")
    import_run = models.ForeignKey(CompetitorImport, on_delete=models.CASCADE)
    observed_at = models.DateTimeField(db_index=True)
    likes = models.BigIntegerField(null=True)
    comments = models.BigIntegerField(null=True)
    views = models.BigIntegerField(null=True)
    view_metric = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "import_run"], name="unique_post_observation")]
        ordering = ["observed_at", "id"]


class ContentEvent(models.Model):
    """Append-only learning trail; future published/results observations use the same run link."""

    run = models.ForeignKey(ContentRun, on_delete=models.CASCADE, related_name="events")
    idea_index = models.PositiveSmallIntegerField(null=True)
    action = models.CharField(max_length=30)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class MediaGeneration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ContentRun, on_delete=models.CASCADE, related_name="media_jobs")
    kind = models.CharField(max_length=10)
    provider = models.CharField(max_length=20)
    brief = models.TextField()
    prompt = models.TextField()
    parameters = models.JSONField(default=dict)
    source_asset = models.ForeignKey("MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="variations")
    provider_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, default="queued")
    error = models.CharField(max_length=500, blank=True)
    usage = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MediaAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="media_assets")
    kind = models.CharField(max_length=10, choices=[("image", "Bild"), ("video", "Video")])
    origin = models.CharField(max_length=10, choices=[("uploaded", "Uppladdad"), ("generated", "AI-genererad")])
    provider = models.CharField(max_length=20)
    storage_backend = models.CharField(max_length=10)
    storage_key = models.CharField(max_length=300)
    mime_type = models.CharField(max_length=80)
    byte_size = models.PositiveBigIntegerField()
    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)
    duration_seconds = models.FloatField(null=True)
    alt_text = models.CharField(max_length=500, blank=True)
    brief = models.TextField(blank=True)
    generation = models.ForeignKey(MediaGeneration, null=True, on_delete=models.SET_NULL, related_name="assets")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True)
    used_at = models.DateTimeField(null=True)
