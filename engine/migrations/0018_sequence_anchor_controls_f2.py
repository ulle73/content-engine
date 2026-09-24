# Generated for Content Engine Creative Intelligence F2 on 2026-09-24

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def seed_anchor_revisions(apps, schema_editor):
    Anchor = apps.get_model("engine", "SequenceAnchor")
    Revision = apps.get_model("engine", "SequenceAnchorRevision")
    for anchor in Anchor.objects.all().iterator():
        Revision.objects.create(
            anchor_id=anchor.pk,
            revision_number=1,
            asset_id=anchor.asset_id,
            source_type=anchor.source_type,
            source_clip_version_id=anchor.source_clip_version_id,
            source_metadata=anchor.source_metadata or {},
            reason="baseline",
        )


def reverse_seed_anchor_revisions(apps, schema_editor):
    Revision = apps.get_model("engine", "SequenceAnchorRevision")
    Revision.objects.filter(reason="baseline", revision_number=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("engine", "0017_sequence_transition_bridge"),
    ]

    operations = [
        migrations.CreateModel(
            name="SequenceAnchorRevision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("revision_number", models.PositiveIntegerField()),
                ("source_type", models.CharField(choices=[("existing", "Existing asset"), ("uploaded", "Uploaded"), ("generated", "Generated"), ("clip_frame", "Clip frame"), ("output_chain", "Output chain")], default="existing", max_length=20)),
                ("source_metadata", models.JSONField(blank=True, default=dict)),
                ("reason", models.CharField(default="created", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("anchor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisions", to="engine.sequenceanchor")),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sequence_anchor_revisions", to="engine.mediaasset")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("source_clip_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anchor_revisions", to="engine.sequenceclipversion")),
            ],
            options={"ordering": ["revision_number", "created_at"]},
        ),
        migrations.AddConstraint(
            model_name="sequenceanchorrevision",
            constraint=models.UniqueConstraint(fields=("anchor", "revision_number"), name="uniq_seq_anchor_revision"),
        ),
        migrations.AddConstraint(
            model_name="sequenceanchorrevision",
            constraint=models.CheckConstraint(condition=models.Q(("revision_number__gte", 1)), name="seq_anchor_revision_gte_1"),
        ),
        migrations.AddIndex(
            model_name="sequenceanchorrevision",
            index=models.Index(fields=["anchor", "revision_number"], name="seq_anchor_revision_idx"),
        ),
        migrations.CreateModel(
            name="SequenceAnchorGenerationTarget",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("mode", models.CharField(choices=[("create", "Create anchor"), ("replace", "Replace anchor")], max_length=12)),
                ("target_label", models.CharField(blank=True, max_length=120)),
                ("target_role", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("applied_anchor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applied_generation_targets", to="engine.sequenceanchor")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("generation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sequence_anchor_target", to="engine.mediageneration")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="anchor_generation_targets", to="engine.sequenceproject")),
                ("target_anchor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generation_targets", to="engine.sequenceanchor")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="sequenceanchorgenerationtarget",
            index=models.Index(fields=["project", "mode", "created_at"], name="seq_anchor_gen_target_idx"),
        ),
        migrations.AlterField(
            model_name="sequenceclipversion",
            name="status",
            field=models.CharField(choices=[("queued", "Queued"), ("ready", "Ready"), ("selected", "Selected"), ("rejected", "Rejected"), ("failed", "Failed"), ("stale", "Stale")], default="queued", max_length=20),
        ),
        migrations.AlterField(
            model_name="sequencebridgeversion",
            name="status",
            field=models.CharField(choices=[("queued", "Queued"), ("ready", "Ready"), ("selected", "Selected"), ("rejected", "Rejected"), ("failed", "Failed"), ("stale", "Stale")], default="queued", max_length=20),
        ),
        migrations.RunPython(seed_anchor_revisions, reverse_seed_anchor_revisions),
    ]
