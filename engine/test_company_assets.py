"""Logo from the company's own website, and importing the company's own film/photos into the media bank."""

import io
from unittest import mock

import httpx
from django.core.management import call_command
from django.core.management.base import CommandError
from PIL import Image

from . import branding
from .models import MediaAsset
from .test_edit import EditTestCase, movie

# The FAIV homepage as it looked on 2026-10-12: the header logo, then supplier logos further down.
PAGE = (
    '<html><head><link rel="icon" href="https://faiv.se/wp-content/uploads/2022/05/favicon.png"></head><body>'
    '<header><img src="https://faiv.se/wp-content/uploads/2022/04/faiv-logotype.png" width="149" height="48" '
    'alt="FAIV - Vi bygger din bil" id="logo" data-height-percentage="54" /></header>'
    + "<p>Extraljus och inredning.</p>" * 60
    + '<img loading="lazy" width="300" height="78" src="https://faiv.se/wp-content/uploads/2022/04/osram-logo.png" '
    'alt="" title="osram logo" class="wp-image-170" />'
    '<img width="1280" height="792" src="https://faiv.se/wp-content/uploads/2025/10/fulllogo_nobuffer.png" '
    'title="fulllogo_nobuffer" class="wp-image-2199" />'
    '<img src="https://cdn.example.com/partner-logo.png" alt="partner logo" />'
    "</body></html>"
)


def png(width=149, height=48, color=(0, 0, 0, 255)):
    out = io.BytesIO()
    Image.new("RGBA", (width, height), color).save(out, "PNG")
    return out.getvalue()


class CompanyAssetTests(EditTestCase):
    def setUp(self):
        super().setUp()
        self.company.brand = {**self.company.brand, "landing_url": "https://www.faiv.se"}
        self.company.save(update_fields=["brand"])
        self.requests = []

    def client_for(self, routes):
        def handler(request):
            self.requests.append(str(request.url))
            body = routes.get(str(request.url))
            if body is None:
                return httpx.Response(404)
            return httpx.Response(200, text=body) if isinstance(body, str) else httpx.Response(200, content=body)

        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_discovers_the_header_logo_not_supplier_logos(self):
        found = branding.discover_logos(self.company, PAGE, "https://www.faiv.se")
        self.assertEqual(found[0]["url"], "https://faiv.se/wp-content/uploads/2022/04/faiv-logotype.png")
        self.assertIn("markerad som sidans logga", found[0]["why"])
        self.assertIn("bolagets namn", found[0]["why"])
        urls = [c["url"] for c in found]
        self.assertLess(next(c["score"] for c in found if "partner" in c["url"]), 0)  # other host
        osram = next(c for c in found if "osram" in c["url"])
        self.assertNotIn("bolagets namn", osram["why"])  # faiv.se is in every URL; the name must be in the file
        self.assertGreater(found[0]["score"], osram["score"])
        self.assertIn("https://faiv.se/wp-content/uploads/2022/04/osram-logo.png", urls)

    def test_fetch_logo_sets_the_official_logo_and_warns_when_small(self):
        client = self.client_for({"https://www.faiv.se/": PAGE,
                                  "https://faiv.se/wp-content/uploads/2022/04/faiv-logotype.png": png()})
        result = branding.fetch_logo(self.company, client=client)
        self.company.refresh_from_db()
        self.assertEqual(self.company.official_logo_id, result["asset"].pk)
        self.assertEqual(result["asset"].purpose, "logo")
        self.assertEqual((result["width"], result["height"]), (149, 48))
        self.assertIn("149×48", result["warning"])
        again = branding.fetch_logo(self.company, client=client)  # same bytes: the same asset, no new version
        self.assertEqual(again["asset"].pk, result["asset"].pk)
        dry = branding.fetch_logo(self.company, client=client, dry_run=True)
        self.assertIsNone(dry["asset"])

    def test_fetch_logo_errors_are_clear(self):
        from .media_storage import MediaError

        with self.assertRaisesRegex(MediaError, "Hittade ingen logga"):
            branding.fetch_logo(self.company, client=self.client_for({"https://www.faiv.se/": "<html></html>"}))
        self.company.brand = {}
        self.company.save(update_fields=["brand"])
        with self.assertRaisesRegex(MediaError, "saknar webbadress"):
            branding.fetch_logo(self.company, client=self.client_for({}))

    def test_import_media_takes_only_own_material_and_tags_it(self):
        url = "https://faiv.se/wp-content/uploads/2022/06/Faiv-film.mp4"
        with self.assertRaisesRegex(CommandError, "Bara bolagets eget material"):
            call_command("import_media", company="faiv", url="https://example.com/film.mp4", stdout=io.StringIO())
        client = self.client_for({url: movie(3.0)})
        with mock.patch("engine.management.commands.import_media.httpx.Client", return_value=client):
            call_command("import_media", company="faiv", url=url, shots="fa-v2", description="Verkstaden, Sortimo",
                         stdout=io.StringIO())
            call_command("import_media", company="faiv", url=url, shots="fa-v2", stdout=io.StringIO())  # idempotent
        assets = MediaAsset.objects.filter(company=self.company, provider="website")
        self.assertEqual(assets.count(), 1)
        asset = assets.get()
        self.assertEqual(asset.kind, "video")
        self.assertIn("fa-v2", asset.ad_tags.tags)
        self.assertIn("footage", asset.ad_tags.roles)
        self.assertEqual(self.requests.count(url), 1)

    def test_logo_from_a_repo_file(self):
        call_command("fetch_logo", company="faiv", file="library/brands/faiv/logo.png", stdout=io.StringIO())
        self.company.refresh_from_db()
        logo = self.company.official_logo
        self.assertEqual((logo.kind, logo.purpose, logo.width), ("image", "logo", 1707))
        with Image.open(io.BytesIO(branding.read_logo(logo))) as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((5, 5))[3], 0)  # the baked-in white background is gone
        with self.assertRaisesRegex(CommandError, "Hittar ingen loggfil"):
            call_command("fetch_logo", company="faiv", file="../secrets.png", stdout=io.StringIO())
