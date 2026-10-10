"""The shot list (docs/FILMLISTA.md) as data: shot ids such as `fa-m1`, their text and section, and footage tags.

Own footage is matched to recipe scenes by these ids: a clip in the media bank whose AssetTags.tags contain `fa-m1`
can fill every recipe scene that asks for `fa-m1`. Ids are set with the MCP tool tag_media, in the media library
dialog, or automatically on upload when the file name contains one (e.g. `fa-m1_volvo.mp4`).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILMLISTA = ROOT / "docs" / "FILMLISTA.md"
SHOT = re.compile(r"^- `([a-z]{2}-[a-z0-9]+)`\s*(?:★\s*)?(.*)$")
IN_NAME = re.compile(r"(?<![a-z0-9])((?:gk|fa|bo)-[a-z0-9]+)(?![a-z0-9])", re.IGNORECASE)
PREFIXES = {"golfkuponger": ("gk", "bo"), "faiv": ("fa", "bo")}


class FootageError(ValueError):
    pass


@lru_cache(maxsize=4)
def _parse(mtime: float) -> dict[str, dict]:
    shots: dict[str, dict] = {}
    company = group = ""
    for line in FILMLISTA.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            company, group = line[3:].split("(")[0].strip(), ""
        elif line.startswith("**") and line.rstrip().endswith("**"):
            group = line.strip("* ").strip()
        elif match := SHOT.match(line):
            shots[match.group(1)] = {"id": match.group(1), "text": match.group(2).strip(), "company": company,
                                     "group": group, "star": "★" in line}
    return shots


def shots() -> dict[str, dict]:
    """{id: {"id", "text", "company", "group", "star"}} in shot-list order."""
    if not FILMLISTA.exists():
        return {}
    return _parse(FILMLISTA.stat().st_mtime)


def is_shot_id(value: str) -> bool:
    return value in shots()


def text(shot_id: str) -> str:
    return (shots().get(shot_id) or {}).get("text", "")


def for_company(company) -> list[dict]:
    """The shots relevant for a company (its own prefix + shared `bo-`), or all when the company is unknown."""
    from engine.motion.brand import _slug

    prefixes = PREFIXES.get(_slug(company.name)) if company is not None else None
    return [s for s in shots().values() if not prefixes or s["id"].split("-")[0] in prefixes]


def grouped(company) -> list[dict]:
    """[{"label": "FAIV · Produkt", "shots": [...]}] for pickers."""
    out: list[dict] = []
    for shot in for_company(company):
        label = " · ".join(filter(None, [shot["company"], shot["group"]]))
        if not out or out[-1]["label"] != label:
            out.append({"label": label, "shots": []})
        out[-1]["shots"].append(shot)
    return out


def clean_ids(values) -> list[str]:
    """Validate shot ids against docs/FILMLISTA.md. Raises FootageError (Swedish) listing unknown ids."""
    if isinstance(values, str):
        values = re.split(r"[\s,;]+", values)
    if not isinstance(values, (list, tuple)):
        raise FootageError("footage_ids ska vara en lista med filmlista-id, t.ex. [\"fa-m1\"].")
    ids = list(dict.fromkeys(str(v).strip().casefold() for v in values if str(v).strip()))
    unknown = [v for v in ids if not is_shot_id(v)]
    if unknown:
        raise FootageError("Okända filmlista-id: " + ", ".join(unknown) + ". Giltiga id finns i docs/FILMLISTA.md, "
                           "t.ex. fa-m1, gk-o1, bo-1.")
    if len(ids) > 12:
        raise FootageError("Högst 12 filmlista-id per fil.")
    return ids


def ids_in_filename(name: str) -> list[str]:
    """Known shot ids mentioned in a file name, e.g. "fa-m1_volvo.mp4" → ["fa-m1"]."""
    stem = Path(name or "").name.casefold()
    return list(dict.fromkeys(m for m in (x.casefold() for x in IN_NAME.findall(stem)) if is_shot_id(m)))


def ids_of(tags) -> list[str]:
    """The shot ids among an AssetTags.tags list."""
    return [t for t in (tags or []) if isinstance(t, str) and is_shot_id(t)]


def set_tags(company, asset_id, footage_ids, *, description: str = "", verified: bool = True):
    """Replace the asset's shot ids (other tags are kept) and add the footage role. Returns AssetTags."""
    from engine.ad_studio.models import AssetTags
    from engine.models import MediaAsset

    ids = clean_ids(footage_ids)
    asset = MediaAsset.objects.filter(company=company, pk=asset_id).first() if _uuid(asset_id) else None
    if asset is None:
        raise FootageError("Mediefilen finns inte i bolagets mediabank.")
    if asset.kind not in {"video", "image"}:
        raise FootageError("Bara video och bilder kan märkas med filmlista-id.")
    tags = AssetTags.objects.filter(asset=asset).first() or AssetTags(asset=asset)
    kept = [t for t in (tags.tags or []) if not is_shot_id(t)]
    tags.tags = sorted(set(kept + ids))[:30]
    roles = set(tags.roles or [])
    if ids:
        roles.add("footage")
    tags.roles = sorted(roles)
    description = (description or "").strip()
    if description:
        tags.description = description[:500]
    elif not tags.description and ids:
        tags.description = "; ".join(f"{i}: {text(i)}" for i in ids)[:500]
    tags.verified = tags.verified or verified
    tags.save()
    return tags


def _uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True
