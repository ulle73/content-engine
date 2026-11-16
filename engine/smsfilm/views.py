"""Dashboard page "Generera video → SMS-film": the form, the job list and a JSON status endpoint for polling."""

import json
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt

from engine.ownership import company_required

from . import service, spec

MAX_FORM_JSON = 200_000


def _wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


@login_required
@company_required
def sms_film(request, workspace_id):
    return _sms_film(request, workspace_id, embedded=False)


def _sms_film(request, workspace_id, *, embedded):
    company = request.workspace
    if request.method == "POST":
        raw = request.POST.get("form_json") or ""
        try:
            if len(raw) > MAX_FORM_JSON:
                raise spec.SmsFilmError("Formuläret är för stort. Korta texterna och försök igen.")
            try:
                form = json.loads(raw)
            except ValueError:
                raise spec.SmsFilmError("Formuläret kom inte fram. Ladda om sidan och försök igen.") from None
            title = spec._text(form.get("title") if isinstance(form, dict) else "", "Namn på filmen", 200)
            if isinstance(form, dict) and form.get("kind") == "slutmall":
                saved, total = spec.build_slutmall(form)
                saved["title"] = title
                job = service.create_job(company, request.user, title=title or f"Slutmall – {spec.SLUTMALLAR[saved['mall']]}",
                                         form=saved, conversation={}, image_asset_ids=[], duration_s=total,
                                         dispatch_now=False, kind="slutmall")
            else:
                with transaction.atomic():
                    conv, image_ids, saved, total = spec.build(form, request.FILES, company)
                    saved["title"] = title
                    job = service.create_job(company, request.user, title=title or "SMS-film", form=saved,
                                             conversation=conv, image_asset_ids=image_ids, duration_s=total,
                                             dispatch_now=False)
            service.dispatch(job)
        except spec.SmsFilmError as exc:
            if _wants_json(request):
                return JsonResponse({"error": str(exc)}, status=400)
            messages.error(request, str(exc))
            return redirect("engine:sms_film", workspace_id=company.pk)
        if _wants_json(request):
            return JsonResponse({"job": service.serialize(job)}, status=201)
        messages.success(request, "Filmen ligger i kö och renderas nu.")
        return redirect("engine:sms_film", workspace_id=company.pk)

    reopen = None
    if request.GET.get("from"):
        try:
            reopen = service.get_job(company, uuid.UUID(request.GET["from"])).form
        except (spec.SmsFilmError, ValueError):
            reopen = None
    jobs = list(service.jobs_for(company))
    return render(request, "engine/sms_film.html", {
        "workspace": company,
        "sms_embed": embedded,
        "jobs": jobs,
        "jobs_json": [service.serialize(j) for j in jobs],
        "reopen": reopen,
        "limits": {"messages": spec.MAX_MESSAGES, "text": spec.MAX_TEXT, "seconds": spec.MAX_SECONDS,
                   "uploads": spec.MAX_UPLOADS, "outro": spec.OUTRO_LEN},
        "slutmallar": [{"id": k, "namn": v} for k, v in spec.SLUTMALLAR.items()],
        "slutmall_limits": {"rad1": spec.SLUTMALL_RAD1, "rad2": spec.SLUTMALL_RAD2},
        "slutmall_len": spec.SLUTMALL_LEN,
    })


@login_required
@company_required
def job_status(request, workspace_id, job_id):
    try:
        job = service.get_job(request.workspace, job_id)
    except service.SmsFilmError:
        raise Http404("Filmen finns inte.") from None
    return JsonResponse({"job": service.serialize(job)})


@xframe_options_exempt
def sms_film_embed(request, workspace_id):
    """Only the SMS editor may be framed by Golfkuponger's dashboard."""
    if request.get_host().split(":", 1)[0] != "content.golfkuponger.se":
        raise Http404
    if not request.user.is_authenticated:
        response = render(request, "engine/sms_film_embed_login.html")
    else:
        response = _authorized_embed(request, workspace_id)
    response["Content-Security-Policy"] = "frame-ancestors https://dashboard.golfkuponger.se"
    response["Cache-Control"] = "private, no-store"
    return response


@company_required
def _authorized_embed(request, workspace_id):
    return _sms_film(request, workspace_id, embedded=True)
