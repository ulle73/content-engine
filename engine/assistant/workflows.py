"""Adapters reuse the established engines; compilation has no external side effects."""
import math
import re
import uuid

from django.urls import reverse

from engine.creative_controls import MODEL_LABELS
from engine.creative_director import build_plan
from engine.forms import snapshot_company_context
from engine.media import create_job
from engine.models import ContentRun

from .registry import WorkflowDefinition, register

RATIOS = {"portrait": "9:16", "square": "1:1", "landscape": "16:9"}


def bind_job(plan, job):
    """Legacy/MCP entry points cannot bypass the studio's order-wide budget gate."""
    from engine.models import MediaGeneration
    parameters = {**job.parameters, "assistant_plan_id": str(plan.pk)}
    MediaGeneration.objects.filter(pk=job.pk).update(parameters=parameters)
    job.parameters = parameters


def recommendation(run, brief, *, kind, source, end_source, shape, budget, recipe_id=None, clip_count=1):
    from decimal import Decimal

    from engine.creative_budget import known_video_cost
    from engine.creative_registry import verified_models
    candidates = []
    mode = ("image-to-" if source else "text-to-") + kind
    for model in verified_models(kind, mode):
        try:
            plan = build_plan(run, brief, kind=kind, source=source, end_source=end_source, shape=shape, count=1,
                              priority="quality", recipe_id=recipe_id, model_override=model.model_id)
        except ValueError:
            continue
        price = known_video_cost(model.model_id, plan.parameters.get("duration", 0), plan.parameters.get("resolution", "")) if kind == "video" else None
        candidates.append((model, price, plan))
    if not candidates:
        raise ValueError("Ingen verifierad modell stöder detta material och upplägg. Ändra bilder, längd eller mall.")
    affordable = [row for row in candidates if row[1] is not None and row[1] * clip_count <= Decimal(str(budget))]
    pool = affordable or [row for row in candidates if row[1] is None] or candidates
    model, price, best = max(pool, key=lambda row: (row[0].quality_tier, row[0].speed_tier, -row[0].cost_tier, row[0].model_id))
    reason = "Bästa kompatibla modell enligt det verifierade registrets kvalitets- och kapabilitetsprofil. "
    reason += "Prisförslaget ryms inom din budget; aktuellt kontopris kontrolleras före start." if affordable else "Priset behöver verifieras mot din budget före start." if price is None else "Prisförslaget överstiger din budget. Kortare klipp eller högre budget behövs."
    return {"model_id": best.selection.model_id, "model_label": MODEL_LABELS.get(best.selection.model_id, best.selection.model_id), "reason": reason}


def _run(company, user, spec, *, save=False):
    values = dict(workspace=company, author=user, model="assistant-workspace", context={**spec.get("company_context", snapshot_company_context(company)), "media_only": True},
                  ideas=[{"title": spec["proposal"]["title"], "angle": spec["brief"], "photo_brief": spec["brief"]}], selected=0,
                  draft={"photo_brief": spec["brief"], "instagram": spec["proposal"].get("caption", ""), "facebook": spec["proposal"].get("caption", "")})
    return ContentRun.objects.create(**values) if save else ContentRun(**values)


