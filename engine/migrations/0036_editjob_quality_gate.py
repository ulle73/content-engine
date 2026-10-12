from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0035_editjob_ai_critique'),
    ]

    operations = [
        migrations.AddField(
            model_name='editjob',
            name='quality_gate',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
