#!/usr/bin/env python3
"""Publikens resultat in i idébanken: Meta-annonsernas siffror summerade per idé, så att förslagen inte bara följer
Jonas tycke utan också vad som faktiskt får folk att stanna, klicka och köpa.

Flöde (skills/ny-video, "Resultat"):
  1. Hämta annonsdata med dashboard-MCP:n data_fraga (en rad per Meta-annons):
       table ads_daily, filter platform = Meta, period = senaste 120 dagarna,
       group_by [ad_id, ad, campaign, format], sum cost→kr, impressions→vis, clicks→klick, outcome→kv,
       purchases→kop, offline_purchases→portal, video_3s_views→v3, thruplays→tp
     och spara raderna (listan "rows") som work/_idebank/export-<datum>.json.
  2. python library/ideas/resultat.py importera work/_idebank/export-<datum>.json --period 2026-07-29:2026-11-26
     → work/_idebank/resultat.json (gitignorerat: repot är publikt, siffrorna stannar lokalt)
  3. python library/ideas/resultat.py rapport      # per idé + annonser som inte är kopplade till någon idé

Koppling annons → idé: library/ideas/annonskoppling.json (mönster mot annonsnamnet). Ej kopplade annonser med
kostnad listas – titta på bilden och lägg till en regel (eller en ny idé).

Mått per idé: kostnad, visningar, länkklick, CTR, kundvagnar (Meta AddToCart = dashboardens utfall), kr per
kundvagn, köp (pixel + portal), och för video 3-sekundersvisningar per visning ("stannar") och ThruPlays per
3-sekundersvisning ("tittar klart"). Index = idéns kr per kundvagn / kontots snitt (under 1 = bättre än snittet).
En idé räknas först när den kostat minst MIN_KR (samma tröskel som dashboardens ranking).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UT = ROOT / "work" / "_idebank" / "resultat.json"
KOPPLING = HERE / "annonskoppling.json"
MIN_KR = 300.0
FALT = ("kr", "vis", "klick", "kv", "kop", "portal", "v3", "tp", "vis_video")


def rules() -> list[tuple[re.Pattern, str]]:
    data = json.loads(KOPPLING.read_text(encoding="utf-8"))
    return [(re.compile(r["monster"], re.IGNORECASE), r["ide"]) for r in data["regler"]]


def idea_for(name: str, rs) -> str | None:
    for pat, ide in rs:
        if pat.search(name or ""):
            return ide
    return None


def derive(s: dict, tot: dict | None = None) -> dict:
    """tot = hela kontot; index jämför idén med alla ÖVRIGA annonser (annars drar en stor idé snittet mot sig själv)."""
    out = dict(s)
    out["ctr_pct"] = round(100 * s["klick"] / s["vis"], 2) if s["vis"] else None
    out["kr_per_kv"] = round(s["kr"] / s["kv"], 1) if s["kv"] else None
    out["kop_totalt"] = s["kop"] + s["portal"]
    out["kr_per_kop"] = round(s["kr"] / out["kop_totalt"], 0) if out["kop_totalt"] else None
    out["stannar_pct"] = round(100 * s["v3"] / s["vis_video"], 1) if s.get("vis_video") and s["v3"] else None
    out["tittar_klart_pct"] = round(100 * s["tp"] / s["v3"], 1) if s["v3"] else None
    if tot and out["kr_per_kv"]:
        ovr_kr, ovr_kv = tot["kr"] - s["kr"], tot["kv"] - s["kv"]
        if ovr_kv > 0:
            out["index"] = round(out["kr_per_kv"] / (ovr_kr / ovr_kv), 2)
    out["tillrackligt"] = s["kr"] >= MIN_KR
    return out


def importera(path: Path, period: str) -> dict:
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows = rows.get("rows", rows) if isinstance(rows, dict) else rows
    rs = rules()
    tot = {f: 0.0 for f in FALT}
    per: dict[str, dict] = {}
    okopplade: dict[str, dict] = {}
    for r in rows:
        vals = {f: float(r.get(f) or 0) for f in FALT}
        vals["vis_video"] = vals["vis"] if r.get("format") == "video" else 0.0  # "stannar" räknas bara på video
        for f in FALT:
            tot[f] += vals[f]
        ide = idea_for(r.get("ad", ""), rs)
        bucket = per.setdefault(ide, {f: 0.0 for f in FALT} | {"annonser": 0, "format": {}}) if ide else \
            okopplade.setdefault(r.get("ad", "?"), {f: 0.0 for f in FALT} | {"annonser": 0, "format": {}})
        for f in FALT:
            bucket[f] += vals[f]
        bucket["annonser"] += 1
        fmt = r.get("format") or "?"
        bucket["format"][fmt] = bucket["format"].get(fmt, 0) + 1
    data = {
        "hamtad": dt.date.today().isoformat(), "period": period, "kalla": f"dashboard ads_daily (Meta) via {path.name}",
        "konto": derive(tot | {"annonser": len(rows)}),
        "ideer": {k: derive(v, tot) for k, v in sorted(per.items(), key=lambda kv: -kv[1]["kr"])},
        "ej_kopplade": {k: derive(v, tot) for k, v in sorted(okopplade.items(), key=lambda kv: -kv[1]["kr"])},
    }
    UT.parent.mkdir(parents=True, exist_ok=True)
    UT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def load() -> dict | None:
    return json.loads(UT.read_text(encoding="utf-8")) if UT.exists() else None


def kort_rad(r: dict) -> str:
    """En rad för ark och förslag, t.ex. '58 kr/kundvagn · index 0,6 · 12 annonser · 46 000 kr'."""
    if not r:
        return "inga annonsresultat än"
    delar = []
    if r.get("kr_per_kv"):
        delar.append(f"{r['kr_per_kv']:.0f} kr/kundvagn")
    if r.get("index") is not None:
        delar.append(f"index {r['index']:.2f}".replace(".", ","))
    if r.get("stannar_pct"):
        delar.append(f"stannar {r['stannar_pct']:.0f} %")
    delar.append(f"{int(r['annonser'])} annonser · {r['kr']:,.0f} kr".replace(",", " "))
    if not r.get("tillrackligt"):
        delar.append("för lite data")
    return " · ".join(delar)


def faktor(r: dict | None) -> float:
    """Hur mycket resultaten lyfter eller sänker en idé i förslagen (1 = neutral)."""
    if not r or not r.get("tillrackligt") or r.get("index") is None:
        return 1.0
    return max(0.6, min(1.6, (1 / r["index"]) ** 0.5))


def rapport(data: dict) -> None:
    k = data["konto"]
    print(f"Period {data['period']} (hämtad {data['hamtad']}). Kontot: {kort_rad(k)}, CTR {k['ctr_pct']} %")
    print("\nPer idé (index = kr per kundvagn jämfört med alla övriga annonser; under 1 = billigare):")
    for ide, r in data["ideer"].items():
        extra = f", CTR {r['ctr_pct']} %" + (f", tittar klart {r['tittar_klart_pct']} %" if r.get("tittar_klart_pct") else "")
        extra += f", {r['kr_per_kop']:.0f} kr/köp" if r.get("kr_per_kop") else ""
        print(f"  {ide:28} {kort_rad(r)}{extra}")
    ej = [(n, r) for n, r in data["ej_kopplade"].items() if r["kr"] >= 50]
    if ej:
        print(f"\nEj kopplade till någon idé ({len(data['ej_kopplade'])} annonsnamn; visar de med minst 50 kr):")
        for n, r in ej:
            print(f"  {n[:60]:60} {kort_rad(r)}")
        print("→ Titta på bilderna och lägg till regler i library/ideas/annonskoppling.json (eller nya idéer).")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    im = sub.add_parser("importera")
    im.add_argument("export", type=Path)
    im.add_argument("--period", default="")
    sub.add_parser("rapport")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # -I ignorerar PYTHONIOENCODING; Windows-konsolen är annars cp1252
    if a.cmd == "importera":
        rapport(importera(a.export, a.period))
        print(f"\nsparat: {UT}")
    else:
        data = load()
        if not data:
            sys.exit(f"saknas: {UT} – kör importera först")
        rapport(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
