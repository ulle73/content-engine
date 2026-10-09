from django.core.management.base import BaseCommand, CommandError

from engine import product_catalog
from engine.edit.service import create_job, serialize
from engine.models import CatalogProduct, Company, MediaAsset


class Command(BaseCommand):
    help = "Cloud-edit smoke test: cut a short test video from the company's own catalog images and post it to Discord."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="Golfkuponger")
        parser.add_argument("--scenes", type=int, default=3)

    def handle(self, **options):
        company = Company.objects.filter(name__iexact=options["company"]).first()
        if not company:
            raise CommandError(f"Hittar inget bolag: {options['company']}")
        wanted = max(2, min(options["scenes"], 6))

        def products():
            return [p for p in CatalogProduct.objects.filter(company=company, active=True) if p.image_urls][:wanted]

        found = products()
        if len(found) < wanted:
            try:
                product_catalog.sync(company, page_budget=20)
            except product_catalog.CatalogError as exc:
                self.stdout.write(f"Produktkatalogen gick inte att läsa: {exc}")
            found = products()
        picked = []
        for product in found:
            assets = product_catalog.materialize(product, indexes=[0])
            if assets:
                picked.append((product.name, assets[0]))
        if len(picked) < 2:
            # Fall back to images/clips already in the media bank.
            bank = (MediaAsset.objects.filter(company=company, kind__in=["image", "video"], expires_at__isnull=True)
                    .exclude(purpose="logo").order_by("-created_at")[:wanted])
            picked = [(asset.alt_text or "Ur mediabanken", asset) for asset in bank]
            self.stdout.write(f"Använder {len(picked)} filer ur mediabanken i stället.")
        if len(picked) < 2:
            raise CommandError("Hittade färre än två bilder eller klipp att klippa (katalog och mediabank).")
        transitions = ["cut.transition.fade", "cut.transition.light-leak", "cut.transition.push",
                       "cut.transition.blur", "cut.transition.whip", "cut.transition.zoom"]
        scenes = [{
            "id": f"s{index + 1}", "purpose": "hook" if index == 0 else "proof", "duration_s": 2.5,
            "asset_id": str(asset.pk), "trim_start_s": 0.0, "fit": "cover",
            "text": "*Testklippning* i molnet" if index == 0 else name[:60],
            "text_style": "cut.text.rise", "text_position": "center", "audio": "mute",
            "effects": ["cut.effect.ken-burns"], "transition_in": None if index == 0 else transitions[index % len(transitions)],
        } for index, (name, asset) in enumerate(picked)]
        spec = {
            "schema": "cut/v1", "format": "9:16", "fps": 30, "title": "Testklippning i molnet",
            "caption": "Test av molnklippningen med bilder ur produktkatalogen. Inte för publicering.",
            "recipe_id": None, "scenes": scenes, "music_asset_id": None,
            "cta": {"text": "Testklippning klar", "url": product_catalog.shop_url(company)},
        }
        job = create_job(company, spec)
        data = serialize(job)
        self.stdout.write(f"Klippjobb {data.get('job_id', job.pk)}: {data.get('status')} ({len(scenes)} scener)")
