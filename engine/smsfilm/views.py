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

from engine.edit.outros import ROOT as OUTRO_DIR
from engine.media_views import local_asset_response
from engine.ownership import company_required

from . import mallar, publicera, service, spec
from .models import Publicering, SmsFilmOutput

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
            if isinstance(form, dict) and form.get("kind") == "mall":
                job = _create_mall_job(company, request.user, form, title, request.FILES)
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
            gammal = service.get_job(company, uuid.UUID(request.GET["from"]))
            if gammal.mall_id and not _far_se(gammal.mall_id, request.user):
                raise ValueError
            reopen = ({"kind": "mall", "mall": gammal.mall_id, "title": gammal.title, "varden": gammal.varden,
                       "formats": gammal.formats} if gammal.mall_id else gammal.form)
        except (spec.SmsFilmError, ValueError):
            reopen = None
    jobs = [j for j in service.jobs_for(company) if not j.mall_id or _far_se(j.mall_id, request.user)]
    return render(request, "engine/sms_film.html", {
        "workspace": company,
        "sms_embed": embedded,
        "jobs": jobs,
        "jobs_json": [service.serialize(j) for j in jobs],
        "reopen": reopen,
        "limits": {"messages": spec.MAX_MESSAGES, "text": spec.MAX_TEXT, "seconds": spec.MAX_SECONDS,
                   "uploads": spec.MAX_UPLOADS, "outro": spec.OUTRO_LEN},
        "mallar": mallar.for_formularet(request.user),
        "slutmall_klara": service.finished_slutmallar(company),
    })


SLUTMALL_ID = "golfkuponger-slutmallar"


def _far_se(mall_id, user):
    """Jobs and reopen links for a template the user may not use stay hidden (mall.json "endast_for")."""
    try:
        return mallar.far_anvanda(mallar.hamta(mall_id), user)
    except spec.SmsFilmError:
        return True   # a template that is gone: keep showing the old job as before


def _create_mall_job(company, user, form, title, files):
    """A dashboard template job: the values are checked against the template's mall.json (mallar.validera)."""
    mall = mallar.hamta_for(form.get("mall"), user)
    with transaction.atomic():
        images = spec._Images(company, files)
        varden, formats = mallar.validera(mall, form.get("varden"), form.get("format"), images=images)
        saved = {"kind": "mall", "mall": mall["id"], "title": title, "varden": varden, "format": formats}
        return service.create_job(company, user, title=title or mall["titel"], form=saved, conversation={},
                                  image_asset_ids=mallar.bild_asset_ids(mall, varden), duration_s=None,
                                  dispatch_now=False, kind="slutmall" if mall["id"] == SLUTMALL_ID else "mall",
                                  mall_id=mall["id"], varden=varden, formats=formats)


DASHBOARD_ORIGIN = "https://dashboard.golfkuponger.se"
SLUTMALL_TYPES = {"html": "text/html; charset=utf-8", "woff2": "font/woff2", "png": "image/png", "jpg": "image/jpeg"}


@login_required
@company_required
@xframe_options_exempt
def slutmall_preview(request, workspace_id, fil):
    """Serves the Spotlight clip (the SMS film's default end) for the end preview.

    The form itself may sit inside Golfkuponger's dashboard, and browsers check framing against every
    ancestor, so X-Frame-Options SAMEORIGIN would block the preview there. CSP allows this site and the
    dashboard instead.
    """
    if fil == "spotlight-9x16.mp4":
        path = OUTRO_DIR / "golfkuponger" / fil
        if not path.is_file():
            raise Http404
        response = local_asset_response(request, path, "video/mp4")
        response["Cache-Control"] = "private, max-age=300"
        return response
    raise Http404  # the template itself is served by mall_fil (sms-film/mall/<mall>/<fil>)


