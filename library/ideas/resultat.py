#!/usr/bin/env python3
"""Publikens resultat in i idébanken: Meta-annonsernas siffror per idé och SÄSONG, med mätbarhetsnivå, så att förslagen
inte bara följer Jonas tycke utan vad som faktiskt får folk att stanna, klicka och köpa – vid rätt tid på året.

Flöde (skills/ny-video avsnitt 4):
  1. Hämta med dashboard-MCP:n data_fraga, EN fråga per säsongsfönster (säsongerna i library/ideas/sasonger.json):
       table ads_daily, filter platform = Meta, date_from/date_to = säsongens dagar (bara de som finns i data),
       group_by [ad, format], sum cost→kr, impressions→vis, clicks→klick, outcome→kv, purchases→kop,
       offline_purchases→portal, video_3s_views→v3, thruplays→tp, having kr >= 20
     Spara som work/_idebank/export-<säsong>-<år>.json: {"fran": "YYYY-MM-DD", "till": "YYYY-MM-DD", "rows": [...]}
  2. python library/ideas/resultat.py importera work/_idebank/export-*.json
     → work/_idebank/historik.json (sparar varje säsong och år; en ny import av samma säsong ersätter den)
     → work/_idebank/resultat.json (per idé: totalt, per säsong, mätbarhet, index mot övriga i samma säsong)
     Allt i work/ är gitignorerat: repot är publikt, siffrorna stannar lokalt.
  3. python library/ideas/resultat.py rapport [--sasong deadline]

Mätbarhet (sasonger.json → matbarhet): kr per kundvagn är bara så säker som antalet kundvagnar (Poisson):
  för lite   < 10 kundvagnar eller < 500 kr  → visas men påverkar inte förslagen
  indikation ≥ 10 kundvagnar och ≥ 500 kr    → ±~50 %, påverkar förslagen till hälften
  mätbart    ≥ 30 kundvagnar och ≥ 1 500 kr  → ±~30 %, påverkar fullt
"Säkert bättre/sämre" = hela 90 %-intervallet ligger under/över övriga annonsers kr per kundvagn i samma säsong.
Index = idéns kr per kundvagn / övriga annonsers i samma säsong (under 1 = billigare).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAPP = ROOT / "work" / "_idebank"
HISTORIK = MAPP / "historik.json"
UT = MAPP / "resultat.json"
KOPPLING = HERE / "annonskoppling.json"
SASONGER = json.loads((HERE / "sasonger.json").read_text(encoding="utf-8"))
M = SASONGER["matbarhet"]
FALT = ("kr", "vis", "klick", "kv", "kop", "portal", "v3", "tp", "vis_video")
Z90 = 1.645


def sasong_for(datum: dt.date) -> str:
    for s in SASONGER["sasonger"]:
        if datum.month in s["manader"]:
            return s["id"]
    raise ValueError(f"ingen säsong för månad {datum.month}")


def sasong_namn(sid: str) -> str:
    return next((s["namn"] for s in SASONGER["sasonger"] if s["id"] == sid), sid)


def rules() -> list[tuple[re.Pattern, str]]:
    data = json.loads(KOPPLING.read_text(encoding="utf-8"))
    return [(re.compile(r["monster"], re.IGNORECASE), r["ide"]) for r in data["regler"]]


def idea_for(name: str, rs) -> str | None:
    for pat, ide in rs:
        if pat.search(name or ""):
            return ide
    return None


def tom() -> dict:
    return {f: 0.0 for f in FALT} | {"annonser": 0}


def addera(acc: dict, r: dict) -> None:
    for f in FALT:
        acc[f] += float(r.get(f) or 0)
    acc["annonser"] += r.get("annonser", 1)


def niva(s: dict) -> str:
    if s["kv"] >= M["matbart"]["min_kv"] and s["kr"] >= M["matbart"]["min_kr"]:
        return "mätbart"
    if s["kv"] >= M["indikation"]["min_kv"] and s["kr"] >= M["indikation"]["min_kr"]:
        return "indikation"
    return "för lite"


def derive(s: dict, tot: dict) -> dict:
    """tot = alla annonser i samma säsong (eller totalt); jämförelsen görs mot ÖVRIGA = tot − idén."""
    out = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()}
    out["ctr_pct"] = round(100 * s["klick"] / s["vis"], 2) if s["vis"] else None
    out["kr_per_kv"] = round(s["kr"] / s["kv"], 1) if s["kv"] else None
    out["kop_totalt"] = s["kop"] + s["portal"]
    out["kr_per_kop"] = round(s["kr"] / out["kop_totalt"]) if out["kop_totalt"] else None
    out["stannar_pct"] = round(100 * s["v3"] / s["vis_video"], 1) if s["vis_video"] >= M["video_stannar_min_visningar"] else None
    out["tittar_klart_pct"] = round(100 * s["tp"] / s["v3"], 1) if s["vis_video"] >= M["video_stannar_min_visningar"] and s["v3"] else None
    out["matbarhet"] = niva(s)
    ovr_kr, ovr_kv = tot["kr"] - s["kr"], tot["kv"] - s["kv"]
    if out["kr_per_kv"] and ovr_kv > 0:
        ovr = ovr_kr / ovr_kv
        out["ovriga_kr_per_kv"] = round(ovr, 1)
        out["index"] = round(out["kr_per_kv"] / ovr, 2)
        k = s["kv"]
        lo_k, hi_k = max(k - Z90 * math.sqrt(k), 0.5), k + Z90 * math.sqrt(k)
        out["intervall_kr_per_kv"] = [round(s["kr"] / hi_k), round(s["kr"] / lo_k)]
        if out["matbarhet"] != "för lite":
            if s["kr"] / lo_k < ovr:
                out["slutsats"] = "säkert bättre"
            elif s["kr"] / hi_k > ovr:
                out["slutsats"] = "säkert sämre"
            else:
                out["slutsats"] = "ingen säker skillnad"
    return out


def aggregate(rows: list[dict], rs) -> tuple[dict, dict, dict]:
    tot, per, ej = tom(), {}, {}
    for r in rows:
        r = dict(r)
        r["vis_video"] = float(r.get("vis") or 0) if r.get("format") == "video" else 0.0
        addera(tot, r)
        ide = idea_for(r.get("ad", ""), rs)
        addera(per.setdefault(ide, tom()) if ide else ej.setdefault(r.get("ad", "?"), tom()), r)
    return tot, per, ej


def importera(paths: list[Path]) -> dict:
    hist = json.loads(HISTORIK.read_text(encoding="utf-8")) if HISTORIK.exists() else {}
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        fran, till = dt.date.fromisoformat(data["fran"]), dt.date.fromisoformat(data["till"])
        sid = sasong_for(fran)
        if sasong_for(till) != sid:
            sys.exit(f"{p.name}: {fran}–{till} går över två säsonger – hämta en fråga per säsong")
        nyckel = f"{sid}-{fran.year}"
        hist[nyckel] = {"sasong": sid, "ar": fran.year, "fran": data["fran"], "till": data["till"], "fil": p.name,
                        "rows": data["rows"]}
        print(f"importerad: {nyckel} ({data['fran']}–{data['till']}, {len(data['rows'])} annonsrader)")
    MAPP.mkdir(parents=True, exist_ok=True)
    HISTORIK.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return berakna(hist)


def berakna(hist: dict) -> dict:
    rs = rules()
    alla_rader, per_sasong_rader = [], {}
    for h in hist.values():
        alla_rader += h["rows"]
        per_sasong_rader.setdefault(h["sasong"], []).extend(h["rows"])
    tot, per, ej = aggregate(alla_rader, rs)
    ideer = {k: {"totalt": derive(v, tot), "sasonger": {}} for k, v in per.items()}
    konto = {"totalt": derive(tot, tot | {"kr": tot["kr"] * 2, "kv": tot["kv"] * 2}), "sasonger": {}}
    for sid, rader in per_sasong_rader.items():
        stot, sper, _ = aggregate(rader, rs)
        konto["sasonger"][sid] = derive(stot, stot | {"kr": stot["kr"] * 2, "kv": stot["kv"] * 2})
        for k, v in sper.items():
            ideer.setdefault(k, {"totalt": derive(v, tot), "sasonger": {}})["sasonger"][sid] = derive(v, stot)
    data = {
        "hamtad": dt.date.today().isoformat(),
        "perioder": {k: f"{h['fran']}–{h['till']}" for k, h in sorted(hist.items())},
        "konto": konto,
        "ideer": dict(sorted(ideer.items(), key=lambda kv: -kv[1]["totalt"]["kr"])),
        "ej_kopplade": {k: derive(v, tot) for k, v in sorted(ej.items(), key=lambda kv: -kv[1]["kr"])},
    }
    UT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return data


def load() -> dict | None:
    return json.loads(UT.read_text(encoding="utf-8")) if UT.exists() else None


def for_idea(data: dict | None, ide: str, sasong: str | None = None) -> tuple[dict | None, str]:
    """Resultatet som ska gälla för en idé: säsongens om det är minst en indikation, annars totalen."""
    if not data or ide not in data.get("ideer", {}):
        return None, ""
    d = data["ideer"][ide]
    s = d["sasonger"].get(sasong) if sasong else None
    if s and s["matbarhet"] != "för lite":
        return s, sasong_namn(sasong)
    return d["totalt"], "alla säsonger" + (f" ({sasong_namn(sasong)}: för lite data)" if sasong else "")


def kort_rad(r: dict | None, etikett: str = "") -> str:
    """T.ex. 'Deadline: 58 kr/kundvagn (50–70) · index 0,93 · mätbart · säkert bättre · 68 annonser · 65 481 kr'."""
    if not r:
        return "inga annonsresultat än"
    delar = []
    if r.get("kr_per_kv"):
        iv = r.get("intervall_kr_per_kv")
        delar.append(f"{r['kr_per_kv']:.0f} kr/kundvagn" + (f" ({iv[0]}–{iv[1]})" if iv else ""))
    if r.get("index") is not None:
        delar.append(f"index {r['index']:.2f}".replace(".", ","))
    delar.append(r.get("matbarhet", ""))
    if r.get("slutsats"):
        delar.append(r["slutsats"])
    if r.get("stannar_pct"):
        delar.append(f"stannar {r['stannar_pct']:.0f} %")
    delar.append(f"{int(r['annonser'])} annonser · {r['kr']:,.0f} kr".replace(",", " "))
    return (f"{etikett}: " if etikett else "") + " · ".join(d for d in delar if d)


def faktor(r: dict | None) -> float:
    """Hur mycket resultaten lyfter eller sänker en idé i förslagen (1 = neutral). För lite data påverkar inte."""
    if not r or r.get("index") is None or r.get("matbarhet") == "för lite":
        return 1.0
    vikt = M["matbart"]["vikt"] if r["matbarhet"] == "mätbart" else M["indikation"]["vikt"]
    full = max(0.6, min(1.6, (1 / r["index"]) ** 0.5))
    return 1 + (full - 1) * vikt


def rapport(data: dict, sasong: str | None) -> None:
    print("Perioder: " + ", ".join(f"{k} {v}" for k, v in data["perioder"].items()))
    for sid, k in [("totalt", data["konto"]["totalt"])] + list(data["konto"]["sasonger"].items()):
        if sasong and sid not in ("totalt", sasong):
            continue
        print(f"Kontot {sasong_namn(sid) if sid != 'totalt' else 'totalt'}: {k.get('kr_per_kv') or '–'} kr/kundvagn, "
              f"{int(k['kv'])} kundvagnar, {k['kr']:,.0f} kr".replace(",", " "))
    for ide, d in data["ideer"].items():
        print(f"\n{ide}")
        print("  " + kort_rad(d["totalt"], "Totalt"))
        for sid, r in d["sasonger"].items():
            if sasong and sid != sasong:
                continue
            print("  " + kort_rad(r, sasong_namn(sid)))
    ej = [(n, r) for n, r in data["ej_kopplade"].items() if r["kr"] >= 50]
    if ej:
        print(f"\nEj kopplade till någon idé (visar de med minst 50 kr):")
        for n, r in ej:
            print(f"  {n[:58]:58} {kort_rad(r)}")
        print("→ Titta på bilderna och lägg till regler i library/ideas/annonskoppling.json (eller nya idéer).")


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # -I ignorerar PYTHONIOENCODING; Windows-konsolen är annars cp1252
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    im = sub.add_parser("importera")
    im.add_argument("export", type=Path, nargs="+")
    ra = sub.add_parser("rapport")
    ra.add_argument("--sasong", choices=[s["id"] for s in SASONGER["sasonger"]])
    sub.add_parser("berakna", help="räkna om resultat.json från historiken (t.ex. efter ändrad annonskoppling)")
    a = ap.parse_args(argv)
    if a.cmd == "importera":
        rapport(importera(a.export), None)
        print(f"\nsparat: {UT}")
    elif a.cmd == "berakna":
        if not HISTORIK.exists():
            sys.exit(f"saknas: {HISTORIK}")
        rapport(berakna(json.loads(HISTORIK.read_text(encoding="utf-8"))), None)
    else:
        data = load()
        if not data:
            sys.exit(f"saknas: {UT} – kör importera först")
        rapport(data, a.sasong)
    return 0


if __name__ == "__main__":
    sys.exit(main())
