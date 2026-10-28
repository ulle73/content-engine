"""Build library/catalog.json and library/gallery.html from every library/**/LIBRARY.json.

Usage: python library/tools/build_catalog.py [--check]
--check validates only (exit 1 on problems) without writing files.

Also validates every production recipe (library/recipes/<id>/recipe.json, schema recipe/v1): the exact
schema, that footage ids exist in docs/FILMLISTA.md, that effect/transition/music ids exist in the catalog,
that AI upgrades name a model playbook (library/models/<model>/PLAYBOOK.md) and that {fact:F<n>}
placeholders exist in the company's fact skill.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1]
ROOT = LIBRARY.parent

TYPES = {"template", "scene", "effect", "transition", "text", "caption", "grade", "background", "technique",
         "carousel", "skill", "prompt", "sound", "tool", "recipe", "model"}
MEDIA = {"video", "carousel", "image", "audio", "text"}
FORMATS = {"9:16", "1:1", "4:5", "16:9", "any"}
ENGINES = {"hyperframes", "remotion", "html-playwright", "python", "canvas", "blender", "none"}
COSTS = {"free", "paid"}
STATUSES = {"verified", "unverified", "broken"}
REQUIRED = ("id", "name", "type", "medium", "formats", "engine", "description", "tags", "path", "status")

# Production recipes (recipe/v1) and model playbooks – see "Recept och modell-playbooks" in library/README.md.
RECIPES = LIBRARY / "recipes"
MODELS = LIBRARY / "models"
FILMLISTA = ROOT / "docs" / "FILMLISTA.md"
FACT_SKILLS = {"faiv": ROOT / "skills" / "faiv-fakta" / "SKILL.md",
               "golfkuponger": ROOT / "skills" / "golfkuponger-friskvard" / "SKILL.md"}
RECIPE_KEYS = ("schema", "id", "company", "title", "type", "formats", "duration_s", "hook", "why_it_works",
               "references", "music", "scenes", "cta", "qa", "status")
SCENE_KEYS = ("id", "purpose", "duration_s", "source", "footage_ids", "catalog_query", "ai_upgrade", "text",
              "effects", "transition_in", "camera", "notes")
RECIPE_COMPANIES = {"faiv", "golfkuponger", "any"}
RECIPE_TYPES = {"before-after", "sketch", "pov", "product-in-context", "tips", "seasonal", "testimonial", "mood",
                "match-cut"}
RECIPE_FORMATS = {"9:16", "4:5", "1:1", "16:9"}
RECIPE_STATUSES = {"draft", "verified"}
SCENE_SOURCES = {"footage", "product_image", "ai_video", "ai_image", "graphic"}
NOT_SCENE_ELEMENTS = {"recipe", "model", "template", "skill", "tool", "carousel"}
FACT_PLACEHOLDER = re.compile(r"\{fact:([A-Za-z0-9_-]+)\}")


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
            # tekniker är godkända genom sitt bevis (länk/egen film); en preview är bra men inget krav
            if item["status"] == "verified" and not preview and item["type"] != "technique":
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
    problems.extend(recipe_problems(items))
    return items, problems


def footage_ids() -> set[str]:
    """Shot ids such as `fa-m1`, `gk-o1`, `bo-1` from the shot list docs/FILMLISTA.md."""
    if not FILMLISTA.exists():
        return set()
    return set(re.findall(r"^- `([a-z]{2}-[a-z0-9]+)`", FILMLISTA.read_text(encoding="utf-8"), re.MULTILINE))


def fact_ids(company: str) -> set[str] | None:
    """Fact ids (F1, F2 …) in the company's fact skill; None when the company has no fact skill."""
    path = FACT_SKILLS.get(company)
    if not path or not path.exists():
        return None
    return set(re.findall(r"^\| (F\d+) \|", path.read_text(encoding="utf-8"), re.MULTILINE))


def model_ids() -> set[str]:
    """Model playbooks: library/models/<model>/PLAYBOOK.md."""
    return {p.parent.name for p in MODELS.glob("*/PLAYBOOK.md")} if MODELS.exists() else set()


