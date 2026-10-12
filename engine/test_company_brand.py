from django.contrib.auth import get_user_model
from django.test import TestCase

from .ad_studio import service
from .forms import BrandForm
from .models import Company
from .motion import brand


class CompanyBrandKitTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", password="x")
        self.gk = Company.objects.create(owner=self.user, name="Golfkuponger")
        self.faiv = Company.objects.create(owner=self.user, name="FAIV")

    def test_defaults_keep_existing_behaviour(self):
        self.assertEqual(brand.brand_id_for(self.gk), "golfkuponger")
        self.assertEqual(brand.brand_id_for(self.faiv), "workspace")
        self.assertEqual(brand.landing_url(self.gk), "https://golfkuponger.se")
        self.assertEqual(brand.fact_skill(self.faiv), None)

    def test_custom_kit_gets_own_id_and_tokens(self):
        self.faiv.brand = {"background": "#0a0a0a", "accent": "#ffcc00", "landing_url": "https://faiv.se"}
        self.assertEqual(brand.brand_id_for(self.faiv), "faiv")
        snap = brand.snapshot(self.faiv, "faiv")
        self.assertEqual(snap["accent"], "#ffcc00")
        self.assertEqual(snap["background"], "#0a0a0a")
        self.assertEqual(snap["foreground"], "#ffffff")
        self.assertEqual(snap["name"], "FAIV")
        self.assertEqual(brand.landing_url(self.faiv), "https://faiv.se")

    def test_cannot_use_another_companys_preset(self):
        with self.assertRaises(ValueError):
            brand.snapshot(self.faiv, "golfkuponger")
        self.assertEqual(brand.snapshot(self.faiv, "workspace")["id"], "workspace")

    def test_clean_kit_validates(self):
        self.assertEqual(brand.clean_kit({"accent": "#FFCC00", "skills": "faiv-brand, Bad Name"}),
                         {"accent": "#ffcc00", "skills": ["faiv-brand"]})
        with self.assertRaises(ValueError):
            brand.clean_kit({"accent": "gul"})
        with self.assertRaises(ValueError):
            brand.clean_kit({"landing_url": "faiv.se"})

    def test_brand_form_saves_kit(self):
        form = BrandForm({"profile": "Extraljus", "current": "Höst", "source": "faiv.se", "valid_until": "2030-01-01",
                          "brand_accent": "#ffcc00", "brand_background": "#000000", "brand_landing_url": "https://faiv.se",
                          "brand_skills": "faiv-brand"}, instance=self.faiv)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.faiv.refresh_from_db()
        # An untouched color picker (#000000) is not stored.
        self.assertEqual(self.faiv.brand, {"accent": "#ffcc00", "landing_url": "https://faiv.se", "skills": ["faiv-brand"]})

    def test_ad_brief_follows_company(self):
        self.faiv.brand = {"accent": "#ffcc00", "landing_url": "https://faiv.se"}
        self.faiv.save()
        draft = service.start_draft(self.faiv, self.user, message="Extraljus i mörkret")
        self.assertEqual(draft.brief["brand_preset"], "faiv")
        self.assertEqual(draft.brief["copy"]["landing_url"], "https://faiv.se")
        gk_draft = service.start_draft(self.gk, self.user, message="Friskvård")
        self.assertEqual(gk_draft.brief["brand_preset"], "golfkuponger")

    def test_fact_bank_seeds_only_from_company_fact_skill(self):
        self.assertEqual(service.seed_facts(self.faiv), 0)
        self.assertGreater(service.seed_facts(self.gk), 0)


class FaivSkillTests(TestCase):
    def test_faiv_fact_skill_seeds_bank(self):
        user = get_user_model().objects.create_user("owner2", password="x")
        faiv = Company.objects.create(owner=user, name="FAIV", brand={"fact_skill": "faiv-fakta", "skills": ["faiv-brand", "faiv-fakta"]})
        self.assertEqual(service.seed_facts(faiv), 10)
        self.assertTrue(faiv.ad_facts.filter(claim__icontains="grillkit").exists())
        self.assertTrue(faiv.ad_facts.filter(claim__icontains="90 km/h").exists())
        self.assertFalse(faiv.ad_facts.filter(status="verified").exists())
