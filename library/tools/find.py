"""Search the content library.

Usage:
  python library/tools/find.py "premium golf reel ljusläcka" [--type template] [--format 9:16]
                               [--medium video] [--kit nextphase] [--verified] [--limit 15] [--json]

Ranks entries in library/catalog.json by how well the words match name, tags, description,
kit and `use`; verified entries and entries with a preview rank higher.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1]


def tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^\wåäöÅÄÖ:+-]+", text.lower()) if len(t) > 1]


def score(item: dict, words: list[str]) -> float:
    fields = {
        "name": (item.get("name", ""), 4.0),
        "tags": (" ".join(item.get("tags", [])), 3.0),
        "id": (item.get("id", ""), 2.0),
        "type": (item.get("type", ""), 2.0),
        "description": (item.get("description", ""), 1.5),
        "kit": (item.get("kit", ""), 1.0),
        "use": (item.get("use", ""), 0.5),
        "notes": (item.get("notes", ""), 0.3),
    }
    total = 0.0
    for word in words:
        for text, weight in fields.values():
            low = text.lower()
            if word in tokens(low):
                total += weight
            elif word in low:
                total += weight * 0.5
    if not words:
        total = 1.0
    if total == 0:
        return 0.0
    if item.get("status") == "verified":
        total *= 1.6
    elif item.get("status") == "broken":
        total *= 0.2
    if item.get("preview"):
        total *= 1.2
    if item.get("cost") == "paid":
        total *= 0.8
    return total


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--type")
    parser.add_argument("--format")
    parser.add_argument("--medium")
    parser.add_argument("--kit")
    parser.add_argument("--verified", action="store_true")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    catalog_path = LIBRARY / "catalog.json"
    if not catalog_path.exists():
        print("library/catalog.json saknas – kör: python library/tools/build_catalog.py", file=sys.stderr)
        return 1
    items = json.loads(catalog_path.read_text(encoding="utf-8"))["items"]
    words = tokens(args.query)

    def keep(item: dict) -> bool:
        if args.type and item["type"] != args.type:
            return False
        if args.medium and item["medium"] != args.medium:
            return False
        if args.kit and item["kit"] != args.kit:
            return False
        if args.format and args.format not in item["formats"] and "any" not in item["formats"]:
            return False
        if args.verified and item["status"] != "verified":
            return False
        return True

    ranked = sorted(((score(i, words), i) for i in items if keep(i)), key=lambda p: -p[0])
    hits = [i for s, i in ranked if s > 0][: args.limit]

    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return 0
    if not hits:
        print("Inga träffar. Prova färre/andra ord eller ta bort filter.")
        return 0
    for item in hits:
        preview = (item.get("preview") or {})
        shown = preview.get("video") or preview.get("still") or "–"
        flags = item["status"] + (" · betald" if item.get("cost") == "paid" else "")
        print(f"{item['id']}  [{item['type']} · {item['engine']} · {'/'.join(item['formats'])} · {flags}]")
        print(f"    {item['name']}: {item['description']}")
        if item.get("use"):
            print(f"    använd: {item['use']}")
        print(f"    fil: {item['path']}   förhandsvisning: {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
