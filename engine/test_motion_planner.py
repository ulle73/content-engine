import unittest
from engine.motion.planner import recommend, compile_template, template_schema
from engine.motion.catalog import catalog


class PlannerTests(unittest.TestCase):
    def test_explicit_swedish_wrapped(self):
        r = recommend(
            "Skapa en 9:16 September Wrapped. 877 inl\u00f6sen. 721 515 kr totalt inl\u00f6st. Stockholm som popul\u00e4raste omr\u00e5de."
        )
        self.assertEqual(r["fields"], {"month": "September", "count": 877, "total": 721515.0, "area": "Stockholm"})
        self.assertEqual(r["missing_fields"], [])
        s = compile_template(r["template_id"], r["fields"])
        self.assertEqual(s["scenes"][1]["props"]["value"], 877)
        self.assertEqual(s["scenes"][2]["props"]["value"], 721515)
        self.assertEqual(s["scenes"][3]["props"]["items"][0]["label"], "Stockholm")

    def test_missing_data_not_invented(self):
        r = recommend("September Wrapped")
        self.assertIn("count", r["missing_fields"])
        self.assertNotIn("area", r["fields"])

    def test_templates_have_machine_readable_fields(self):
        for t in catalog(kind="template"):
            s = template_schema(t["id"])
            self.assertTrue(set(s["required"]).issubset(s["properties"]))

    def test_missing_required_field_rejected(self):
        with self.assertRaises(ValueError):
            compile_template("monthly-wrapped", {"month": "September"})

    def test_wrapped_rejects_fields_that_would_be_silently_discarded(self):
        fields = {"month": "September", "count": 0, "total": 0, "area": "Stockholm", "headline": "Custom"}
        with self.assertRaises(ValueError):
            compile_template("monthly-wrapped", fields)

    def test_injection_not_accepted_as_extra_field(self):
        with self.assertRaises(ValueError):
            compile_template("custom-storyboard", {"headline": "X", "imports": ["os"]})


    def test_friskvard_portal_ad_exact_timeline(self):
        fields = {
            "hook_asset_id": "00000000-0000-0000-0000-000000000001",
            "portal_asset_id": "00000000-0000-0000-0000-000000000002",
            "purchase_asset_id": "00000000-0000-0000-0000-000000000003",
            "app_asset_id": "00000000-0000-0000-0000-000000000004",
            "proof_asset_id": "00000000-0000-0000-0000-000000000005",
        }
        spec = compile_template("friskvard-portal-ad", fields)
        self.assertEqual(
            [scene["component"] for scene in spec["scenes"]],
            ["footage", "device", "device", "device", "footage", "end-card"],
        )
        self.assertEqual([scene["duration_frames"] for scene in spec["scenes"]], [60, 90, 90, 90, 60, 60])
        self.assertEqual(sum(scene["duration_frames"] for scene in spec["scenes"]), 15 * spec["fps"])
        self.assertEqual(spec["scenes"][0]["props"]["asset_id"], fields["hook_asset_id"])
        self.assertEqual(spec["scenes"][1]["props"]["asset_id"], fields["portal_asset_id"])
        self.assertEqual(spec["scenes"][2]["props"]["asset_id"], fields["purchase_asset_id"])
        self.assertEqual(spec["scenes"][3]["props"]["asset_id"], fields["app_asset_id"])
        self.assertEqual(spec["scenes"][4]["props"]["asset_id"], fields["proof_asset_id"])
        self.assertEqual(spec["scenes"][0]["props"]["headline"], "DITT FRISKVÅRDSBIDRAG\nBRINNER INNE 31/12")
        self.assertEqual(spec["scenes"][4]["props"]["headline"], "GOLF PÅ 300+ KLUBBAR\nHELA NÄSTA SÄSONG")

    def test_friskvard_direct_ad_exact_timeline_and_copy_override(self):
        fields = {
            "hook_asset_id": "00000000-0000-0000-0000-000000000011",
            "website_asset_id": "00000000-0000-0000-0000-000000000012",
            "receipt_asset_id": "00000000-0000-0000-0000-000000000013",
            "montage_asset_id": "00000000-0000-0000-0000-000000000014",
            "hook_text": "INGEN PORTAL?",
            "cta": "Köp på Golfkuponger.se",
        }
        spec = compile_template("friskvard-direct-ad", fields)
        self.assertEqual(
            [scene["component"] for scene in spec["scenes"]],
            ["footage", "device", "device", "footage", "end-card"],
        )
        self.assertEqual([scene["duration_frames"] for scene in spec["scenes"]], [60, 90, 90, 90, 90])
        self.assertEqual(sum(scene["duration_frames"] for scene in spec["scenes"]), 14 * spec["fps"])
        self.assertEqual(spec["scenes"][0]["props"]["headline"], "INGEN PORTAL?")
        self.assertEqual(spec["scenes"][-1]["props"]["cta"], "Köp på Golfkuponger.se")

    def test_friskvard_ad_templates_expose_only_real_asset_slots(self):
        portal = template_schema("friskvard-portal-ad")
        direct = template_schema("friskvard-direct-ad")
        self.assertEqual(
            portal["required"],
            ["hook_asset_id", "portal_asset_id", "purchase_asset_id", "app_asset_id", "proof_asset_id"],
        )
        self.assertEqual(
            direct["required"],
            ["hook_asset_id", "website_asset_id", "receipt_asset_id", "montage_asset_id"],
        )
        self.assertNotIn("headline", portal["properties"])
        self.assertNotIn("headline", direct["properties"])
