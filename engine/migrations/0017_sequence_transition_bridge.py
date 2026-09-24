# Generated for Content Engine Creative Intelligence E4 on 2026-09-24

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0016_sequence_output_chain_provenance"),
    ]

    operations = [
        migrations.CreateModel(
            name="SequenceBridge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("recipe_id", models.CharField(default="scroll_transition_bridge", max_length=80)),
                ("recipe_version", models.CharField(max_length=40)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("duration_seconds_target", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("aspect_ratio", models.CharField(blank=True, max_length=20)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("review", "Review"), ("selected", "Selected"), ("approved", "Approved"), ("archived", "Archived")], default="draft", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("end_anchor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ending_bridges", to="engine.sequenceanchor")),
                ("left_clip", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_bridges", to="engine.sequenceclip")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bridges", to="engine.sequenceproject")),
                ("right_clip", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_bridges", to="engine.sequenceclip")),
                ("start_anchor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="starting_bridges", to="engine.sequenceanchor")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="SequenceBridgeVersion",
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
                ("bridge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="engine.sequencebridge")),
                ("generation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sequence_bridge_version", to="engine.mediageneration")),
            ],
            options={"ordering": ["version_number", "created_at"]},
        ),
        migrations.AddField(
            model_name="sequencebridge",
            name="selected_version",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="engine.sequencebridgeversion"),
        ),
        migrations.AddConstraint(
            model_name="sequencebridge",
            constraint=models.UniqueConstraint(fields=("project", "left_clip", "right_clip"), name="uniq_seq_bridge_pair"),
        ),
        migrations.AddConstraint(
            model_name="sequencebridge",
            constraint=models.CheckConstraint(condition=~models.Q(("left_clip", models.F("right_clip"))), name="seq_bridge_distinct_clips"),
        ),
        migrations.AddConstraint(
            model_name="sequencebridge",
            constraint=models.CheckConstraint(condition=~models.Q(("start_anchor", models.F("end_anchor"))), name="seq_bridge_distinct_anchors"),
        ),
        migrations.AddConstraint(
            model_name="sequencebridgeversion",
            constraint=models.UniqueConstraint(fields=("bridge", "version_number"), name="uniq_seq_bridge_ver_num"),
        ),
        migrations.AddConstraint(
            model_name="sequencebridgeversion",
            constraint=models.CheckConstraint(condition=models.Q(("version_number__gte", 1)), name="seq_bridge_ver_num_gte_1"),
        ),
        migrations.AddIndex(
            model_name="sequencebridge",
            index=models.Index(fields=["project", "status"], name="seq_bridge_project_idx"),
        ),
        migrations.AddIndex(
            model_name="sequencebridgeversion",
            index=models.Index(fields=["bridge", "status", "version_number"], name="seq_bridge_ver_idx"),
        ),
    ]
