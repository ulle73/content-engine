"""Small REST adapter. Apify owns scraping and execution; this app only imports results."""

import os

import httpx

PRIMARY_ACTOR = "esdrasdw/instagram-content-scraper"
FALLBACK_ACTOR = "apify/instagram-post-scraper"
FIELDS = [
    "ownerUsername",
    "url",
    "timestamp",
    "videoPlayCount",
    "likesCount",
    "commentsCount",
    "videoDuration",
    "shortCode",
    "id",
    "caption",
    "childPosts",
    "isPinned",
    "productType",
    "type",
]


class ApifyError(Exception):
    def __init__(self, message, *, uncertain=False, status_code=None, error_type=None):
        super().__init__(message)
        self.uncertain = uncertain
        self.status_code = status_code
        self.error_type = error_type


def _clean_error_text(value):
    return " ".join(str(value or "").split())[:500]


def _error_details(response):
    try:
        payload = response.json()
    except (ValueError, TypeError):
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    if not isinstance(error, dict):
        error = {}
    return _clean_error_text(error.get("type")), _clean_error_text(error.get("message"))


def _compat_payload(path, payload):
    """Keep the importer compatible with the primary Actor's 2026 field migration."""
    if path.endswith("/records/OUTPUT") and isinstance(payload, dict):
        users = payload.get("users")
        if isinstance(users, list):
            for user in users:
                if isinstance(user, dict) and user.get("error") and not user.get("erro"):
                    user["erro"] = user["error"]
    return payload


def api(method, path, **kwargs):
    token = os.environ.get("APIFY_API_TOKEN", "")
    if not token:
        raise ApifyError("APIFY_API_TOKEN saknas i serverns miljöinställningar.")
    try:
        response = httpx.request(
            method,
            "https://api.apify.com/v2" + path,
            headers={"Authorization": "Bearer " + token},
            timeout=45,
            **kwargs,
        )
        if response.is_error:
            error_type, provider_message = _error_details(response)
            if provider_message:
                message = f"Apify: {provider_message}"
                if error_type:
                    message += f" ({error_type})"
            else:
                message = f"Apify svarade med HTTP {response.status_code}."
            raise ApifyError(
                message,
                uncertain=response.status_code >= 500,
                status_code=response.status_code,
                error_type=error_type or None,
            )
        return _compat_payload(path, response.json())
    except ApifyError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise ApifyError(
            "Apify-anropet kunde inte bekräftas. Kontrollera körningen innan nytt försök.", uncertain=True
        ) from exc


def account_summary():
    """Return only billing fields safe to show in the Content Engine UI."""
    user = api("GET", "/users/me").get("data", {})
    limits_payload = api("GET", "/users/me/limits").get("data", {})
    plan = user.get("plan") or {}
    limits = limits_payload.get("limits") or {}
    current = limits_payload.get("current") or {}
    cycle = limits_payload.get("monthlyUsageCycle") or {}

    def amount(value):
        try:
            return max(0.0, float(value or 0))
        except (TypeError, ValueError):
            return 0.0

    used = amount(current.get("monthlyUsageUsd"))
    hard_limit = amount(limits.get("maxMonthlyUsageUsd") or plan.get("maxMonthlyUsageUsd"))
    included = amount(plan.get("monthlyUsageCreditsUsd"))
    return {
        "plan": str(plan.get("id") or ""),
        "is_paying": bool(user.get("isPaying")),
        "used_usd": used,
        "hard_limit_usd": hard_limit,
        "remaining_to_limit_usd": max(0.0, hard_limit - used) if hard_limit else None,
        "included_credits_usd": included,
        "included_remaining_usd": max(0.0, included - used),
        "hard_limit_reached": bool(hard_limit and used >= hard_limit),
        "cycle_start": cycle.get("startAt"),
        "cycle_end": cycle.get("endAt"),
    }


def instagram_input(username, actor, limit):
    return (
        {
            "directUrls": [username],
            "resultsType": "posts",
            "resultsLimit": limit,
            "selectedFields": FIELDS,
        }
        if actor == PRIMARY_ACTOR
        else {"username": [username], "resultsLimit": limit}
    )


def start_actor(username, actor=PRIMARY_ACTOR, limit=100, *, inputs=None):
    return api(
        "POST", f"/acts/{actor.replace('/', '~')}/runs", json=inputs if inputs is not None else instagram_input(username, actor, limit),
        params={"timeout": 300, "maxTotalChargeUsd": 0.05 if actor == PRIMARY_ACTOR else 0.25}
    )["data"]


def get_run(run_id):
    return api("GET", f"/actor-runs/{run_id}")["data"]


def _legacy_instagram_aliases(row):
    if not isinstance(row, dict) or not row.get("ownerUsername") or not row.get("url"):
        return row
    aliased = dict(row)
    mapping = {
        "usuario": "ownerUsername",
        "link_post": "url",
        "data_criacao_iso": "timestamp",
        "visualizacoes": "videoPlayCount",
        "curtidas": "likesCount",
        "comentarios": "commentsCount",
        "duracao": "videoDuration",
        "codigo": "shortCode",
        "itens_carrossel": "childPosts",
        "fixado": "isPinned",
        "product_type": "productType",
        "media_type": "type",
    }
    for old, new in mapping.items():
        if old not in aliased and new in aliased:
            aliased[old] = aliased[new]
    return aliased


def dataset_items(dataset_id, max_items=101):
    # Inputs cap each profile at 100 items. Paginate so API defaults cannot silently truncate a run.
    rows = []
    while True:
        limit = min(250, max_items-len(rows))
        page = api("GET", f"/datasets/{dataset_id}/items", params={"offset": len(rows), "limit": limit, "clean": "true"})
        if not isinstance(page, list):
            raise ApifyError("Apify gav ett oväntat datasetformat.")
        rows.extend(_legacy_instagram_aliases(row) for row in page)
        if len(page) < limit or len(rows) >= max_items:
            return rows
