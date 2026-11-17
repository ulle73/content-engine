"""Dashboard page "Generera video → SMS-film": the form, the job list and a JSON status endpoint for polling."""

import json
import re
import uuid
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
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
        "slutmall_effekter": [{"id": k, "namn": v} for k, v in spec.SLUTMALL_EFFEKTER.items()],
        "slutmall_stil": [{"id": k, "namn": namn, "enhet": enhet, "min": lo, "max": hi, "std": std}
                          for k, (namn, enhet, lo, hi, std) in spec.SLUTMALL_STIL.items()],
        "slutmall_skak": spec.SLUTMALL_SKAK,
    })


DASHBOARD_ORIGIN = "https://dashboard.golfkuponger.se"
SLUTMALL_DIR = Path(__file__).resolve().parents[2] / "library" / "templates" / "golfkuponger-slutmallar"
SLUTMALL_FILE_RE = re.compile(r"^(slutmall\.html|assets/[a-z0-9-]+\.(woff2|png|jpg))$")
SLUTMALL_TYPES = {"html": "text/html; charset=utf-8", "woff2": "font/woff2", "png": "image/png", "jpg": "image/jpeg"}


@login_required
@company_required
@xframe_options_exempt
def slutmall_preview(request, workspace_id, fil):
    """Serves the end-card template and its assets so the form can show a live preview in an iframe.

    The form itself may sit inside Golfkuponger's dashboard, and browsers check framing against every
    ancestor, so X-Frame-Options SAMEORIGIN would block the preview there. CSP allows this site and the
    dashboard instead.
    """
    if not SLUTMALL_FILE_RE.match(fil):
        raise Http404
    path = SLUTMALL_DIR / fil
    if not path.is_file():
        raise Http404
    response = FileResponse(path.open("rb"), content_type=SLUTMALL_TYPES[fil.rsplit(".", 1)[-1]])
    response["Cache-Control"] = "private, max-age=300"
    response["Content-Security-Policy"] = f"frame-ancestors 'self' {DASHBOARD_ORIGIN}"
    return response


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
    response["Content-Security-Policy"] = f"frame-ancestors {DASHBOARD_ORIGIN}"
    response["Cache-Control"] = "private, no-store"
    return response


@company_required
def _authorized_embed(request, workspace_id):
    return _sms_film(request, workspace_id, embedded=True)
