import uuid

from django.core.management.base import BaseCommand, CommandError

from engine import product_catalog
from engine.models import Company


class Command(BaseCommand):
    help = "Sync product data and image URLs from each company's own webshop (no image downloads)."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Company id or name; default every company with a brand kit URL.")

    def handle(self, **options):
        companies = Company.objects.all()
        if options["company"]:
            ref = options["company"]
            try:
                companies = companies.filter(pk=uuid.UUID(ref))
            except ValueError:
                companies = companies.filter(name__iexact=ref)
            if not companies:
                raise CommandError(f"Hittar inget bolag: {ref}")
        failed = 0
        for company in companies:
            try:
                result = product_catalog.sync(company)
            except product_catalog.CatalogError as exc:
                if options["company"]:
                    raise CommandError(f"{company.name}: {exc}") from exc
                self.stdout.write(f"{company.name}: hoppar över ({exc})")
                failed += 1
                continue
            self.stdout.write(f"{company.name}: {result['products']} produkter, {result['image_urls']} bilder ({result['source']})")
        if failed and failed == len(companies):
            self.stdout.write("Inga produkter synkades.")
