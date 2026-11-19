"""Mallformatet mall/v1: läs och kontrollera library/templates/<mall>/mall.json.

Används av build_catalog.py --check (statisk kontroll) och senare av Django (engine/smsfilm/mallar.py), så att
gränserna bara finns i mall.json. Schemat ligger i library/templates/_mall/mall.schema.json; här görs dessutom
kontrollerna som ett JSON-schema inte kan uttrycka (standardvärden inom gränserna, standard_per, filer som finns,
inga bildfiler i repot).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1]
ROOT = LIBRARY.parent
TEMPLATES = LIBRARY / "templates"
SCHEMA_PATH = TEMPLATES / "_mall" / "mall.schema.json"

# Storlek per format. Samma värden som FORMATS i edit-renderer/src/safezones.js (testet jämför dem).
FORMAT_STORLEK = {"9x16": (1080, 1920), "4x5": (1080, 1350), "1x1": (1080, 1080), "16x9": (1920, 1080)}

# Bakgrunder och klipp kommer från R2 eller work/, aldrig från repot (det är publikt).
MEDIAFIL = re.compile(r"\.(jpe?g|png|webp|gif|heic|tiff?|mp4|mov|m4v|webm)$", re.IGNORECASE)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _schema_problem(data) -> list[str]:
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(_schema())
    out = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in error.absolute_path) or "(roten)"
        out.append(f"schema: {where}: {error.message}")
    return out


def _tal_ok(reglage: dict, varde, where: str) -> list[str]:
    if isinstance(varde, bool) or not isinstance(varde, (int, float)):
        return [f"{where}: ska vara ett tal, inte {varde!r}"]
    if not reglage["min"] <= varde <= reglage["max"]:
        return [f"{where}: {varde} ligger utanför {reglage['min']}–{reglage['max']}"]
    return []


def _varde_problem(reglage: dict, varde, where: str) -> list[str]:
    typ = reglage["typ"]
    if typ == "tal":
        return _tal_ok(reglage, varde, where)
    if typ == "text":
        if not isinstance(varde, str):
            return [f"{where}: ska vara text"]
        if len(varde) > reglage["max_langd"]:
            return [f"{where}: {len(varde)} tecken, högst {reglage['max_langd']}"]
        return []
    if typ in ("val", "typsnitt"):
        tillatna = [v["varde"] for v in reglage["val"]]
        return [] if varde in tillatna else [f"{where}: '{varde}' är inte ett av {tillatna}"]
    if typ == "farg":
        return [] if isinstance(varde, str) and re.fullmatch(r"#[0-9a-f]{6}", varde) else [f"{where}: '{varde}' är ingen färg (#rrggbb)"]
    if typ == "avpa":
        return [] if isinstance(varde, bool) else [f"{where}: ska vara true/false"]
    if typ == "bild":
        return [] if varde is None else [f"{where}: en bild har inget standardvärde (den laddas upp per jobb)"]
    return []


def _mediafiler(value, where: str) -> list[str]:
    if isinstance(value, str):
        return [f"{where}: pekar på en bild- eller filmfil ('{value}'); bakgrunder kommer från R2, aldrig från repot"] \
            if MEDIAFIL.search(value.strip()) else []
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in _mediafiler(v, f"{where}[{i}]")]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _mediafiler(v, f"{where}.{k}")]
    return []


def kontrollera(data, mappnamn: str | None = None, mapp: Path | None = None) -> list[str]:
    """Alla problem i en mall.json (tom lista = godkänd)."""
    problems = _schema_problem(data)
    if problems:
        return problems
    if mappnamn is not None and data["id"] != mappnamn:
        problems.append(f"id '{data['id']}' ska vara samma som mappnamnet '{mappnamn}'")
    if mapp is not None:
        for key in ("sida", "render"):
            if not (mapp / data[key]).is_file():
                problems.append(f"{key}: filen {data[key]} finns inte i mappen")
    reglage: dict[str, dict] = {}
    for i, r in enumerate(data["reglage"]):
        where = f"reglage[{i}] ({r['nyckel']})"
        if r["nyckel"] in reglage:
            problems.append(f"{where}: nyckeln finns redan")
        reglage[r["nyckel"]] = r
        if r["typ"] == "tal":
            if r["min"] >= r["max"]:
                problems.append(f"{where}: min ({r['min']}) måste vara mindre än max ({r['max']})")
                continue
            if r["steg"] > r["max"] - r["min"]:
                problems.append(f"{where}: steg ({r['steg']}) är större än spannet")
        elif any(k in r for k in ("min", "max", "steg")):
            problems.append(f"{where}: min/max/steg gäller bara typen tal")
        if r["typ"] in ("val", "typsnitt"):
            varden = [v["varde"] for v in r["val"]]
            if len(set(varden)) != len(varden):
                problems.append(f"{where}: val har dubbletter")
        elif "val" in r:
            problems.append(f"{where}: val gäller bara typerna val och typsnitt")
        if "standard" in r:
            problems += _varde_problem(r, r["standard"], f"{where} standard")
    for j, ut in enumerate(data["utdata"]):
        utanfor = [f for f in ut["format"] if f not in data["format"]]
        if utanfor:
            problems.append(f"utdata[{j}]: format {utanfor} finns inte i mallens format {data['format']}")
        if (ut["typ"] == "video") != (ut["filtyp"] == "mp4"):
            problems.append(f"utdata[{j}]: typ {ut['typ']} passar inte filtyp {ut['filtyp']}")
        if ut["typ"] == "video" and data["typ"] != "video":
            problems.append(f"utdata[{j}]: en bildmall kan inte ge video")
    for fmt, varden in (data.get("standard_per") or {}).get("format", {}).items():
        if fmt not in data["format"]:
            problems.append(f"standard_per.format.{fmt}: formatet finns inte i mallens format")
        for nyckel, varde in varden.items():
            if nyckel not in reglage:
                problems.append(f"standard_per.format.{fmt}.{nyckel}: inget reglage med den nyckeln")
            else:
                problems += _varde_problem(reglage[nyckel], varde, f"standard_per.format.{fmt}.{nyckel}")
    problems += _mediafiler({k: v for k, v in data.items() if k not in ("sida", "render")}, "mall.json")
    return problems


def alla_mallar() -> list[Path]:
    """Alla mall.json under library/templates (även testmallen i _mall/)."""
    return sorted(TEMPLATES.glob("*/mall.json")) + sorted((TEMPLATES / "_mall").glob("*/mall.json"))


def kontrollera_fil(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"ogiltig JSON ({exc})"]
    return kontrollera(data, mappnamn=path.parent.name, mapp=path.parent)


def mall_problems(items: list[dict] | None = None) -> list[str]:
    """Problem i alla mallar plus LIBRARY.json-poster vars fält 'mall' pekar fel. För build_catalog.py."""
    problems = []
    for path in alla_mallar():
        rel = path.relative_to(ROOT).as_posix()
        problems += [f"{rel}: {p}" for p in kontrollera_fil(path)]
    for item in items or []:
        if "mall" in item:
            target = ROOT / Path(item["path"]).parent / item["mall"]
            if not target.is_file():
                problems.append(f"{item['id']}: fältet mall pekar på {target.relative_to(ROOT).as_posix()}, som inte finns")
    return problems
