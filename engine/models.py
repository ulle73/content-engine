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
    official_logo = models.ForeignKey("MediaAsset", null=True, blank=True, on_delete=models.PROTECT, related_name="official_for")

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
    channel = models.CharField(max_length=10, default="organic", choices=[("organic", "Organiskt"), ("paid", "Annonser")])
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
    scrape_request = models.OneToOneField("ScrapeRequest", null=True, on_delete=models.PROTECT)
    sync_mode = models.CharField(max_length=20, default="discovery")


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
    logo_asset = models.ForeignKey("MediaAsset", null=True, blank=True, on_delete=models.PROTECT, related_name="logo_generations")
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
    purpose = models.CharField(max_length=10, default="content", choices=[("content", "Innehåll"), ("logo", "Logga")])
    sha256 = models.CharField(max_length=64, blank=True)
    # Clean generation before deterministic logo placement; never feed a rendered logo back to AI.
    generation_base_key = models.CharField(max_length=300, blank=True)


class DailyRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day = models.DateField(unique=True)
    status = models.CharField(max_length=15, default="running")
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    lease_token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    summary = models.JSONField(default=dict)


class DailyStep(models.Model):
    run = models.ForeignKey(DailyRun, on_delete=models.CASCADE, related_name="steps")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="daily_steps")
    stage = models.CharField(max_length=60)
    version = models.CharField(max_length=30, default="v1")
    key = models.CharField(max_length=160)
    status = models.CharField(max_length=15, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    message = models.CharField(max_length=500, blank=True)
    result = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "company", "stage", "version", "key"], name="unique_daily_work")]


class ScraperState(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    source = models.CharField(max_length=30)
    external_key = models.CharField(max_length=200)
    backfill_attempted_at = models.DateTimeField(null=True)
    watermark = models.DateTimeField(null=True)
    last_refresh_at = models.DateTimeField(null=True)
    next_attempt_at = models.DateTimeField(null=True)
    coverage = models.CharField(max_length=30, default="uninitialized")
    details = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "source", "external_key"], name="unique_scraper_source")]


class ScrapeRequest(models.Model):
    state = models.ForeignKey(ScraperState, on_delete=models.CASCADE, related_name="requests")
    key = models.CharField(max_length=64, unique=True)
    actor = models.CharField(max_length=100)
    mode = models.CharField(max_length=20)
    inputs = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default="starting")
    actor_run_id = models.CharField(max_length=100, unique=True, null=True)
    dataset_id = models.CharField(max_length=100, blank=True)
    max_cost_usd = models.DecimalField(max_digits=10, decimal_places=4)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    result = models.JSONField(default=dict)


class AnalysisMemo(models.Model):
    scrape_request = models.ForeignKey(ScrapeRequest, null=True, on_delete=models.PROTECT, related_name="analysis_memos")
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    key = models.CharField(max_length=64)
    status = models.CharField(max_length=20, default="started")
    model = models.CharField(max_length=100)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "key"], name="unique_paid_analysis")]


class AdAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="ad_accounts")
    name = models.CharField(max_length=200)
    page_url = models.URLField(max_length=500)
    page_id = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=3, default="SE")
    active = models.BooleanField(default=True)
    sync = models.OneToOneField(ScraperState, null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "page_url", "country"], name="unique_ad_account"),
                       models.UniqueConstraint(fields=["company", "page_id", "country"], condition=~models.Q(page_id=""), name="unique_ad_page_country")]


class CompetitorAd(models.Model):
    account = models.ForeignKey(AdAccount, on_delete=models.CASCADE, related_name="ads")
    external_id = models.CharField(max_length=100)
    creative = models.JSONField(default=dict)
    creative_hash = models.CharField(max_length=64)
    classification = models.JSONField(default=dict)
    classification_hash = models.CharField(max_length=64, blank=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["account", "external_id"], name="unique_account_ad")]


class AdObservation(models.Model):
    ad = models.ForeignKey(CompetitorAd, on_delete=models.CASCADE, related_name="observations")
    request = models.ForeignKey(ScrapeRequest, on_delete=models.PROTECT)
    observed_at = models.DateTimeField()
    data = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["ad", "request"], name="unique_ad_observation")]


class LearningModel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    channel = models.CharField(max_length=10)
    version = models.CharField(max_length=64)
    target = models.CharField(max_length=60)
    mode = models.CharField(max_length=15, default="shadow")
    trained_at = models.DateTimeField(auto_now_add=True)
    training_cutoff = models.DateTimeField()
    artifact = models.JSONField(default=dict)
    evaluation = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "channel", "version"], name="unique_learning_model")]


class Prediction(models.Model):
    run = models.ForeignKey(ContentRun, on_delete=models.CASCADE, related_name="predictions")
    idea_index = models.PositiveSmallIntegerField()
    channel = models.CharField(max_length=10)
    features = models.JSONField()
    feature_version = models.CharField(max_length=40)
    model_version = models.CharField(max_length=64)
    model = models.ForeignKey(LearningModel, null=True, on_delete=models.PROTECT)
    value = models.FloatField(null=True)
    target = models.CharField(max_length=60)
    mode = models.CharField(max_length=15, default="shadow")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "idea_index", "model_version"], name="unique_idea_prediction")]


class OwnOutcome(models.Model):
    target = models.CharField(max_length=100, blank=True)
    platform = models.CharField(max_length=30, blank=True)
    snapshot = models.ForeignKey("OwnSnapshot", null=True, on_delete=models.PROTECT)
    prediction = models.ForeignKey(Prediction, on_delete=models.PROTECT, related_name="outcomes")
    source = models.CharField(max_length=60)
    external_id = models.CharField(max_length=200)
    published_at = models.DateTimeField()
    window_end = models.DateTimeField()
    observed_at = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField()
    label = models.FloatField()
    evidence = models.URLField(max_length=1000)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["prediction", "source", "target", "external_id", "window_end"], name="unique_own_outcome_target")]


class OwnPost(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="own_posts")
    postiz_id = models.CharField(max_length=100)
    integration_id = models.CharField(max_length=100)
    release_id = models.CharField(max_length=200, blank=True)
    platform = models.CharField(max_length=30)
    format = models.CharField(max_length=30, default="unknown")
    caption = models.TextField(blank=True)
    url = models.URLField(max_length=2000, blank=True)
    published_at = models.DateTimeField()
    run = models.ForeignKey(ContentRun, null=True, on_delete=models.PROTECT, related_name="own_posts")
    next_check_at = models.DateTimeField(null=True)
    finalized_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company","integration_id","postiz_id"], name="unique_own_post"),
            models.UniqueConstraint(fields=["company","integration_id","release_id"],condition=~models.Q(release_id=""),name="unique_own_release")]


class OwnSnapshot(models.Model):
    post = models.ForeignKey(OwnPost, on_delete=models.CASCADE, related_name="snapshots")
    observed_at = models.DateTimeField()
    source_day = models.DateField()
    metrics = models.JSONField()
    raw = models.JSONField()
    contract = models.CharField(max_length=60, default="postiz-current-totals-v1")
    checkpoint = models.CharField(max_length=10, default="daily")
    baseline = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post","source_day","contract","checkpoint"],name="unique_own_snapshot_checkpoint")]

# Kept in a separate module for readability, registered with the same Django app/database.
from .creative_models import PromptEntry, PromptTerm  # noqa: E402,F401
