"""Bygger LIBRARY.json för yihui-dev/awesome-opus5-5-videos.

Användning (från repots rot):
  curl -sL https://raw.githubusercontent.com/yihui-dev/awesome-opus5-5-videos/main/data/videos.json -o work/opus55-import/videos.json
  python library/external/opus55-videos-yihui/make_library.py work/opus55-import/videos.json

Läser våra egna svenska sammanfattningar ur summaries.json i samma mapp. Prompttexterna
kopieras inte – posterna länkar till originalet.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = "opus55-videos-yihui"
REPO = "https://github.com/yihui-dev/awesome-opus5-5-videos"
SKILLRY = "https://skillry.dev/ai-videos/opus-5-5"

CATEGORIES = {
    "motion": ("Motion graphics", "Kodade motion graphics: kinetisk typografi, partiklar, former och loopar."),
    "explainer": ("Explainers", "Kodade förklaringsvideor: processer, data, anatomi, recept och koncept steg för steg."),
    "3d": ("3D-scener", "Kodade 3D-scener i Three.js/WebGL: objekt, miljöer, kamerafärder och shaders."),
    "interactive": ("Spel och interaktivt", "Kodade spel och interaktiva upplevelser som går att spela in som video."),
}
ENGINE = {"three.js": "canvas", "canvas": "canvas", "webgl": "canvas", "glsl": "canvas"}


def entry(**kw):
    base = {"medium": "text", "formats": ["any"], "engine": "none", "requires": [], "cost": "free",
            "status": "unverified", "verified_at": None, "preview": None}
    base.update(kw)
    return base


def main(videos_path):
    videos = json.loads(Path(videos_path).read_text(encoding="utf-8"))
    by_slug = {v["slug"]: v for v in videos}
    summaries = json.loads((HERE / "summaries.json").read_text(encoding="utf-8"))
    counts = {c: sum(1 for v in videos if v["category"] == c) for c in CATEGORIES}

    items = [entry(
        id=f"ext.{KIT}.gallery",
        name="Opus 5.5-videor – galleri med remakes (Skillry)",
        type="prompt",
        description=f"{len(videos)} prompts för kodade videor gjorda med Claude Opus 5.5; "
                    f"{sum(v['has_remake'] for v in videos)} med original bredvid levande remake.",
        tags=["galleri", "inspiration", "prompts", "opus-5-5", "kodad video", "motion"],
        path=SKILLRY,
        use="Bläddra för inspiration; öppna en post och läs prompten som förebild för vår egen.",
        notes="MIT för repot; prompterna tillhör skaparna och länkas, kopieras inte.",
    )]
    for cat, (label, desc) in CATEGORIES.items():
        items.append(entry(
            id=f"ext.{KIT}.cat-{cat}",
            name=f"Opus 5.5-videor: {label} ({counts[cat]})",
            type="prompt",
            description=desc,
            tags=["opus-5-5", "prompts", cat, "kodad video"],
            path=f"{REPO}#readme",
            use="Filtrera på kategorin i data/videos.json eller på Skillry.",
            notes="Länkat, inte kopierat.",
        ))
    for s in summaries:
        v = by_slug.get(s["slug"])
        if not v:
            print(f"saknas i videos.json: {s['slug']}", file=sys.stderr)
            continue
        tech = [t.lower() for t in v.get("tech_tags", [])]
        engine = next((ENGINE[t] for t in tech if t in ENGINE), "html-playwright")
        items.append(entry(
            id=f"ext.{KIT}.{s['slug']}",
            name=s["name"],
            type="prompt",
            medium="video",
            formats=s.get("formats") or ["any"],
            engine=engine,
            description=s["description"],
            tags=sorted(set(s["tags"] + tech + ["opus-5-5", v["category"]])),
            path=f"{REPO}/blob/main/prompts/{s['slug']}.md",
            use=f"Läs prompten som förebild. Original: {v['post_url']} · Remake: {v['skillry_url']}",
            notes=f"Skapare @{v['author']}. Prompt {'delvis publicerad' if v['prompt_partial'] else 'publicerad i sin helhet'}; länkas, kopieras inte.",
        ))

    out = {"kit": KIT, "title": "Awesome Opus 5.5 Videos (yihui-dev)",
           "source": {"name": "yihui-dev/awesome-opus5-5-videos", "url": REPO,
                      "license": "MIT (repot); skaparnas prompts, videor och omslag omfattas inte – länkas, kopieras inte"},
           "items": items}
    (HERE / "LIBRARY.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} poster skrivna till {HERE / 'LIBRARY.json'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "work/opus55-import/videos.json")
