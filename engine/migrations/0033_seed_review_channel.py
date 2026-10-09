from django.db import migrations

# Discord channel the owner chose for reviewing Golfkuponger and FAIV videos (2026-10-09). Never overwrites a value
# set in the UI.
CHANNEL = "1558018708981555230"
NAMES = {"golfkuponger", "faiv", "f.a.i.v", "f.a.i.v.", "fordonsanpassning i väst", "fordonsanpassning i väst ab"}


def seed(apps, schema_editor):
    Company = apps.get_model("engine", "Company")
    for company in Company.objects.filter(review_channel_id=""):
        if company.name.strip().casefold() in NAMES:
            company.review_channel_id = CHANNEL
            company.save(update_fields=["review_channel_id"])


class Migration(migrations.Migration):
    dependencies = [("engine", "0032_review_loop")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
