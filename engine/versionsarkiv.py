"""Versionsarkiv för filmer i work/ – "GitHub för video", lokalt och utan databas.

Varje film (work/<film>/) får work/<film>/versioner/vNN/ som aldrig skrivs över:
  film-<format>.mp4   en eller flera format (9x16, 4x5, 16x9 …)
  poster.jpg          bildruta vid ~1 s
  kontakt.jpg         8 bildrutor jämnt fördelade
  kalla/              kopia av byggunderlaget (film.json, html, js, ljudval …) som skapade versionen
  meta.json           låst: nr, datum, ändring, filer med sha256, källa, git-commit, föregående version
Bredvid (inte låst): granskning.json – Jonas kommentarer på tidpunkt och status (utkast/godkänd/underkänd).

Samma fil (samma sha256) sparas inte två gånger. Återställning skriver aldrig över aktuella källfiler:
den lägger underlaget i work/<film>/fran-vNN/ som utgångspunkt för en ny version.

Bara standardbiblioteket, så att både renderare (via scripts/versioner.py) och Django-vyn kan använda modulen.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("GK_WORK_DIR", REPO / "work"))
FORMAT_RE = re.compile(r"(9x16|4x5|16x9|1x1)")
VERSION_RE = re.compile(r"^v(\d{2,})$")
STATUSAR = ("utkast", "godkänd", "underkänd")
# Byggunderlag som kopieras med varje version (filnamn eller glob, relativt filmmappen).
STANDARD_KALLA = ["film*.json", "*.html", "*.js", "*.mjs", "*.py", "*.sh", "MANUS.md", "README.md"]
MAX_KALLA_BYTES = 2 * 1024 * 1024
# Hjälpfilmer i resultat/ som inte är versioner av filmen (t.ex. jämförelser sida vid sida med en referens).
IGNORERA_PREFIX = ("jamforelse", ".")


class ArkivFel(Exception):
    pass


# ---------- hjälpare ----------
def _nu() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _las_json(path: Path, standard):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return standard


def _skriv_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _las_bara(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode & ~stat.S_IWRITE & ~stat.S_IWGRP & ~stat.S_IWOTH)
    except OSError:
        pass


def _format(namn: str, standard: str = "9x16") -> str:
    m = FORMAT_RE.search(namn)
    return m.group(1) if m else standard


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _ffmpeg(*args) -> bool:
    try:
        return subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], capture_output=True, timeout=180).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def langd(path: Path) -> float:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return round(float(out), 3)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


# ---------- filmer och versioner ----------
def filmmapp(film: str | Path) -> Path:
    p = Path(film)
    if not p.is_absolute():
        p = WORK / p
    p = p.resolve()
    if not p.is_dir():
        raise ArkivFel(f"Filmmappen finns inte: {p}")
    if WORK.resolve() not in p.parents:
        raise ArkivFel(f"Filmen måste ligga i {WORK}")
    return p


def versioner(film: str | Path) -> list[dict]:
    mapp = filmmapp(film) / "versioner"
    ut = []
    if not mapp.is_dir():
        return ut
    for d in sorted(mapp.iterdir()):
        m = VERSION_RE.match(d.name)
        if not (d.is_dir() and m):
            continue
        meta = _las_json(d / "meta.json", None)
        if not meta:
            continue
        meta["granskning"] = _las_json(d / "granskning.json", {"status": "utkast", "kommentarer": []})
        meta["mapp"] = str(d)
        ut.append(meta)
    return sorted(ut, key=lambda v: v["nr"])


def filmer() -> list[dict]:
    ut = []
    if not WORK.is_dir():
        return ut
    for d in sorted(WORK.iterdir()):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        vs = versioner(d)
        if not vs:
            continue
        senaste = vs[-1]
        godkand = next((v for v in reversed(vs) if v["granskning"].get("status") == "godkänd"), None)
        ut.append({"film": d.name, "antal": len(vs), "senaste": senaste, "godkand": godkand,
                   "oppna": sum(1 for v in vs for k in v["granskning"].get("kommentarer", []) if not k.get("klar"))})
    return sorted(ut, key=lambda f: f["senaste"]["datum"], reverse=True)


def version(film: str | Path, nr: int | str) -> dict:
    n = int(str(nr).lstrip("vV"))
    for v in versioner(film):
        if v["nr"] == n:
            return v
    raise ArkivFel(f"Version v{n:02d} finns inte för {film}")


def _alla_hashar(film: Path) -> set[str]:
    return {f["sha256"] for v in versioner(film) for f in v.get("filer", [])}


# ---------- spara ----------
def spara(film: str | Path, videor: list[str | Path], andring: str = "", kalla: list[str] | None = None,
          titel: str = "", av: str = "", tvinga: bool = False) -> dict | None:
    """Spara en ny version. Returnerar meta, eller None om exakt samma film(er) redan finns arkiverade."""
    mapp = filmmapp(film)
    filer = []
    for v in videor:
        p = Path(v)
        if not p.is_absolute():
            p = (mapp / p) if (mapp / p).exists() else Path.cwd() / p
        if not p.is_file():
            raise ArkivFel(f"Videon finns inte: {p}")
        filer.append(p.resolve())
    if not filer:
        raise ArkivFel("Ingen video angiven")
    hashar = [sha256(p) for p in filer]
    if not tvinga and set(hashar) <= _alla_hashar(mapp):
        return None

    rot = mapp / "versioner"
    rot.mkdir(exist_ok=True)
    befintliga = versioner(mapp)
    nr = (befintliga[-1]["nr"] + 1) if befintliga else 1
    vmapp = rot / f"v{nr:02d}"
    tmp = rot / f".v{nr:02d}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()

    meta_filer, anvanda = [], set()
    for p, h in zip(filer, hashar):
        fmt = _format(p.name)
        namn = f"film-{fmt}.mp4"
        i = 2
        while namn in anvanda:
            namn = f"film-{fmt}-{i}.mp4"
            i += 1
        anvanda.add(namn)
        shutil.copy2(p, tmp / namn)
        meta_filer.append({"namn": namn, "format": fmt, "kalla": str(p), "sha256": h, "bytes": p.stat().st_size,
                           "langd": langd(p)})

    huvud = tmp / meta_filer[0]["namn"]
    lang = meta_filer[0]["langd"] or 2
    _ffmpeg("-ss", min(1.0, lang / 3), "-i", huvud, "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3", tmp / "poster.jpg")
    _ffmpeg("-i", huvud, "-vf", "fps=" + f"{8 / max(lang, 0.5):.4f}" + ",scale=240:-2,tile=8x1", "-frames:v", "1",
            "-q:v", "4", tmp / "kontakt.jpg")

    kopierat = []
    monster = kalla if kalla is not None else STANDARD_KALLA
    (tmp / "kalla").mkdir()
    for m in monster:
        for k in sorted(mapp.glob(m)):
            if not k.is_file() or k.stat().st_size > MAX_KALLA_BYTES or "versioner" in k.parts:
                continue
            rel = k.relative_to(mapp)
            dst = tmp / "kalla" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(k, dst)
            kopierat.append({"fil": str(rel).replace("\\", "/"), "sha256": sha256(k)})

    meta = {
        "nr": nr, "namn": f"v{nr:02d}", "film": mapp.name, "datum": _nu(),
        "titel": titel or andring[:60] or f"Version {nr}", "andring": andring, "av": av,
        "foregaende": befintliga[-1]["nr"] if befintliga else None,
        "filer": meta_filer, "kalla": kopierat, "git": _git_commit(),
    }
    _skriv_json(tmp / "meta.json", meta)
    _skriv_json(tmp / "granskning.json", {"status": "utkast", "kommentarer": []})
    os.replace(tmp, vmapp)
    for f in vmapp.rglob("*"):
        if f.is_file() and f.name != "granskning.json":
            _las_bara(f)
    meta["mapp"] = str(vmapp)
    return meta


# ---------- granskning (kommentarer och status, låser inte versionen) ----------
def _granskning(film, nr) -> tuple[Path, dict]:
    v = version(film, nr)
    p = Path(v["mapp"]) / "granskning.json"
    return p, _las_json(p, {"status": "utkast", "kommentarer": []})


def kommentera(film, nr, text: str, tid: float | None = None, av: str = "Jonas") -> dict:
    text = (text or "").strip()
    if not text:
        raise ArkivFel("Tom kommentar")
    p, g = _granskning(film, nr)
    k = {"id": hashlib.sha1(f"{_nu()}{text}".encode()).hexdigest()[:10], "tid": None if tid is None else round(float(tid), 2),
         "text": text[:2000], "av": av, "datum": _nu(), "klar": False}
    g.setdefault("kommentarer", []).append(k)
    _skriv_json(p, g)
    return k


def markera_kommentar(film, nr, kid: str, klar: bool = True) -> None:
    p, g = _granskning(film, nr)
    for k in g.get("kommentarer", []):
        if k["id"] == kid:
            k["klar"] = klar
    _skriv_json(p, g)


def satt_status(film, nr, status: str) -> None:
    if status not in STATUSAR:
        raise ArkivFel(f"Okänd status: {status}")
    p, g = _granskning(film, nr)
    g["status"] = status
    g["status_datum"] = _nu()
    _skriv_json(p, g)


def uppdrag(film, nr) -> str:
    """Öppna kommentarer som ett uppdrag till Claude/Codex: gör nästa version."""
    v = version(film, nr)
    oppna = [k for k in v["granskning"].get("kommentarer", []) if not k.get("klar")]
    rader = [f"Film: work/{v['film']} – utgå från {v['namn']} ({v['titel']}).",
             f"Byggunderlag: work/{v['film']}/versioner/{v['namn']}/kalla/ (återställ med `python scripts/versioner.py aterstall {v['film']} {v['namn']}` om nuvarande källfiler har ändrats).",
             "Åtgärda Jonas kommentarer och spara resultatet som en ny version (renderaren gör det automatiskt):"]
    for k in oppna:
        t = f"{k['tid']:.1f} s" if k.get("tid") is not None else "hela filmen"
        rader.append(f"- [{t}] {k['text']}")
    if not oppna:
        rader.append("- (inga öppna kommentarer)")
    return "\n".join(rader)


# ---------- återställ ----------
def aterstall(film, nr) -> Path:
    v = version(film, nr)
    mapp = filmmapp(film)
    src = Path(v["mapp"]) / "kalla"
    dst = mapp / f"fran-{v['namn']}"
    if dst.exists():
        raise ArkivFel(f"{dst} finns redan – ta bort eller döp om den först")
    shutil.copytree(src, dst)
    for f in dst.rglob("*"):
        if f.is_file():
            f.chmod(f.stat().st_mode | stat.S_IWRITE)
    return dst


def samla(av: str = "") -> list[dict]:
    """Arkivera alla färdiga filmer i resultat/ som saknar version. Filer som bara skiljer sig i format
    (…-9x16.mp4 / …-4x5.mp4 med samma namn i övrigt) blir en version med flera format."""
    nya = []
    grupper: dict[tuple[str, str], list[dict]] = {}
    for s in kontroll():
        nyckel = FORMAT_RE.sub("", Path(s["fil"]).stem).strip("-_ ")
        grupper.setdefault((s["film"], nyckel), []).append(s)
    for (film, _), filer in sorted(grupper.items(), key=lambda g: min(f["datum"] for f in g[1])):
        mapp = WORK / film
        meta = spara(mapp, [mapp / f["fil"] for f in filer], titel=Path(filer[0]["fil"]).stem,
                     andring="Ny fil i " + ", ".join(f["fil"] for f in filer), av=av)
        if meta:
            nya.append(meta)
    return nya


# ---------- kontroll ----------
def kontroll() -> list[dict]:
    """Färdiga filmer i work/*/resultat som inte finns i någon version."""
    saknas = []
    if not WORK.is_dir():
        return saknas
    for d in sorted(WORK.iterdir()):
        res = d / "resultat"
        if not res.is_dir() or d.name.startswith(("_", ".")):
            continue
        hashar = _alla_hashar(d) if (d / "versioner").is_dir() else set()
        for f in sorted(res.rglob("*.mp4")):
            if f.name.startswith(IGNORERA_PREFIX):
                continue
            if sha256(f) not in hashar:
                saknas.append({"film": d.name, "fil": str(f.relative_to(d)).replace("\\", "/"), "datum": _dt.datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")})
    return saknas
