from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .edit import outros, service
from .edit import spec as cut_spec
from .media import store_asset
from .models import Company
from .motion import brand
from .test_edit import picture


class BrandOutroTests(TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        override = override_settings(MEDIA_ROOT=Path(tmp.name))
        override.enable()
        self.addCleanup(override.disable)
        user = get_user_model().objects.create_user("owner", password="x")
        self.gk = Company.objects.create(owner=user, name="Golfkuponger")
        self.faiv = Company.objects.create(owner=user, name="FAIV", brand={"accent": "#ff1a1a"})

    def spec(self, company, fmt="9:16"):
        still = store_asset(company, picture())
        return {"schema": "cut/v1", "format": fmt, "fps": 30, "title": "Test", "caption": "",
                "scenes": [{"id": "s1", "purpose": "hook", "duration_s": 2.0, "asset_id": str(still.pk), "text": "Hej"}],
                "cta": {"text": "Köp", "url": "https://golfkuponger.se"}}

    def test_golfkuponger_gets_spotlight_outro_instead_of_cta_in_every_format(self):
        self.assertEqual(outros.available("golfkuponger"), ["spotlight"])
        for fmt in ("9:16", "4:5", "1:1"):
            spec, warnings = cut_spec.validate(self.gk, self.spec(self.gk, fmt))
            self.assertEqual(spec["outro"]["id"], "outro.golfkuponger.spotlight")
            self.assertTrue((outros.ROOT.parent / spec["outro"]["file"]).is_file())
            self.assertIsNone(spec["cta"])
            self.assertEqual(spec["duration_s"], 5.1)
            self.assertIn("ersätts av bolagets slutbild", " ".join(warnings))
        manifest = service.build_manifest(spec)
        self.assertEqual(manifest["scenes"][-1]["items"][0]["id"], "outro.golfkuponger.spotlight")
        self.assertEqual((manifest["scenes"][-1]["start"], manifest["duration_s"]), (2.0, 5.1))

    def test_no_outro_for_other_brands_formats_or_when_switched_off(self):
        spec, _ = cut_spec.validate(self.faiv, self.spec(self.faiv))
        self.assertIsNone(spec["outro"])
        self.assertEqual(spec["cta"]["text"], "Köp")
        spec, _ = cut_spec.validate(self.gk, self.spec(self.gk, "16:9"))  # no 16:9 file yet
        self.assertIsNone(spec["outro"])
        self.gk.brand = {"outro": "none"}
        self.assertIsNone(outros.outro_for(self.gk, "9:16"))

    def test_brand_kit_validates_outro(self):
        self.assertEqual(brand.clean_kit({"outro": "spotlight"}), {"outro": "spotlight"})
        with self.assertRaises(ValueError):
            brand.clean_kit({"outro": "../hack"})