def _is_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _validate_scene(scene, at: str, *, catalog: dict[str, dict], footage: set[str], models: set[str]) -> list[str]:
    if not isinstance(scene, dict):
        return [f"{at}: måste vara ett objekt"]
    if missing := [k for k in SCENE_KEYS if k not in scene]:
        return [f"{at}: saknar {', '.join(missing)}"]
    problems: list[str] = []
    if extra := sorted(set(scene) - set(SCENE_KEYS)):
        problems.append(f"{at}: okända fält {extra} (recipe/v1 är exakt)")
    at = f"{at} ({scene['id']})"
    if not _is_text(scene["id"]) or not _is_text(scene["purpose"]):
        problems.append(f"{at}: id och purpose måste vara texter")
    if not _is_number(scene["duration_s"]):
        problems.append(f"{at}: duration_s måste vara ett positivt tal")
    source = scene["source"]
    if source not in SCENE_SOURCES:
        problems.append(f"{at}: source='{source}' är inte ett av {sorted(SCENE_SOURCES)}")
    elif source in {"ai_video", "ai_image"} and scene.get("ai_upgrade") is None:
        problems.append(f"{at}: source='{source}' kräver ai_upgrade {{model, prompt_template}} som beskriver genereringen")
    shots = scene["footage_ids"]
    if not (isinstance(shots, list) and all(isinstance(s, str) for s in shots)):
        problems.append(f"{at}: footage_ids måste vara en lista med id:n")
    else:
        if source == "footage" and not shots:
            problems.append(f"{at}: source=footage kräver minst ett footage_id")
        if unknown := [s for s in shots if s not in footage]:
            problems.append(f"{at}: footage_ids finns inte i docs/FILMLISTA.md: {unknown}")
    query = scene["catalog_query"]
    if query is not None and not _is_text(query):
        problems.append(f"{at}: catalog_query måste vara null eller en text")
    if source == "product_image" and not _is_text(query):
        problems.append(f"{at}: source=product_image kräver catalog_query (sökning i produktkatalogen)")
    upgrade = scene["ai_upgrade"]
    if upgrade is not None:
        if not (isinstance(upgrade, dict) and set(upgrade) == {"model", "prompt_template"}):
            problems.append(f"{at}: ai_upgrade måste vara null eller {{model, prompt_template}}")
        else:
            if upgrade["model"] not in models:
                problems.append(f"{at}: ai_upgrade.model '{upgrade['model']}' saknar library/models/<modell>/PLAYBOOK.md "
                                f"(finns: {sorted(models)})")
            if not _is_text(upgrade["prompt_template"]):
                problems.append(f"{at}: ai_upgrade.prompt_template måste vara en text")
    for key in ("text", "camera", "notes"):
        if not isinstance(scene[key], str):
            problems.append(f"{at}: {key} måste vara en sträng (tom om inget)")
    effects = scene["effects"]
    if not (isinstance(effects, list) and all(isinstance(e, str) for e in effects)):
        problems.append(f"{at}: effects måste vara en lista med katalog-id:n")
    else:
        for effect in effects:
            entry = catalog.get(effect)
            if entry is None:
                problems.append(f"{at}: effect '{effect}' finns inte i catalog.json")
            elif entry["type"] in NOT_SCENE_ELEMENTS:
                problems.append(f"{at}: effect '{effect}' är av typen {entry['type']}, inte ett scenelement")
    transition = scene["transition_in"]
    if transition is not None and (catalog.get(transition) or {}).get("type") != "transition":
        problems.append(f"{at}: transition_in '{transition}' är inte en transition-post i catalog.json")
    return problems


