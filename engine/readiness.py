"""What a company needs before monitoring can turn into idea cards – shown as a checklist, never a silent zero.

Without a profile and a current focus no post or ad is analysed (signals.analysis_candidates,
daily_stages.ads_analysis_units), so a company can be scraped for weeks and still never produce an idea.
Targets follow the masterplan's phase 1: at least 10 followed accounts and 5 ad pages, plus the company's own account.
"""
from django.urls import reverse

ACCOUNT_TARGET = 10
AD_PAGE_TARGET = 5
PROFILE_MISSING = ("Analysen är pausad: fyll i Företagsprofil och Aktuellt under Inställningar → Företagsuppgifter. "
                   "Bevakningen hämtar data, men inga inlägg eller annonser analyseras och inga idékort skapas.")


def analysis_ready(company) -> bool:
    return bool(company.profile.strip() and company.current.strip())


def checklist(company) -> list[dict]:
    context = reverse("engine:home", kwargs={"workspace_id": company.pk}) + "#company-context"
    insights = reverse("engine:intelligence", kwargs={"workspace_id": company.pk})
    accounts = company.competitors.filter(active=True, own=False).count()
    own = company.competitors.filter(active=True, own=True).exists()
    pages = company.ad_accounts.filter(active=True).count()
    return [
        {"key": "profile", "label": "Företagsprofil", "ok": bool(company.profile.strip()), "url": context,
         "detail": "Vilka ni är, vad ni säljer och till vem. Krävs för all analys."},
        {"key": "current", "label": "Aktuellt", "ok": bool(company.current.strip()), "url": context,
         "detail": "Erbjudanden, säsong och fokus just nu. Krävs för all analys."},
        {"key": "accounts", "label": "Bevakade konton", "ok": accounts >= ACCOUNT_TARGET, "url": insights,
         "detail": f"{accounts} av minst {ACCOUNT_TARGET} konkurrent- och inspirationskonton."},
        {"key": "own", "label": "Eget konto i bevakningen", "ok": own, "url": insights,
         "detail": "Egna hits är de bästa förlagorna till nya idéer."},
        {"key": "ad_pages", "label": "Annonssidor", "ok": pages >= AD_PAGE_TARGET, "url": insights + "?channel=paid",
         "detail": f"{pages} av minst {AD_PAGE_TARGET} annonssidor eller sökord i Ads Library."},
    ]
