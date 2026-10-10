"""Recipe → cut spec planner: turn a production recipe (library/recipes/<id>/recipe.json, recipe/v1) into a cut/v1
spec from the company's own media bank, so a professional cut needs no hand-picked asset ids.

    plan_cut(company, "faiv-dark-to-light-reveal", format="9:16")
    → {"spec": <cut/v1 for edit.service.create_job>, "missing": [{"scene", "footage_ids", "hint"}], "notes": [...], …}

Per scene:
  footage / ai_video / ai_image → media-bank clips whose AssetTags.tags contain the shot id (docs/FILMLISTA.md, e.g.
      "fa-m1"), else whose description matches the shot text; least recently used first (EditJob history), never the
      same file twice unless the recipe asks for the same shot again (then the clip continues where it left off).
  product_image → product_catalog.search(catalog_query), first image (downloaded only when materialize=True).
  graphic → the final CTA scene becomes the template's end card (or is replaced by the brand outro); other graphic
      scenes use a media-bank graphic (role end_card/background) or the company logo on the brand background.
Text: `{fact:Fn}` is shown only when Fn's claim is verified in the company's fact bank (AdFact); otherwise the recipe's
safe wording from the scene notes is used, or the line is dropped. Other `{placeholders}` come from overrides.
Lessons from the Discord review loop (engine/review/lessons) remove avoided items, rank liked ones first and are
listed in `notes`. Planning never writes anything unless materialize=True (product image download).
"""

from __future__ import annotations

import json
import re
from datetime import date

from django.db.models import Q
from django.utils import timezone

from . import footage
from . import spec as cut_spec

RECIPES = cut_spec.RECIPES
FACT = re.compile(r"\{fact:([A-Za-z0-9_-]+)\}")
PLACEHOLDER = re.compile(r"\{([^{}]+)\}")
FALLBACK = re.compile(r"(?:[Aa]nnars|[Uu]tan verifierad formulering)[^'\"‘’“”]*['\"‘“]([^'\"’”]{3,160})['\"’”]")
FACT_SKILLS = {"faiv": "faiv-fakta", "golfkuponger": "golfkuponger-friskvard"}
SCENE_OVERRIDE_KEYS = {"asset_id", "text", "trim_start_s", "duration_s", "transition_in", "effects", "text_style",
                       "text_position", "fit", "audio", "skip"}
OVERRIDE_KEYS = {"title", "caption", "placeholders", "product_id", "product_query", "scenes", "music_asset_id",
                 "music_volume", "fps"}
CAMERA_EFFECTS = {"ken-burns", "push-in", "pull-back", "punch-in", "drift", "shake"}
STILL_MOTION = "hyperframes.registry.push-in"
STOP = {"samma", "eller", "från", "efter", "under", "över", "utan", "med", "som", "och", "för", "till", "inte", "bara",
        "scen", "scenen", "klipp", "klippet", "bild", "bilden", "video", "the", "with", "and"}


class PlanError(ValueError):
    pass


