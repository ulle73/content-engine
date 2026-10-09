"""Cut spec v1: what the cloud editor should cut, scene by scene. Validated strictly, with Swedish messages.

    {"schema": "cut/v1", "format": "9:16", "fps": 30, "title": "…", "caption": "…post text…",
     "recipe_id": "faiv-dark-to-light-reveal", "brand": "faiv",
     "scenes": [{"id": "s1", "purpose": "hook", "duration_s": 2.0, "asset_id": "<MediaAsset uuid: video or image>",
                 "trim_start_s": 0.0, "fit": "cover", "text": "Kort *text*", "text_style": "<catalog text id or null>",
                 "text_position": "center", "audio": "mute",
                 "effects": ["<catalog effect ids>"], "transition_in": "<catalog transition id or null>"}],
     "music_asset_id": null, "music_volume": 1.0,
     "cta": {"text": "…", "url": "…", "duration_s": 2.5}}

Library ids are looked up in edit-renderer/support.json (what the cut template renders natively). Unknown or
unsupported ids never fail a job: they are skipped and reported as warnings.
"""

from __future__ import annotations

import json
import re
import uuid
from functools import lru_cache
from pathlib import Path

from django.utils import timezone

ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / "edit-renderer" / "support.json"
RECIPES = ROOT / "library" / "recipes"

SCHEMA = "cut/v1"
FORMATS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
FPS = {24, 25, 30, 50, 60}
MAX_TOTAL_S = 90.0
MAX_SCENES = 30
CTA_DEFAULT_S = 2.5
TOP_KEYS = {"schema", "format", "fps", "title", "caption", "recipe_id", "brand", "scenes", "music_asset_id",
            "music_volume", "cta"}
SCENE_KEYS = {"id", "purpose", "duration_s", "asset_id", "trim_start_s", "fit", "text", "text_style", "text_position",
              "audio", "effects", "transition_in"}
