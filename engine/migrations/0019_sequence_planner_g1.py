# Generated for Content Engine Creative Intelligence G1 on 2026-09-24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0018_sequence_anchor_controls_f2"),
    ]

    operations = [
        migrations.AddField(
            model_name="sequenceproject",
            name="plan",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sequenceproject",
            name="plan_generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sequenceproject",
            name="plan_revision",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="sequenceproject",
            name="plan_usage",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