MALL_ROOT = Path(__file__).resolve().parents[2] / "library" / "templates"
MALL_NAMN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
MALL_FIL_RE = re.compile(r"^(mall\.json|[a-z0-9_-]+\.html|assets/[a-z0-9-]+\.(woff2|png|jpg))$")
MALL_TYPES = {**SLUTMALL_TYPES, "json": "application/json", "mjs": "text/javascript", "js": "text/javascript"}
# The page helper shared by every template (library/templates/_mall). safezones.js is served next to it so a
# page never has to reach outside library/templates; render-bas.mjs maps the same path.
MALL_DELAT = {
    "sida.mjs": MALL_ROOT / "_mall" / "sida.mjs",
    "safezones.js": MALL_ROOT.parents[1] / "edit-renderer" / "src" / "safezones.js",
}


@login_required
@company_required
@xframe_options_exempt
def mall_fil(request, workspace_id, mall, fil):
    """Serves a dashboard template (mall/v1) for the live preview: its page, mall.json and assets, plus the shared
    page helper under _mall. Only folders with a mall.json, only the page that mall.json names and only listed
    file types; nothing else in the repository is reachable.
    """
    if mall == "_mall":
        path = MALL_DELAT.get(fil)
    else:
        if not MALL_NAMN_RE.match(mall) or not MALL_FIL_RE.match(fil):
            raise Http404
        manifest = MALL_ROOT / mall / "mall.json"
        if not manifest.is_file():
            raise Http404
        if fil.endswith(".html") and fil != json.loads(manifest.read_text(encoding="utf-8")).get("sida"):
            raise Http404
        path = MALL_ROOT / mall / fil
    if path is None or not path.is_file():
        raise Http404
    response = FileResponse(path.open("rb"), content_type=MALL_TYPES[fil.rsplit(".", 1)[-1]])
    response["Cache-Control"] = "private, max-age=300"
    response["Content-Security-Policy"] = f"frame-ancestors 'self' {DASHBOARD_ORIGIN}"
    return response


@login_required
@company_required
def godkann(request, workspace_id, output_id):
    """Godkänn: publish one finished file to Drive CONTENT/01 Publicerat (engine/smsfilm/publicera.py).

    GET gives the suggested campaign, city and variant; POST {kampanj, stad, variant} creates the next version and
    uploads it. Every approval is a new version, so approving the same image twice gives v01 and v02."""
    output = SmsFilmOutput.objects.filter(pk=output_id, job__company=request.workspace).select_related("job", "asset").first()
    if output is None:
        return JsonResponse({"error": "Filen finns inte."}, status=404)
    if request.method == "GET":
        return JsonResponse({"forslag": publicera.forslag(output)})
    if request.method != "POST":
        return JsonResponse({"error": "Använd POST."}, status=405)
    try:
        data = json.loads(request.body or b"{}")
        if not isinstance(data, dict):
            raise ValueError
        pub = publicera.godkann(output, request.user, kampanj=data.get("kampanj"), stad=data.get("stad"),
                                variant=data.get("variant"))
    except ValueError:
        return JsonResponse({"error": "Formuläret kom inte fram. Försök igen."}, status=400)
    except spec.SmsFilmError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    pub = publicera.ladda_upp(pub)
    return JsonResponse({"publicering": publicera.serialize(pub)}, status=201 if pub.status == "klar" else 502)


@login_required
@company_required
def publicera_igen(request, workspace_id, pub_id):
    """Försök igen: continue a failed upload with the same upload_url. A finished one is not uploaded twice."""
    if request.method != "POST":
        return JsonResponse({"error": "Använd POST."}, status=405)
    pub = Publicering.objects.filter(pk=pub_id, company=request.workspace).select_related("output__asset").first()
    if pub is None:
        return JsonResponse({"error": "Publiceringen finns inte."}, status=404)
    pub = publicera.ladda_upp(pub)
    return JsonResponse({"publicering": publicera.serialize(pub)}, status=200 if pub.status == "klar" else 502)


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
