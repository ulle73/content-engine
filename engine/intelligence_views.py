from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from openai import APIError

from . import apify
from .competitors import OPEN_STATUSES, collect_import, instagram_username, start_import
from .models import Competitor, CompetitorImport, CompetitorPost, ContentEvent, ContentRun
from .openrouter import OpenRouterError
from .ownership import company_required
from .signals import analyze_top, catalog, classification_hash, classify, recurring_patterns


class CompetitorForm(forms.ModelForm):
    username = forms.CharField(label="Instagram-profil eller användarnamn", max_length=200)

    class Meta:
        model = Competitor
        fields = ["name", "username"]
        labels = {"name": "Kontots namn"}

    def clean_username(self):
        try:
            value = instagram_username(self.cleaned_data["username"])
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        if self.instance.pk and value != self.instance.username and self.instance.imports.exists():
            raise forms.ValidationError(
                "Lägg till ett nytt konto och inaktivera det gamla så att historiken hålls isär."
            )
        return value


@login_required
@company_required
def intelligence(request, workspace_id):
    from . import ads_views
    if request.GET.get("channel") == "paid":
        return ads_views.intelligence(request, workspace_id)
    company = request.workspace
    editing = (
        get_object_or_404(Competitor, pk=request.GET["edit"], company=company) if request.GET.get("edit") else None
    )
    if request.method == "POST" and request.POST.get("competitor_id"):
        editing = get_object_or_404(Competitor, pk=request.POST["competitor_id"], company=company)
    form = CompetitorForm(request.POST or None, instance=editing)
    if request.method == "POST" and form.is_valid():
        if (
            company.competitors.filter(username=form.cleaned_data["username"])
            .exclude(pk=editing.pk if editing else None)
            .exists()
        ):
            form.add_error("username", "Kontot finns redan för företaget.")
        else:
            competitor = form.save(commit=False)
            competitor.company = company
            competitor.save()
            messages.success(request, "Referenskontot är sparat.")
            if not editing:
                try:
                    start_import(competitor)
                    messages.success(request, "Första historikhämtningen har startats i Apify.")
                except apify.ApifyError as exc:
                    messages.error(request, str(exc))
            return redirect("engine:intelligence", workspace_id=workspace_id)
    signals = catalog(company)
    for signal in signals:
        signal["analysis_current"] = signal["post"].classification_hash == classification_hash(signal["post"], company)
    runs = list(
        CompetitorImport.objects.filter(competitor__company=company)
        .select_related("competitor")
        .order_by("-started_at")[:15]
    )
    return render(
        request,
        "engine/intelligence.html",
        {
            "workspace": company,
            "form": form,
            "editing": editing,
            "competitors": company.competitors.order_by("name"),
            "runs": runs,
            "pending": any(r.status in OPEN_STATUSES and r.actor_run_id for r in runs),
            "weekly": [s for s in signals if s["age_days"] <= 7][:8],
            "references": [s for s in signals if s["age_days"] > 7 and s["relative"] and s["relative"] >= 1.5][:4],
            "patterns": recurring_patterns(signals),
            "channel":"organic", "learning":ads_views.overview(company, "organic"),
        },
    )


@login_required
@company_required
@require_POST
def competitor_action(request, workspace_id, competitor_id):
    competitor = get_object_or_404(Competitor, pk=competitor_id, company=request.workspace)
    try:
        if request.POST.get("action") == "toggle":
            competitor.active = not competitor.active
            competitor.save(update_fields=["active"])
        else:
            run = start_import(competitor)
            messages.success(request, "Hämtningen körs hos Apify." if run.actor_run_id else run.error)
    except apify.ApifyError as exc:
        messages.error(request, str(exc))
    return redirect("engine:intelligence", workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def refresh_imports(request, workspace_id):
    errors = []
    for run in CompetitorImport.objects.filter(
            competitor__company=request.workspace, status__in=OPEN_STATUSES
        ).select_related("competitor"):
        try:
            collect_import(run)
        except apify.ApifyError:
            errors.append(run.pk)
    pending = CompetitorImport.objects.filter(
            competitor__company=request.workspace, status__in=("starting", "running")
        ).exists()
    try:
        if not pending:
            analyze_top(request.workspace)
    except (ValueError, APIError):
        errors.append("analysis")
    return JsonResponse({"pending":pending, "partial":bool(errors), "needs_attention":errors})


@login_required
@company_required
@require_POST
def analyze_signal(request, workspace_id, post_id):
    post = get_object_or_404(CompetitorPost, pk=post_id, competitor__company=request.workspace, competitor__active=True)
    try:
        classify(post, request.workspace)
        messages.success(request, "Mekanismen är analyserad utifrån caption och metadata.")
    except OpenRouterError as exc:
        messages.error(request, str(exc))
    except (ValueError, APIError):
        messages.error(request, "AI-analysen kunde inte slutföras. Den hämtade statistiken finns kvar.")
    return redirect("engine:intelligence", workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def reject_idea(request, workspace_id, run_id, idea_index):
    run = get_object_or_404(ContentRun, pk=run_id, workspace=request.workspace)
    if idea_index < len(run.ideas):
        ContentEvent.objects.create(
            run=run, idea_index=idea_index, action="rejected", data={"idea": run.ideas[idea_index]}
        )
        messages.success(request, "Ditt avvisande är sparat som återkoppling.")
    return redirect("engine:home", workspace_id=workspace_id)
