from django.db import migrations


def seed_lock(apps, schema_editor):
    apps.get_model("engine", "SetupState").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("engine", "0001_initial")]
    operations = [migrations.RunPython(seed_lock, migrations.RunPython.noop)]