def media_compile(company, user, spec, assets):
    from engine.prompt_library import retrieve_inspiration
    options = spec["options"]
    kind = spec["workflow"]
    source = assets.get("start") or (assets.get("reference") if kind == "image" else None)
    end = assets.get("end")
    if any(key.startswith("reference:") for key in assets):
        raise ValueError("Detta flöde använder en referensbild. Välj en bild eller använd Flera scener för fler bilder.")
    if kind == "image" and end:
        raise ValueError("Slutbild används för video. Ändra dess roll eller välj AI-video.")
    if kind == "video" and assets.get("reference"):
        raise ValueError("Välj om referensbilden är startbild eller slutbild innan vi förbereder videon.")
    if kind == "image" and assets.get("start") and assets.get("reference"):
        raise ValueError("Denna bildmodell använder en referensbild. Välj vilken bild som ska styra resultatet.")
    if assets.get("audio") and kind == "image":
        raise ValueError("Eget ljud läggs på i Motion. Välj Motion eller ta bort ljudbilagan för detta klipp.")
    finishing = kind == "video" and bool(assets.get("logo") or assets.get("audio"))
    generation_brief = spec["proposal"].get("clip_brief") if finishing else spec["brief"]
    if not generation_brief:
        raise ValueError("Beskriv själva videoklippet. Loggan och ljudfilen monteras efteråt i Motion.")
    recommended = recommendation(_run(company, user, spec), generation_brief, kind=kind, source=source, end_source=end, shape=options["shape"], budget=options.get("max_cost_usd", "5"))
    plan = build_plan(_run(company, user, spec), generation_brief, kind=kind, source=source, end_source=end,
                      shape=options["shape"], count=1, priority=options["priority"], model_override=options["model"] or recommended["model_id"],
                      inspirations=retrieve_inspiration(user, company.pk, generation_brief, limit=3))
    return {"prompt": plan.prompt, "model_id": plan.selection.model_id, "model_label": MODEL_LABELS.get(plan.selection.model_id, plan.selection.model_id),
            "recommendation": recommended,
            "parameters": plan.parameters, "warnings": [issue.message for issue in plan.preflight],
            "compiler_version": plan.compiler_version, "registry_version": plan.registry_version,
            "generation_brief": generation_brief, "finishing": finishing,
            "finish_note": "Efter AI-klippet monteras original-logga/text och eget ljud med Motion. Klippljudet används inte i detta filmsteg." if finishing else ""}


def media_prepare(company, user, plan, assets):
    spec = {**plan.spec, "compiled": plan.prepared["compiled"]}
    run = _run(company, user, spec, save=True)
    kind = spec["workflow"]
    job = create_job(run, token=uuid.uuid5(plan.pk, "media"), kind=kind, brief=spec["compiled"]["generation_brief"], count=1,
                     source=assets.get("start") or (assets.get("reference") if kind == "image" else None), end_source=assets.get("end"),
                     shape=spec["options"]["shape"], priority=spec["options"]["priority"], model_override=spec["compiled"]["model_id"],
                     include_logo=kind == "image" and bool(assets.get("logo")), logo_override=assets.get("logo"))
    if job.prompt != spec["compiled"]["prompt"] or any(job.parameters.get(key) != value for key, value in spec["compiled"]["parameters"].items()):
        raise ValueError("Modellregistret eller underlaget har ändrats. Skapa en ny plan före start.")
    bind_job(plan, job)
    return {"kind": "media", "job_id": str(job.pk), "run_id": str(run.pk),
            "url": reverse("engine:media_job", kwargs={"workspace_id": company.pk, "run_id": run.pk, "job_id": job.pk})}


def motion_compile(company, user, spec, assets):
    from engine.motion.planner import compile_template
    proposal = spec["proposal"]
    fields = {"headline": proposal["headline"] or proposal["title"], "body": proposal["body"], "cta": proposal["cta"], "attribution": company.name}
    primary = assets.get("start") or assets.get("reference")
    extra = [asset for key, asset in assets.items() if key.startswith("reference:")]
    if len(extra) > 1 or (extra and assets.get("end")) or (assets.get("start") and assets.get("reference")):
        raise ValueError("Detta Motion-upplägg använder två mediefiler. Välj högst två eller använd Flera scener.")
    if primary:
        fields["asset_id"] = str(primary.pk)
    if assets.get("end"):
        fields["secondary_asset_id"] = str(assets["end"].pk)
    elif extra:
        fields["secondary_asset_id"] = str(extra[0].pk)
    if primary and primary.kind == "video":
        return {"model_label": "Motion · befintligt videoklipp", "prompt": "", "motion_spec": finishing_spec(company, spec, primary, assets),
                "warnings": ["Originalklippet återanvänds. Logga och text monteras med Motion, utan ny AI-videogeneration. Klippljudet används inte; välj eget ljud eller musik."]}
    compiled = compile_template("kinetic-text", fields, aspect_ratio=RATIOS[spec["options"]["shape"]],
                                audio=proposal["audio"] != "none", brand_id="golfkuponger" if company.name.casefold() == "golfkuponger" else "workspace")
    if assets.get("audio"):
        compiled["audio"].update(enabled=True, music_asset_id=str(assets["audio"].pk))
    return {"model_label": "Motion · Remotion", "prompt": "", "motion_spec": compiled,
            "warnings": ["Rendering sker när din lokala renderare är ansluten. Förhandsvisningen måste godkännas före slutrendering."]}


