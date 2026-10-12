import hashlib
import uuid

import httpx
from django.core.management.base import BaseCommand, CommandError

from engine.branding import _same_site, company_site
from engine.edit import footage
from engine.media import describe_file
from engine.media_storage import MediaError, put
from engine.models import Company, MediaAsset

MAX_BYTES = 200 * 1024 * 1024


class Command(BaseCommand):
    help = ("Import the company's own photo or film from its own website into the media bank and tag it with shot "
            "ids (docs/FILMLISTA.md), so recipes can use it. Idempotent per company and URL.")

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True)
        parser.add_argument("--url", required=True)
        parser.add_argument("--shots", default="", help="Shot-list ids, comma separated (e.g. fa-v2).")
        parser.add_argument("--description", default="", help="What is visible.")

    def handle(self, **options):
        company = Company.objects.filter(name__iexact=options["company"]).first()
        if not company:
            raise CommandError(f"Hittar inget bolag: {options['company']}")
        url, site = options["url"].strip(), company_site(company)
        if not site or not _same_site(url, site):
            raise CommandError(f"Bara bolagets eget material importeras: {url} ligger inte på {site or '(okänd webbplats)'}.")
        asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{company.pk}:import:{url}")
        asset = MediaAsset.objects.filter(pk=asset_id, company=company).first()
        if asset is None:
            try:
                with httpx.Client(timeout=120, follow_redirects=True) as client:
                    response = client.get(url)
            except httpx.HTTPError as exc:
                raise CommandError(f"Kunde inte hämta {url}: {exc}") from exc
            data = response.content
            if response.status_code != 200 or not data or len(data) > MAX_BYTES:
                raise CommandError(f"Kunde inte hämta {url} ({response.status_code}, {len(data)} byte).")
            try:
                metadata = describe_file(data)
            except MediaError as exc:
                raise CommandError(str(exc)) from exc
            if metadata["kind"] not in {"video", "image"}:
                raise CommandError("Bara film och bilder importeras.")
            key = f"{company.pk}/{asset_id}.{metadata.pop('extension')}"
            backend = put(key, data, metadata["mime_type"])
            asset = MediaAsset.objects.create(
                pk=asset_id, company=company, storage_backend=backend, storage_key=key, byte_size=len(data),
                origin="uploaded", provider="website", purpose="content",
                alt_text=(options["description"] or url.rsplit("/", 1)[-1])[:500],
                brief=f"Bolagets eget material från {url}"[:2000], sha256=hashlib.sha256(data).hexdigest(), **metadata)
            self.stdout.write(f"Importerade {url} → {asset.kind} {asset.pk} "
                              f"({asset.width}×{asset.height}{f', {asset.duration_seconds:.1f} s' if asset.duration_seconds else ''}).")
        else:
            self.stdout.write(f"Finns redan: {asset.pk}.")
        shots = [s for s in options["shots"].split(",") if s.strip()]
        if shots:
            try:
                tags = footage.set_tags(company, asset.pk, shots, description=options["description"])
            except footage.FootageError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(f"Taggad med {', '.join(footage.ids_of(tags.tags))}.")
