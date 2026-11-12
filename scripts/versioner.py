"""Versioner för filmer i work/ (se engine/versionsarkiv.py).

  python scripts/versioner.py spara <film> <video.mp4> [<video2.mp4> ...] -m "vad som ändrats" [--av Claude]
  python scripts/versioner.py lista [<film>]
  python scripts/versioner.py kontroll                  # färdiga filmer i resultat/ som saknar version
  python scripts/versioner.py samla                     # arkivera alla sådana (formatvarianter blir en version)
  python scripts/versioner.py importera <film>          # arkivera befintliga resultat/*.mp4 (äldst först)
  python scripts/versioner.py aterstall <film> v03      # byggunderlaget till work/<film>/fran-v03/
  python scripts/versioner.py uppdrag <film> v03        # öppna kommentarer som uppdrag för nästa version
  python scripts/versioner.py backup [<film>] --mapp <drive-mapp-id>   # granskade versioner till Drive

Renderare anropar `spara` sist (make-mall.sh gör det automatiskt). Visaren: Content Engine → /versioner/.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT))
from engine import versionsarkiv as va  # noqa: E402


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("spara"); s.add_argument("film"); s.add_argument("video", nargs="+")
    s.add_argument("-m", "--andring", default=""); s.add_argument("--titel", default=""); s.add_argument("--av", default=os.environ.get("GK_AGENT", ""))
    s.add_argument("--kalla", nargs="*"); s.add_argument("--tvinga", action="store_true")
    s.add_argument("--tyst", action="store_true", help="avsluta med 0 även om arkivet inte kunde skrivas (för renderare)")
    li = sub.add_parser("lista"); li.add_argument("film", nargs="?")
    sub.add_parser("kontroll")
    sa = sub.add_parser("samla"); sa.add_argument("--av", default=os.environ.get("GK_AGENT", ""))
    im = sub.add_parser("importera"); im.add_argument("film")
    at = sub.add_parser("aterstall"); at.add_argument("film"); at.add_argument("version")
    up = sub.add_parser("uppdrag"); up.add_argument("film"); up.add_argument("version")
    bk = sub.add_parser("backup"); bk.add_argument("film", nargs="?"); bk.add_argument("--mapp", default=os.environ.get("GK_DRIVE_VERSIONER_ID", ""))
    a = ap.parse_args(argv)

    try:
        if a.cmd == "spara":
            meta = va.spara(a.film, a.video, andring=a.andring, kalla=a.kalla, titel=a.titel, av=a.av, tvinga=a.tvinga)
            print(f"version: {meta['film']} {meta['namn']} sparad" if meta else "version: oförändrad film – ingen ny version")
        elif a.cmd == "lista":
            if a.film:
                for v in va.versioner(a.film):
                    g = v["granskning"]
                    print(f"{v['namn']}  {v['datum'][:16]}  {g.get('status'):9}  {len(g.get('kommentarer', []))} komm.  {v['titel']}")
            else:
                for f in va.filmer():
                    print(f"{f['film']:28} {f['antal']:3} versioner  senaste {f['senaste']['namn']}  öppna komm. {f['oppna']}")
        elif a.cmd == "kontroll":
            saknas = va.kontroll()
            for s_ in saknas:
                print(f"saknar version: {s_['film']}/{s_['fil']}  ({s_['datum']})")
            print(f"{len(saknas)} färdiga filmer saknar version" if saknas else "alla färdiga filmer har en version")
            return 1 if saknas else 0
        elif a.cmd == "samla":
            nya = va.samla(av=a.av)
            for m in nya:
                print(f"version: {m['film']} {m['namn']} – {m['titel']}")
            print(f"{len(nya)} nya versioner")
        elif a.cmd == "importera":
            mapp = va.filmmapp(a.film)
            filer = sorted((mapp / "resultat").rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
            for f in filer:
                meta = va.spara(mapp, [f], andring=f"Importerad från resultat/{f.relative_to(mapp / 'resultat').as_posix()}",
                                titel=f.stem, kalla=[])
                print(f"{f.name}: {meta['namn'] if meta else 'fanns redan'}")
        elif a.cmd == "aterstall":
            print(f"byggunderlaget ligger i {va.aterstall(a.film, a.version)}")
        elif a.cmd == "uppdrag":
            print(va.uppdrag(a.film, a.version))
        elif a.cmd == "backup":
            if not a.mapp:
                print("ange --mapp <drive-mapp-id> eller GK_DRIVE_VERSIONER_ID", file=sys.stderr); return 2
            lista = [f for f in va.filmer() if not a.film or f["film"] == a.film]
            for f in lista:
                for v in va.versioner(f["film"]):
                    g = v["granskning"]
                    if g.get("status") == "utkast" and not g.get("kommentarer"):
                        continue  # ogranskad
                    if g.get("backup"):
                        continue
                    mapp = Path(v["mapp"])
                    filer = [mapp / x["namn"] for x in v["filer"]]
                    # filnamn i Drive: <film>__vNN__film-9x16.mp4
                    for p in filer:
                        namn = mapp.parent / f".{f['film']}__{v['namn']}__{p.name}"
                        if not namn.exists():
                            import shutil; shutil.copy2(p, namn)
                        r = subprocess.run([sys.executable, str(ROT / "scripts" / "drive_upload.py"), a.mapp, str(namn)])
                        namn.unlink(missing_ok=True)
                        if r.returncode:
                            raise va.ArkivFel(f"uppladdningen misslyckades: {p}")
                    gp = mapp / "granskning.json"
                    data = json.loads(gp.read_text(encoding="utf-8")); data["backup"] = va._nu()
                    gp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"backup: {f['film']} {v['namn']}")
    except va.ArkivFel as e:
        print(f"versioner: {e}", file=sys.stderr)
        return 0 if getattr(a, "tyst", False) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