def motion_prepare(company, user, plan, assets):
    from engine.motion.service import create_project
    project = create_project(company, user, title=plan.spec["proposal"]["title"], spec=plan.prepared["compiled"]["motion_spec"],
                             key=str(plan.pk), logo_asset=assets.get("logo"))
    return {"kind": "motion", "project_id": str(project.pk), "motion_revision": project.current_revision,
            "url": reverse("engine:motion_workspace", kwargs={"workspace_id": company.pk, "project_id": project.pk})}


def sequence_compile(company, user, spec, assets):
    material = {key: asset for key, asset in assets.items() if key not in {"logo", "audio"}}
    if any(asset.kind != "image" for asset in material.values()):
        raise ValueError("Sekvensens startpunkter behöver vara bilder.")
    images = list(dict.fromkeys(material.values()))
    if len(images) < 2:
        raise ValueError("Lägg till minst två bilder i den ordning filmen ska följa.")
    if (assets.get("start") and images[0] != assets["start"]) or (assets.get("end") and images[-1] != assets["end"]):
        raise ValueError("Flytta startbilden först och slutbilden sist. Övergångarna följer bilagornas ordning.")
    from engine.creative_budget import cost_ceiling
    from engine.creative_director import parse_brief
    numbers = {"en": 1, "ett": 1, "två": 2, "tre": 3, "fyra": 4, "fem": 5, "sex": 6, "sju": 7, "åtta": 8, "nio": 9, "tio": 10, "elva": 11, "tolv": 12}
    duration_text = re.sub(r"\b(" + "|".join(numbers) + r")\s+(?=sekund|sek\b|seconds?\b)", lambda match: str(numbers[match[1].casefold()])+" ", spec["brief"], flags=re.I)
    duration = parse_brief(duration_text, kind="video", has_reference=True, shape=spec["options"]["shape"], priority=spec["options"]["priority"]).duration_seconds or spec["proposal"].get("clip_duration_seconds") or 5
    clips = []
    for index, (source, end) in enumerate(zip(images, images[1:])):
        brief = spec["brief"][:5400]
        request = f"{brief} Duration: {duration} seconds. Aspect ratio: {RATIOS[spec['options']['shape']]}. Use the supplied start and end anchors as fixed canonical visual anchors."
        recommended = recommendation(_run(company, user, spec), request, kind="video", source=source, end_source=end,
                                     shape=spec["options"]["shape"], budget=spec["options"].get("max_cost_usd", "5"), recipe_id="scroll_transition_bridge", clip_count=len(images)-1)
        compiled = build_plan(_run(company, user, spec), request, kind="video", source=source, end_source=end,
                              shape=spec["options"]["shape"], count=1, priority=spec["options"]["priority"],
                              recipe_id="scroll_transition_bridge", model_override=spec["options"]["model"] or recommended["model_id"])
        clips.append({"position": index, "from": str(source.pk), "to": str(end.pk), "brief": brief,
                      "prompt": compiled.prompt, "parameters": compiled.parameters, "model_id": compiled.selection.model_id,
                      "model_label": MODEL_LABELS.get(compiled.selection.model_id, compiled.selection.model_id),
                      "warnings": [issue.message for issue in compiled.preflight]})
    return {"model_label": clips[0]["model_label"], "clips": clips, "parameters": clips[0]["parameters"],
            "recommendation": recommended, "finishing": True,
            "warnings": [f"{len(images)} bilder → {len(clips)} övergångar. Varje klipp granskas och godkänns separat. Kostnadsgränsen är ${cost_ceiling()} per klipp.",
                         "AI-övergångar kan ändra detaljer eller ge oönskad morphing. Granska ett testklipp innan du beställer resten."] + list(dict.fromkeys(warning for clip in clips for warning in clip["warnings"]))}


