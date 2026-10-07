import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .ad_studio import library


def entry(item_id, **overrides):
    data = {
        "id": item_id, "name": item_id, "type": "effect", "medium": "video", "formats": ["9:16"],
        "engine": "hyperframes", "description": "", "tags": [], "kit": "test", "use": "", "cost": "free",
        "requires": [], "status": "unverified", "preview": None, "path": "library/README.md", "notes": "",
    }
    data.update(overrides)
    return data


class ContentLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.catalog = Path(self.tmp.name) / "catalog.json"
        items = [
            entry("kit.leak", name="Ljusläcka", tags=["light-leak", "premium"], type="transition"),
            entry("kit.leak-verified", name="Ljusläcka guld", tags=["light-leak"], type="transition",
                  status="verified", preview={"still": "library/previews/x.jpg"}),
            entry("kit.carousel", name="Pastoral", type="carousel", medium="carousel", formats=["4:5"]),
            entry("kit.any", name="Grain", tags=["grain"], formats=["any"]),
        ]
        self.catalog.write_text(json.dumps({"items": items}), encoding="utf-8")
        patcher = mock.patch.object(library, "CATALOG", self.catalog)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        library._load.cache_clear()

    def test_verified_with_preview_ranks_first(self):
        ids = [r["id"] for r in library.search("ljusläcka")["results"]]
        self.assertEqual(ids[:2], ["kit.leak-verified", "kit.leak"])

    def test_filters_by_type_and_format(self):
        result = library.search("", type="carousel", format="4:5")
        self.assertEqual([r["id"] for r in result["results"]], ["kit.carousel"])
        any_format = library.search("grain", format="16:9")
        self.assertEqual([r["id"] for r in any_format["results"]], ["kit.any"])

    def test_verified_only(self):
        ids = [r["id"] for r in library.search("light-leak", verified_only=True)["results"]]
        self.assertEqual(ids, ["kit.leak-verified"])

    def test_get_unknown_id_raises(self):
        self.assertEqual(library.get("kit.leak")["name"], "Ljusläcka")
        with self.assertRaises(ValueError):
            library.get("finns-inte")

    def test_missing_catalog_is_empty(self):
        with mock.patch.object(library, "CATALOG", Path(self.tmp.name) / "saknas.json"):
            self.assertEqual(library.search("x")["results"], [])


if __name__ == "__main__":
    unittest.main()
