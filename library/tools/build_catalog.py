"""Build library/catalog.json and library/gallery.html from every library/**/LIBRARY.json.

Usage: python library/tools/build_catalog.py [--check]
--check validates only (exit 1 on problems) without writing files.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1]
ROOT = LIBRARY.parent

TYPES = {"template", "scene", "effect", "transition", "text", "caption", "grade", "background",
         "carousel", "skill", "prompt", "sound", "tool"}
MEDIA = {"video", "carousel", "image", "audio", "text"}
FORMATS = {"9:16", "1:1", "4:5", "16:9", "any"}
ENGINES = {"hyperframes", "remotion", "html-playwright", "python", "canvas", "none"}
COSTS = {"free", "paid"}
STATUSES = {"verified", "unverified", "broken"}
REQUIRED = ("id", "name", "type", "medium", "formats", "engine", "description", "tags", "path", "status")


def load_manifests() -> tuple[list[dict], list[str]]:
    items: list[dict] = []
    problems: list[str] = []
    seen: dict[str, str] = {}
    for manifest in sorted(LIBRARY.rglob("LIBRARY.json")):
        rel = manifest.relative_to(ROOT).as_posix()
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}: ogiltig JSON ({exc})")
            continue
        kit = data.get("kit") or manifest.parent.name
        source = data.get("source") or {}
        for index, item in enumerate(data.get("items", [])):
            where = f"{rel} items[{index}]"
            missing = [key for key in REQUIRED if key not in item]
            if missing:
                problems.append(f"{where}: saknar {', '.join(missing)}")
                continue
            item_id = item["id"]
            if item_id in seen:
                problems.append(f"{where}: id '{item_id}' finns redan i {seen[item_id]}")
            seen[item_id] = rel
            for key, allowed in (("type", TYPES), ("medium", MEDIA), ("engine", ENGINES), ("status", STATUSES)):
                if item[key] not in allowed:
                    problems.append(f"{where} ({item_id}): {key}='{item[key]}' är inte ett av {sorted(allowed)}")
            if item.get("cost", "free") not in COSTS:
                problems.append(f"{where} ({item_id}): cost='{item.get('cost')}'")
            bad_formats = [f for f in item["formats"] if f not in FORMATS]
            if bad_formats:
                problems.append(f"{where} ({item_id}): okända format {bad_formats}")
            path = item["path"]
            if not path.startswith(("http://", "https://")) and not (ROOT / path).exists():
                problems.append(f"{where} ({item_id}): path finns inte: {path}")
            preview = item.get("preview") or {}
            for kind in ("video", "still"):
                if preview.get(kind) and not (ROOT / preview[kind]).exists():
                    problems.append(f"{where} ({item_id}): preview.{kind} finns inte: {preview[kind]}")
            if item["status"] == "verified" and not preview:
                problems.append(f"{where} ({item_id}): verified kräver en preview")
            items.append({
                "kit": kit,
                "kit_title": data.get("title", kit),
                "source": source,
                "cost": "free",
                "requires": [],
                "use": "",
                "notes": "",
                "verified_at": None,
                "preview": None,
                **item,
            })
    items.sort(key=lambda i: (i["status"] != "verified", i["type"], i["id"]))
    return items, problems


def write_catalog(items: list[dict]) -> None:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["type"]] = counts.get(item["type"], 0) + 1
    catalog = {
        "version": 1,
        "generated": date.today().isoformat(),
        "count": len(items),
        "verified": sum(1 for i in items if i["status"] == "verified"),
        "by_type": dict(sorted(counts.items())),
        "items": items,
    }
    (LIBRARY / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


GALLERY = """<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Content Library</title>
<style>
:root{--bg:#0d1411;--card:#16201b;--line:#25332c;--ink:#eef3ef;--muted:#93a39a;--accent:#d6a536;--ok:#4ec27a;--warn:#e0a03a;--bad:#e05a4a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,Segoe UI,Inter,sans-serif}
header{position:sticky;top:0;z-index:2;background:rgba(13,20,17,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:14px 16px}
h1{margin:0 0 10px;font-size:18px}h1 small{color:var(--muted);font-weight:400}
.filters{display:flex;flex-wrap:wrap;gap:8px}
input,select{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:7px 9px;font:inherit}
input{flex:1;min-width:200px}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;display:flex;flex-direction:column}
.media{aspect-ratio:16/10;background:#000;display:grid;place-items:center;color:var(--muted);font-size:12px}
.media video,.media img{width:100%;height:100%;object-fit:contain;display:block}
.body{padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px}
.name{font-weight:600}.id{color:var(--muted);font:11px ui-monospace,Consolas,monospace;word-break:break-all}
.desc{color:#cfd9d3}.chips{display:flex;flex-wrap:wrap;gap:4px}
.chip{font-size:11px;padding:2px 7px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.chip.verified{color:var(--ok);border-color:var(--ok)}.chip.unverified{color:var(--warn);border-color:var(--warn)}.chip.broken{color:var(--bad);border-color:var(--bad)}
.chip.paid{color:var(--accent);border-color:var(--accent)}
.path{font:11px ui-monospace,Consolas,monospace;color:var(--muted);word-break:break-all}
.empty{padding:40px;color:var(--muted)}
</style>
</head>
<body>
<header>
<h1>Content Library <small id="count"></small></h1>
<div class="filters">
<input id="q" placeholder="Sök: namn, taggar, beskrivning, kit …" autofocus>
<select id="type"><option value="">Alla typer</option></select>
<select id="format"><option value="">Alla format</option></select>
<select id="kit"><option value="">Alla kit</option></select>
<select id="status"><option value="">Alla statusar</option><option>verified</option><option>unverified</option><option>broken</option></select>
</div>
</header>
<main id="grid"></main>
<script>
const ITEMS = __DATA__;
const $ = (s) => document.querySelector(s);
const uniq = (xs) => [...new Set(xs)].sort();
for (const [sel, vals] of [["#type", uniq(ITEMS.map(i => i.type))], ["#format", uniq(ITEMS.flatMap(i => i.formats))], ["#kit", uniq(ITEMS.map(i => i.kit))]])
  for (const v of vals) $(sel).insertAdjacentHTML("beforeend", `<option>${v}</option>`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function media(i) {
  const p = i.preview || {};
  if (p.video) return `<video src="../${esc(p.video)}" ${p.still ? `poster="../${esc(p.still)}"` : ""} muted loop playsinline preload="none" onmouseenter="this.play()" onmouseleave="this.pause()"></video>`;
  if (p.still) return `<img src="../${esc(p.still)}" loading="lazy" alt="">`;
  return "ingen förhandsvisning än";
}
function render() {
  const q = $("#q").value.trim().toLowerCase(), t = $("#type").value, f = $("#format").value, k = $("#kit").value, s = $("#status").value;
  const hits = ITEMS.filter(i => (!t || i.type === t) && (!f || i.formats.includes(f) || i.formats.includes("any")) && (!k || i.kit === k) && (!s || i.status === s)
    && (!q || [i.id, i.name, i.description, i.kit, i.use, ...(i.tags || [])].join(" ").toLowerCase().includes(q)));
  $("#count").textContent = `${hits.length} av ${ITEMS.length} · ${ITEMS.filter(i => i.status === "verified").length} verifierade`;
  $("#grid").innerHTML = hits.length ? hits.map(i => `<article class="card"><div class="media">${media(i)}</div><div class="body">
    <div class="name">${esc(i.name)}</div><div class="id">${esc(i.id)}</div><div class="desc">${esc(i.description)}</div>
    <div class="chips"><span class="chip ${esc(i.status)}">${esc(i.status)}</span><span class="chip">${esc(i.type)}</span><span class="chip">${esc(i.engine)}</span>
    ${i.formats.map(x => `<span class="chip">${esc(x)}</span>`).join("")}${i.cost === "paid" ? '<span class="chip paid">betald</span>' : ""}</div>
    ${i.use ? `<div class="desc"><b>Använd:</b> ${esc(i.use)}</div>` : ""}<div class="path">${esc(i.path)}</div></div></article>`).join("") : '<div class="empty">Inga träffar.</div>';
}
for (const el of ["#q", "#type", "#format", "#kit", "#status"]) $(el).addEventListener("input", render);
render();
</script>
</body>
</html>
"""


def write_gallery(items: list[dict]) -> None:
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    (LIBRARY / "gallery.html").write_text(GALLERY.replace("__DATA__", data), encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    items, problems = load_manifests()
    for problem in problems:
        print(f"  ✗ {problem}")
    if "--check" in sys.argv:
        print(f"{len(items)} poster, {len(problems)} problem")
        return 1 if problems else 0
    write_catalog(items)
    write_gallery(items)
    verified = sum(1 for i in items if i["status"] == "verified")
    print(f"✓ {len(items)} poster ({verified} verifierade) → library/catalog.json + library/gallery.html"
          + (f" · {len(problems)} problem" if problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
