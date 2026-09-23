# Generated for Creative Intelligence C1 on 2026-09-23

import django.db.models.deletion
from django.db import migrations, models


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
                            ("START_IMAGE", "Start Image"),
                            ("END_IMAGE", "End Image"),
                            ("PRODUCT_REFERENCE", "Product Reference"),
                            ("CHARACTER_REFERENCE", "Character Reference"),
                            ("LOCATION_REFERENCE", "Location Reference"),
                            ("STYLE_REFERENCE", "Style Reference"),
                            ("VIDEO_REFERENCE", "Video Reference"),
                            ("AUDIO_REFERENCE", "Audio Reference"),
                        ],
                        max_length=40,
                    ),
                ),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
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
                fields=("generation", "role", "position"),
                name="unique_generation_ref_position",
            ),
        ),
        migrations.AddConstraint(
            model_name="mediagenerationreference",
            constraint=models.UniqueConstraint(
                fields=("generation", "role", "asset"),
                name="unique_generation_ref_asset_role",
            ),
        ),
        migrations.AddIndex(
            model_name="mediagenerationreference",
            index=models.Index(fields=["generation", "role", "position"], name="media_ref_gen_role_idx"),
        ),
        migrations.AddIndex(
            model_name="mediagenerationreference",
            index=models.Index(fields=["asset"], name="media_ref_asset_idx"),
        ),
    ]