CTA_KEYS = {"text", "url", "duration_s"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
SCENE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
GROUP_LABEL = {"transitions": "Övergången", "effects": "Effekten", "text": "Textstilen"}


class CutSpecError(ValueError):
    pass


@lru_cache(maxsize=1)
def support() -> dict:
    """{group: {native: {"label", "ids", ...}}} plus a reverse index {group: {id: native}}."""
    data = json.loads(SUPPORT.read_text(encoding="utf-8"))
    index = {}
    for group in ("transitions", "effects", "text"):
        index[group] = {}
        for native, entry in data[group].items():
            index[group][f"cut.{_singular(group)}.{native}"] = native
            for item_id in entry["ids"]:
                index[group][item_id] = native
    data["index"] = index
    return data


def _singular(group: str) -> str:
    return {"transitions": "transition", "effects": "effect", "text": "text"}[group]


def resolve(group: str, item_id: str) -> str | None:
    """The native treatment the cut template uses for a library id, or None if it is not supported."""
    return support()["index"][group].get(item_id)


def label(group: str, item_id: str) -> str:
    native = resolve(group, item_id)
    if native:
        return support()[group][native]["label"]
    from engine.ad_studio import library

    found = next((i for i in library.items() if i["id"] == item_id), None)
    return (found or {}).get("name") or item_id


def _known_in_catalog(item_id: str) -> bool:
    from engine.ad_studio import library

    return any(i["id"] == item_id for i in library.items())


def _number(value, where, *, low, high, default=None):
    if value is None and default is not None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CutSpecError(f"{where} ska vara ett tal.")
    if not low <= float(value) <= high:
        raise CutSpecError(f"{where} ska vara mellan {low:g} och {high:g}.")
    return round(float(value), 3)


def _text(value, where, *, maximum, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise CutSpecError(f"{where} ska vara text.")
    value = value.strip()
    if required and not value:
        raise CutSpecError(f"{where} saknas.")
    if len(value) > maximum:
        raise CutSpecError(f"{where} får vara högst {maximum} tecken.")
    return value


def _unknown(data, allowed, where):
    extra = sorted(set(data) - allowed)
    if extra:
        raise CutSpecError(f"{where}: okänt fält {', '.join(extra)}. Tillåtna fält: {', '.join(sorted(allowed))}.")


def _asset(company, value, where, kinds):
    from engine.models import MediaAsset

    try:
        asset_id = uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise CutSpecError(f"{where}: asset_id ska vara ett MediaAsset-id (uuid).") from None
    asset = MediaAsset.objects.filter(pk=asset_id, company=company).first()
    if not asset:
        raise CutSpecError(f"{where}: mediefilen finns inte i bolagets mediabank.")
    if asset.kind not in kinds:
        names = {"video": "video", "image": "bild", "audio": "ljud"}
        raise CutSpecError(f"{where}: mediefilen är {names[asset.kind]}, men här krävs "
                           + " eller ".join(names[k] for k in kinds) + ".")
    if asset.expires_at and asset.expires_at <= timezone.now() and not asset.used_at:
        raise CutSpecError(f"{where}: mediefilen har gått ut. Spara den i mediabanken först.")
    return asset


def _library_id(group, value, where, warnings):
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > 200:
        raise CutSpecError(f"{where} ska vara ett biblioteks-id (text).")
    value = value.strip()
    if resolve(group, value):
        return value
    if _known_in_catalog(value):
        warnings.append(f"{where}: {GROUP_LABEL[group]} {value} stöds inte av klippmallen ännu och hoppas över.")
    else:
        warnings.append(f"{where}: {value} finns inte i biblioteket och hoppas över.")
    return value


def validate(company, raw) -> tuple[dict, list[str]]:
    """Return (normalized spec, warnings). Raises CutSpecError with a Swedish message."""
    from engine.motion import brand as brand_kit

    if not isinstance(raw, dict):
        raise CutSpecError("Klippspecen ska vara ett JSON-objekt.")
    _unknown(raw, TOP_KEYS, "Klippspecen")
    if raw.get("schema") != SCHEMA:
        raise CutSpecError(f"schema ska vara \"{SCHEMA}\".")
    warnings: list[str] = []
    fmt = raw.get("format") or "9:16"
    if fmt not in FORMATS:
        raise CutSpecError("format ska vara något av " + ", ".join(FORMATS) + ".")
    fps = raw.get("fps", 30)
    if isinstance(fps, bool) or fps not in FPS:
        raise CutSpecError("fps ska vara 24, 25, 30, 50 eller 60.")
    spec = {
        "schema": SCHEMA, "format": fmt, "fps": int(fps),
        "title": _text(raw.get("title"), "title", maximum=200, required=True),
        "caption": _text(raw.get("caption"), "caption", maximum=2200),
    }
    recipe_id = _text(raw.get("recipe_id"), "recipe_id", maximum=100)
    if recipe_id and not SLUG.match(recipe_id):
        raise CutSpecError("recipe_id ska vara ett recept-id med gemener, siffror och bindestreck.")
    if recipe_id and not (RECIPES / recipe_id).is_dir():
        warnings.append(f"Receptet {recipe_id} finns inte i library/recipes ännu; id:t sparas ändå i manifestet.")
    spec["recipe_id"] = recipe_id or None

    own_brand = brand_kit.brand_id_for(company)
    requested = _text(raw.get("brand"), "brand", maximum=60)
    if requested and requested not in {own_brand, "workspace"}:
        raise CutSpecError(f"brand \"{requested}\" hör inte till {company.name}. Använd \"{own_brand}\" eller utelämna fältet.")
    spec["brand"] = requested or own_brand

    scenes = raw.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise CutSpecError("scenes ska vara en lista med minst en scen.")
    if len(scenes) > MAX_SCENES:
        raise CutSpecError(f"Högst {MAX_SCENES} scener per video.")
    seen, out, total = set(), [], 0.0
    for index, scene in enumerate(scenes):
        where = f"Scen {index + 1}"
        if not isinstance(scene, dict):
            raise CutSpecError(f"{where} ska vara ett objekt.")
        scene_id = str(scene.get("id") or f"s{index + 1}")
        if not SCENE_ID.match(scene_id) or scene_id in seen:
            raise CutSpecError(f"{where}: id ska vara unikt och bestå av bokstäver, siffror, - eller _.")
        seen.add(scene_id)
        where = f"Scen {scene_id}"
        _unknown(scene, SCENE_KEYS, where)
        duration = _number(scene.get("duration_s"), f"{where}: duration_s", low=0.5, high=30)
        asset = _asset(company, scene.get("asset_id"), where, ("video", "image"))
        trim = _number(scene.get("trim_start_s"), f"{where}: trim_start_s", low=0, high=1200, default=0.0)
        if asset.kind == "image" and trim:
            raise CutSpecError(f"{where}: trim_start_s gäller bara video.")
        if asset.kind == "video":
            length = float(asset.duration_seconds or 0)
            if length and trim + duration > length + 0.05:
                raise CutSpecError(f"{where}: klippet är {length:.1f} s långt men scenen behöver "
                                   f"{trim:.1f}–{trim + duration:.1f} s. Korta scenen eller ändra trim_start_s.")
        fit = scene.get("fit") or "cover"
        if fit not in {"cover", "contain"}:
            raise CutSpecError(f"{where}: fit ska vara \"cover\" eller \"contain\".")
        position = scene.get("text_position")
        if position not in {None, "top", "center", "bottom"}:
            raise CutSpecError(f"{where}: text_position ska vara top, center eller bottom.")
        audio = scene.get("audio")
        if audio not in {None, "mute", "keep"}:
            raise CutSpecError(f"{where}: audio ska vara \"mute\" eller \"keep\".")
        effects = scene.get("effects") or []
        if not isinstance(effects, list) or len(effects) > 8:
            raise CutSpecError(f"{where}: effects ska vara en lista med högst 8 biblioteks-id.")
        out.append({
            "id": scene_id,
            "purpose": _text(scene.get("purpose"), f"{where}: purpose", maximum=40),
            "duration_s": duration,
            "asset_id": str(asset.pk), "asset_kind": asset.kind,
            "trim_start_s": trim, "fit": fit,
            "text": _text(scene.get("text"), f"{where}: text", maximum=200),
            "text_style": _library_id("text", scene.get("text_style"), f"{where}: text_style", warnings),
            "text_position": position,
            "audio": audio,
            "effects": [e for e in (_library_id("effects", e, f"{where}: effects", warnings) for e in effects) if e],
            "transition_in": _library_id("transitions", scene.get("transition_in"), f"{where}: transition_in", warnings),
        })
        total += duration
    if out[0]["transition_in"]:
        warnings.append(f"Scen {out[0]['id']}: transition_in på första scenen används inte.")
    spec["scenes"] = out

    music = raw.get("music_asset_id")
    spec["music_asset_id"] = str(_asset(company, music, "music_asset_id", ("audio",)).pk) if music else None
    spec["music_volume"] = _number(raw.get("music_volume"), "music_volume", low=0, high=1, default=1.0)

    cta = raw.get("cta")
    if cta is not None:
        if not isinstance(cta, dict):
            raise CutSpecError("cta ska vara ett objekt med text och url.")
        _unknown(cta, CTA_KEYS, "cta")
        url = _text(cta.get("url"), "cta.url", maximum=200)
        if url and not url.startswith(("https://", "http://")):
            raise CutSpecError("cta.url ska börja med https://")
        cta = {"text": _text(cta.get("text"), "cta.text", maximum=80, required=True), "url": url,
               "duration_s": _number(cta.get("duration_s"), "cta.duration_s", low=1, high=6, default=CTA_DEFAULT_S)}
        total += cta["duration_s"]
    spec["cta"] = cta
    if total > MAX_TOTAL_S + 1e-6:
        raise CutSpecError(f"Videon blir {total:.1f} s. Max är {MAX_TOTAL_S:.0f} s inklusive slutkortet.")
    spec["duration_s"] = round(total, 3)
    return spec, list(dict.fromkeys(warnings))


def asset_ids(spec: dict) -> list[str]:
    ids = [s["asset_id"] for s in spec["scenes"]]
    if spec.get("music_asset_id"):
        ids.append(spec["music_asset_id"])
    return list(dict.fromkeys(ids))
