"""Production recipes (library/recipes, schema recipe/v1) and model playbooks (library/models)."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from .ad_studio import library

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ROOT / "library" / "recipes"
MODELS = ROOT / "library" / "models"


def _build_catalog():
    spec = importlib.util.spec_from_file_location("build_catalog", ROOT / "library" / "tools" / "build_catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_catalog = _build_catalog()


def recipe_files():
    return sorted(RECIPES.glob("*/recipe.json"))


class RecipeSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.problems = build_catalog.load_manifests()
        cls.catalog = {item["id"]: item for item in cls.items}
        cls.footage = build_catalog.footage_ids()
        cls.models = build_catalog.model_ids()

    def validate(self, data):
        return build_catalog.validate_recipe(data, catalog=self.catalog, footage=self.footage, models=self.models)

    def test_library_has_no_problems(self):
        self.assertEqual(self.problems, [])

    def test_six_recipes_per_company(self):
        companies = [json.loads(p.read_text(encoding="utf-8"))["company"] for p in recipe_files()]
        self.assertGreaterEqual(companies.count("faiv"), 6)
        self.assertGreaterEqual(companies.count("golfkuponger"), 6)

    def test_every_recipe_validates(self):
        for path in recipe_files():
            with self.subTest(recipe=path.parent.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(self.validate(data), [])
                self.assertEqual(list(data), list(build_catalog.RECIPE_KEYS))
                for scene in data["scenes"]:
                    self.assertEqual(list(scene), list(build_catalog.SCENE_KEYS))
                self.assertTrue((path.parent / "RECIPE.md").exists())

    def test_playbooks_exist_for_required_models(self):
        self.assertTrue({"kling", "seedance", "veo-3.1", "gpt-image-2"} <= self.models)
        self.assertTrue((MODELS / "README.md").exists())

    def sample(self):
        return json.loads((RECIPES / "faiv-dark-to-light-reveal" / "recipe.json").read_text(encoding="utf-8"))

    def test_rejects_unknown_ids(self):
        data = self.sample()
        scene = data["scenes"][0]
        scene["footage_ids"] = ["fa-zz9"]
        scene["effects"] = ["finns.inte"]
        scene["transition_in"] = "hyperframes.registry.grain-overlay"  # an effect, not a transition
        scene["ai_upgrade"] = {"model": "sora", "prompt_template": "x"}
        problems = "\n".join(self.validate(data))
        self.assertIn("fa-zz9", problems)
        self.assertIn("finns.inte", problems)
        self.assertIn("transition_in", problems)
        self.assertIn("sora", problems)

    def test_rejects_schema_drift(self):
        data = self.sample()
        data["extra"] = 1
        self.assertIn("okända fält", "\n".join(self.validate(data)))
        data = self.sample()
        del data["scenes"][0]["camera"]
        self.assertIn("saknar camera", "\n".join(self.validate(data)))
        data = self.sample()
        data["duration_s"] = 30
        self.assertIn("duration_s", "\n".join(self.validate(data)))

    def test_rejects_paid_ai_as_primary_source_and_unknown_facts(self):
        data = self.sample()
        data["scenes"][0]["source"] = "ai_video"
        data["scenes"][1]["text"] = "{fact:F99}"
        problems = "\n".join(self.validate(data))
        self.assertIn("ai_video", problems)
        self.assertIn("F99", problems)

    def test_product_image_requires_catalog_query(self):
        data = copy.deepcopy(self.sample())
        data["scenes"][0].update(source="product_image", footage_ids=[], catalog_query=None)
        self.assertIn("catalog_query", "\n".join(self.validate(data)))


class RecipeSearchTests(unittest.TestCase):
    def setUp(self):
        library._load.cache_clear()

    def test_search_finds_every_recipe(self):
        ids = {f"recipe.{p.parent.name}" for p in recipe_files()}
        found = {r["id"] for r in library.search("", type="recipe", limit=50)["results"]}
        self.assertEqual(found, ids)

    def test_search_ranks_by_company_and_idea(self):
        result = library.search("mörker ljus grillkit", type="recipe")["results"]
        self.assertEqual(result[0]["id"], "recipe.faiv-dark-to-light-reveal")
        self.assertEqual(result[0]["company"], "faiv")
        golf = library.search("golfkuponger sketch karaktär", type="recipe")["results"]
        self.assertEqual(golf[0]["id"], "recipe.gk-recurring-character-sketch")

    def test_models_are_searchable(self):
        ids = {r["id"] for r in library.search("", type="model", limit=50)["results"]}
        self.assertTrue({"model.kling", "model.seedance", "model.veo-3.1", "model.gpt-image-2"} <= ids)

    def test_get_recipe_includes_full_document(self):
        item = library.get("recipe.gk-pov-hr-mail")
        self.assertEqual(item["recipe"]["schema"], "recipe/v1")
        self.assertEqual(item["recipe"]["id"], "gk-pov-hr-mail")
        self.assertNotIn("recipe", library.get("model.kling"))


if __name__ == "__main__":
    unittest.main()
