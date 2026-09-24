# Generated for Content Engine Creative Intelligence E3 on 2026-09-24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0015_sequence_engine_e1"),
    ]

    operations = [
        migrations.AddField(
            model_name="sequenceanchor",
            name="source_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="sequenceanchor",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("existing", "Existing asset"),
                    ("uploaded", "Uploaded"),
                    ("generated", "Generated"),
                    ("clip_frame", "Clip frame"),
                    ("output_chain", "Output chain"),
                ],
                default="existing",
                max_length=20,
            ),
        ),
    ]
