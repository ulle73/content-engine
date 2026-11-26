#!/usr/bin/env python3
"""Riktningsarket: tre helt olika helheter för en ny film, sida vid sida – Jonas väljer en (och får låna en sak från
en annan). Används i skills/ny-video, väg B (utan referensfilm), före storyboarden.

Varje riktning är en sammanhängande helhet ur idébanken: idé + genre, formspråk, bärande effekt, textbehandling, ljud,
en stillbild och gärna ett rörelsetest på ~3 s av det bärande ögonblicket. Arket kräver för varje riktning:
  - **Blender-frågan:** hade riktningen blivit mer premium med Blender? (ja / delvis / nej + varför + vad)
  - **Material:** vad som behövs för att den ska bli perfekt, och vad som saknas.
och att de tre riktningarna har olika genre (annars blir det tre varianter av samma idé).

  python scripts/riktningar.py work/<film> --forslag "instruktion tre steg" [--bolag golfkuponger]
      # väljer 3 idéer ur idébanken i olika genrer (nyligen använda och 👎 hamnar längre ner, minst en oprövad)
      # och skriver ett utkast till work/<film>/riktningar.json att fylla i
  python scripts/riktningar.py work/<film>          # renderar work/<film>/out/riktningar.png från riktningar.json

riktningar.json:
{"titel": "Instruktionsvideo – 3 steg", "bestallning": "…", "format": "16:9",
 "riktningar": [{"bokstav": "A", "ide": "ide.level-up", "titel": "…", "genre": "spel-utmaning", "premiss": "…",
   "formsprak": "färg, typsnitt, rörelse", "barande": "bärande effekt/övergång (bank-id)", "text": "textbehandling",
   "ljud": "musik/ljudgrepp", "bild": "stillbild.png", "rorelsetest": "test.mp4",
   "blender": {"bedomning": "ja|delvis|nej", "varfor": "…", "vad": "vilka scener/element"},
   "material": [{"vad": "appens skärmar", "status": "finns|saknas", "kalla": "var / hur vi skaffar det"}]}],
 "gemensamt_material": [{"vad": "fakta om köpflödet", "status": "finns", "kalla": "golfkuponger-friskvard"}]}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "library" / "tools"))
sys.path.insert(0, str(ROOT / "library" / "ideas"))
import resultat as res  # noqa: E402  (publikens resultat per idé, work/_idebank/resultat.json)
import storyboard as sb  # noqa: E402  (esc, frame_from_video, screenshot)

CATALOG = ROOT / "library" / "catalog.json"
BLENDER_SVAR = {"ja", "delvis", "nej"}
STATUS = {"finns", "saknas"}
STOPPORD = {"jag", "vill", "göra", "gör", "en", "ett", "den", "det", "som", "för", "från", "till", "och", "att", "på",
            "med", "av", "om", "är", "vi", "ska", "kan", "video", "film", "videon", "filmen", "mål", "start"}


def load_ideas() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    return [i for i in items if i.get("type") == "idea"]


def recently_used(idea: dict, days: int = 60) -> bool:
    today = dt.date.today()
    for a in (idea.get("ide") or {}).get("anvand", []):
        try:
            d = dt.date.fromisoformat(str(a.get("datum", ""))[:10] + ("-01" if len(str(a.get("datum", ""))) == 7 else ""))
        except ValueError:
            continue
        if (today - d).days <= days:
            return True
    return False


def thumbs_down(idea: dict) -> bool:
    return any(o.get("betyg") == "👎" for o in (idea.get("ide") or {}).get("omdome", []))


def suggest(query: str, company: str, n: int = 3) -> list[dict]:
    """n idéer i olika genrer: bäst matchning först, nyligen använda och 👎 längre ner, minst en oprövad (bredd)."""
    from find import score, tokens  # library/tools/find.py

    words = [w for w in tokens(query) if w not in STOPPORD]
    ranked = []
    resultat = (res.load() or {}).get("ideer", {})
    for idea in load_ideas():
        bolag = (idea.get("ide") or {}).get("bolag")
        if company and bolag not in (company, "alla"):
            continue
        s = score(idea, words) or 0.3  # alla idéer är kandidater; matchning lyfter
        if recently_used(idea):
            s *= 0.5
        if thumbs_down(idea):
            s *= 0.6
        s *= res.faktor(resultat.get(idea["id"]))  # publikens resultat i Meta: bättre än övriga lyfter, sämre sänker
        ranked.append((s, idea))
    ranked.sort(key=lambda x: -x[0])
    picked, genres = [], set()
    for _, idea in ranked:
        g = idea["ide"]["genre"]
        if g in genres:
            continue
        picked.append(idea)
        genres.add(g)
        if len(picked) == n:
            break
    if picked and all(p["status"] == "verified" for p in picked):  # kollision: byt sista mot bästa oprövade
        for _, idea in ranked:
            if idea["status"] != "verified" and idea["ide"]["genre"] not in genres:
                picked[-1] = idea
                break
    return picked


def draft(folder: Path, query: str, company: str) -> Path:
    ideas = suggest(query, company)
    out = {"titel": query, "bestallning": query, "format": "9:16", "riktningar": [], "gemensamt_material": []}
    for letter, idea in zip("ABC", ideas):
        d = idea["ide"]
        b = d.get("blender")
        out["riktningar"].append({
            "bokstav": letter, "ide": idea["id"], "titel": idea["name"], "genre": d["genre"], "premiss": d["premiss"],
            "formsprak": "", "barande": "", "text": "", "ljud": "", "bild": "", "rorelsetest": "",
            "blender": {"bedomning": "ja" if b else "nej", "varfor": b or "3D tillför inget här – håll det platt.", "vad": ""},
            "material": [{"vad": m.lstrip("✓ ").strip(), "status": "finns" if m.startswith("✓") else "saknas", "kalla": ""}
                         for m in d.get("material", [])],
        })
    path = folder / "riktningar.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    resultat = (res.load() or {}).get("ideer", {})
    for r in out["riktningar"]:
        print(f"{r['bokstav']}. {r['titel']} [{r['genre']}] ({r['ide']}) – Meta: {res.kort_rad(resultat.get(r['ide']))}")
    print(f"utkast: {path} – fyll i formspråk, bärande effekt, text, ljud, bild/rörelsetest och material; rendera sedan.")
    return path


def check(data: dict) -> list[tuple[str | None, str, str]]:
    out = []
    rs = data.get("riktningar") or []
    if len(rs) < 2:
        out.append((None, "fel", "minst två riktningar (helst tre) behövs"))
    genres = [r.get("genre") for r in rs]
    if len(set(genres)) < len(genres):
        out.append((None, "fel", f"två riktningar har samma genre ({', '.join(genres)}) – välj olika genrer"))
    for r in rs:
        k = r.get("bokstav")
        b = r.get("blender") or {}
        if b.get("bedomning") not in BLENDER_SVAR or not (b.get("varfor") or "").strip():
            out.append((k, "fel", "Blender-frågan är inte besvarad (bedomning ja/delvis/nej + varför)"))
        mat = r.get("material") or []
        if not mat:
            out.append((k, "fel", "materiallistan saknas – vad behövs för att den ska bli perfekt?"))
        for m in mat:
            if m.get("status") not in STATUS:
                out.append((k, "fel", f"material '{m.get('vad')}': status ska vara finns/saknas"))
        for key, label in (("formsprak", "formspråk"), ("barande", "bärande effekt"), ("text", "textbehandling"),
                           ("ljud", "ljud")):
            if not (r.get(key) or "").strip():
                out.append((k, "varning", f"{label} saknas"))
        if not r.get("bild"):
            out.append((k, "varning", "ingen stillbild – visa hur riktningen ser ut"))
    return out


def build_html(data: dict, folder: Path, problems) -> str:
    esc = sb.esc
    rs = data.get("riktningar") or []
    resdata = res.load() or {}
    resultat = resdata.get("ideer", {})
    by = {}
    for k, lvl, msg in problems:
        by.setdefault(k, []).append((lvl, msg))
    aw, ah = sb.ASPECT.get(data.get("format") or "9:16", (9, 16))
    cols = []
    for r in rs:
        img = r.get("bild")
        img_uri = (folder / img).resolve().as_uri() if img and (folder / img).exists() else None
        strip = ""
        if r.get("rorelsetest") and (folder / r["rorelsetest"]).exists():
            work = folder / "out" / "riktningar"
            frames = []
            for n, t in enumerate((0.3, 1.0, 1.8, 2.6)):
                dest = work / f"{r['bokstav']}-{n}.jpg"
                if sb.frame_from_video((folder / r["rorelsetest"]).resolve(), t, dest):
                    frames.append(dest.as_uri())
            strip = '<div class="strip">' + "".join(f'<img src="{f}">' for f in frames) + "</div>"
        b = r.get("blender") or {}
        bcls = {"ja": "ja", "delvis": "delvis"}.get(b.get("bedomning"), "nej")
        mats = "".join(f'<li class="{esc(m.get("status"))}">{"✓" if m.get("status") == "finns" else "✗"} {esc(m.get("vad"))}'
                       f'{(" – " + esc(m.get("kalla"))) if m.get("kalla") else ""}</li>' for m in r.get("material") or [])
        warn = "".join(f'<li class="{lvl}">{esc(msg)}</li>' for lvl, msg in by.get(r.get("bokstav"), []))
        rows = "".join(f"<dt>{lab}</dt><dd>{esc(r.get(key))}</dd>" for key, lab in
                       (("formsprak", "Formspråk"), ("barande", "Bärande"), ("text", "Text"), ("ljud", "Ljud")) if r.get(key))
        pic = f'<img src="{img_uri}">' if img_uri else '<div class="empty">Ingen stillbild ännu</div>'
        cols.append(f'''<section class="dir"><div class="head"><span class="letter">{esc(r.get("bokstav"))}</span>
<div><h2>{esc(r.get("titel"))}</h2><div class="genre">{esc(r.get("genre"))} · {esc(r.get("ide"))}</div></div></div>
<div class="frame" style="aspect-ratio:{aw}/{ah}">{pic}</div>{strip}
<p class="premiss">{esc(r.get("premiss"))}</p>
<div class="meta-res">Publiken i Meta: {esc(res.kort_rad(resultat.get(r.get("ide"))))}</div><dl>{rows}</dl>
<div class="blender {bcls}"><b>Premium med Blender? {esc((b.get("bedomning") or "?").upper())}</b> {esc(b.get("varfor"))}
{('<br><i>' + esc(b.get("vad")) + '</i>') if b.get("vad") else ''}</div>
<h3>Material för att bli perfekt</h3><ul class="mat">{mats}</ul>{f'<ul class="warn">{warn}</ul>' if warn else ''}</section>''')
    gm = "".join(f'<li class="{esc(m.get("status"))}">{"✓" if m.get("status") == "finns" else "✗"} {esc(m.get("vad"))}'
                 f'{(" – " + esc(m.get("kalla"))) if m.get("kalla") else ""}</li>' for m in data.get("gemensamt_material") or [])
    general = "".join(f'<li class="{lvl}">{esc(msg)}</li>' for lvl, msg in by.get(None, []))
    saknas = sum(1 for r in rs for m in r.get("material") or [] if m.get("status") == "saknas")
    return f'''<!doctype html><html lang="sv"><head><meta charset="utf-8"><style>
:root{{--paper:#f4f1ea;--ink:#16201b;--soft:#5d6660;--rule:#d9d3c5;--card:#fbfaf6;--clay:#c2410c;--green:#14532d;--gold:#b88a1b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 "Segoe UI",Arial,sans-serif;padding:40px 44px 48px;width:1920px}}
header{{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:22px}}h1{{font-size:34px;margin:0 0 6px}}header p{{margin:0;color:var(--soft);font-size:17px}}
.dirs{{display:grid;grid-template-columns:repeat({len(rs) or 1},1fr);gap:24px}}.dir{{background:var(--card);border:1px solid var(--rule);padding:18px}}
.head{{display:flex;gap:14px;align-items:center;margin-bottom:12px}}.letter{{background:var(--ink);color:var(--paper);font-weight:800;font-size:28px;width:52px;height:52px;display:grid;place-items:center}}
h2{{font-size:22px;margin:0;line-height:1.15}}.genre{{color:var(--clay);font-size:13px;font-weight:600}}
.frame{{position:relative;width:100%;max-height:760px;background:#e4dfd2;overflow:hidden;margin:0 auto}}.frame img{{width:100%;height:100%;object-fit:cover;display:block}}
.frame .empty{{position:absolute;inset:0;display:grid;place-items:center;color:var(--soft)}}
.strip{{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:6px}}.strip img{{width:100%;display:block}}
.premiss{{font-size:16px;font-weight:600;margin:14px 0 8px}}.meta-res{{font-size:13px;color:var(--green);background:#e8efe9;padding:6px 10px;margin:0 0 10px}}dl{{display:grid;grid-template-columns:90px 1fr;gap:5px 10px;margin:0 0 12px;font-size:14px}}dt{{color:var(--soft)}}dd{{margin:0}}
.blender{{padding:10px 12px;border-left:4px solid var(--soft);background:#eeeae0;font-size:14px;margin-bottom:10px}}.blender.ja{{border-color:var(--green)}}.blender.delvis{{border-color:var(--gold)}}
h3{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--soft);margin:10px 0 4px}}
.mat,.warn,.general,.gm{{margin:0;padding:0;list-style:none;font-size:14px}}.mat li.saknas,.gm li.saknas{{color:#b42318;font-weight:650}}.mat li.finns,.gm li.finns{{color:var(--green)}}
.warn li.fel,.general li.fel{{color:#d62828;font-weight:650}}.warn li.varning,.general li.varning{{color:#a16207}}.warn{{margin-top:8px}}
footer{{margin-top:24px;padding-top:12px;border-top:1px solid var(--rule);color:var(--soft);display:flex;justify-content:space-between}}
</style></head><body>
<header><h1>{esc(data.get("titel") or "Riktningar")}</h1><p>{esc(data.get("bestallning"))}</p></header>
{f'<ul class="general">{general}</ul>' if general else ''}
<main class="dirs">{''.join(cols)}</main>
{f'<h3>Gemensamt material</h3><ul class="gm">{gm}</ul>' if gm else ''}
<footer><span>{f"Meta-resultat: {esc(resdata.get('period'))} (hämtat {esc(resdata.get('hamtad'))}). " if resdata else "Inga Meta-resultat importerade (library/ideas/resultat.py). "}{saknas} saker saknas för att det ska bli perfekt (rött). Välj en riktning – du får låna en sak från en annan.</span>
<span>Nästa steg: storyboard för den valda riktningen.</span></footer></body></html>'''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mapp")
    ap.add_argument("--forslag", help="beställningen i ord – väljer tre idéer i olika genrer och skriver ett utkast")
    ap.add_argument("--bolag", default="golfkuponger")
    ap.add_argument("--ut", type=Path)
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(a.mapp).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if a.forslag:
        draft(folder, a.forslag, a.bolag)
        return 0
    src = folder / "riktningar.json"
    if not src.exists():
        sys.exit(f"saknas: {src} (börja med --forslag \"<beställningen>\")")
    data = json.loads(src.read_text(encoding="utf-8"))
    problems = check(data)
    page = folder / "out" / "riktningar" / "riktningar.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(build_html(data, folder, problems), encoding="utf-8")
    out = (a.ut or folder / "out" / "riktningar.png").resolve()
    aw, ah = sb.ASPECT.get(data.get("format") or "9:16", (9, 16))
    col_w = (1920 - 88 - 48) / max(len(data.get("riktningar") or []), 1)
    sb.screenshot(page, out, int(600 + min(col_w * ah / aw, 760) + 1100))
    for k, lvl, msg in problems:
        print(f"{lvl.upper():8} {('riktning ' + k) if k else 'arket'}: {msg}")
    print(f"riktningar: {out}")
    return 1 if any(lvl == "fel" for _, lvl, _ in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
