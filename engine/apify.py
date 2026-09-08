"""Small REST adapter. Apify owns scraping and execution; this app only imports results."""

import os

import httpx

PRIMARY_ACTOR = "esdrasdw/instagram-content-scraper"
FALLBACK_ACTOR = "apify/instagram-post-scraper"
FIELDS = [
    "usuario",
    "link_post",
    "data_criacao_iso",
    "visualizacoes",
    "curtidas",
    "comentarios",
    "duracao",
    "codigo",
    "id",
    "caption",
    "itens_carrossel",
    "fixado",
    "autor_username",
    "product_type",
    "media_type",
]


class ApifyError(Exception):
    def __init__(self, message, *, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


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
            raise ApifyError(
                f"Apify svarade med HTTP {response.status_code}. Kontrollera kontot i Apify.",
                uncertain=response.status_code >= 500,
            )
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApifyError(
            "Apify-anropet kunde inte bekräftas. Kontrollera körningen innan nytt försök.", uncertain=True
        ) from exc


def start_actor(username, actor=PRIMARY_ACTOR, limit=100):
    body = (
        {"usernames": [username], "content_type": "all", "quantity_per_user": limit, "selected_fields": FIELDS}
        if actor == PRIMARY_ACTOR
        else {"username": [username], "resultsLimit": limit}
    )
    return api(
        "POST", f"/acts/{actor.replace('/', '~')}/runs", json=body, params={"timeout": 300, "maxTotalChargeUsd": 0.25}
    )["data"]


def get_run(run_id):
    return api("GET", f"/actor-runs/{run_id}")["data"]


def dataset_items(dataset_id):
    # Inputs cap each profile at 100 items. Paginate so API defaults cannot silently truncate a run.
    rows = []
    while True:
        page = api("GET", f"/datasets/{dataset_id}/items", params={"offset": len(rows), "limit": 250, "clean": "true"})
        if not isinstance(page, list):
            raise ApifyError("Apify gav ett oväntat datasetformat.")
        rows.extend(page)
        if len(page) < 250:
            return rows
