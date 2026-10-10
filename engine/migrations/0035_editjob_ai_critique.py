from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0034_edit_job'),
    ]

    operations = [
        migrations.AddField(
            model_name='editjob',
            name='ai_critique',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
