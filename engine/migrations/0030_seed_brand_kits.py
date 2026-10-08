"""Seed brand kits for Golfkuponger and FAIV when they have none. Never overwrites an existing kit."""

from django.db import migrations

KITS = {
    # golfkuponger.se theme tokens (--gk-home-deep / -green / -gold / -cream), 2026-10-09.
    "golfkuponger": {
        "background": "#01170f",
        "foreground": "#f8f4ec",
        "accent": "#d6a536",
        "muted": "#073c2b",
        "paper": "#f8f4ec",
        "ink": "#01170f",
        "font_family": "Inter, Arial, sans-serif",
        "landing_url": "https://golfkuponger.se",
        "skills": ["golfkuponger-brand", "golfkuponger-friskvard"],
        "fact_skill": "golfkuponger-friskvard",
    },
    # faiv.se colors (graphite, white, signal red), 2026-10-09.
    "faiv": {
        "background": "#2d2d2d",
        "foreground": "#ffffff",
        "accent": "#ff1a1a",
        "muted": "#4a4a4a",
        "paper": "#f4f4f4",
        "ink": "#1a1a1a",
        "font_family": "Inter, Arial, sans-serif",
        "landing_url": "https://www.faiv.se",
        "skills": ["faiv-brand", "faiv-fakta"],
        "fact_skill": "faiv-fakta",
    },
}
ALIASES = {"golfkuponger": "golfkuponger", "faiv": "faiv", "f.a.i.v": "faiv", "f.a.i.v.": "faiv",
           "fordonsanpassning i väst": "faiv", "fordonsanpassning i väst ab": "faiv"}


def seed(apps, schema_editor):
    Company = apps.get_model("engine", "Company")
    for company in Company.objects.all():
        key = ALIASES.get(company.name.strip().casefold())
        if key and not company.brand:
            company.brand = KITS[key]
            company.save(update_fields=["brand"])


class Migration(migrations.Migration):
    dependencies = [("engine", "0029_company_brand")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
