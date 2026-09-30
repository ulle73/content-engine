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

    def test_injection_not_accepted_as_extra_field(self):
        with self.assertRaises(ValueError):
            compile_template("custom-storyboard", {"headline": "X", "imports": ["os"]})
