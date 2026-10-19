# Additive company-scoped overlay to the existing Content Library.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("engine", "0041_batch_runs_share_actor_run_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TechniqueImport",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("source_url", models.URLField(max_length=2000)),
                ("source_kind", models.CharField(max_length=10, choices=[("page", "Webbsida"), ("video", "Video")])),
                ("source_title", models.CharField(max_length=300, blank=True)),
                ("suggestions", models.JSONField(default=list)),
                ("status", models.CharField(max_length=12, default="review", choices=[("review", "Granskas"), ("approved", "Godkänd")])),
                ("approved_indices", models.JSONField(default=list)),
                ("analysis_cost_usd", models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(null=True, blank=True)),
                ("author", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
                ("company", models.ForeignKey(to="engine.company", on_delete=django.db.models.deletion.CASCADE, related_name="technique_imports")),
                ("reference", models.ForeignKey(to="engine.referencevideo", null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="StoredTechnique",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("key", models.SlugField(max_length=120)),
                ("data", models.JSONField(default=dict)),
                ("approved_at", models.DateTimeField(auto_now_add=True)),
                ("approved_by", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
                ("batch", models.ForeignKey(to="engine.techniqueimport", on_delete=django.db.models.deletion.PROTECT, related_name="saved")),
                ("company", models.ForeignKey(to="engine.company", on_delete=django.db.models.deletion.CASCADE, related_name="stored_techniques")),
            ],
            options={"ordering": ["-approved_at"]},
        ),
        migrations.AddConstraint(
            model_name="techniqueimport",
            constraint=models.UniqueConstraint(fields=("company", "source_url"), name="unique_company_technique_source"),
        ),
        migrations.AddConstraint(
            model_name="storedtechnique",
            constraint=models.UniqueConstraint(fields=("company", "key"), name="unique_company_technique_key"),
        ),
    ]
