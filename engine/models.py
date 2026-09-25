import base64
import hashlib
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .creative_core import ReferenceRole


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


class MediaGenerationReference(models.Model):
    """Provider-neutral typed input reference with durable provenance.

    The asset may be cleaned up after a terminal generation; asset_snapshot keeps
    safe identity/provenance while active generations are protected in media.py.
    """

    generation = models.ForeignKey(MediaGeneration, on_delete=models.CASCADE, related_name="references")
    asset = models.ForeignKey(
        "MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="generation_references"
    )
    role = models.CharField(max_length=30, choices=[(role.value, role.value) for role in ReferenceRole])
    position = models.PositiveSmallIntegerField(default=0)
    asset_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.asset_id and self.generation_id:
            generation_company_id = self.generation.run.workspace_id
            if self.asset.company_id != generation_company_id:
                raise ValidationError("Generation reference asset must belong to the generation company.")
        if self.asset_id and self.role in {ReferenceRole.start_image.value, ReferenceRole.end_image.value}:
            if self.asset.kind != "image" or self.asset.purpose == "logo":
                raise ValidationError("Start/end references must be non-logo images.")
        if self.asset_id and self.role == ReferenceRole.video_reference.value and self.asset.kind != "video":
            raise ValidationError("VIDEO_REFERENCE must point to a video asset.")
        if self.role == ReferenceRole.audio_reference.value:
            raise ValidationError("AUDIO_REFERENCE is reserved until MediaAsset supports audio.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.asset_id and not self.asset_snapshot:
            self.asset_snapshot = {
                "asset_id": str(self.asset_id),
                "kind": self.asset.kind,
                "sha256": self.asset.sha256,
            }
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["generation", "role", "position"], name="unique_generation_reference_slot"
            ),
        ]
        indexes = [
            models.Index(fields=["generation", "role", "position"], name="generation_reference_idx"),
            models.Index(fields=["asset", "generation"], name="asset_generation_reference_idx"),
        ]
        ordering = ["role", "position", "id"]


class SequenceProject(models.Model):
    """Company-scoped container for one connected creative sequence."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("approved", "Approved"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sequence_projects")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sequence_projects"
    )
    title = models.CharField(max_length=200)
    brief = models.TextField(blank=True)
    goal = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    format = models.CharField(max_length=40, blank=True)
    platform = models.CharField(max_length=40, blank=True)
    blueprint_id = models.CharField(max_length=80, blank=True)
    blueprint_version = models.CharField(max_length=40, blank=True)
    plan = models.JSONField(default=dict, blank=True)
    plan_revision = models.PositiveIntegerField(default=0)
    plan_usage = models.JSONField(default=dict, blank=True)
    plan_generated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "updated_at"], name="seq_project_company_idx"),
        ]


class SequenceAnchor(models.Model):
    """Canonical visual keyframe. The MediaAsset is the source of visual truth."""

    SOURCE_CHOICES = [
        ("existing", "Existing asset"),
        ("uploaded", "Uploaded"),
        ("generated", "Generated"),
        ("clip_frame", "Clip frame"),
        ("output_chain", "Output chain"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(SequenceProject, on_delete=models.CASCADE, related_name="anchors")
    position = models.PositiveIntegerField()
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="sequence_anchors")
    label = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=40, blank=True)
    locked = models.BooleanField(default=False)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="existing")
    source_clip_version = models.ForeignKey(
        "SequenceClipVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="promoted_anchors"
    )
    source_metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.asset_id and self.project_id:
            if self.asset.company_id != self.project.company_id:
                raise ValidationError("Sequence anchor asset must belong to the project company.")
            if self.asset.kind != "image" or self.asset.purpose == "logo":
                raise ValidationError("Sequence anchors must use non-logo image assets.")
        if self.source_clip_version_id and self.project_id:
            if self.source_clip_version.clip.project_id != self.project_id:
                raise ValidationError("Anchor source clip version must belong to the same project.")
        if self.source_type in {"clip_frame", "output_chain"} and not self.source_clip_version_id:
            raise ValidationError("Clip-derived anchors must retain their source clip version.")
        if self.source_type == "output_chain":
            metadata = self.source_metadata if isinstance(self.source_metadata, dict) else {}
            if metadata.get("mode") != "output_chain" or metadata.get("frame_selector") != "final":
                raise ValidationError("Output-chain anchors must retain final-frame provenance.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["project", "position"], name="uniq_seq_anchor_pos"),
        ]
        indexes = [
            models.Index(fields=["project", "locked", "position"], name="seq_anchor_project_idx"),
        ]


class SequenceAnchorRevision(models.Model):
    """Non-destructive history of each canonical anchor asset/provenance state."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anchor = models.ForeignKey(SequenceAnchor, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="sequence_anchor_revisions")
    source_type = models.CharField(max_length=20, choices=SequenceAnchor.SOURCE_CHOICES, default="existing")
    source_clip_version = models.ForeignKey(
        "SequenceClipVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="anchor_revisions"
    )
    source_metadata = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=40, default="created")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.anchor_id and self.asset_id:
            if self.asset.company_id != self.anchor.project.company_id:
                raise ValidationError("Anchor revision asset must belong to the project company.")
            if self.asset.kind != "image" or self.asset.purpose == "logo":
                raise ValidationError("Anchor revision must use a non-logo image.")
        if self.source_clip_version_id and self.anchor_id:
            if self.source_clip_version.clip.project_id != self.anchor.project_id:
                raise ValidationError("Anchor revision source clip version must belong to the same project.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["revision_number", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["anchor", "revision_number"], name="uniq_seq_anchor_revision"),
            models.CheckConstraint(
                condition=models.Q(revision_number__gte=1), name="seq_anchor_revision_gte_1"
            ),
        ]
        indexes = [
            models.Index(fields=["anchor", "revision_number"], name="seq_anchor_revision_idx"),
        ]