def validate_recipe(data, *, catalog: dict[str, dict], footage: set[str], models: set[str],
                    where: str = "recipe") -> list[str]:
    """Problems with one recipe/v1 document (empty list = valid)."""
    if not isinstance(data, dict):
        return [f"{where}: måste vara ett JSON-objekt"]
    if missing := [k for k in RECIPE_KEYS if k not in data]:
        return [f"{where}: saknar {', '.join(missing)}"]
    problems: list[str] = []
    if extra := sorted(set(data) - set(RECIPE_KEYS)):
        problems.append(f"{where}: okända fält {extra} (recipe/v1 är exakt)")
    where = f"{where} ({data['id']})"
    if data["schema"] != "recipe/v1":
        problems.append(f"{where}: schema='{data['schema']}', ska vara 'recipe/v1'")
    if not (isinstance(data["id"], str) and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", data["id"])):
        problems.append(f"{where}: id ska vara gemener-med-bindestreck")
    for key, allowed in (("company", RECIPE_COMPANIES), ("type", RECIPE_TYPES), ("status", RECIPE_STATUSES)):
        if data[key] not in allowed:
            problems.append(f"{where}: {key}='{data[key]}' är inte ett av {sorted(allowed)}")
    for key in ("title", "hook", "why_it_works"):
        if not _is_text(data[key]):
            problems.append(f"{where}: {key} måste vara en icke-tom text")
    formats = data["formats"]
    if not (isinstance(formats, list) and formats and all(f in RECIPE_FORMATS for f in formats)):
        problems.append(f"{where}: formats måste vara en icke-tom lista av {sorted(RECIPE_FORMATS)}")
    if not _is_number(data["duration_s"]):
        problems.append(f"{where}: duration_s måste vara ett positivt tal")
    references = data["references"]
    if not (isinstance(references, list) and references and all(
            isinstance(r, dict) and set(r) == {"label", "url"} and _is_text(r["label"])
            and str(r["url"]).startswith(("http://", "https://")) for r in references)):
        problems.append(f"{where}: references måste vara minst en {{label, url}} med http(s)-url")
    music = data["music"]
    if not (isinstance(music, dict) and set(music) == {"mood", "bpm", "library_id"}):
        problems.append(f"{where}: music måste ha exakt mood, bpm, library_id")
    else:
        if not _is_text(music["mood"]):
            problems.append(f"{where}: music.mood måste vara en text")
        bpm = music["bpm"]
        if bpm is not None and not (isinstance(bpm, int) and not isinstance(bpm, bool) and 40 <= bpm <= 220):
            problems.append(f"{where}: music.bpm måste vara null eller ett heltal 40–220")
        library_id = music["library_id"]
        if library_id is not None and (catalog.get(library_id) or {}).get("type") != "sound":
            problems.append(f"{where}: music.library_id '{library_id}' är inte en sound-post i catalog.json")
    cta = data["cta"]
    if not (isinstance(cta, dict) and set(cta) == {"text", "landing"} and _is_text(cta["text"])
            and _is_text(cta["landing"])):
        problems.append(f"{where}: cta måste ha exakt text och landing")
    qa = data["qa"]
    if not (isinstance(qa, list) and qa and all(_is_text(q) for q in qa)):
        problems.append(f"{where}: qa måste vara en icke-tom lista med kontrollpunkter")
    scenes = data["scenes"]
    if not (isinstance(scenes, list) and scenes):
        return problems + [f"{where}: scenes måste vara en icke-tom lista"]
    scene_ids = [s.get("id") for s in scenes if isinstance(s, dict)]
    if len(scene_ids) != len(set(scene_ids)):
        problems.append(f"{where}: scen-id:n måste vara unika")
    for index, scene in enumerate(scenes):
        problems += _validate_scene(scene, f"{where} scenes[{index}]", catalog=catalog, footage=footage, models=models)
    total = sum(s["duration_s"] for s in scenes if isinstance(s, dict) and _is_number(s.get("duration_s")))
    if _is_number(data["duration_s"]) and abs(total - data["duration_s"]) > 0.51:
        problems.append(f"{where}: scenernas längd ({total:g} s) ≠ duration_s ({data['duration_s']} s)")
    facts = fact_ids(data["company"])
    if facts is not None:
        texts = [data["hook"], cta.get("text") if isinstance(cta, dict) else ""]
        texts += [s.get("text") for s in scenes if isinstance(s, dict)]
        used = {fact for text in texts if isinstance(text, str) for fact in FACT_PLACEHOLDER.findall(text)}
        skill = FACT_SKILLS[data["company"]].relative_to(ROOT).as_posix()
        problems += [f"{where}: {{fact:{fact}}} finns inte i {skill}" for fact in sorted(used - facts)]
    return problems


def recipe_problems(items: list[dict]) -> list[str]:
    """Validate every library/recipes/<id>/recipe.json and its catalog entry `recipe.<id>`."""
    if not RECIPES.exists():
        return []
    catalog = {item["id"]: item for item in items}
    footage, models = footage_ids(), model_ids()
    problems: list[str] = []
    found: set[str] = set()
    for path in sorted(RECIPES.glob("*/recipe.json")):
        rel = path.relative_to(ROOT).as_posix()
        found.add(path.parent.name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}: ogiltig JSON ({exc})")
            continue
        problems += validate_recipe(data, catalog=catalog, footage=footage, models=models, where=rel)
        if not isinstance(data, dict) or data.get("id") != path.parent.name:
            problems.append(f"{rel}: id ska vara samma som mappnamnet '{path.parent.name}'")
        if not (path.parent / "RECIPE.md").exists():
            problems.append(f"{rel}: RECIPE.md saknas bredvid recipe.json")
        entry = catalog.get(f"recipe.{path.parent.name}")
        if entry is None or entry["type"] != "recipe":
            problems.append(f"{rel}: saknar posten 'recipe.{path.parent.name}' (type recipe) i library/recipes/LIBRARY.json")
    for item in items:
        if item["type"] == "recipe" and item["id"].removeprefix("recipe.") not in found:
            problems.append(f"{item['id']}: recipe-post utan library/recipes/<id>/recipe.json")
    return problems


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
