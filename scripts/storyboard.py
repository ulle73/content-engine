#!/usr/bin/env python3
"""Storyboard-arket: hela filmen på EN bild, godkänns innan något byggs.

Varje scen är ett numrerat kort med bild och fälten Tid · I bild · Rörelse · Blir (hur scenen går över i nästa) ·
Ljud · Text. Överst: filmens idé, regler och valda tekniker. Arket kontrollerar läsregeln per text och att tidslinjen
hänger ihop, och ritar plattformens osäkra zoner på varje bild (värdena läses ur edit-renderer/src/safezones.js).

  python scripts/storyboard.py work/<film>                     # film.json → "storyboard" → out/storyboard.png
  python scripts/storyboard.py work/<film> --stillbilder       # renderar stillbilder via filmens render.mjs först
  python scripts/storyboard.py work/<film> --fran-video out/utkast.mp4   # bilder ur ett utkast/en referens
  python scripts/storyboard.py work/<film> --godkann --av Jonas            # efter Jonas "godkänt": låser upp ./make.sh bild
  python scripts/storyboard.py work/references/<slug> --fran-rea work/references/<slug>/rea
      # referensens berättelse (rea-video) som storyboard i vårt format → storyboard-referens.json + out/storyboard-referens.png;
      # kopiera sedan in den i den nya filmens film.json och skriv om varje scen till vårt innehåll

Storyboarden kan också ligga i en egen fil (work/<film>/storyboard.json eller --json <fil>) med samma innehåll.

"storyboard": {
  "titel": "Spelat den här? · 22 s · 9:16", "sammanfattning": "Två meningar om hela filmen.",
  "format": "9:16", "regler": ["en textposition, y 560", "Spotlight sist"],
  "tekniker": ["Krok: teknik.fragor-som-krok – ...", "CTA: ..."],
  "referens": "work/references/<slug>/VIDEO.md (valfritt)",
  "scener": [
    {"tid": [0, 2.4], "titel": "Krok", "bild": "out/stills/t1.20.png", "still": 1.2,
     "i_bild": "...", "rorelse": "...", "blir": "...", "ljud": "...", "text": "KÖR DU {DEN HÄR?}", "text_tid": [0.15, 2.4]}
  ]
}
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFEZONES_JS = ROOT / "edit-renderer" / "src" / "safezones.js"

# Läsregeln, samma som engine/edit/spec.py (mellanslag och skiljetecken räknas).
READ_CPS, READ_MIN_S, READ_OVERHEAD_S = 12.0, 5 / 6, 0.9
try:  # håll värdena i synk med motorn när den går att läsa in
    sys.path.insert(0, str(ROOT))
    from engine.edit.spec import READ_CPS, READ_MIN_S, READ_OVERHEAD_S  # type: ignore  # noqa: F811
except Exception:
    pass

ASPECT = {"9:16": (9, 16), "4:5": (4, 5), "1:1": (1, 1), "16:9": (16, 9)}
COLUMNS = {"9:16": 6, "4:5": 5, "1:1": 5, "16:9": 4}
CHROME = [
    Path(r"C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


def safe_zones(fmt: str) -> dict:
    """Plattformens osäkra band som andelar, ur safezones.js (aldrig egna siffror)."""
    text = SAFEZONES_JS.read_text(encoding="utf-8")
    m = re.search(r"'" + re.escape(fmt) + r"'\s*:\s*\{([^}]*)\}", text)
    if not m:
        return {}
    return {k: float(v) for k, v in re.findall(r"(top|bottom|left|right)\s*:\s*([0-9.]+)", m.group(1))}


def read_need(text: str) -> float:
    n = len(re.sub(r"[{}\[\]]", "", text).replace("\n", " ").strip())
    return max(READ_MIN_S, n / READ_CPS) + READ_OVERHEAD_S


def load_board(folder: Path, json_path: Path | None) -> tuple[dict, Path, str | None]:
    """Returnerar (storyboard, filen den ligger i, nyckel eller None om hela filen är storyboarden)."""
    candidates = [json_path] if json_path else [folder / "film.json", folder / "storyboard.json"]
    for p in candidates:
        if p and p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if "storyboard" in data:
                return data["storyboard"], p, "storyboard"
            if "scener" in data:
                return data, p, None
    sys.exit(f"Ingen storyboard hittades i {', '.join(str(c) for c in candidates if c)} "
             "(lägg ett \"storyboard\"-block i film.json, se --help).")


def check(board: dict) -> list[tuple[int | None, str, str]]:
    """(scen eller None, nivå 'fel'/'varning', text)."""
    out: list[tuple[int | None, str, str]] = []
    scener = board.get("scener") or []
    if not scener:
        out.append((None, "fel", "storyboarden har inga scener"))
    prev_end = None
    for i, s in enumerate(scener, 1):
        t = s.get("tid")
        if not (isinstance(t, list) and len(t) == 2 and t[1] > t[0]):
            out.append((i, "fel", "tid saknas eller är fel (ska vara [start, slut] i sekunder)"))
            continue
        if prev_end is not None and abs(t[0] - prev_end) > 0.05:
            out.append((i, "varning", f"glapp/överlapp mot förra scenen ({prev_end:g} → {t[0]:g} s)"))
        prev_end = t[1]
        if board.get("referensutkast"):
            continue
        if i < len(scener) and not (s.get("blir") or "").strip():
            out.append((i, "varning", "”Blir” saknas – hur går scenen över i nästa?"))
        if not (s.get("rorelse") or "").strip():
            out.append((i, "varning", "”Rörelse” saknas – något ska röra sig i varje scen"))
        txt = (s.get("text") or "").strip()
        if txt:
            tt = s.get("text_tid") or t
            dur, need = tt[1] - tt[0], read_need(txt)
            if dur + 1e-6 < need:
                out.append((i, "fel", f"läsregeln: texten syns {dur:.2f} s men behöver {need:.2f} s"))
    return out


ROLLER = {"hook": "Krok", "context": "Bakgrund", "info": "Information", "proof": "Bevis", "turn": "Vändning",
          "payoff": "Slutsats", "cta": "Uppmaning", "mood": "Stämning"}
OVERGANG = {"cut": "hårt klipp", "dissolve": "övertoning", "fade": "tona", "wipe": "avtäckning", "start": "start"}


def board_from_rea(rea: Path) -> dict:
    """Gör referensens nedbrytning (rea-video breakdown.json) till ett storyboard-utkast: ett kort per berättelsesteg."""
    b = json.loads((rea / "breakdown.json").read_text(encoding="utf-8"))
    shots = {int(s["index"]) if "index" in s else n: s for n, s in enumerate(b.get("shots") or [], 1)}
    src = b.get("source") or {}
    steg = b.get("narrative") or [{"start": s["start"], "end": s["end"], "shots": [i], "role": "", "points": []}
                                  for i, s in shots.items()]

    def desc(s):
        return ((s.get("review") or {}).get("description") or (s.get("vlm") or {}).get("description") or "").strip()

    scener = []
    for k, st in enumerate(steg):
        nums = st.get("shots") or []
        first = shots.get(nums[0]) if nums else None
        nxt = shots.get((steg[k + 1].get("shots") or [None])[0]) if k + 1 < len(steg) else None
        bild = rea / "shots" / f"shot_{nums[0]:03d}_first.jpg" if nums else None
        ov = OVERGANG.get(str((nxt or {}).get("transition_in") or ""), str((nxt or {}).get("transition_in") or ""))
        scener.append({
            "tid": [round(float(st["start"]), 2), round(float(st["end"]), 2)],
            "titel": f"{ROLLER.get(st.get('role', ''), st.get('role') or 'Scen')} · klipp {', '.join(map(str, nums))}",
            "bild": str(bild) if bild and bild.exists() else None,
            "i_bild": " / ".join(d for d in (desc(shots[i]) for i in nums if i in shots) if d),
            "rorelse": "",
            "blir": f"{ov} till nästa" if ov else "",
            "ljud": "",
            "poang": " → ".join(st.get("points") or []),
        })
    w, h = src.get("width") or 1080, src.get("height") or 1920
    fmt = min(ASPECT, key=lambda f: abs(ASPECT[f][0] / ASPECT[f][1] - w / h))
    summ = (b.get("review_story") or {}).get("summary") or ""
    return {"referensutkast": True, "titel": f"REFERENS: {rea.parent.name} · {src.get('duration', 0):.0f} s · {fmt}",
            "sammanfattning": summ or "Referensens berättelse steg för steg (rea-video). Behåll ordningen och varje stegs uppgift – fyll med vårt innehåll.",
            "format": fmt, "regler": ["referensens berättelse – byt innehållet, behåll uppgiften i varje steg",
                                      "låna mekaniken, aldrig bilder, personer, formuleringar eller musik"],
            "tekniker": [], "referens": str(rea / "VIDEO.md"), "scener": scener}


def frame_from_video(video: Path, t: float, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=720:-2", str(dest)], capture_output=True)
    return r.returncode == 0 and dest.exists()


def render_stills(folder: Path, times: list[float]) -> None:
    if not (folder / "render.mjs").exists():
        sys.exit("--stillbilder: filmen har ingen render.mjs – ange \"bild\" per scen eller --fran-video.")
    arg = ",".join(f"{t:.2f}" for t in times)
    if len(times) == 1:
        arg = f"{arg},{arg}"
    subprocess.run(["node", "render.mjs", "stills", arg, "out/storyboard/stills-ark.png"], cwd=folder, check=True)


def esc(s) -> str:
    return html.escape(str(s or ""))


def mark_words(s: str) -> str:
    """{ord} = markerat ord, som i film.json."""
    return re.sub(r"\{([^}]*)\}", r"<mark>\1</mark>", esc(s)).replace("\n", "<br>")


def build_html(board: dict, frames: list[str | None], problems, fmt: str, zones: dict) -> str:
    aw, ah = ASPECT.get(fmt, (9, 16))
    cols = COLUMNS.get(fmt, 6)
    scener = board.get("scener") or []
    total = max((s["tid"][1] for s in scener if isinstance(s.get("tid"), list) and len(s["tid"]) == 2), default=0)
    by_scene: dict[int | None, list] = {}
    for i, lvl, msg in problems:
        by_scene.setdefault(i, []).append((lvl, msg))

    z = zones
    zone_css = ""
    if z:
        zone_css = (f".zones{{position:absolute;inset:0;pointer-events:none}}"
                    f".zones i{{position:absolute;background:rgba(214,40,40,.16)}}"
                    f".zones .t{{left:0;right:0;top:0;height:{z.get('top',0)*100:.2f}%;border-bottom:2px solid rgba(214,40,40,.8)}}"
                    f".zones .b{{left:0;right:0;bottom:0;height:{z.get('bottom',0)*100:.2f}%;border-top:2px solid rgba(214,40,40,.8)}}"
                    f".zones .l{{left:0;top:0;bottom:0;width:{z.get('left',0)*100:.2f}%;border-right:2px solid rgba(214,40,40,.8)}}"
                    f".zones .r{{right:0;top:0;bottom:0;width:{z.get('right',0)*100:.2f}%;border-left:2px solid rgba(214,40,40,.8)}}")

    cards = []
    for n, (s, img) in enumerate(zip(scener, frames), 1):
        t = s.get("tid") or [0, 0]
        rows = []
        for key, label in (("poang", "Poäng"), ("i_bild", "I bild"), ("rorelse", "Rörelse"), ("blir", "Blir"), ("ljud", "Ljud")):
            if s.get(key):
                rows.append(f'<dt>{label}</dt><dd class="{key}">{esc(s[key])}</dd>')
        if s.get("text"):
            tt = s.get("text_tid") or t
            need = read_need(s["text"])
            ok = (tt[1] - tt[0]) + 1e-6 >= need
            rows.append(f'<dt>Text</dt><dd class="txt">{mark_words(s["text"])}'
                        f'<span class="read {"ok" if ok else "bad"}">{tt[1]-tt[0]:.1f} s / behöver {need:.1f} s</span></dd>')
        warn = "".join(f'<li class="{lvl}">{esc(msg)}</li>' for lvl, msg in by_scene.get(n, []))
        pic = (f'<img src="{esc(img)}">' if img else
               f'<div class="empty">{esc(s.get("skiss") or "Ingen bild ännu")}</div>')
        cards.append(f'''<section class="shot{' has-bad' if any(l=='fel' for l,_ in by_scene.get(n,[])) else ''}">
  <div class="frame">{pic}<div class="zones"><i class="t"></i><i class="b"></i><i class="l"></i><i class="r"></i></div><span class="num">{n}</span></div>
  <div class="body"><div class="time">{t[0]:.1f}–{t[1]:.1f} s · {t[1]-t[0]:.1f} s</div><h2>{esc(s.get("titel"))}</h2>
  <dl>{''.join(rows)}</dl>{f'<ul class="warn">{warn}</ul>' if warn else ''}</div></section>''')

    rules = "".join(f"<li>{esc(r)}</li>" for r in board.get("regler") or [])
    tekn = "".join(f"<li>{esc(r)}</li>" for r in board.get("tekniker") or [])
    general = "".join(f'<li class="{lvl}">{esc(msg)}</li>' for lvl, msg in by_scene.get(None, []))
    n_bad = sum(1 for _, lvl, _ in problems if lvl == "fel")
    status = ("Referensens berättelse – underlag för vår version, inte vår film." if board.get("referensutkast") else
              f'<b class="bad">{n_bad} fel att rätta före godkännande</b>' if n_bad else
              (f'<b class="ok">Godkänd {esc(board["godkand"])}</b>' if board.get("godkand") else
               "Godkänn, eller be om ändringar, innan något byggs."))
    ref = f'<p class="ref">Referens: {esc(board["referens"])}</p>' if board.get("referens") else ""
    return f'''<!doctype html><html lang="sv"><head><meta charset="utf-8"><style>
:root{{--paper:#f4f1ea;--ink:#16201b;--soft:#5d6660;--rule:#d9d3c5;--card:#fbfaf6;--clay:#c2410c;--green:#14532d;--gold:#b88a1b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.42 "Segoe UI","Helvetica Neue",Arial,sans-serif;padding:40px 44px 48px;width:1920px}}
header{{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:16px}}
h1{{font-size:34px;line-height:1.1;margin:0 0 8px}}header p{{margin:0;max-width:1300px;color:var(--soft);font-size:17px}}.ref{{font-size:14px!important;margin-top:6px!important}}
.facts{{text-align:right;color:var(--soft);white-space:nowrap}}.facts b{{display:block;color:var(--ink);font-size:24px}}
.meta{{display:grid;grid-template-columns:1fr 1fr;gap:6px 40px;margin:14px 0 22px}}.meta h3{{margin:0 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--soft)}}
.meta ul{{margin:0;padding:0;list-style:none;font-size:14px}}.meta li::before{{content:"— ";color:var(--clay)}}
.shots{{display:grid;grid-template-columns:repeat({cols},1fr);gap:22px 18px}}
.shot{{background:var(--card);border:1px solid var(--rule)}}.shot.has-bad{{border:2px solid #d62828}}
.frame{{position:relative;aspect-ratio:{aw}/{ah};background:#e4dfd2;overflow:hidden}}
.frame img{{width:100%;height:100%;object-fit:cover;display:block}}
.frame .empty{{position:absolute;inset:0;display:grid;place-items:center;color:var(--soft);font-size:14px;padding:16px;text-align:center}}
{zone_css}
.num{{position:absolute;left:0;top:0;background:var(--ink);color:var(--paper);font-weight:700;font-size:19px;width:38px;height:38px;display:grid;place-items:center}}
.body{{padding:12px 13px 14px}}.time{{font-size:13px;color:var(--soft);font-variant-numeric:tabular-nums}}
h2{{font-size:18px;margin:2px 0 8px;line-height:1.2}}dl{{margin:0;display:grid;grid-template-columns:62px 1fr;gap:5px 8px;font-size:13.5px}}
dt{{color:var(--soft);font-size:12.5px;padding-top:1px}}dd{{margin:0}}dd.blir{{font-weight:650}}
dd.txt{{font-weight:600}}dd.poang{{color:var(--clay);font-weight:600}}mark{{background:var(--gold);color:#fff;padding:0 3px}}
.read{{display:block;font-weight:400;font-size:12px;margin-top:2px}}.read.ok{{color:var(--green)}}.read.bad{{color:#d62828;font-weight:700}}
.warn{{margin:8px 0 0;padding:0;list-style:none;font-size:12.5px}}.warn li.fel,.general li.fel{{color:#d62828;font-weight:650}}.warn li.varning,.general li.varning{{color:#a16207}}
.general{{margin:0 0 16px;padding:0;list-style:none}}
footer{{margin-top:26px;padding-top:12px;border-top:1px solid var(--rule);color:var(--soft);font-size:14px;display:flex;justify-content:space-between;gap:24px}}
b.bad{{color:#d62828}}b.ok{{color:var(--green)}}
</style></head><body>
<header><div><h1>{esc(board.get("titel") or "Storyboard")}</h1><p>{esc(board.get("sammanfattning"))}</p>{ref}</div>
<div class="facts"><b>{total:.1f} s</b>{len(scener)} scener · {esc(fmt)}</div></header>
<div class="meta"><div><h3>Regler för hela filmen</h3><ul>{rules}</ul></div><div><h3>Valda tekniker</h3><ul>{tekn}</ul></div></div>
{f'<ul class="general">{general}</ul>' if general else ''}
<main class="shots">{''.join(cards)}</main>
<footer><span>Röda band = plattformens osäkra zoner ({esc(fmt)}). Läsregeln: max(5/6 s, tecken/12) + 0,9 s.</span><span>{status}</span></footer>
</body></html>'''


def find_chrome() -> Path:
    for c in CHROME:
        if c.exists():
            return c
    found = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("msedge")
    if found:
        return Path(found)
    sys.exit("Hittar ingen Chrome/Edge att rendera arket med.")


def screenshot(html_file: Path, png: Path, height: int) -> None:
    from PIL import Image  # Pillow finns i projektets .venv

    tmp = png.with_suffix(".tmp.png")
    subprocess.run([str(find_chrome()), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size=1920,{height}",
                    f"--screenshot={tmp}", "--virtual-time-budget=4000", html_file.resolve().as_uri()],
                   check=True, capture_output=True)
    im = Image.open(tmp).convert("RGB")
    # beskär tom papperyta nertill (höjden gissas generöst)
    bg = im.getpixel((5, im.height - 5))
    px, last = im.load(), 0
    for y in range(im.height - 1, 0, -4):
        if any(px[x, y] != bg for x in range(0, im.width, 7)):
            last = y
            break
    im.crop((0, 0, im.width, min(im.height, last + 48))).save(png, optimize=True)
    tmp.unlink(missing_ok=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mapp", help="filmens mapp, t.ex. work/gk-banor")
    ap.add_argument("--json", type=Path, help="annan fil än film.json/storyboard.json")
    ap.add_argument("--fran-video", type=Path, help="ta bilderna ur en video (utkast eller referens) vid scenernas 'still'/mitt")
    ap.add_argument("--stillbilder", action="store_true", help="rendera stillbilder med filmens render.mjs först")
    ap.add_argument("--ut", type=Path, help="var arket skrivs (standard <mapp>/out/storyboard.png)")
    ap.add_argument("--godkann", action="store_true", help="markera storyboarden som godkänd (bara efter beställarens ja)")
    ap.add_argument("--av", default="Jonas", help="vem som godkände (med --godkann)")
    ap.add_argument("--fran-rea", type=Path, help="gör ett storyboard-utkast av en rea-video-nedbrytning (mappen med breakdown.json)")
    a = ap.parse_args(argv)

    folder = Path(a.mapp).resolve()
    if a.fran_rea:
        draft = board_from_rea(a.fran_rea.resolve())
        a.json = folder / "storyboard-referens.json"
        a.json.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        a.ut = a.ut or folder / "out" / "storyboard-referens.png"
        print(f"utkast: {a.json}")
    board, src, key = load_board(folder, a.json.resolve() if a.json else None)
    problems = check(board)

    if a.godkann:
        bad = [p for p in problems if p[1] == "fel"]
        if bad:
            for i, _, msg in bad:
                print(f"FEL scen {i}: {msg}")
            print("Rätta felen innan storyboarden kan godkännas.")
            return 1
        data = json.loads(src.read_text(encoding="utf-8"))
        stamp = f"{dt.date.today().isoformat()} {a.av}"
        (data[key] if key else data)["godkand"] = stamp
        if src.name == "film.json":
            data["storyboard_godkand"] = stamp
        src.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"storyboarden godkänd: {stamp} ({src})")
        board = data[key] if key else data

    fmt = board.get("format") or "9:16"
    scener = board.get("scener") or []
    out_png = (a.ut or folder / "out" / "storyboard.png").resolve()
    work = out_png.parent / "storyboard"
    work.mkdir(parents=True, exist_ok=True)

    def still_time(s):
        t = s.get("tid") or [0, 0]
        return float(s.get("still", (t[0] + t[1]) / 2 if len(t) == 2 else 0))

    if a.stillbilder:
        render_stills(folder, [still_time(s) for s in scener])
    frames: list[str | None] = []
    for n, s in enumerate(scener, 1):
        img = None
        if s.get("bild") and (folder / s["bild"]).exists():
            img = (folder / s["bild"]).resolve()
        elif a.stillbilder and (folder / "out" / "stills" / f"t{still_time(s):.2f}.png").exists():
            img = (folder / "out" / "stills" / f"t{still_time(s):.2f}.png").resolve()
        elif a.fran_video:
            dest = work / f"scen-{n:02d}.jpg"
            if frame_from_video(a.fran_video.resolve(), still_time(s), dest):
                img = dest
        frames.append(img.as_uri() if img else None)

    zones = safe_zones(fmt)
    page = work / "storyboard.html"
    page.write_text(build_html(board, frames, problems, fmt, zones), encoding="utf-8")
    cols = COLUMNS.get(fmt, 6)
    aw, ah = ASPECT.get(fmt, (9, 16))
    card_w = (1920 - 88 - (cols - 1) * 18) / cols
    rows = math.ceil(max(len(scener), 1) / cols)
    height = int(420 + rows * (card_w * ah / aw + 560) + 200)
    screenshot(page, out_png, height)

    for i, lvl, msg in problems:
        print(f"{lvl.upper():8} {'scen ' + str(i) if i else 'filmen'}: {msg}")
    print(f"storyboard: {out_png}  ({len(scener)} scener, {fmt})")
    if board.get("referensutkast"):
        print("Referensens berättelse som storyboard. Kopiera till den nya filmens film.json (\"storyboard\"), ta bort "
              "\"referensutkast\" och skriv om varje scen till vårt innehåll.")
    elif not board.get("godkand"):
        print("Visa arket för beställaren och vänta på godkännande. Därefter: --godkann (låser upp ./make.sh bild).")
    return 1 if any(lvl == "fel" for _, lvl, _ in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
