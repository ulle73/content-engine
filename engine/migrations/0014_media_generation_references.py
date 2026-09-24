# Generated for Content Engine Creative Intelligence C1 on 2026-09-24

import django.db.models.deletion
from django.db import migrations, models


def backfill_start_references(apps, schema_editor):
    MediaGeneration = apps.get_model("engine", "MediaGeneration")
    MediaGenerationReference = apps.get_model("engine", "MediaGenerationReference")
    for job in MediaGeneration.objects.exclude(source_asset_id=None).select_related("source_asset").iterator():
        asset = job.source_asset
        MediaGenerationReference.objects.get_or_create(
            generation_id=job.pk,
            role="START_IMAGE",
            position=0,
            defaults={
                "asset_id": job.source_asset_id,
                "asset_snapshot": {
                    "asset_id": str(job.source_asset_id),
                    "kind": asset.kind,
                    "sha256": asset.sha256,
                },
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0013_prompt_library"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediaGenerationReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("START_IMAGE", "START_IMAGE"),
                            ("END_IMAGE", "END_IMAGE"),
                            ("PRODUCT_REFERENCE", "PRODUCT_REFERENCE"),
                            ("CHARACTER_REFERENCE", "CHARACTER_REFERENCE"),
                            ("LOCATION_REFERENCE", "LOCATION_REFERENCE"),
                            ("STYLE_REFERENCE", "STYLE_REFERENCE"),
                            ("VIDEO_REFERENCE", "VIDEO_REFERENCE"),
                            ("AUDIO_REFERENCE", "AUDIO_REFERENCE"),
                        ],
                        max_length=30,
                    ),
                ),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("asset_snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generation_references",
                        to="engine.mediaasset",
                    ),
                ),
                (
                    "generation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="references",
                        to="engine.mediageneration",
                    ),
                ),
            ],
            options={"ordering": ["role", "position", "id"]},
        ),
        migrations.AddConstraint(
            model_name="mediagenerationreference",
            constraint=models.UniqueConstraint(
                fields=("generation", "role", "position"), name="unique_generation_reference_slot"
            ),
        ),
        migrations.AddIndex(
            model_name="mediagenerationreference",
            index=models.Index(fields=["generation", "role", "position"], name="generation_reference_idx"),
        ),
        migrations.AddIndex(
            model_name="mediagenerationreference",
            index=models.Index(fields=["asset", "generation"], name="asset_generation_reference_idx"),
        ),
        migrations.RunPython(backfill_start_references, migrations.RunPython.noop),
    ]