def sequence_prepare(company, user, plan, assets):
    from engine.sequence import add_anchor, create_clip, create_sequence_project, prepare_anchor_chain_version
    project = create_sequence_project(company, author=user, title=plan.spec["proposal"]["title"], brief=plan.spec["brief"], format="scroll_story", platform="web" if plan.spec["options"]["shape"] == "landscape" else "social")
    anchors = []
    material = [asset for role, asset in assets.items() if role not in {"logo", "audio"}]
    for position, asset in enumerate(dict.fromkeys(material)):
        anchors.append(add_anchor(project, asset, position=position, locked=True))
    jobs = []
    for row, start, end in zip(plan.prepared["compiled"]["clips"], anchors, anchors[1:]):
        clip = create_clip(project, start, end, position=row["position"], recipe_id="scroll_transition_bridge",
                           label=f"Bild {row['position']+1} → {row['position']+2}", model_override=row["model_id"],
                           duration_seconds_target=row["parameters"].get("duration", 5), aspect_ratio=RATIOS[plan.spec["options"]["shape"]])
        version = prepare_anchor_chain_version(clip, brief=row["brief"], priority=plan.spec["options"]["priority"], token=uuid.uuid5(plan.pk, f"clip:{row['position']}"))
        if version.generation.parameters.get("model") != row["model_id"] or any(version.generation.parameters.get(key) != value for key, value in row["parameters"].items()):
            raise ValueError("Vald modell har ändrats. Skapa en ny plan före generation.")
        jobs.append(str(version.generation_id))
        bind_job(plan, version.generation)
        row["prompt"] = version.generation.prompt
    return {"kind": "sequence", "project_id": str(project.pk), "job_ids": jobs,
            "url": reverse("engine:sequence_workspace", kwargs={"workspace_id": company.pk, "project_id": project.pk})}


def text_compile(company, user, spec, assets):
    return {"model_label": "Inläggstext", "prompt": spec["proposal"].get("caption") or spec["proposal"]["body"], "warnings": []}


def text_prepare(company, user, plan, assets):
    run = _run(company, user, plan.spec, save=True)
    return {"kind": "text", "run_id": str(run.pk), "url": reverse("engine:review", kwargs={"workspace_id": company.pk, "run_id": run.pk})}


def finishing_spec(company, spec, footage, assets):
    from engine.motion.schema import validate_spec
    from engine.sequence_export import validate_film_asset
    ratio = RATIOS[spec["options"]["shape"]]
    frames = math.floor((footage.duration_seconds or 0) * 30)
    if not 30 <= frames <= 1800:
        raise ValueError("Använd ett videoklipp mellan 1 och 60 sekunder för detta upplägg.")
    validate_film_asset(footage, ratio, frames)
    proposal = spec["proposal"]
    ending_frames = max(120, math.ceil((len((proposal["headline"] + " " + proposal["cta"]).split()) / 2.5 + 1) * 30))
    audio = assets.get("audio")
    scenes = [{"id": "original-clip", "component": "footage", "duration_frames": frames, "props": {"asset_id": str(footage.pk)}}]
    ending_image = assets.get("end") or next((asset for key, asset in assets.items() if key.startswith("reference:")), None)
    if ending_image:
        validate_film_asset(ending_image, ratio, 120)
        scenes.append({"id": "ending-image", "component": "footage", "duration_frames": 120, "props": {"asset_id": str(ending_image.pk)}})
    scenes.append({"id": "brand-ending", "component": "end-card", "duration_frames": ending_frames,
                   "props": {"headline": proposal["headline"], "cta": proposal["cta"], "eyebrow": company.name[:80]}})
    return validate_spec({"template_id": "sequence-film", "aspect_ratio": ratio,
                          "brand_id": "golfkuponger" if company.name.casefold() == "golfkuponger" else "workspace",
                          "scenes": scenes,
                          "audio": {"enabled": bool(audio) or proposal["audio"] == "music", "music": "bed", "music_asset_id": str(audio.pk) if audio else None}})