def load_recipe(recipe_id: str) -> dict:
    recipe_id = str(recipe_id or "").strip()
    if not cut_spec.SLUG.match(recipe_id):
        raise PlanError("recipe_id ska vara ett recept-id, t.ex. faiv-dark-to-light-reveal.")
    path = RECIPES / recipe_id / "recipe.json"
    if not path.is_file():
        known = ", ".join(sorted(p.parent.name for p in RECIPES.glob("*/recipe.json")))
        raise PlanError(f"Receptet {recipe_id} finns inte. Recept: {known}.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "recipe/v1" or not isinstance(data.get("scenes"), list):
        raise PlanError(f"Receptet {recipe_id} följer inte schemat recipe/v1.")
    return data


def _words(*texts) -> set[str]:
    out = set()
    for text in texts:
        for word in re.split(r"[^\wåäö]+", str(text or "").casefold()):
            if len(word) >= 4 and word not in STOP and not word.isdigit():
                out.add(word)
    return out


def _round(value: float) -> float:
    return round(float(value) + 1e-9, 2)


class Planner:
    def __init__(self, company, recipe, *, fmt, overrides, materialize):
        from engine.models import MediaAsset

        self.company, self.recipe, self.format, self.materialize = company, recipe, fmt, materialize
        self.overrides = overrides
        self.notes: list[str] = []
        self.missing: list[dict] = []
        self.pending: list[dict] = []
        self.choices: list[dict] = []
        self.applied: dict[int, str] = {}
        self.used: dict[str, float] = {}  # asset id → where the previous scene's clip ended
        self.used_shots: dict[str, str] = {}  # asset id → the shot id it was chosen for
        self.product = None
        self.product_tried = False
        self._load_lessons()
        self.last_used = self._usage()
        now = timezone.now()
        self.pool = list(
            MediaAsset.objects.filter(company=company, purpose="content", kind__in=["video", "image"])
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now) | Q(used_at__isnull=False))
            .exclude(provider__in=["hyperframes", "remotion"])
            .select_related("ad_tags").order_by("-created_at")[:600])

    # ------------------------------------------------------------ lessons and history

    def _load_lessons(self):
        from engine.review import lessons

        self.avoid, self.prefer, self.adjust, self.aspects = {}, {}, {}, []
        for lesson in lessons.active(self.company):
            if lesson.target_type == "library":
                {"avoid": self.avoid, "prefer": self.prefer, "adjust": self.adjust}[lesson.polarity][lesson.target_id] = lesson
            else:
                self.aspects.append(lesson)

    def _apply(self, lesson, text):
        self.applied[lesson.pk] = text

    def _usage(self) -> dict[str, float]:
        """asset id → when it was last cut into a video (EditJob history)."""
        from .models import EditJob

        out: dict[str, float] = {}
        for spec, created in EditJob.objects.filter(company=self.company).values_list("cut_spec", "created_at")[:300]:
            for scene in (spec or {}).get("scenes") or []:
                asset_id = str(scene.get("asset_id") or "")
                if asset_id:
                    out[asset_id] = max(out.get(asset_id, 0.0), created.timestamp())
        return out

    # ------------------------------------------------------------ text and facts

    def _fact_claims(self) -> dict[str, str]:
        from engine.ad_studio import skills
        from engine.motion.brand import fact_skill

        name = fact_skill(self.company) or FACT_SKILLS.get(self.recipe.get("company"))
        try:
            text = skills.read(name) if name else ""
        except ValueError:
            text = ""
        claims = {}
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 4 and re.fullmatch(r"F\d+", cells[0]):
                claims[cells[0]] = cells[1]
        return claims

    def _verified_fact(self, fact_id: str) -> str | None:
        if not hasattr(self, "_facts"):
            claims = self._fact_claims()
            bank = {f.claim.casefold(): f.claim for f in self.company.ad_facts.filter(status="verified")}
            self._facts = {fid: bank.get(claim[:300].casefold()) for fid, claim in claims.items()}
        return self._facts.get(fact_id)

    def _placeholder(self, name: str) -> str | None:
        values = self.overrides.get("placeholders") or {}
        if name in values and str(values[name]).strip():
            return str(values[name]).strip()[:80]
        if name == "product":
            product = self._product()
            return product.name if product else None
        if name == "dagar_kvar":
            today = timezone.localdate()
            return str((date(today.year, 12, 31) - today).days)
        return None

    def resolve_text(self, raw: str, *, where: str, notes_text: str = "") -> str:
        """Fill placeholders; unverified facts → the recipe's safe wording or the line is dropped. Never invents."""
        raw = str(raw or "")
        if not raw.strip():
            return ""
        fallback = None
        lines = []
        for line in raw.split("\n"):
            drop = False
            for fact_id in FACT.findall(line):
                claim = self._verified_fact(fact_id)
                if claim:
                    line = line.replace(f"{{fact:{fact_id}}}", claim)
                    self.notes.append(f"{where}: faktat {fact_id} är verifierat i faktabanken och visas.")
                    continue
                fallback = fallback or (FALLBACK.search(notes_text or "") or [None, None])[1]
                if fallback:
                    self.notes.append(f"{where}: faktat {fact_id} är inte verifierat i faktabanken; receptets säkra "
                                      f"formulering används: \"{fallback}\".")
                    return self.resolve_text(fallback, where=where)
                line = re.sub(r"\s*[·•|–-]?\s*\{fact:" + re.escape(fact_id) + r"\}\s*[·•|–-]?\s*", " ", line).strip()
                self.notes.append(f"{where}: faktat {fact_id} är inte verifierat i faktabanken och visas inte. "
                                  "Verifiera det i faktabanken för att få med det.")
            for name in PLACEHOLDER.findall(line):
                if name.startswith("fact:"):
                    continue
                value = self._placeholder(name)
                if value is None:
                    drop = True
                    self.notes.append(f"{where}: {{{name}}} saknar värde och raden \"{line.strip()}\" tas bort. "
                                      f"Ange overrides.placeholders.{name} för att få med den.")
                    break
                line = line.replace(f"{{{name}}}", value)
            line = line.strip()
            if drop or not re.search(r"[A-Za-zÅÄÖåäö]{2,}", line):
                continue
            lines.append(line)
        text = "\n".join(lines).strip()
        if len(text) > 200:
            self.notes.append(f"{where}: texten blev längre än 200 tecken och tas bort. Korta den med overrides.")
            return ""
        return text

    # ------------------------------------------------------------ assets

    def _product(self):
        from engine.models import CatalogProduct

        if self.product is not None or self.product_tried:
            return self.product
        self.product_tried = True
        pid = self.overrides.get("product_id")
        if pid not in (None, ""):
            self.product = CatalogProduct.objects.filter(company=self.company, pk=pid, active=True).first()
            if not self.product:
                raise PlanError(f"Produkten {pid} finns inte i bolagets produktkatalog.")
            return self.product
        query = self.overrides.get("product_query") or next(
            (s.get("catalog_query") for s in self.recipe["scenes"] if s.get("source") == "product_image"
             and s.get("catalog_query")), "")
        self.product = self._search_product(query)
        return self.product

    def _search_product(self, query: str):
        from engine import product_catalog

        values = self.overrides.get("placeholders") or {}
        unresolved = [name for name in PLACEHOLDER.findall(str(query or "")) if not str(values.get(name, "")).strip()]
        query = PLACEHOLDER.sub(lambda m: str(values.get(m.group(1), "")), str(query or "")).strip()
        if not query:
            return None
        found = product_catalog.search(self.company, query, limit=1)
        if found and unresolved:
            missing = ", ".join("{" + name + "}" for name in unresolved)
            self.notes.append(f"Produktsökningen saknar {missing}; \"{found[0].name}\" valdes på \"{query}\". "
                              "Ange overrides.placeholders eller overrides.product_id för rätt produkt.")
        if not found:
            for word in sorted(query.split(), key=len, reverse=True):
                found = product_catalog.search(self.company, word, limit=1) if len(word) >= 3 else []
                if found:
                    self.notes.append(f"Ingen produkt matchade \"{query}\" helt; \"{found[0].name}\" valdes på ordet "
                                      f"\"{word}\". Ange overrides.product_id för en annan produkt.")
                    break
        return found[0] if found else None

    def _rank(self, scene, candidates):
        """Sort (score, asset, why) best first: liked > score > never used > least recently used > newest."""
        def key(item):
            score, asset, _ = item
            liked = str(asset.pk) in self.prefer
            return (-int(liked), -score, self.last_used.get(str(asset.pk), 0.0), -asset.created_at.timestamp())

        return sorted(candidates, key=key)

    def _footage_candidates(self, scene):
        shot_ids = [i for i in scene.get("footage_ids") or [] if isinstance(i, str)]
        wanted = _words(scene.get("camera"), scene.get("purpose"), *[footage.text(i) for i in shot_ids])
        kinds = {"ai_image": {"image"}, "ai_video": {"video"}}.get(scene.get("source"), {"video", "image"})
        out = []
        for asset in self.pool:
            if asset.kind not in kinds:
                continue
            lesson = self.avoid.get(str(asset.pk))
            if lesson:
                self._apply(lesson, f"Hoppade över material som ägaren ogillat ({lesson.target_label or asset.pk}).")
                continue
            tags = getattr(asset, "ad_tags", None)
            tag_ids = footage.ids_of(tags.tags if tags else [])
            score, why = 0.0, []
            for rank, shot in enumerate(shot_ids):
                if shot in tag_ids:
                    score += 10 - rank * 2
                    why.append(f"taggad {shot}")
                    break
            hay = _words(tags.search_text() if tags else "", asset.alt_text, asset.brief)
            overlap = wanted & hay
            if not why and len(overlap) < 2:
                continue
            score += len(overlap) * 0.6
            if overlap and not why:
                why.append("beskrivningen matchar (" + ", ".join(sorted(overlap)[:4]) + ")")
            if tags and tags.verified:
                score += 0.5
            if asset.kind == "video":
                score += 1
                length = float(asset.duration_seconds or 0)
                if not length or length + 0.05 >= float(scene["duration_s"]):
                    score += 1.5
            out.append((score, asset, "; ".join(why)))
        return out

    def _place(self, scene, asset, why, *, shot=None) -> dict | None:
        """Scene fields for one chosen asset (trim and duration that fit the clip)."""
        duration = float(scene["duration_s"])
        trim = 0.0
        if asset.kind == "video":
            length = float(asset.duration_seconds or 0)
            if length:
                start = self.used.get(str(asset.pk))
                if start is not None and start + duration <= length + 0.05:
                    trim = start
                elif length >= duration:
                    trim = min(1.0, length - duration)
                elif length >= 0.6:
                    duration = _round(length - 0.05)
                    self.notes.append(f"Scen {scene['id']}: klippet är bara {length:.1f} s, scenen kortas från "
                                      f"{scene['duration_s']} s till {duration} s.")
                else:
                    return None
            self.used[str(asset.pk)] = trim + duration
        else:
            self.used[str(asset.pk)] = 0.0
        if shot:
            self.used_shots[str(asset.pk)] = shot
        lesson = self.prefer.get(str(asset.pk))
        if lesson:
            self._apply(lesson, f"Scen {scene['id']}: valde gillat material ({lesson.target_label or asset.pk}).")
        self.choices.append({"scene": scene["id"], "asset_id": str(asset.pk), "kind": asset.kind, "why": why,
                             "trim_start_s": _round(trim), "duration_s": _round(duration)})
        return {"asset_id": str(asset.pk), "trim_start_s": _round(trim), "duration_s": _round(duration),
                "kind": asset.kind}

    def pick_footage(self, scene):
        candidates = self._rank(scene, self._footage_candidates(scene))
        shot_ids = scene.get("footage_ids") or []
        fresh = [c for c in candidates if str(c[1].pk) not in self.used]
        for score, asset, why in fresh:
            placed = self._place(scene, asset, why, shot=next(iter(shot_ids), None))
            if placed:
                return placed
        # The recipe asks for the same shot again (e.g. fa-m1 lights off, then on): continue in the same clip.
        for score, asset, why in candidates:
            if self.used_shots.get(str(asset.pk)) in shot_ids:
                placed = self._place(scene, asset, why + "; samma klipp som tidigare scen, fortsätter i klippet")
                if placed:
                    self.notes.append(f"Scen {scene['id']}: samma klipp som en tidigare scen används (samma filmlista-"
                                      "id), med senare startpunkt. Ladda upp fler tagningar för variation.")
                    return placed
        self._missing(scene)
        return None

    def _missing(self, scene, hint=None):
        shot_ids = [i for i in scene.get("footage_ids") or [] if isinstance(i, str)]
        if hint is None:
            if shot_ids:
                first = shot_ids[0]
                shots = " eller ".join(f"{i} ({footage.text(i)})" for i in shot_ids)
                hint = (f"Filma {shots} och ladda upp i mediabiblioteket. Märk klippet med {first} "
                        f"(tag_media, dialogen i mediabiblioteket, eller filnamn som {first}_klipp.mp4).")
            else:
                hint = "Ladda upp material som passar scenen och beskriv det i mediabiblioteket."
            if scene.get("camera"):
                hint = f"Bilden: {scene['camera'].rstrip('.')}. " + hint
            upgrade = scene.get("ai_upgrade") or {}
            if upgrade.get("model"):
                hint += f" Alternativ: AI-generera med {upgrade['model']} enligt receptets ai_upgrade (kostar)."
        self.missing.append({"scene": scene["id"], "purpose": scene.get("purpose", ""), "source": scene.get("source"),
                             "duration_s": scene.get("duration_s"), "footage_ids": shot_ids, "hint": hint})

    def pick_product(self, scene):
        from engine import product_catalog

        if self.overrides.get("product_id") not in (None, "") or self.overrides.get("product_query"):
            product = self._product()
        else:
            product = self._search_product(scene.get("catalog_query") or "")
            if product and self.product is None:
                self.product, self.product_tried = product, True
        if product is None:
            self._missing(scene, "Ingen produkt i katalogen matchar \"" + str(scene.get("catalog_query") or "")
                          + "\". Kör sync_products, ange overrides.product_id, eller ladda upp en produktbild.")
            return None
        existing = [a for a in product.assets.filter(kind="image").order_by("created_at") if str(a.pk) not in self.used]
        if existing:
            return self._place(scene, existing[0], f"produktbild: {product.name}")
        if not product.image_urls:
            self._missing(scene, f"Produkten {product.name} har inga bilder i katalogen. Ladda upp en produktbild.")
            return None
        if not self.materialize:
            self.pending.append({"scene": scene["id"], "product_id": product.pk, "product": product.name,
                                 "image_url": product.image_urls[0]})
            self.notes.append(f"Scen {scene['id']}: produktbilden för {product.name} laddas ner till mediabanken när "
                              "render_recipe körs.")
            return {"pending": True}
        assets = product_catalog.materialize(product, indexes=[0])
        if not assets:
            self._missing(scene, f"Produktbilden för {product.name} kunde inte laddas ner. Ladda upp den själv.")
            return None
        return self._place(scene, assets[0], f"produktbild: {product.name} (nedladdad från katalogen)")

    def pick_graphic(self, scene):
        for asset in self.pool:
            tags = getattr(asset, "ad_tags", None)
            if (asset.kind == "image" and tags and {"end_card", "background"} & set(tags.roles or [])
                    and str(asset.pk) not in self.used and str(asset.pk) not in self.avoid):
                placed = self._place(scene, asset, "grafik från mediabanken (end_card/background)")
                placed["fit"] = "cover"
                return placed
        logo = self.company.official_logo if self.company.official_logo_id else None
        if logo and logo.company_id == self.company.pk and logo.kind == "image":
            placed = self._place(scene, logo, "bolagets logga på varumärkesbakgrund")
            placed["fit"] = "contain"
            return placed
        self._missing(scene, "Grafikscen utan material: ladda upp bolagets logga (officiell logga) eller en "
                             "bakgrundsbild med rollen end_card i mediabiblioteket.")
        return None

    # ------------------------------------------------------------ library items

    def _avoided(self, item_id, where) -> bool:
        lesson = self.avoid.get(item_id)
        if lesson:
            self._apply(lesson, f"{where}: tog bort {lesson.target_label or item_id} ({lesson.rule}).")
        return bool(lesson)

    def _adjusted(self, item_id, where):
        lesson = self.adjust.get(item_id)
        if lesson:
            self._apply(lesson, f"{where}: {lesson.target_label or item_id} – justera: {lesson.rule}.")

    def _preferred_transition(self):
        for item_id in self.prefer:
            if cut_spec.resolve("transitions", item_id):
                return item_id
        return None

    def items(self, scene, *, has_text: bool, is_still: bool):
        where = f"Scen {scene['id']}"
        text_style, effects = None, []
        for item_id in scene.get("effects") or []:
            if not isinstance(item_id, str) or self._avoided(item_id, where):
                continue
            self._adjusted(item_id, where)
            if cut_spec.resolve("text", item_id) or _catalog_type(item_id) in {"text", "caption"}:
                if has_text and text_style is None:
                    text_style = item_id
                continue
            effects.append(item_id)
        if is_still and not any(cut_spec.resolve("effects", e) in CAMERA_EFFECTS for e in effects):
            effects.insert(0, STILL_MOTION)
            self.notes.append(f"{where}: stillbild, så en långsam inzoomning läggs till för rörelse.")
        transition = scene.get("transition_in")
        if transition and self._avoided(transition, where):
            transition = self._preferred_transition() or "cut.transition.cut"
            lesson = self.prefer.get(transition)
            if lesson:
                self._apply(lesson, f"{where}: använde gillad övergång {lesson.target_label or transition}.")
        elif transition:
            self._adjusted(transition, where)
        return text_style, effects[:8], transition

    # ------------------------------------------------------------ music

    def music(self):
        from engine.models import MediaAsset

        if "music_asset_id" in self.overrides:
            chosen = self.overrides["music_asset_id"]
            return str(chosen) if chosen else None
        audio = (MediaAsset.objects.filter(company=self.company, kind="audio").select_related("ad_tags")
                 .order_by("-created_at")[:200])
        for asset in audio:
            tags = getattr(asset, "ad_tags", None)
            words = {t.casefold() for t in [*(tags.tags if tags else []), *(tags.roles if tags else [])]}
            if not words & {"music", "musik"}:
                continue
            if self._avoided(str(asset.pk), "Musik"):
                continue
            self.choices.append({"scene": "music", "asset_id": str(asset.pk), "kind": "audio",
                                 "why": "senaste ljudfilen taggad music"})
            return str(asset.pk)
        mood = (self.recipe.get("music") or {}).get("mood")
        self.notes.append("Ingen ljudfil taggad \"music\" i mediabanken, så videon får ingen musik."
                          + (f" Receptet vill ha: {mood}." if mood else ""))
        return None


