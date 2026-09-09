from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from openai import APIError

from . import ads, apify
from .models import AdAccount, CompetitorAd, ContentRun, LearningModel, OwnOutcome
from .ownership import company_required


class AccountForm(forms.ModelForm):
    country = forms.ChoiceField(label="Land där annonserna visas", choices=list(ads.COUNTRIES.items()))
    class Meta:
        model = AdAccount
        fields = ["name", "page_url", "page_id", "country"]
        labels = {"name":"Annonsörens namn", "page_url":"Facebook-sida eller Ads Library-länk", "page_id":"Facebook-sid-id (fylls från Ads Library-länk)"}

    def clean(self):
        data = super().clean()
        raw = self.data.get("page_url", "")
        try:
            _, from_url = ads.page_url(raw)
        except ValueError:
            from_url = ""
        value = from_url or data.get("page_id", "")
        if not value.isdigit():
            self.add_error("page_id", "Kopiera annonsörens länk från Ads Library (view_all_page_id), eller ange dess numeriska Facebook-sid-id.")
        elif self.instance.pk and self.instance.page_id and value != self.instance.page_id:
            self.add_error("page_id", "Skapa en ny bevakning för ett annat sid-id så att historiken hålls isär.")
        data["page_id"] = value
        return data

    def clean_page_url(self):
        try:
            value, _ = ads.page_url(self.cleaned_data["page_url"])
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        if self.instance.pk and value != self.instance.page_url:
            raise forms.ValidationError("Lägg till en ny annonsör och inaktivera den gamla för att behålla historikens identitet.")
        return value

    def clean_country(self):
        value = self.cleaned_data["country"].upper()
        if value not in ads.COUNTRIES:
            raise forms.ValidationError("Välj ett land som stöds.")
        if self.instance.pk and value != self.instance.country:
            raise forms.ValidationError("Skapa en ny bevakning för ett annat land så att sync-fönstren hålls isär.")
        return value


def destination(company):
    return reverse("engine:intelligence", kwargs={"workspace_id":company.pk})+"?channel=paid"


def overview(company, channel):
    model = LearningModel.objects.filter(company=company, channel=channel).order_by("-trained_at").first()
    return {"channel":channel, "labels":OwnOutcome.objects.filter(prediction__run__workspace=company, prediction__channel=channel).count(),
            "model":model, "predictions":company.contentrun_set.filter(channel=channel, predictions__isnull=False).distinct().count()}


def intelligence(request, workspace_id):
    # Called only from the already authenticated/company-scoped intelligence view.
    company = request.workspace
    editing = get_object_or_404(AdAccount, pk=request.GET["edit"], company=company) if request.GET.get("edit") else None
    if request.POST.get("account_id"):
        editing = get_object_or_404(AdAccount, pk=request.POST["account_id"], company=company)
    form = AccountForm(request.POST or None, instance=editing)
    if request.method == "POST" and form.is_valid():
        from django.db.models import Q
        if company.ad_accounts.filter(Q(page_url=form.cleaned_data["page_url"]) | Q(page_id=form.cleaned_data["page_id"]), country=form.cleaned_data["country"]).exclude(pk=editing.pk if editing else None).exists():
            form.add_error("page_url", "Den bevakningen finns redan.")
        else:
            account = form.save(commit=False)
            account.company = company
            account.save()
            messages.success(request, "Annonsören är sparad och kontrolleras av daily-körningen. Du kan också hämta nu.")
            return redirect(destination(company))
    cards = list(CompetitorAd.objects.filter(account__company=company, account__active=True).select_related("account").order_by("-last_seen_at", "-pk")[:60])
    for ad in cards:
        ad.analysis_current = bool(ad.classification) and ad.classification_hash == ads.classification_hash(ad, company)
        ad.observed_days = (ad.last_seen_at-ad.first_seen_at).days
        ad.url = f"https://www.facebook.com/ads/library/?id={ad.external_id}"
    themes = {}
    for ad in cards:
        if ad.analysis_current:
            for theme in set(ad.classification.get("themes", [])):
                themes[theme] = themes.get(theme, 0)+1
    return render(request, "engine/ads.html", {"workspace":company, "channel":"paid", "form":form, "editing":editing,
        "accounts":company.ad_accounts.select_related("sync").order_by("name"), "ads":cards,
        "themes":[(k,v) for k,v in themes.items() if v>1], "learning":overview(company, "paid")})


