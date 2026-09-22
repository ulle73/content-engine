# Generated for the Content Engine MCP operator bridge.
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("engine", "0012_remove_ownsnapshot_unique_own_snapshot_day_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RunState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision", models.PositiveIntegerField(default=0)),
                ("delivery_mode", models.CharField(blank=True, default="", max_length=10)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("synced_hash", models.CharField(blank=True, default="", max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="operator_state", to="engine.contentrun")),
            ],
        ),
        migrations.CreateModel(
            name="MediaProvenance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=30)),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="operator_provenance", to="engine.mediaasset")),
            ],
        ),
        migrations.CreateModel(
            name="OperatorAction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=60)),
                ("key", models.CharField(max_length=128)),
                ("request_hash", models.CharField(max_length=64)),
                ("status", models.CharField(default="started", max_length=20)),
                ("result", models.JSONField(default=dict)),
                ("error", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="operator_actions", to="engine.company")),
                ("run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="operator_actions", to="engine.contentrun")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [models.Index(fields=["company", "status", "created_at"], name="operator_action_status_idx")],
                "constraints": [models.UniqueConstraint(fields=("company", "key"), name="unique_operator_action_company_key")],
            },
        ),
    ]
