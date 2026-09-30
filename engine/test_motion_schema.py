"""Executable MotionSpec contract; no network, DB, or renderer required."""

import copy
import importlib.util
import unittest


class MotionContractTests(unittest.TestCase):
    def test_contract_module_exists(self):
        self.assertIsNotNone(
            importlib.util.find_spec("engine.motion.schema"), "versioned MotionSpec is not implemented"
        )

    def spec(self):
        return {
            "version": 1,
            "template_id": "monthly-wrapped",
            "template_version": 1,
            "aspect_ratio": "9:16",
            "fps": 30,
            "seed": 42,
            "brand_id": "golfkuponger",
            "scenes": [
                {
                    "id": "intro",
                    "component": "hero",
                    "duration_frames": 90,
                    "props": {"headline": "September"},
                    "background": "solid",
                    "transition": "cut",
                    "transition_frames": 0,
                    "effects": [],
                }
            ],
            "audio": {
                "enabled": True,
                "gain": 0.7,
                "music": "bed",
                "music_asset_id": None,
                "fade_frames": 15,
                "ducking": 0.3,
            },
            "end_card_asset_id": None,
        }

    def validate(self, data):
        from engine.motion.schema import validate_spec

        return validate_spec(data)

    def test_valid_spec_canonical_hash_and_ids(self):
        from engine.motion.schema import spec_hash

        a = self.validate(self.spec())
        b = self.validate(copy.deepcopy(self.spec()))
        self.assertEqual(spec_hash(a), spec_hash(b))
        self.assertEqual(a["scenes"][0]["id"], "intro")

    def test_closed_schema(self):
        for key, value in [("imports", ["os"]), ("code", "process.exit()"), ("url", "http://169.254.169.254")]:
            data = self.spec()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(data)

    def test_invalid_components_and_assets(self):
        for key, value in [
            ("component", "../../evil.js"),
            ("background", "url(http://evil)"),
            ("effects", ["javascript"]),
        ]:
            data = self.spec()
            data["scenes"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(data)
        data = self.spec()
        data["scenes"][0]["props"]["asset_id"] = "https://evil/a.png"
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_no_css_or_html_interpretation(self):
        data = self.spec()
        data["scenes"][0]["props"]["headline"] = "<script>alert(1)</script>"
        self.assertEqual(self.validate(data)["scenes"][0]["props"]["headline"], data["scenes"][0]["props"]["headline"])
        data["scenes"][0]["props"]["style"] = {"background": "url(https://evil)"}
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_duplicate_ids_rejected(self):
        data = self.spec()
        data["scenes"].append(copy.deepcopy(data["scenes"][0]))
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_bounds_and_nonfinite(self):
        for field, value in [("fps", 0), ("fps", True), ("aspect_ratio", "21:9"), ("seed", -1), ("version", 999)]:
            data = self.spec()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.validate(data)
        for frames in [-1, 0, 1, 7201]:
            data = self.spec()
            data["scenes"][0]["duration_frames"] = frames
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                self.validate(data)
        for value in [float("nan"), float("inf")]:
            data = self.spec()
            data["scenes"][0]["props"]["value"] = value
            with self.assertRaises(ValueError):
                self.validate(data)

    def test_first_scene_cannot_transition_from_nothing(self):
        data = self.spec()
        data["scenes"][0].update(transition="fade", transition_frames=15)
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_transition_cannot_consume_scene(self):
        data = self.spec()
        second = copy.deepcopy(data["scenes"][0])
        second.update(id="second", transition="fade", transition_frames=90)
        data["scenes"].append(second)
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_template_version_must_exist(self):
        data = self.spec()
        data["template_version"] = 100
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_max_duration(self):
        data = self.spec()
        data["scenes"] = [dict(data["scenes"][0], id=f"s{i}", duration_frames=900) for i in range(5)]
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_text_and_collection_limits(self):
        for prop, value in [("headline", "x" * 241), ("items", [{"label": "x", "value": 1}] * 13)]:
            data = self.spec()
            data["scenes"][0]["props"][prop] = value
            with self.subTest(prop=prop), self.assertRaises(ValueError):
                self.validate(data)

    def test_catalogue_ids_unique(self):
        from engine.motion.catalog import catalog

        items = catalog()
        self.assertEqual(len(items), len({x["id"] for x in items}))
        self.assertGreaterEqual(len([x for x in items if x["kind"] == "template"]), 16)
        for item in items:
            self.assertTrue(item["license"])
            self.assertTrue(item["source"])
            self.assertIn("required_props", item)
