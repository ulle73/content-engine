"""Local planning hints; the authenticated provider estimate remains authoritative."""
import os
from decimal import Decimal, InvalidOperation

SEEDANCE_25_PRICE_SOURCE = "higgsfield-account-estimate-2026-09-29"
SEEDANCE_25_USD_PER_SECOND = {
    "480p": Decimal("0.2056"),
    "720p": Decimal("0.4622"),
}


def cost_ceiling():
    try:
        ceiling = Decimal(os.environ.get("HIGGSFIELD_MAX_USD", "2"))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Serverns videokostnadsgräns är ogiltig. Ingen generation startades.") from exc
    if not ceiling.is_finite() or ceiling < 0:
        raise ValueError("Serverns videokostnadsgräns är ogiltig. Ingen generation startades.")
    return ceiling


def known_video_cost(model_id, duration, resolution):
    if model_id != "bytedance/seedance-2.5":
        return None
    rate = SEEDANCE_25_USD_PER_SECOND.get(resolution)
    return (Decimal(duration) * rate).quantize(Decimal("0.0001")) if rate is not None else None


def video_resolution(model_id, duration, requested, resolutions):
    """Preserve explicit choices; adapt Auto only where a local price is known."""
    ceiling = cost_ceiling()
    preferred = "720p" if "720p" in resolutions else (resolutions[0] if resolutions else "")
    choices = [requested] if requested != "auto" else list(dict.fromkeys([preferred, *resolutions]))
    for resolution in choices:
        price = known_video_cost(model_id, duration, resolution)
        if price is None or price <= ceiling:
            return resolution
    raise ValueError(
        "Videons längd och upplösning överskrider serverns kostnadsgräns för denna modell. "
        "Välj kortare video, lägre upplösning eller en annan modell. Ingen generation startades."
    )
