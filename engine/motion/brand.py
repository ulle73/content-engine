"""Versioned brand snapshot from existing UI tokens and company-owned logo."""

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


def snapshot(company, preset_id):
    if preset_id not in PRESETS:
        raise ValueError("Unknown brand preset")
    if preset_id == "golfkuponger" and company.name.casefold() != "golfkuponger":
        raise ValueError("Golfkuponger preset belongs to the Golfkuponger workspace")
    value = deepcopy(PRESETS[preset_id])
    value["name"] = company.name
    logo = company.official_logo
    if logo and logo.company_id != company.id:
        raise ValueError("Official logo must belong to this company")
    value["logo_asset_id"] = str(logo.id) if logo else None
    value["logo_sha256"] = logo.sha256 if logo else None
    return value