def _catalog_type(item_id: str) -> str:
    from engine.ad_studio import library

    found = next((i for i in library.items() if i["id"] == item_id), None)
    return (found or {}).get("type", "")


def _check_overrides(overrides) -> dict:
    if overrides in (None, ""):
        return {}
    if not isinstance(overrides, dict):
        raise PlanError("overrides ska vara ett objekt.")
    extra = sorted(set(overrides) - OVERRIDE_KEYS)
    if extra:
        raise PlanError(f"overrides: okänt fält {', '.join(extra)}. Tillåtna: {', '.join(sorted(OVERRIDE_KEYS))}.")
    scenes = overrides.get("scenes") or {}
    if not isinstance(scenes, dict):
        raise PlanError("overrides.scenes ska vara ett objekt {scen-id: {fält: värde}}.")
    for scene_id, values in scenes.items():
        if not isinstance(values, dict):
            raise PlanError(f"overrides.scenes.{scene_id} ska vara ett objekt.")
        extra = sorted(set(values) - SCENE_OVERRIDE_KEYS)
        if extra:
            raise PlanError(f"overrides.scenes.{scene_id}: okänt fält {', '.join(extra)}. "
                            f"Tillåtna: {', '.join(sorted(SCENE_OVERRIDE_KEYS))}.")
    if not isinstance(overrides.get("placeholders") or {}, dict):
        raise PlanError("overrides.placeholders ska vara ett objekt, t.ex. {\"car_model\": \"Volvo XC60\"}.")
    return overrides


