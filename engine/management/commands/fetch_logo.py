from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from engine.branding import fetch_logo, replace_logo
from engine.media_storage import MediaError
from engine.models import Company


class Command(BaseCommand):
    help = "Find the company's logo on its own website (or take --url), download it and make it the official logo."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True)
        parser.add_argument("--url", default="", help="Logo file to use instead of searching the website.")
        parser.add_argument("--file", default="", help="Logo file in the repo (e.g. library/brands/faiv/logo.png).")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, **options):
        company = Company.objects.filter(name__iexact=options["company"]).first()
        if not company:
            raise CommandError(f"Hittar inget bolag: {options['company']}")
        if options["file"]:
            path = (settings.ENGINE_ROOT / options["file"]).resolve()
            if not path.is_file() or settings.ENGINE_ROOT.resolve() not in path.parents:
                raise CommandError(f"Hittar ingen loggfil i repot: {options['file']}")
            try:
                asset = None if options["dry_run"] else replace_logo(company, path.read_bytes(), path.name)
            except MediaError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(f"Officiell logga satt från {options['file']}"
                              + (f", asset {asset.pk}" if asset else " (dry run)") + ".")
            return
        try:
            result = fetch_logo(company, options["url"] or None, dry_run=options["dry_run"])
        except MediaError as exc:
            raise CommandError(str(exc)) from exc
        for c in result["candidates"]:
            self.stdout.write(f"  kandidat {c['score']:+.0f}: {c['url']} ({c['why'] or '–'})")
        done = "Skulle använda" if options["dry_run"] else "Officiell logga satt från"
        self.stdout.write(f"{done} {result['url']} ({result['width']}×{result['height']} px)"
                          + (f", asset {result['asset'].pk}" if result["asset"] else "") + ".")
        if result["warning"]:
            self.stdout.write(f"Obs: {result['warning']}")
