"""Dashboard templates (mall/v1): which templates exist, and the server-side check of a job's values.

Every limit lives in library/templates/<mall>/mall.json (docs/designs/mallmotor.md). This module reads those files
through library/tools/mallformat.py (the same code build_catalog.py --check uses) and validates what the form sends:
unknown controls, values outside the limits and texts that are too long are rejected, not clamped. The page clamps
too, but only as a safety net.
"""

from __future__ import annotations

import importlib.util
import json
import re
import uuid
from functools import lru_cache
from pathlib import Path

from .spec import SmsFilmError

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "library" / "templates"


@lru_cache(maxsize=1)
def _mallformat():
    spec = importlib.util.spec_from_file_location("mallformat", ROOT / "library" / "tools" / "mallformat.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _alla() -> dict[str, dict]:
    """Templates shown in the dashboard: items in a LIBRARY.json with "mall": "mall.json" (the test template is not)."""
    ut = {}
    for manifest in sorted(TEMPLATES.glob("*/LIBRARY.json")):
        try:
            items = json.loads(manifest.read_text(encoding="utf-8")).get("items", [])
        except ValueError:
            continue
        for item in items:
            if item.get("mall"):
                path = manifest.parent / item["mall"]
                data = json.loads(path.read_text(encoding="utf-8"))
                if not _mallformat().kontrollera(data, mappnamn=manifest.parent.name, mapp=manifest.parent):
                    ut[data["id"]] = data
    return ut


def alla() -> dict[str, dict]:
    return _alla()


def hamta(mall_id) -> dict:
    mall = _alla().get(str(mall_id or ""))
    if mall is None:
        raise SmsFilmError("Mallen finns inte. Ladda om sidan och välj en mall.")
    return mall


def standardvarden(mall: dict, format: str, valda: dict | None = None) -> dict:
    return _mallformat().standardvarden(mall, format, valda)


def _beror_pa_format(mall: dict) -> set[str]:
    per = (mall.get("standard_per") or {}).get("format") or {}
    return {k for varden in per.values() for k in varden}


def _tal(r, x, etikett):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        try:
            x = float(x)
        except (TypeError, ValueError):
            raise SmsFilmError(f"{etikett}: ska vara ett tal.") from None
    if not r["min"] <= x <= r["max"]:
        raise SmsFilmError(f"{etikett}: {x:g} ligger utanför {r['min']:g}–{r['max']:g}.")
    return int(x) if float(x).is_integer() and float(r["steg"]).is_integer() else float(x)


def _ett(r: dict, x, images):
    etikett = r["etikett"]
    typ = r["typ"]
    if typ == "tal":
        return _tal(r, x, etikett)
    if typ == "text":
        if not isinstance(x, str):
            raise SmsFilmError(f"{etikett}: ska vara text.")
        x = x.strip()
        if len(x) > r["max_langd"]:
            raise SmsFilmError(f"{etikett}: högst {r['max_langd']} tecken.")
        if r.get("kravs") and not x:
            raise SmsFilmError(f"{etikett}: får inte vara tom.")
        return x
    if typ in ("val", "typsnitt"):
        if x not in [v["varde"] for v in r["val"]]:
            raise SmsFilmError(f"{etikett}: välj ett av alternativen.")
        return x
    if typ == "farg":
        if not isinstance(x, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", x):
            raise SmsFilmError(f"{etikett}: ogiltig färg.")
        return x.lower()
    if typ == "avpa":
        if not isinstance(x, bool):
            raise SmsFilmError(f"{etikett}: ska vara på eller av.")
        return x
    if typ == "bild":
        if not x:
            return None
        if images is None:
            raise SmsFilmError(f"{etikett}: bilden kunde inte tas emot.")
        resolved = images.path(x, etikett)
        return resolved[1]["asset"] if resolved else None
    raise SmsFilmError(f"{etikett}: okänd typ.")


def validera(mall: dict, raw, formats, *, images=None) -> tuple[dict, list[str]]:
    """The values to store on a job, and the formats to render.

    raw: {nyckel: värde} from the form. Missing controls get the template's default, frozen now (format-dependent
    defaults are left out so the page picks the right one per format). Unknown keys are rejected.
    images: a spec._Images for uploads ("bild" controls send {"file": "f1"} or {"asset": "<uuid>"}).
    """
    if not isinstance(raw, dict):
        raise SmsFilmError("Mallens värden kom inte fram. Ladda om sidan och försök igen.")
    reglage = {r["nyckel"]: r for r in mall["reglage"]}
    okanda = sorted(set(raw) - set(reglage))
    if okanda:
        raise SmsFilmError(f"Okända reglage: {', '.join(okanda)}.")
    if not isinstance(formats, list) or not formats:
        raise SmsFilmError("Välj minst ett format.")
    formats = list(dict.fromkeys(formats))
    if any(f not in mall["format"] for f in formats):
        raise SmsFilmError(f"Mallen finns bara i {', '.join(mall['format'])}.")
    varden = {k: _ett(reglage[k], x, images) for k, x in raw.items()}
    # defaults that depend on another choice (e.g. skak on effekt) follow the chosen value
    std = standardvarden(mall, formats[0], varden)
    per_format = _beror_pa_format(mall)
    for k, r in reglage.items():
        if k not in varden and k not in per_format:
            varden[k] = std.get(k)
    for k, r in reglage.items():
        if r["typ"] == "text" and r.get("kravs") and not varden.get(k):
            raise SmsFilmError(f"{r['etikett']}: får inte vara tom.")
    return varden, formats


def bild_asset_ids(mall: dict, varden: dict) -> list[str]:
    ids = []
    for r in mall["reglage"]:
        if r["typ"] == "bild" and varden.get(r["nyckel"]):
            ids.append(str(uuid.UUID(str(varden[r["nyckel"]]))))
    return ids


def utdata(mall: dict, formats: list[str]) -> list[dict]:
    """The files a job will produce: [{typ, filtyp, format, variant}] in render order (9:16 first)."""
    ut = []
    for u in mall["utdata"]:
        for f in u["format"]:
            if f in formats:
                ut.append({"typ": u["typ"], "filtyp": u["filtyp"], "format": f, "variant": u.get("variant", "")})
    return sorted(ut, key=lambda x: (x["format"] != "9x16", x["variant"]))


def for_formularet() -> list[dict]:
    """What the dashboard form needs to draw every template's controls."""
    return [{"id": m["id"], "titel": m["titel"], "beskrivning": m.get("beskrivning", ""), "typ": m["typ"],
             "sida": m["sida"], "format": m["format"], "reglage": m["reglage"],
             "standard_per": m.get("standard_per") or {}} for m in alla().values()]