def prepare_finish(company, user, plan, assets):
    from engine.models import MediaGeneration
    from engine.motion.service import create_project
    if not plan.prepared["compiled"].get("finishing"):
        raise ValueError("Denna plan saknar ett Motion-avslut.")
    if plan.prepared["kind"] == "sequence":
        from engine.motion.schema import validate_spec
        from engine.sequence_export import validate_film_asset
        pieces = []
        for index, job_id in enumerate(plan.prepared["job_ids"]):
            job = MediaGeneration.objects.get(pk=job_id, run__workspace=company)
            outputs = list(job.assets.filter(kind="video"))
            if job.status != "completed" or len(outputs) != 1:
                raise ValueError("Alla övergångar behöver vara färdiga och ha ett entydigt videoresultat före filmen.")
            from engine.sequence import assert_sequence_generation_video_ready
            assert_sequence_generation_video_ready(job)
            frames = math.floor((outputs[0].duration_seconds or 0) * 30)
            validate_film_asset(outputs[0], RATIOS[plan.spec["options"]["shape"]], frames)
            pieces.append({"id": f"clip-{index}", "component": "footage", "duration_frames": frames, "props": {"asset_id": str(outputs[0].pk)}})
        ending = finishing_spec(company, plan.spec, outputs[0], {key: value for key, value in assets.items() if key in {"logo", "audio"}})
        ending["scenes"] = [*pieces, ending["scenes"][-1]]
        project = create_project(company, user, title=plan.spec["proposal"]["title"], spec=validate_spec(ending), key=str(plan.pk)+":finish", logo_asset=assets.get("logo"))
        return {"finish_project_id": str(project.pk), "motion_revision": project.current_revision,
                "finish_url": reverse("engine:motion_workspace", kwargs={"workspace_id": company.pk, "project_id": project.pk})}
    job = MediaGeneration.objects.get(pk=plan.prepared["job_id"], run__workspace=company)
    outputs = list(job.assets.filter(kind="video"))
    if job.status != "completed" or len(outputs) != 1:
        raise ValueError("Ett färdigt, entydigt videoklipp krävs före filmsteget.")
    project = create_project(company, user, title=plan.spec["proposal"]["title"], spec=finishing_spec(company, plan.spec, outputs[0], assets),
                             key=str(plan.pk) + ":finish", run=job.run, logo_asset=assets.get("logo"))
    return {"finish_project_id": str(project.pk), "motion_revision": project.current_revision,
            "finish_url": reverse("engine:motion_workspace", kwargs={"workspace_id": company.pk, "project_id": project.pk})}


for definition in (
    WorkflowDefinition("image", "Bild", "Skapa eller bearbeta en bild.", media_compile, media_prepare),
    WorkflowDefinition("video", "AI-video", "Generera ett klipp från din idé och valda bilder.", media_compile, media_prepare),
    WorkflowDefinition("motion", "Motion", "Animera text, logga och befintligt material.", motion_compile, motion_prepare),
    WorkflowDefinition("sequence", "Flera scener", "Planera en film med flera sammanhängande delar.", sequence_compile, sequence_prepare),
    WorkflowDefinition("text", "Inläggstext", "Skriv och vidareutveckla text i företagets tonalitet.", text_compile, text_prepare),
):
    register(definition)
