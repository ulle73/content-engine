"""Motion-only metadata; media, ownership, auth and action ledger stay shared."""

import uuid

from django.db import models


class MotionWorkerSession(models.Model):
    """Short-lived presence for an outbound-only renderer on an operator's computer."""

    id = models.UUIDField(primary_key=True, editable=False)
    expires_at = models.DateTimeField()


class MotionProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.PROTECT, related_name="motion_projects")
    run = models.OneToOneField("engine.ContentRun", on_delete=models.PROTECT, related_name="motion_project")
    source_sequence = models.OneToOneField(
        "engine.SequenceProject", null=True, blank=True, on_delete=models.PROTECT, related_name="film"
    )
    sequence_settings = models.JSONField(default=dict, blank=True)
    title = models.CharField(max_length=160)
    current_revision = models.PositiveIntegerField(default=1)
    approved_preview = models.ForeignKey(
        "engine.MotionRender", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MotionRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(MotionProject, on_delete=models.CASCADE, related_name="revisions")
    number = models.PositiveIntegerField()
    spec = models.JSONField()
    spec_hash = models.CharField(max_length=64)
    brand = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "number"], name="motion_revision_number_unique")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Motion revisions are immutable; create a new revision.")
        return super().save(*args, **kwargs)


class MotionAssetReference(models.Model):
    revision = models.ForeignKey(MotionRevision, on_delete=models.CASCADE, related_name="asset_references")
    asset = models.ForeignKey("engine.MediaAsset", on_delete=models.PROTECT, related_name="motion_references")
    sha256 = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "asset"], name="motion_revision_asset_unique")]


class MotionRender(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(MotionRevision, on_delete=models.PROTECT, related_name="renders")
    generation = models.OneToOneField("engine.MediaGeneration", on_delete=models.PROTECT, related_name="motion_render")
    mode = models.CharField(max_length=10, choices=[("preview", "Preview"), ("final", "Final")])
    progress = models.FloatField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    output_asset = models.ForeignKey(
        "engine.MediaAsset", null=True, blank=True, on_delete=models.PROTECT, related_name="motion_outputs"
    )
    keyframes = models.ManyToManyField("engine.MediaAsset", through="MotionKeyframe", related_name="motion_keyframes")
    diagnostics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["lease_expires_at", "created_at"], name="motion_lease_idx")]


class MotionKeyframe(models.Model):
    render = models.ForeignKey(MotionRender, on_delete=models.CASCADE, related_name="storyboard")
    asset = models.ForeignKey("engine.MediaAsset", on_delete=models.PROTECT, related_name="motion_storyboards")
    scene_id = models.CharField(max_length=64)
    frame = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["render", "scene_id"], name="motion_keyframe_scene_unique")]
