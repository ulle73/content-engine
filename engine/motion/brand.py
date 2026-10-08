"""Versioned brand snapshot from a company's brand kit (or a built-in preset) and its own logo.

A company's brand kit lives in `Company.brand` (JSON):
  {"background": "#01170f", "foreground": "#ffffff", "accent": "#d6a536", "muted": "...", "paper": "...",
   "ink": "...", "font_family": "Inter, Arial, sans-serif", "landing_url": "https://…",
   "skills": ["golfkuponger-brand", "golfkuponger-friskvard"], "fact_skill": "golfkuponger-friskvard"}
Every key is optional. Without colors the company uses the Golfkuponger preset (if it is Golfkuponger)
or the neutral workspace preset.
"""

import re
from copy import deepcopy

# Source: engine/static/css/gk-design-system.css and app.css, not a new palette.
PRESETS = {
    "golfkuponger": {
        "id": "golfkuponger",
        "version": 1,
        "background": "#082f27",
        "foreground": "#ffffff",
        "accent": "#0f7a50",
        "muted": "#e8f7ef",
        "paper": "#f6f8f7",
        "ink": "#111814",
        "font_family": "Inter, Arial, sans-serif",
        "source": "engine/static/css/gk-design-system.css; engine/static/css/app.css",
    },
    "workspace": {
        "id": "workspace",
        "version": 1,
        "background": "#111814",
        "foreground": "#ffffff",
        "accent": "#68766f",
        "muted": "#dfe7e3",
        "paper": "#f6f8f7",
        "ink": "#111814",
        "font_family": "Inter, Arial, sans-serif",
        "source": "Content Engine neutral workspace tokens",
    },
}

COLOR_KEYS = ("background", "foreground", "accent", "muted", "paper", "ink")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
GOLFKUPONGER_DEFAULTS = {
    "landing_url": "https://golfkuponger.se",
    "skills": ["golfkuponger-brand", "golfkuponger-friskvard"],
    "fact_skill": "golfkuponger-friskvard",
}


def _is_golfkuponger(company) -> bool:
    return company.name.casefold() == "golfkuponger"


def _kit(company) -> dict:
    return company.brand if isinstance(company.brand, dict) else {}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "company"


def has_custom_tokens(company) -> bool:
    kit = _kit(company)
    return any(kit.get(key) for key in COLOR_KEYS) or bool(kit.get("font_family"))


def brand_id_for(company) -> str:
    """The brand id a company's renders should use."""
    if has_custom_tokens(company):
        return _slug(company.name)
    return "golfkuponger" if _is_golfkuponger(company) else "workspace"


def tokens_for(company) -> dict:
    brand_id = brand_id_for(company)
    if brand_id in PRESETS and not has_custom_tokens(company):
        return deepcopy(PRESETS[brand_id])
    kit = _kit(company)
    base = deepcopy(PRESETS["golfkuponger" if _is_golfkuponger(company) else "workspace"])
    for key in COLOR_KEYS:
        if HEX.match(str(kit.get(key, ""))):
            base[key] = kit[key]
    if kit.get("font_family"):
        base["font_family"] = str(kit["font_family"])[:200]
    base.update({"id": brand_id, "version": int(kit.get("version", 1)), "source": "Company brand kit"})
    return base


def landing_url(company) -> str:
    kit = _kit(company)
    return kit.get("landing_url") or (GOLFKUPONGER_DEFAULTS["landing_url"] if _is_golfkuponger(company) else "")


def skills_for(company) -> list[str]:
    kit = _kit(company)
    return list(kit.get("skills") or (GOLFKUPONGER_DEFAULTS["skills"] if _is_golfkuponger(company) else []))


def fact_skill(company) -> str | None:
    kit = _kit(company)
    return kit.get("fact_skill") or (GOLFKUPONGER_DEFAULTS["fact_skill"] if _is_golfkuponger(company) else None)


def clean_kit(data: dict) -> dict:
    """Validate a brand kit from a form or MCP. Raises ValueError with a Swedish message."""
    out = {}
    for key in COLOR_KEYS:
        value = str(data.get(key) or "").strip()
        if value:
            if not HEX.match(value):
                raise ValueError(f"{key}: ange en färg som #rrggbb.")
            out[key] = value.lower()
    if data.get("font_family"):
        out["font_family"] = str(data["font_family"]).strip()[:200]
    url = str(data.get("landing_url") or "").strip()
    if url:
        if not url.startswith(("https://", "http://")):
            raise ValueError("Webbadressen måste börja med https://")
        out["landing_url"] = url[:300]
    skills = data.get("skills")
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",")]
    if skills:
        out["skills"] = [s for s in skills if re.fullmatch(r"[a-z0-9-]{1,60}", s)]
    if data.get("fact_skill"):
        value = str(data["fact_skill"]).strip()
        if not re.fullmatch(r"[a-z0-9-]{1,60}", value):
            raise ValueError("fact_skill: ogiltigt skillnamn.")
        out["fact_skill"] = value
    return out


def snapshot(company, preset_id):
    own = brand_id_for(company)
    if preset_id == own:
        value = tokens_for(company)
    elif preset_id == "workspace":
        value = deepcopy(PRESETS["workspace"])
    elif preset_id in PRESETS:
        raise ValueError(f"Brand preset '{preset_id}' belongs to another workspace")
    else:
        raise ValueError("Unknown brand preset")
    value["name"] = company.name
    logo = company.official_logo
    if logo and logo.company_id != company.id:
        raise ValueError("Official logo must belong to this company")
    value["logo_asset_id"] = str(logo.id) if logo else None
    value["logo_sha256"] = logo.sha256 if logo else None
    return value
