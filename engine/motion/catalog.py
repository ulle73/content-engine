"""One versioned catalogue shared by Django, MCP and the renderer."""

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _registry():
    items = json.loads((ROOT / "catalog.json").read_text())["items"]
    if len(items) != len({item["id"] for item in items}):
        raise RuntimeError("Duplicate motion catalogue IDs")
    return {item["id"]: item for item in items}


def catalog(query="", kind="", category=""):
    words = query.casefold().split()
    result = []
    for item in _registry().values():
        if kind and item["kind"] != kind:
            continue
        if category and item["category"] != category:
            continue
        haystack = " ".join([item["id"], item["name"], item["description"], *item["tags"]]).casefold()
        if not all(word in haystack for word in words):
            continue
        copy = dict(item)
        poster = Path(__file__).resolve().parent.parent / "static" / "motion" / "previews" / (item["id"] + ".webp")
        copy["preview"] = "/static/motion/previews/" + poster.name if poster.is_file() else None
        copy["status"] = "ready" if poster.is_file() else "candidate"
        result.append(copy)
    return result


def get_item(item_id, *, kinds=None, version=1):
    item = _registry().get(item_id)
    if not item or item["version"] != version or (kinds and item["kind"] not in kinds):
        raise ValueError("Unknown or unsupported motion catalogue item/version: " + str(item_id)[:60])
    return item


def ids(*kinds):
    return {key for key, value in _registry().items() if value["kind"] in kinds}