@login_required
@company_required
@require_POST
def account_action(request, workspace_id, account_id):
    account = get_object_or_404(AdAccount, pk=account_id, company=request.workspace)
    try:
        action = request.POST.get("action")
        if action == "toggle":
            account.active = not account.active
            account.save(update_fields=["active"])
        elif action == "resume_new":
            state = ads.account_state(account)
            if state.coverage != "limited":
                raise ValueError("Bevakningen har inget pausat urval.")
            state.coverage = "bounded_gap_accepted"
            state.watermark = timezone.now()
            state.last_refresh_at = state.watermark
            state.next_attempt_at = None
            state.save()
            messages.success(request, "Framtida discovery fortsätter med kort överlapp. Den ofullständiga historiken har inte markerats som komplett.")
        elif action == "reprocess":
            state = ads.account_state(account)
            run = state.requests.exclude(actor_run_id=None).order_by("-created_at").first()
            if not account.page_id or not run:
                raise ValueError("Ange rätt sid-id och kontrollera att ett sparat dataset finns.")
            ads.collect(run, account, reprocess=True)
            messages.success(request, "Det befintliga datasetet har lästs om utan ny betald scrape.")
        else:
            run = ads.start(account)
            if run:
                run = ads.collect(run, account)
                messages.info(request, f"Annonskontroll: {run.status}. Nya starter begränsas och samma körnings-id återanvänds.")
    except (apify.ApifyError, ValueError) as exc:
        messages.error(request, str(exc))
    return redirect(destination(request.workspace))


@login_required
@company_required
@require_POST
def analyze(request, workspace_id, ad_id):
    ad = get_object_or_404(CompetitorAd, pk=ad_id, account__company=request.workspace, account__active=True)
    try:
        ads.classify(ad, request.workspace)
        messages.success(request, "Annonsens text och metadata är analyserade. Saknade uppgifter är okända.")
    except (ValueError, APIError):
        messages.error(request, "Analysen kunde inte slutföras. Underlaget finns kvar; kostnadsgränsen och analysloggen skyddar mot dubbla anrop.")
    return redirect(destination(request.workspace))


class OutcomeForm(forms.Form):
    source = forms.ChoiceField(label="Resultatkälla", choices=[("meta_export","Meta-export"), ("postiz_export","Postiz-export"), ("manual_verified","Manuellt verifierat")])
    external_id = forms.CharField(label="Verkligt post- eller annons-id", max_length=200)
    evidence = forms.URLField(label="Länk till rapporten eller resultatkällan", max_length=1000)
    published_at = forms.DateTimeField(label="Publiceringstid", widget=forms.DateTimeInput(attrs={"type":"datetime-local"}))
    window_end = forms.DateTimeField(label="Mätfönstrets slut (exakt sju dygn senare)", widget=forms.DateTimeInput(attrs={"type":"datetime-local"}))
    observed_at = forms.DateTimeField(label="När resultatet lästes av", widget=forms.DateTimeInput(attrs={"type":"datetime-local"}))
    impressions = forms.IntegerField(label="Impressions under de första sju dygnen", min_value=1, required=False)
    likes = forms.IntegerField(label="Likes under samma fönster", min_value=0, required=False)
    comments = forms.IntegerField(label="Kommentarer under samma fönster", min_value=0, required=False)
    clicks = forms.IntegerField(label="Klick under samma fönster", min_value=0, required=False)
    conversions = forms.IntegerField(label="Verifierade konverteringar",min_value=0,required=False)
    spend = forms.FloatField(label="Verklig annonskostnad",min_value=0,required=False)
    revenue = forms.FloatField(label="Verifierad attribuerad intäkt",min_value=0,required=False)
    currency = forms.ChoiceField(label="Valuta för kostnad/intäkt",required=False,choices=[("","Ej tillämpligt"),("SEK","SEK"),("EUR","EUR"),("USD","USD")])


@login_required
@company_required
def outcome(request, workspace_id, run_id):
    from .learning import record_outcome
    run = get_object_or_404(ContentRun, pk=run_id, workspace=request.workspace)
    form = OutcomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        values = form.cleaned_data.copy()
        metrics = {key:values.pop(key) for key in ("impressions", "likes", "comments", "clicks", "conversions", "spend", "revenue", "currency")}
        try:
            record_outcome(run, **values, metrics={k:v for k,v in metrics.items() if v is not None and v!=""})
            messages.success(request, "Det verkliga resultatet är sparat i rätt learning-spår.")
            return redirect("engine:review", workspace_id=workspace_id, run_id=run_id)
        except ValueError as exc:
            form.add_error(None, str(exc))
    return render(request, "engine/outcome.html", {"workspace":request.workspace, "run":run, "form":form})
