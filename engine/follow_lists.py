"""Curated start lists of accounts and ad pages to follow per company (library/follow-lists/*.json).

Instagram and TikTok accounts, Meta ad pages (page id, or a page URL whose id is learnt on the first fetch) and Ad
Library keyword searches (`ad_keywords`, e.g. "friskvårdsbidrag").

A list is matched to a company by its brand kit (`Company.brand["follow_list"]`) or by name alias.
Applying a list only adds what is missing; existing accounts, paused accounts and history are untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import apify
from .competitors import instagram_username, start_import, tiktok_username, username_for
from .models import AdAccount, Competitor

FOLLOW_LISTS = Path(__file__).resolve().parents[1] / "library" / "follow-lists"


def _lists() -> list[dict]:
    if not FOLLOW_LISTS.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FOLLOW_LISTS.glob("*.json"))]


def for_company(company) -> dict | None:
    kit = company.brand if isinstance(company.brand, dict) else {}
    wanted = kit.get("follow_list")
    name = company.name.strip().casefold()
    for item in _lists():
        if wanted and item.get("company") == wanted:
            return item
        if not wanted and name in [a.casefold() for a in item.get("aliases", [])]:
            return item
    return None


def _page_url(entry: dict) -> str:
    return entry.get("page_url") or f"https://www.facebook.com/{entry['page_id']}"


def _keyword_url(entry: dict) -> str:
    from .ads import keyword_url

    return keyword_url(entry["query"], entry.get("country", "SE"), entry.get("media", "video"))


def missing(company) -> dict:
    """What applying the company's list would add. Empty lists when nothing is missing."""
    item = for_company(company)
    if not item:
        return {"list": None, "instagram": [], "tiktok": [], "ad_pages": [], "ad_keywords": []}
    have_users = set(company.competitors.values_list("platform", "username"))
    have_pages = {(p, c) for p, c in company.ad_accounts.exclude(page_id="").values_list("page_id", "country")}
    have_urls = {(u.rstrip("/"), c) for u, c in company.ad_accounts.values_list("page_url", "country")}
    instagram = [a for a in item.get("instagram", [])
                 if ("instagram", instagram_username(a["username"])) not in have_users]
    tiktok = [a for a in item.get("tiktok", []) if ("tiktok", tiktok_username(a["username"])) not in have_users]
    ad_pages = [p for p in item.get("ad_pages", [])
                if (p.get("page_id"), p.get("country", "SE")) not in have_pages
                and (_page_url(p).rstrip("/"), p.get("country", "SE")) not in have_urls]
    ad_keywords = [k for k in item.get("ad_keywords", [])
                   if (_keyword_url(k).rstrip("/"), k.get("country", "SE")) not in have_urls]
    return {"list": item, "instagram": instagram, "tiktok": tiktok, "ad_pages": ad_pages, "ad_keywords": ad_keywords}


def apply(company, *, start_imports: bool = True) -> dict:
    todo = missing(company)
    added_accounts, added_pages, import_errors = 0, 0, []
    for platform in ("instagram", "tiktok"):
        for entry in todo[platform]:
            competitor = Competitor.objects.create(company=company, name=entry["name"][:200], platform=platform,
                                                   username=username_for(platform, entry["username"]))
            added_accounts += 1
            if start_imports:
                try:
                    start_import(competitor)
                except apify.ApifyError as exc:
                    import_errors.append(f"{competitor.username}: {exc}")
    for entry in todo["ad_pages"]:
        AdAccount.objects.create(company=company, name=entry["name"][:200], page_url=_page_url(entry),
                                 page_id=entry.get("page_id", ""), country=entry.get("country", "SE"))
        added_pages += 1
    for entry in todo["ad_keywords"]:
        AdAccount.objects.create(company=company, name=entry["name"][:200], page_url=_keyword_url(entry),
                                 page_id="", country=entry.get("country", "SE"))
        added_pages += 1
    return {"instagram": len(todo["instagram"]), "tiktok": len(todo["tiktok"]), "accounts": added_accounts,
            "ad_pages": added_pages, "import_errors": import_errors}
