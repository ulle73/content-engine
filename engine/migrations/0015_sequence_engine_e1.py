# Generated for Content Engine Creative Intelligence E1 on 2026-09-24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("engine", "0014_media_generation_references"),
    ]

    operations = [
        migrations.CreateModel(
            name="SequenceProject",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("brief", models.TextField(blank=True)),
                ("goal", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("approved", "Approved"), ("archived", "Archived")], default="draft", max_length=20)),
                ("format", models.CharField(blank=True, max_length=40)),
                ("platform", models.CharField(blank=True, max_length=40)),
                ("blueprint_id", models.CharField(blank=True, max_length=80)),
                ("blueprint_version", models.CharField(blank=True, max_length=40)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sequence_projects", to=settings.AUTH_USER_MODEL)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sequence_projects", to="engine.company")),
            ],
            options={"ordering": ["-updated_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="SequenceAnchor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("position", models.PositiveIntegerField()),
                ("label", models.CharField(blank=True, max_length=120)),
                ("role", models.CharField(blank=True, max_length=40)),
                ("locked", models.BooleanField(default=False)),
                ("source_type", models.CharField(choices=[("existing", "Existing asset"), ("uploaded", "Uploaded"), ("generated", "Generated"), ("clip_frame", "Clip frame")], default="existing", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sequence_anchors", to="engine.mediaasset")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="anchors", to="engine.sequenceproject")),
            ],
            options={"ordering": ["position", "created_at"]},
        ),
        migrations.CreateModel(
            name="SequenceClip",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("position", models.PositiveIntegerField()),
                ("label", models.CharField(blank=True, max_length=120)),
                ("recipe_id", models.CharField(max_length=80)),
                ("recipe_version", models.CharField(max_length=40)),
                ("model_override", models.CharField(blank=True, max_length=120)),
                ("duration_seconds_target", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("aspect_ratio", models.CharField(blank=True, max_length=20)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("generating", "Generating"), ("review", "Review"), ("selected", "Selected"), ("approved", "Approved"), ("archived", "Archived")], default="draft", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("end_anchor", models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name="ending_clips", to="engine.sequenceanchor")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="clips", to="engine.sequenceproject")),
                ("start_anchor", models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name="starting_clips", to="engine.sequenceanchor")),
            ],
            options={"ordering": ["position", "created_at"]},
        ),
        migrations.CreateModel(
            name="SequenceClipVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("version_number", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("queued", "Queued"), ("ready", "Ready"), ("selected", "Selected"), ("rejected", "Rejected"), ("failed", "Failed")], default="queued", max_length=20)),
                ("recipe_id", models.CharField(max_length=80)),
                ("recipe_version", models.CharField(max_length=40)),
                ("model_id", models.CharField(blank=True, max_length=120)),
                ("provider_model", models.CharField(blank=True, max_length=180)),
                ("prompt_snapshot", models.TextField(blank=True)),
                ("reference_snapshot", models.JSONField(blank=True, default=list)),
                ("usage_snapshot", models.JSONField(blank=True, default=dict)),
                ("cost_snapshot", models.JSONField(blank=True, default=dict)),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("clip", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="engine.sequenceclip")),
                ("generation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sequence_clip_version", to="engine.mediageneration")),
            ],
            options={"ordering": ["version_number", "created_at"]},
        ),
        migrations.AddField(
            model_name="sequenceanchor",
            name="source_clip_version",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="promoted_anchors", to="engine.sequenceclipversion"),
        ),
        migrations.AddField(
            model_name="sequenceclip",
            name="selected_version",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="engine.sequenceclipversion"),
        ),
        migrations.AddConstraint(
            model_name="sequenceanchor",
            constraint=models.UniqueConstraint(fields=("project", "position"), name="uniq_seq_anchor_pos"),
        ),
        migrations.AddConstraint(
            model_name="sequenceclip",
            constraint=models.UniqueConstraint(fields=("project", "position"), name="uniq_seq_clip_pos"),
        ),
        migrations.AddConstraint(
            model_name="sequenceclip",
            constraint=models.CheckConstraint(condition=~models.Q(("start_anchor", models.F("end_anchor"))), name="seq_clip_distinct_anchors"),
        ),
        migrations.AddConstraint(
            model_name="sequenceclipversion",
            constraint=models.UniqueConstraint(fields=("clip", "version_number"), name="uniq_seq_version_num"),
        ),
        migrations.AddConstraint(
            model_name="sequenceclipversion",
            constraint=models.CheckConstraint(condition=models.Q(("version_number__gte", 1)), name="seq_version_num_gte_1"),
        ),
        migrations.AddIndex(
            model_name="sequenceproject",
            index=models.Index(fields=["company", "status", "updated_at"], name="seq_project_company_idx"),
        ),
        migrations.AddIndex(
            model_name="sequenceanchor",
            index=models.Index(fields=["project", "locked", "position"], name="seq_anchor_project_idx"),
        ),
        migrations.AddIndex(
            model_name="sequenceclip",
            index=models.Index(fields=["project", "status", "position"], name="seq_clip_project_idx"),
        ),
        migrations.AddIndex(
            model_name="sequenceclipversion",
            index=models.Index(fields=["clip", "status", "version_number"], name="seq_version_clip_idx"),
        ),
    ]