def _company_matches(company, recipe) -> bool:
    from engine.motion.brand import _slug, brand_id_for

    owner = recipe.get("company") or "any"
    return owner == "any" or owner in {_slug(company.name), brand_id_for(company)}


def plan_cut(company, recipe_id, *, format="9:16", overrides=None, materialize=False) -> dict:  # noqa: A002
    """Plan a cut/v1 spec from a recipe and the media bank. Side-effect free unless materialize=True."""
    from engine.motion.brand import landing_url

    from . import outros

    recipe = load_recipe(recipe_id)
    if format not in cut_spec.FORMATS:
        raise PlanError("format ska vara något av " + ", ".join(cut_spec.FORMATS) + ".")
    if not _company_matches(company, recipe):
        raise PlanError(f"Receptet {recipe['id']} är gjort för {recipe.get('company')}, inte för {company.name}.")
    overrides = _check_overrides(overrides)
    plan = Planner(company, recipe, fmt=format, overrides=overrides, materialize=materialize)
    if format not in (recipe.get("formats") or []):
        plan.notes.append(f"Receptet är gjort för {', '.join(recipe.get('formats') or [])}; {format} fungerar men "
                          "utsnitten är inte provade.")
    outro = outros.outro_for(company, format)
    scene_overrides = overrides.get("scenes") or {}
    known_ids = {s.get("id") for s in recipe["scenes"]}
    for unknown in sorted(set(scene_overrides) - known_ids):
        raise PlanError(f"overrides.scenes.{unknown}: receptet har ingen sådan scen ({', '.join(sorted(known_ids))}).")
    scenes, cta = [], None
    last = recipe["scenes"][-1]["id"] if recipe["scenes"] else None
    for scene in recipe["scenes"]:
        where = f"Scen {scene['id']}"
        change = scene_overrides.get(scene["id"]) or {}
        if change.get("skip"):
            plan.notes.append(f"{where} hoppas över (overrides).")
            continue
        scene = {**scene, "duration_s": change.get("duration_s") or scene["duration_s"]}
        raw_text = change["text"] if "text" in change else scene.get("text", "")
        source = scene.get("source")
        if source == "graphic" and scene["id"] == last and scene.get("purpose") == "cta" and "asset_id" not in change:
            if outro:
                plan.notes.append(f"{where} (CTA-grafik) ersätts av bolagets slutbild ({outro['label']}, "
                                  f"{outro['duration_s']:g} s).")
                continue
            text = plan.resolve_text(raw_text, where=where, notes_text=scene.get("notes", ""))
            text = text if 0 < len(text) <= 80 else plan.resolve_text((recipe.get("cta") or {}).get("text", ""),
                                                                       where="CTA")[:80]
            if text:
                cta = {"text": text, "url": landing_url(company),
                       "duration_s": min(6.0, max(1.0, float(scene["duration_s"])))}
                plan.notes.append(f"{where} (CTA-grafik) blir klippmallens slutkort med logga och text.")
                continue
        if "asset_id" in change:
            from engine.models import MediaAsset

            asset = MediaAsset.objects.filter(company=company, pk=change["asset_id"]).first() \
                if footage._uuid(change["asset_id"]) else None
            if asset is None:
                raise PlanError(f"overrides.scenes.{scene['id']}.asset_id finns inte i bolagets mediabank.")
            placed = plan._place(scene, asset, "valt i overrides")
            if placed is None:
                raise PlanError(f"overrides.scenes.{scene['id']}.asset_id: klippet är för kort för scenen.")
        elif source == "product_image":
            placed = plan.pick_product(scene)
        elif source == "graphic":
            placed = plan.pick_graphic(scene)
        else:
            placed = plan.pick_footage(scene)
        if not placed or placed.get("pending"):
            continue
        text = plan.resolve_text(raw_text, where=where, notes_text=scene.get("notes", ""))
        text_style, effects, transition = plan.items(scene, has_text=bool(text), is_still=placed["kind"] == "image"
                                                     and source != "graphic")
        out = {
            "id": scene["id"], "purpose": str(scene.get("purpose") or "")[:40], "duration_s": placed["duration_s"],
            "asset_id": placed["asset_id"], "trim_start_s": placed["trim_start_s"], "fit": placed.get("fit", "cover"),
            "text": text, "text_style": change.get("text_style", text_style),
            "text_position": change.get("text_position"), "audio": change.get("audio"),
            "effects": change.get("effects", effects), "transition_in": change.get("transition_in", transition),
        }
        if "trim_start_s" in change:
            out["trim_start_s"] = change["trim_start_s"]
        if "fit" in change:
            out["fit"] = change["fit"]
        scenes.append(out)
    if scenes:
        scenes[0]["transition_in"] = None
    for lesson in plan.aspects[:8]:
        plan.notes.append(f"Lärdom för hela videon ({lesson.get_polarity_display()}, {lesson.target_id}): {lesson.rule}")
    product = plan.product
    title = overrides.get("title") or (recipe["title"] + (f" – {product.name}" if product else ""))
    caption = overrides.get("caption")
    if caption is None:
        caption = "\n\n".join(filter(None, [plan.resolve_text(recipe.get("hook", ""), where="Bildtext (krok)"),
                                            plan.resolve_text((recipe.get("cta") or {}).get("text", ""),
                                                              where="Bildtext (CTA)")]))
    spec = {
        "schema": cut_spec.SCHEMA, "format": format, "fps": overrides.get("fps", 30), "title": title[:200],
        "caption": caption[:2200], "recipe_id": recipe["id"], "scenes": scenes,
        "music_asset_id": plan.music(), "music_volume": overrides.get("music_volume", 1.0), "cta": cta,
    }
    total = sum(s["duration_s"] for s in scenes) + (cta["duration_s"] if cta else 0) \
        + (outro["duration_s"] if outro else 0)
    if scenes and abs(total - float(recipe.get("duration_s") or total)) > 0.5:
        plan.notes.append(f"Videon blir {total:.1f} s (receptet: {recipe.get('duration_s')} s) "
                          + ("inklusive slutbilden." if outro else "på grund av ändrade eller saknade scener."))
    warnings: list[str] = []
    if scenes:
        try:
            _, warnings = cut_spec.validate(company, spec)
        except cut_spec.CutSpecError as exc:
            plan.missing.append({"scene": "spec", "purpose": "", "source": None, "footage_ids": [],
                                 "hint": f"Klippspecen klarar inte kontrollen: {exc}"})
    lessons_applied = [{"lesson_id": pk, "applied": text} for pk, text in plan.applied.items()]
    notes = list(dict.fromkeys(plan.notes + [f"Lärdom tillämpad: {text}" for text in plan.applied.values()]))
    return {
        "recipe_id": recipe["id"], "recipe_title": recipe["title"], "company": company.name, "format": format,
        "ready": bool(scenes) and not plan.missing and not plan.pending,
        "duration_s": round(total, 2), "spec": spec, "missing": plan.missing, "pending_downloads": plan.pending,
        "choices": plan.choices, "notes": notes, "warnings": warnings, "lessons_applied": lessons_applied,
        "product": {"product_id": product.pk, "name": product.name} if product else None,
    }


def render_recipe(company, recipe_id, *, format="9:16", overrides=None, allow_missing=False):  # noqa: A002
    """Plan (downloading product images) and queue the cut. Refuses when scenes are missing unless allow_missing."""
    from . import service

    plan = plan_cut(company, recipe_id, format=format, overrides=overrides, materialize=True)
    if plan["missing"] and not allow_missing:
        scenes = "; ".join(f"{m['scene']} ({m['hint']})" for m in plan["missing"])
        raise PlanError(f"Material saknas för {len(plan['missing'])} scen(er): {scenes} "
                        "Ladda upp och tagga materialet, eller kör med allow_missing=true för att klippa utan dem.")
    if not plan["spec"]["scenes"]:
        raise PlanError("Inget material hittades för någon scen i receptet. Ladda upp och tagga materialet först.")
    if plan["missing"]:
        plan["notes"].append("Klipps utan scenerna " + ", ".join(m["scene"] for m in plan["missing"])
                             + " (allow_missing).")
    job = service.create_job(company, plan["spec"])
    return plan, job
