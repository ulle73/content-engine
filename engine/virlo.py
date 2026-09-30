"""Virlo v1 Agents contract, verified 2026-09-23. No retry of a paid POST."""
import os
import re
from decimal import Decimal, InvalidOperation

import requests

from .apify import ApifyError


def configured():
    return bool(os.environ.get("VIRLO_API_KEY", "").strip())


def api(method, path, **kwargs):
    token = os.environ.get("VIRLO_API_KEY", "").strip()
    if not token:
        raise ApifyError("VIRLO_API_KEY saknas i serverns inställningar.")
    try:
        response = requests.request(method, "https://api.virlo.ai/v1" + path,
            headers={"Authorization": f"Bearer {token}"}, timeout=(10, 60), allow_redirects=False, **kwargs)
    except requests.RequestException:
        raise ApifyError("Virlo kunde inte bekräfta anropet.", uncertain=True) from None
    if not 200 <= response.status_code < 300:
        raise ApifyError(f"Virlo svarade HTTP {response.status_code}.",
            uncertain=response.status_code >= 500 or response.status_code < 400,
            status_code=response.status_code)
    try:
        data = response.json()["data"]
        if not isinstance(data, dict):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise ApifyError("Virlos svar hade okänt format.", uncertain=True) from None
    cost = None
    try:
        value = Decimal(response.headers.get("X-Cost", "NaN"))
        if value.is_finite() and value >= 0:
            cost = value
    except InvalidOperation:
        pass
    return data, cost


def agent_path(remote_id, suffix=""):
    if not isinstance(remote_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", remote_id):
        raise ValueError("Ogiltigt Virlo-id.")
    return f"/agents/{remote_id}{suffix}"


def rows(remote_id, suffix, key, **params):
    # Bounded sample, never an unbounded corpus download. Reads are free.
    data, _ = api("GET", agent_path(remote_id, suffix), params={"page": 1, "limit": 50, **params})
    values = data.get(key)
    if not isinstance(values, list) or any(not isinstance(row, dict) for row in values):
        raise ApifyError("Virlos resultatlista hade okänt format.", uncertain=True)
    return values[:50]
