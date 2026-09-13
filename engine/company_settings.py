from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import apify
from .branding import BrandingError, save_logo
from .daily import latest_steps
from .models import ScrapeRequest
from .ownership import company_required
from .scraper_efficiency import report


@login_required
@company_required
@require_http_methods(["GET", "POST"])
def company_settings(request, workspace_id):
    company = request.workspace
    if request.method == "POST" and request.FILES.get("logo"):
        try:
            save_logo(company, request.FILES["logo"])
            messages.success(request, "Loggan är sparad som företagets officiella logga.")
        except BrandingError as exc:
            messages.error(request, str(exc))
        return redirect("engine:settings", workspace_id=workspace_id)
    return render(request, "engine/settings.html", {
        "workspace": company,
        "scraping": report(company),
        "steps": latest_steps(company, limit=80),
    })


@login_required
@company_required
def costs(request, workspace_id):
    company = request.workspace
    apify_account = None
    apify_error = ""
    try:
        apify_account = apify.account_summary()
    except apify.ApifyError as exc:
        apify_error = str(exc)

    requests = ScrapeRequest.objects.filter(state__company=company)
    tracked_total = requests.aggregate(value=Sum("cost_usd"))["value"] or Decimal("0")
    recent = list(requests.select_related("state").order_by("-created_at")[:25])
    return render(request, "engine/costs.html", {
        "workspace": company,
        "apify_account": apify_account,
        "apify_error": apify_error,
        "tracked_total": tracked_total,
        "recent_costs": recent,
    })
