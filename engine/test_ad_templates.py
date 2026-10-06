import json
import uuid
from pathlib import Path

from django.test import SimpleTestCase

from .ad_studio import blueprints
from .ad_studio.brief import AdBrief
from .motion.ad_templates import AD_TEMPLATES, total_seconds
from .motion.catalog import ids
from .motion.planner import compile_template, template_schema

ROOT = Path(__file__).resolve().parents[1]


def fields_for(template_id):
    schema = template_schema(template_id)
    return {name: (str(uuid.uuid4()) if name.endswith("_asset_id") else "Kort text") for name in schema["required"]}


class AdTemplateTests(SimpleTestCase):
    def test_every_ad_template_compiles_to_a_valid_spec(self):
        for template_id in AD_TEMPLATES:
            with self.subTest(template_id):
                spec = compile_template(template_id, fields_for(template_id))
                effective = sum(s["duration_frames"] - s["transition_frames"] for s in spec["scenes"]) / spec["fps"]
                self.assertEqual(effective, total_seconds(template_id))
                self.assertEqual(spec["scenes"][0]["transition"], "cut")

    def test_no_default_copy_text_is_required(self):
        for template_id in AD_TEMPLATES:
            with self.subTest(template_id):
                fields = fields_for(template_id)
                fields.pop("end_text")
                with self.assertRaises(ValueError):
                    compile_template(template_id, fields)

    def test_blueprint_matches_template_and_brief_rules(self):
        for template_id in AD_TEMPLATES:
            with self.subTest(template_id):
                bp = blueprints.blueprint(template_id)
                self.assertEqual(bp["duration_s"], total_seconds(template_id))
                self.assertEqual(bp["scenes"][0]["purpose"], "hook")
                self.assertEqual(bp["scenes"][-1]["purpose"], "cta")
                self.assertTrue(bp["tone"] and bp["when"])
                self.assertFalse(any(s["default_text_not_verified"] for s in bp["scenes"]))

    def test_locked_brief_fills_new_template(self):
        bp = blueprints.blueprint("golf-sista-chansen")
        assets = {s["id"]: str(uuid.uuid4()) for s in bp["scenes"] if s["needs_asset"]}
        brief = AdBrief.model_validate({
            "message": "x", "objective": "conversion", "audience": "x",
            "angle": {"title": "x", "hook": "x"},
            "assets": [{"asset_id": a, "role": "footage"} for a in assets.values()],
            "engine": {"engine": "remotion", "remotion_template_id": "golf-sista-chansen"},
            "duration_s": bp["duration_s"],
            "scenes": [{"id": s["id"], "purpose": s["purpose"], "duration_s": s["duration_s"], "on_screen_text": "Kort text",
                        **({"asset_id": assets[s["id"]]} if s["id"] in assets else {})} for s in bp["scenes"]],
            "copy": {"headline": "x"},
        })
        spec = blueprints.compile_brief(brief.lock())
        self.assertEqual(spec["template_id"], "golf-sista-chansen")
        self.assertEqual(spec["scenes"][0]["props"]["value"], 3)


    def test_reference_profile_flows_from_locked_brief_to_motion_spec(self):
        bp = blueprints.blueprint("golf-fracka")
        assets = {s["id"]: str(uuid.uuid4()) for s in bp["scenes"] if s["needs_asset"]}
        profile = {
            "label": "Editorial reference",
            "motion_intensity": "high",
            "camera_style": "push",
            "transition_family": "dynamic",
            "typography_behavior": "kinetic",
            "beat_density": "dense",
            "motion_preset": "snappy",
            "color_behavior": "brand",
            "bpm": 120,
        }
        brief = AdBrief.model_validate({
            "message": "x", "objective": "conversion", "audience": "x",
            "angle": {"title": "x", "hook": "x"},
            "assets": [{"asset_id": a, "role": "footage"} for a in assets.values()],
            "reference_profile": profile,
            "engine": {"engine": "remotion", "remotion_template_id": "golf-fracka"},
            "duration_s": bp["duration_s"],
            "scenes": [{
                "id": s["id"],
                "purpose": s["purpose"],
                "duration_s": s["duration_s"],
                "on_screen_text": "Kort text",
                **({"asset_id": assets[s["id"]]} if s["id"] in assets else {}),
            } for s in bp["scenes"]],
            "copy": {"headline": "x"},
        })
        spec = blueprints.compile_brief(brief.lock())
        self.assertEqual(spec["reference_profile"]["label"], "Editorial reference")
        self.assertEqual(spec["beat_map"]["source"], "profile")
        self.assertIn("snappy", {scene["motion_preset"] for scene in spec["scenes"]})

    def test_renderer_schema_knows_every_template(self):
        """The Node worker validates against spec.schema.json; a missing id makes rendering fail."""
        schema = json.loads((ROOT / "motion-renderer/spec.schema.json").read_text())
        self.assertEqual(sorted(schema["properties"]["template_id"]["enum"]), sorted(ids("template")))
        self.assertEqual(sorted(schema["$defs"]["Scene"]["properties"]["component"]["enum"]),
                         sorted(ids("text", "data", "scene")))
