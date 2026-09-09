from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models import Case, IntegerField, Q, Value, When
from django.urls import reverse

from .branding import replace_logo
from .media_storage import MediaError
from .ownership import company_required


@login_required
@company_required
def company_settings(request, workspace_id):
    company = request.workspace
    if request.method == "POST":
        try:
            file = request.FILES.get("logo")
            if not file or file.size > 8 * 1024 * 1024:
                raise MediaError("Välj företagets officiella logga, högst 8 MB.")
            replace_logo(company, file.read(), file.name)
            messages.success(request, "Den officiella loggan är sparad. Nya bildgenereringar använder denna version när logga väljs.")
        except MediaError as exc:
            messages.error(request, str(exc))
        return redirect("engine:settings", workspace_id=company.pk)
    recent = list(company.daily_steps.select_related("run").exclude(
        Q(status="skipped") & (Q(key="__discovery__") | Q(key="await_imports"))
    ).order_by("-run__day", Case(When(status__in=("failed", "attention", "pending", "blocked"), then=Value(0)), default=Value(1), output_field=IntegerField()), "stage", "key")[:100])
    labels = {"competitor_import":"Konkurrentimport", "competitor_analysis":"AI-analys", "media_collect":"Hämta färdig media", "media_cleanup":"Rensa media"}
    labels.update(ads_import="Annonsbevakning", ads_analysis="Annonsanalys", learning="Learning / shadow")
    labels.update(own_discovery="Egna publiceringar",own_snapshots="Egen performance",own_outcomes="Egen baseline / outcomes")
    accounts = {str(a.pk):a.name for a in company.competitors.all()}
    for step in recent:
        step.label = labels.get(step.stage, step.stage)
        step.subject = accounts.get(step.key.split(":")[0], step.key.split(":")[0][:12]) if step.stage == "competitor_import" else step.key.split(":")[0][:12]
        step.target = ""
        if step.stage.startswith("competitor_"):
            step.target = reverse("engine:intelligence", kwargs={"workspace_id":company.pk})
        elif step.stage.startswith("ads_"):
            step.target = reverse("engine:intelligence", kwargs={"workspace_id":company.pk}) + "?channel=paid"
        elif step.stage == "media_collect" and step.result.get("run_id"):
            step.target = reverse("engine:media_job", kwargs={"workspace_id":company.pk, "run_id":step.result["run_id"], "job_id":step.key})
    from .scraper_efficiency import report
    return render(request, "engine/settings.html", {"workspace": company, "steps": recent, "scraping":report(company)})
