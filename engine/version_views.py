"""Versioner av filmerna i work/: lista, tidslinje per film, synkad jämförelse och kommentarer.

Arkivet är filbaserat (engine/versionsarkiv.py) och finns bara på den dator där work/ ligger – i produktion
(Render) saknas work/ och vyerna svarar 404. Ingen databas används, så inget skrivs till produktionsdatabasen.
"""
import json
import mimetypes
import re
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from . import versionsarkiv as va

FILNAMN_RE = re.compile(r"^(film-[\w-]+\.mp4|poster\.jpg|kontakt\.jpg)$")
MAX_CHUNK = 8 * 1024 * 1024


def _arkiv_finns():
    if not va.WORK.is_dir():
        raise Http404("Versionsarkivet finns bara på datorn där work/ ligger.")


def _film(film: str):
    _arkiv_finns()
    try:
        return va.filmmapp(film)
    except va.ArkivFel:
        raise Http404("Filmen finns inte.") from None


def _version(film: str, nr: str):
    _film(film)
    try:
        return va.version(film, nr)
    except (va.ArkivFel, ValueError):
        raise Http404("Versionen finns inte.") from None


@login_required
@require_GET
def lista(request):
    _arkiv_finns()
    return render(request, "engine/versioner_lista.html", {"filmer": va.filmer(), "saknas": va.kontroll()})


@login_required
@require_POST
def samla(request):
    _arkiv_finns()
    nya = va.samla(av=request.user.get_username())
    return JsonResponse({"ok": True, "nya": [f"{m['film']} {m['namn']}" for m in nya]})


@login_required
@require_GET
def film(request, film):
    _film(film)
    vs = va.versioner(film)
    if not vs:
        raise Http404("Filmen har inga versioner än.")
    return render(request, "engine/versioner_film.html", {
        "film": film, "versioner": list(reversed(vs)), "data": json.dumps(_klientdata(film, vs), ensure_ascii=False),
    })


@login_required
@require_GET
def jamfor(request, film):
    _film(film)
    vs = va.versioner(film)
    if not vs:
        raise Http404("Filmen har inga versioner än.")
    valda = [v.strip() for v in request.GET.get("v", "").split(",") if v.strip()]
    if not valda:
        valda = [vs[-2]["namn"], vs[-1]["namn"]] if len(vs) > 1 else [vs[-1]["namn"]]
    return render(request, "engine/versioner_jamfor.html", {
        "film": film, "data": json.dumps(_klientdata(film, vs), ensure_ascii=False),
        "valda": json.dumps(valda[:4]), "format": request.GET.get("format", ""),
    })


def _klientdata(film, vs):
    return [{
        "namn": v["namn"], "nr": v["nr"], "titel": v["titel"], "andring": v.get("andring", ""), "datum": v["datum"],
        "av": v.get("av", ""), "status": v["granskning"].get("status", "utkast"),
        "kommentarer": v["granskning"].get("kommentarer", []),
        "filer": [{"namn": f["namn"], "format": f["format"], "langd": f.get("langd", 0)} for f in v["filer"]],
    } for v in vs]


@login_required
@require_GET
def fil(request, film, nr, namn):
    if not FILNAMN_RE.match(namn):
        raise Http404()
    v = _version(film, nr)
    path = Path(v["mapp"]) / namn
    if not path.is_file():
        raise Http404("Filen saknas.")
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    size = path.stat().st_size
    match = re.fullmatch(r"bytes=(\d+)-(\d*)", request.headers.get("Range", ""))
    if match:
        start = int(match[1])
        end = min(int(match[2]) if match[2] else start + MAX_CHUNK - 1, size - 1)
        if start > end:
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
        with path.open("rb") as f:
            f.seek(start)
            response = HttpResponse(f.read(end - start + 1), status=206, content_type=ctype,
                                    headers={"Content-Range": f"bytes {start}-{end}/{size}"})
    else:
        response = FileResponse(path.open("rb"), content_type=ctype)
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, max-age=3600"  # versionerna är låsta
    return response


def _json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


@login_required
@require_POST
def kommentar(request, film, nr):
    _version(film, nr)
    data = _json(request)
    try:
        if data.get("klar_id"):
            va.markera_kommentar(film, nr, data["klar_id"], bool(data.get("klar", True)))
            return JsonResponse({"ok": True})
        tid = data.get("tid")
        k = va.kommentera(film, nr, data.get("text", ""), None if tid in (None, "") else float(tid),
                          av=request.user.get_full_name() or request.user.get_username() or "Jonas")
    except (va.ArkivFel, ValueError) as e:
        return JsonResponse({"fel": str(e)}, status=400)
    return JsonResponse({"ok": True, "kommentar": k})


@login_required
@require_POST
def status(request, film, nr):
    _version(film, nr)
    try:
        va.satt_status(film, nr, _json(request).get("status", ""))
    except va.ArkivFel as e:
        return JsonResponse({"fel": str(e)}, status=400)
    return JsonResponse({"ok": True})


@login_required
@require_GET
def uppdrag(request, film, nr):
    _version(film, nr)
    return HttpResponse(va.uppdrag(film, nr), content_type="text/plain; charset=utf-8")
