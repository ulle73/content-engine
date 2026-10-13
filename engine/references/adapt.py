"""Our version of a reference: the breakdown + the company's brand, verified facts, media bank, products, recipes and
model playbooks → a scene-by-scene plan with the same grammar (hook, structure, rhythm, camera, sound) and our content.

The plan says per scene where the material comes from: an existing asset in the media bank, a real product image, a
shot to film, or an AI scene (model chosen from library/models). Facts on screen must be verified in the fact bank;
anything else is listed as a fact to verify. Asset ids and fact ids the model invents are dropped with a warning.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from pathlib import Path

from django.utils import timezone
from pydantic import BaseModel, Field

VERSION = "reference-adaptation/1"
LIBRARY = Path(__file__).resolve().parents[2] / "library"
MATERIALS = ("mediabank", "produktbild", "filma", "ai-video", "ai-bild", "grafik")


class OurScene(BaseModel):
    ref_scene: str = Field(description="Referensens scen-id som scenen motsvarar (s1 …), eller 'ny'")
    start_s: float
    end_s: float
    shows: str = Field(description="Vad som syns i vår scen, konkret")
    camera: str = Field(description="Bildutsnitt och kamerarörelse, som i referensen om inget annat är bättre")
    on_screen_text: str = Field(default="", description="Exakt text på skärmen (svenska, kort)")
    spoken: str = Field(default="", description="Exakt vad som sägs, annars tomt")
    sound: str = Field(default="", description="Musik/ljud i scenen och var det slår")
    material: str = Field(description="En av: mediabank, produktbild, filma, ai-video, ai-bild, grafik")
    asset_id: str = Field(default="", description="Asset-id ur mediabanken när material=mediabank, annars tomt")
    material_detail: str = Field(default="", description="Vad som ska filmas/genereras/användas, så konkret att "
                                                         "någon kan göra det utan att fråga")
    ai_model: str = Field(default="", description="Vid ai-video/ai-bild: modell ur model playbooks och varför")
    fact_ids: list[str] = Field(default_factory=list, description="Fakta-id (F1 …) som scenens text bygger på")


class FactNeed(BaseModel):
    claim: str
    why: str = Field(description="Varför påståendet behövs i filmen")


class OurVersion(BaseModel):
    title: str = Field(description="Arbetsnamn på vår film")
    angle: str = Field(description="Vår vinkel i en mening")
    why_this_angle: str = Field(description="Varför den passar oss och målgruppen")
    keep_from_reference: list[str] = Field(description="Greppen vi lånar (grammatik, inte innehåll)")
    beat_the_reference: list[str] = Field(description="Konkret hur vår blir bättre än referensen")
    hook: str = Field(description="Vår krok 0–2 s: bild, text och ljud")
    scenes: list[OurScene]
    music: str = Field(description="Musik och ljudriktning (känsla, tempo, var den bygger och bryts)")
    end_card: str = Field(description="Slutkort: logga, rader, uppmaning")
    duration_s: float
    facts_to_verify: list[FactNeed] = Field(default_factory=list,
                                            description="Påståenden som skulle stärka filmen men inte är verifierade")
    to_film: list[str] = Field(default_factory=list, description="Inspelningslista: varje bild som måste filmas")
    closest_recipe: str = Field(default="", description="Närmaste recept-id ur listan, annars tomt")
    risks: list[str] = Field(default_factory=list, description="Vad som kan bli sämre än referensen, och juridik")


SYSTEM = (
    "Du är kreativ chef och regissör för korta sociala annonser. Du får nedbrytningen av en referensannons som "
    "fungerar, en kontaktkarta ur den, och allt om vårt företag: profil, ton, brand, faktabank, mediabank, produkter, "
    "produktionsrecept och vilka AI-modeller som passar vilka scener. Gör VÅR version: samma grammatik (krok, "
    "struktur, rytm, kameraspråk, ljudgrepp) men vårt innehåll, vår vinkel och vårt material – och bättre.\n"
    "Regler:\n"
    "1. Kopiera aldrig referensens formuleringar, personer, varumärke, bilder, musik eller påståenden.\n"
    "2. Text och tal får bara använda fakta med status verified (ange fact_ids). Annat som skulle stärka filmen "
    "läggs i facts_to_verify, aldrig på skärmen. Hitta aldrig på siffror, priser eller garantier.\n"
    "3. Material per scen: välj först mediabanken (ange exakt asset_id ur listan), sedan riktiga produktbilder, "
    "sedan 'filma' med en konkret instruktion. AI-video/AI-bild bara för miljö, rörelse och människor – aldrig "
    "för att rita vår produkt eller logga; följ model playbooks.\n"
    "4. Behåll referensens tempo: ungefär samma scenlängder och klipprytm om det inte finns skäl att ändra.\n"
    "5. Text på skärmen ska hinna läsas: minst max(5/6 s, tecken/12) + 0,9 s per textbit.\n"
    "6. Var konkret nog att någon kan filma och klippa utan att fråga. Skriv på svenska."
)


def company_key(company) -> str:
    from engine.follow_lists import for_company

    item = for_company(company)
    if item:
        return item["company"]
    return re.sub(r"[^a-z0-9]+", "-", company.name.casefold()).strip("-")


def _skill(name: str) -> str:
    from engine.ad_studio import skills

    try:
        return skills.read(name)
    except ValueError:
        return ""


def facts(company) -> list[dict]:
    """F-facts from the company's fact skill, each with its status in the fact bank (verified/unverified/blocked)."""
    from engine.edit.planner import FACT_SKILLS
    from engine.motion.brand import fact_skill

    name = fact_skill(company) or FACT_SKILLS.get(company_key(company))
    bank = {f.claim.casefold(): f.status for f in company.ad_facts.all()}
    out = []
    for line in (_skill(name) if name else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"F\d+", cells[0]):
            out.append({"id": cells[0], "claim": cells[1], "source": cells[2],
                        "status": bank.get(cells[1][:300].casefold(), "unverified")})
    return out


