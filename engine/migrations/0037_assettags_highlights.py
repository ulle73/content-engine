from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0036_editjob_quality_gate'),
    ]

    operations = [
        migrations.AddField(
            model_name='assettags',
            name='highlights',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
