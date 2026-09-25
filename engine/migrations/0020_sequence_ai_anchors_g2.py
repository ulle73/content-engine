# Generated for Content Engine Creative Intelligence G2 on 2026-09-25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0019_sequence_planner_g1"),
    ]

    operations = [
        migrations.AddField(
            model_name="sequenceanchorgenerationtarget",
            name="plan_anchor_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sequenceanchorgenerationtarget",
            name="plan_revision",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sequenceanchorgenerationtarget",
            name="target_position",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