class SequenceAnchorGenerationTarget(models.Model):
    """Binds an existing reviewed image-generation job to one anchor action."""

    MODE_CHOICES = [
        ("create", "Create anchor"),
        ("replace", "Replace anchor"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(SequenceProject, on_delete=models.CASCADE, related_name="anchor_generation_targets")
    generation = models.OneToOneField(
        MediaGeneration, on_delete=models.PROTECT, related_name="sequence_anchor_target"
    )
    mode = models.CharField(max_length=12, choices=MODE_CHOICES)
    target_anchor = models.ForeignKey(
        SequenceAnchor, null=True, blank=True, on_delete=models.SET_NULL, related_name="generation_targets"
    )
    applied_anchor = models.ForeignKey(
        SequenceAnchor, null=True, blank=True, on_delete=models.SET_NULL, related_name="applied_generation_targets"
    )
    target_label = models.CharField(max_length=120, blank=True)
    target_role = models.CharField(max_length=40, blank=True)
    target_position = models.PositiveIntegerField(null=True, blank=True)
    plan_revision = models.PositiveIntegerField(null=True, blank=True)
    plan_anchor_snapshot = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.generation_id and self.project_id:
            if self.generation.run.workspace_id != self.project.company_id:
                raise ValidationError("Anchor generation must belong to the project company.")
            if self.generation.kind != "image":
                raise ValidationError("Anchor generation target must reference an image generation.")
        if self.mode == "replace":
            if not self.target_anchor_id:
                raise ValidationError("Replace mode requires a target anchor.")
            if self.target_anchor.project_id != self.project_id:
                raise ValidationError("Target anchor must belong to the same project.")
        if self.mode == "create" and self.target_anchor_id:
            raise ValidationError("Create mode cannot point to an existing target anchor.")
        if self.target_position is not None:
            if self.plan_revision is None or self.plan_revision < 1:
                raise ValidationError("Plan-bound anchor generation requires a positive plan revision.")
            if not isinstance(self.plan_anchor_snapshot, dict) or int(
                self.plan_anchor_snapshot.get("position", -1)
            ) != self.target_position:
                raise ValidationError("Plan-bound anchor generation requires a matching anchor snapshot.")
            if self.target_anchor_id and self.target_anchor.position != self.target_position:
                raise ValidationError("Target anchor position must match the planned position.")
        elif self.plan_revision is not None or self.plan_anchor_snapshot:
            raise ValidationError("Plan provenance requires a target position.")
        if self.applied_anchor_id and self.applied_anchor.project_id != self.project_id:
            raise ValidationError("Applied anchor must belong to the same project.")
        if self.applied_anchor_id and self.target_position is not None:
            if self.applied_anchor.position != self.target_position:
                raise ValidationError("Applied anchor position must match the planned position.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "mode", "created_at"], name="seq_anchor_gen_target_idx"),
        ]


class SequenceClip(models.Model):
    """Logical clip between two canonical anchors."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("generating", "Generating"),
        ("review", "Review"),
        ("selected", "Selected"),
        ("approved", "Approved"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(SequenceProject, on_delete=models.CASCADE, related_name="clips")
    position = models.PositiveIntegerField()
    start_anchor = models.ForeignKey(
        SequenceAnchor, on_delete=models.RESTRICT, related_name="starting_clips"
    )
    end_anchor = models.ForeignKey(
        SequenceAnchor, on_delete=models.RESTRICT, related_name="ending_clips"
    )
    label = models.CharField(max_length=120, blank=True)
    recipe_id = models.CharField(max_length=80)
    recipe_version = models.CharField(max_length=40)
    model_override = models.CharField(max_length=120, blank=True)
    duration_seconds_target = models.PositiveSmallIntegerField(null=True, blank=True)
    aspect_ratio = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    selected_version = models.ForeignKey(
        "SequenceClipVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.project_id and self.start_anchor_id:
            if self.start_anchor.project_id != self.project_id:
                raise ValidationError("Start anchor must belong to the clip project.")
        if self.project_id and self.end_anchor_id:
            if self.end_anchor.project_id != self.project_id:
                raise ValidationError("End anchor must belong to the clip project.")
        if self.start_anchor_id and self.end_anchor_id:
            if self.start_anchor.position >= self.end_anchor.position:
                raise ValidationError("Sequence clip start anchor must precede end anchor.")
        if self.selected_version_id and self.pk:
            if self.selected_version.clip_id != self.pk:
                raise ValidationError("Selected version must belong to this clip.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["project", "position"], name="uniq_seq_clip_pos"),
            models.CheckConstraint(
                condition=~models.Q(start_anchor=models.F("end_anchor")),
                name="seq_clip_distinct_anchors",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status", "position"], name="seq_clip_project_idx"),
        ]


class SequenceClipVersion(models.Model):
    """Immutable-ish generation candidate snapshot for one logical SequenceClip."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("ready", "Ready"),
        ("selected", "Selected"),
        ("rejected", "Rejected"),
        ("failed", "Failed"),
        ("stale", "Stale"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clip = models.ForeignKey(SequenceClip, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    generation = models.OneToOneField(
        MediaGeneration, on_delete=models.PROTECT, related_name="sequence_clip_version"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    recipe_id = models.CharField(max_length=80)
    recipe_version = models.CharField(max_length=40)
    model_id = models.CharField(max_length=120, blank=True)
    provider_model = models.CharField(max_length=180, blank=True)
    prompt_snapshot = models.TextField(blank=True)
    reference_snapshot = models.JSONField(default=list, blank=True)
    usage_snapshot = models.JSONField(default=dict, blank=True)
    cost_snapshot = models.JSONField(default=dict, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.clip_id and self.generation_id:
            if self.generation.run.workspace_id != self.clip.project.company_id:
                raise ValidationError("Sequence clip generation must belong to the project company.")
            if self.generation.kind != "video":
                raise ValidationError("Sequence clip versions must reference video generations.")
            if hasattr(self.generation, "sequence_bridge_version"):
                raise ValidationError("A bridge generation cannot also be reused as a clip generation.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["version_number", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["clip", "version_number"], name="uniq_seq_version_num"),
            models.CheckConstraint(condition=models.Q(version_number__gte=1), name="seq_version_num_gte_1"),
        ]
        indexes = [
            models.Index(fields=["clip", "status", "version_number"], name="seq_version_clip_idx"),
        ]


class SequenceBridge(models.Model):
    """Non-destructive transition segment between two existing sequence clips."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("review", "Review"),
        ("selected", "Selected"),
        ("approved", "Approved"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(SequenceProject, on_delete=models.CASCADE, related_name="bridges")
    left_clip = models.ForeignKey(SequenceClip, on_delete=models.CASCADE, related_name="outgoing_bridges")
    right_clip = models.ForeignKey(SequenceClip, on_delete=models.CASCADE, related_name="incoming_bridges")
    start_anchor = models.ForeignKey(
        SequenceAnchor, on_delete=models.CASCADE, related_name="starting_bridges"
    )
    end_anchor = models.ForeignKey(
        SequenceAnchor, on_delete=models.CASCADE, related_name="ending_bridges"
    )
    recipe_id = models.CharField(max_length=80, default="scroll_transition_bridge")
    recipe_version = models.CharField(max_length=40)
    label = models.CharField(max_length=120, blank=True)
    duration_seconds_target = models.PositiveSmallIntegerField(null=True, blank=True)
    aspect_ratio = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    selected_version = models.ForeignKey(
        "SequenceBridgeVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.recipe_id != "scroll_transition_bridge":
            raise ValidationError("Sequence bridges must use the trusted scroll_transition_bridge recipe.")
        if self.project_id and self.left_clip_id and self.left_clip.project_id != self.project_id:
            raise ValidationError("Left clip must belong to the bridge project.")
        if self.project_id and self.right_clip_id and self.right_clip.project_id != self.project_id:
            raise ValidationError("Right clip must belong to the bridge project.")
        if self.left_clip_id and self.right_clip_id:
            if self.left_clip_id == self.right_clip_id:
                raise ValidationError("Transition bridge requires two different clips.")
            if self.left_clip.position >= self.right_clip.position:
                raise ValidationError("Left clip must precede right clip.")
        if self.project_id and self.start_anchor_id and self.start_anchor.project_id != self.project_id:
            raise ValidationError("Bridge start anchor must belong to the bridge project.")
        if self.project_id and self.end_anchor_id and self.end_anchor.project_id != self.project_id:
            raise ValidationError("Bridge end anchor must belong to the bridge project.")
        if self.left_clip_id and self.start_anchor_id and self.start_anchor_id != self.left_clip.end_anchor_id:
            raise ValidationError("Bridge start anchor must be the left clip end anchor.")
        if self.right_clip_id and self.end_anchor_id and self.end_anchor_id != self.right_clip.start_anchor_id:
            raise ValidationError("Bridge end anchor must be the right clip start anchor.")
        if self.start_anchor_id and self.end_anchor_id:
            if self.start_anchor_id == self.end_anchor_id:
                raise ValidationError("Transition bridge requires two distinct anchors.")
            if self.start_anchor.position >= self.end_anchor.position:
                raise ValidationError("Bridge start anchor must precede bridge end anchor.")
        if self.selected_version_id and self.pk:
            if self.selected_version.bridge_id != self.pk:
                raise ValidationError("Selected bridge version must belong to this bridge.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "left_clip", "right_clip"], name="uniq_seq_bridge_pair"
            ),
            models.CheckConstraint(
                condition=~models.Q(left_clip=models.F("right_clip")),
                name="seq_bridge_distinct_clips",
            ),
            models.CheckConstraint(
                condition=~models.Q(start_anchor=models.F("end_anchor")),
                name="seq_bridge_distinct_anchors",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status"], name="seq_bridge_project_idx"),
        ]


class SequenceBridgeVersion(models.Model):
    """Generation candidate for a non-destructive transition bridge."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("ready", "Ready"),
        ("selected", "Selected"),
        ("rejected", "Rejected"),
        ("failed", "Failed"),
        ("stale", "Stale"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bridge = models.ForeignKey(SequenceBridge, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    generation = models.OneToOneField(
        MediaGeneration, on_delete=models.PROTECT, related_name="sequence_bridge_version"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    recipe_id = models.CharField(max_length=80)
    recipe_version = models.CharField(max_length=40)
    model_id = models.CharField(max_length=120, blank=True)
    provider_model = models.CharField(max_length=180, blank=True)
    prompt_snapshot = models.TextField(blank=True)
    reference_snapshot = models.JSONField(default=list, blank=True)
    usage_snapshot = models.JSONField(default=dict, blank=True)
    cost_snapshot = models.JSONField(default=dict, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.bridge_id and self.generation_id:
            if self.generation.run.workspace_id != self.bridge.project.company_id:
                raise ValidationError("Sequence bridge generation must belong to the project company.")
            if self.generation.kind != "video":
                raise ValidationError("Sequence bridge versions must reference video generations.")
            if hasattr(self.generation, "sequence_clip_version"):
                raise ValidationError("A clip generation cannot also be reused as a bridge generation.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["version_number", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["bridge", "version_number"], name="uniq_seq_bridge_ver_num"),
            models.CheckConstraint(
                condition=models.Q(version_number__gte=1), name="seq_bridge_ver_num_gte_1"
            ),
        ]
        indexes = [
            models.Index(fields=["bridge", "status", "version_number"], name="seq_bridge_ver_idx"),
        ]


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