def media_inventory(company, limit: int = 80) -> list[dict]:
    from engine.models import MediaAsset

    assets = (MediaAsset.objects.filter(company=company, purpose="content", kind__in=("video", "image"))
              .select_related("ad_tags").order_by("-created_at")[:limit])
    out = []
    for asset in assets:
        tags = getattr(asset, "ad_tags", None)
        out.append({"asset_id": str(asset.pk), "kind": asset.kind, "origin": asset.origin,
                    "duration_s": asset.duration_seconds,
                    "size": f"{asset.width}x{asset.height}" if asset.width else "",
                    "description": (tags.description if tags else "") or asset.alt_text or asset.brief[:200],
                    "tags": tags.tags if tags else [], "roles": tags.roles if tags else []})
    return out


def products(company, limit: int = 40) -> list[str]:
    from engine.models import CatalogProduct

    return [p.name for p in CatalogProduct.objects.filter(company=company).order_by("name")[:limit]]


def recipes(key: str) -> list[dict]:
    out = []
    for path in sorted((LIBRARY / "recipes").glob("*/recipe.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("company") in {key, None, ""}:
            out.append({"id": data.get("id") or path.parent.name, "title": data.get("title", ""),
                        "hook": data.get("hook", ""), "duration_s": data.get("duration_s")})
    return out


def context(company) -> dict:
    from engine.motion.brand import skills_for

    key = company_key(company)
    brand_skills = [s for s in skills_for(company) if s.endswith("-brand")] or [f"{key}-brand"]
    playbooks = LIBRARY / "models" / "README.md"
    return {
        "company": {"name": company.name, "profile": company.profile[:3000], "voice": company.voice[:1500],
                    "current": company.current[:2000]},
        "brand": "\n\n".join(_skill(s) for s in brand_skills)[:9000],
        "facts": facts(company),
        "media_bank": media_inventory(company),
        "products": products(company),
        "recipes": recipes(key),
        "model_playbooks": playbooks.read_text(encoding="utf-8")[:6000] if playbooks.is_file() else "",
    }


def _clean(plan: dict, ctx: dict) -> list[str]:
    """Drop invented asset ids and unverified/unknown fact ids; returns warnings (Swedish)."""
    warnings = []
    assets = {a["asset_id"] for a in ctx["media_bank"]}
    verified = {f["id"] for f in ctx["facts"] if f["status"] == "verified"}
    for scene in plan["scenes"]:
        if scene["material"] not in MATERIALS:
            warnings.append(f"{scene['ref_scene']}: okänd materialtyp '{scene['material']}' → filma.")
            scene["material"] = "filma"
        if scene["asset_id"] and scene["asset_id"] not in assets:
            warnings.append(f"{scene['ref_scene']}: asset-id {scene['asset_id']} finns inte i mediabanken och togs bort.")
            scene["asset_id"] = ""
            if scene["material"] == "mediabank":
                scene["material"] = "filma"
        bad = [f for f in scene["fact_ids"] if f not in verified]
        if bad:
            warnings.append(f"{scene['ref_scene']}: fakta {', '.join(bad)} är inte verifierade – texten måste "
                            "skrivas om eller faktat verifieras innan filmen görs.")
    return warnings


def run(company, reference: dict, *, sheet: bytes | None = None, angle: str = "", notes: str = "",
        model: str = "") -> dict:
    """reference: {title, author, url, measurements (summary), breakdown}. → adaptation entry
    {id, created_at, model, cost_usd, angle, plan, warnings}. Raises OpenRouterError."""
    from engine.openrouter import _call

    from .breakdown import default_model

    if not reference.get("breakdown"):
        raise ValueError("Referensen är inte nedbruten än.")
    ctx = context(company)
    images = ["data:image/jpeg;base64," + base64.b64encode(sheet).decode("ascii")] if sheet else None
    payload = {
        "reference": reference,
        "our_company": ctx,
        "request": {"angle": angle, "notes": notes},
        "input": "Kontaktkartan ur referensen bifogas (en bild per scen med tider)." if images else "",
    }
    model = model or default_model()
    result, meta = _call(model, system=SYSTEM, payload=payload, schema=OurVersion, operation="reference_adaptation",
                         max_tokens=10000, temperature=0.4, timeout_seconds=180, strict_schema=False, images=images)
    plan = result.model_dump()
    return {"id": uuid.uuid4().hex[:12], "version": VERSION, "created_at": timezone.now().isoformat(),
            "model": meta.get("model"), "cost_usd": meta.get("cost_usd"), "angle": angle, "notes": notes,
            "plan": plan, "warnings": _clean(plan, ctx)}
