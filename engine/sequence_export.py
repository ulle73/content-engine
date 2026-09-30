"""A guided Sequence -> immutable Motion revision -> shared MediaAsset pipeline.

No provider calls, synthetic footage, embedded clip audio or arbitrary render code.
"""
import math
import hashlib

from django import forms
from django.db import transaction
from django.utils import timezone
from pydantic import Field, StrictStr, field_validator
from typing import Literal

from .media import validate_publishable_asset
from .media_storage import MediaError
from .models import Company, SequenceProject
from .motion import service
from .motion.models import MotionProject
from .motion.outputs import SIZES
from .motion.schema import Closed, validate_spec
from .operator_common import begin_action, finish_action
from .sequence import _assert_generation_matches_current_anchors, _assert_bridge_generation_matches_current_anchors, assert_sequence_project_video_ready


class FilmSettings(Closed):
    mode: Literal["images", "clips"] = "images"
    aspect_ratio: Literal["9:16", "1:1", "16:9"] = "9:16"
    headline: StrictStr = Field(min_length=1, max_length=80)
    cta: StrictStr = Field(default="", max_length=80)
    music: Literal["none", "bed"] = "none"

    @field_validator("headline", "cta")
    @classmethod
    def concise(cls, value, info):
        value = value.strip()
        if info.field_name == "headline" and not value:
            raise ValueError("Skriv ett budskap.")
        if len(value.split()) > 12 or "\n" in value:
            raise ValueError("Använd en kort mening på högst 12 ord.")
        return value


class FilmForm(forms.Form):
    headline = forms.CharField(label="Vad ska tittaren komma ihåg?", max_length=80,
        help_text="En kort mening, högst 12 ord. Exempel: Mer golf för ditt friskvårdsbidrag.")
    cta = forms.CharField(label="Vad ska tittaren göra sedan?", max_length=80, required=False,
        help_text="Valfritt. Exempel: Hitta din nästa golfrunda.")
    mode = forms.ChoiceField(label="Material", choices=[("images", "Mina bilder · färdig bildfilm"), ("clips", "Mina valda videoklipp")])
    aspect_ratio = forms.ChoiceField(label="Var ska filmen visas?", choices=[("9:16", "Reels och Stories · stående"), ("1:1", "Flödet · kvadrat"), ("16:9", "Webb och YouTube · liggande")])
    music = forms.ChoiceField(label="Ljud", choices=[("none", "Utan ljud"), ("bed", "Lugn bakgrundsmusik")],
        help_text="Klippljud används aldrig. Musik får en mjuk start och ett mjukt slut.")

    def clean(self):
        values = super().clean()
        if not self.errors:
            try:
                return FilmSettings.model_validate(values).model_dump()
            except ValueError as exc:
                for error in exc.errors():
                    self.add_error(error["loc"][0], "Skriv en kort mening på högst 12 ord och en rad.")
        return values


def validate_film_asset(asset, ratio, frames, fps=30):
    try:
        validate_publishable_asset(asset)
    except MediaError as exc:
        raise ValueError(str(exc)) from exc
    if asset.purpose == "logo" or asset.kind not in {"image", "video"}:
        raise ValueError("Välj egna bilder eller färdiga videoklipp som material.")
    if asset.expires_at and asset.expires_at <= timezone.now():
        raise ValueError("En mediefil har gått ut. Byt den i sekvensen.")
    if not asset.width or not asset.height:
        raise ValueError("En mediefil saknar verifierbar upplösning. Ladda upp originalet igen.")
    w, h = SIZES[ratio]
    # The full source is contained in the frame. Never stretch or upscale > 1.5x.
    if min(w / asset.width, h / asset.height) > 1.5:
        raise ValueError("En mediefil är för liten för skarp video. Ladda upp en större originalfil.")
    if asset.kind == "video":
        seconds = asset.duration_seconds
        if not seconds or not math.isfinite(seconds) or frames > math.floor(seconds * fps + 1e-6):
            raise ValueError("Ett klipp är kortare än sin scen eller saknar verifierbar längd.")


def _video_asset(version, ratio):
    if not version or version.status != "selected" or version.generation.status != "completed":
        raise ValueError("Granska och välj en färdig version av varje klipp och övergång först.")
    if hasattr(version, "clip_id"):
        _assert_generation_matches_current_anchors(version)
    else:
        _assert_bridge_generation_matches_current_anchors(version)
    videos = list(version.generation.assets.filter(kind="video"))
    if len(videos) != 1:
        raise ValueError("Ett valt klipp saknar ett entydigt videoresultat. Välj en annan version.")
    asset = videos[0]
    seconds = asset.duration_seconds or 0
    if not math.isfinite(seconds):
        raise ValueError("Klippet saknar verifierbar längd.")
    frames = math.floor(seconds * 30 + 1e-6)
    if not 30 <= frames <= 1800:
        raise ValueError("Varje videoklipp behöver vara mellan 1 och 60 sekunder.")
    validate_film_asset(asset, ratio, frames)
    return asset, frames


def compile_film(sequence, settings):
    settings = FilmSettings.model_validate(settings).model_dump()
    if sequence.status == "archived":
        raise ValueError("Öppna en aktiv sekvens för att skapa film.")
    assert_sequence_project_video_ready(sequence)
    pieces = []
    headline_frames = max(120, math.ceil((len(settings["headline"].split()) / 2.5 + 1) * 30))
    ending_frames = max(120, math.ceil(((len(settings["headline"].split()) + len(settings["cta"].split())) / 2.5 + 1) * 30))
    if settings["mode"] == "images":
        for anchor in sequence.anchors.select_related("asset").order_by("position"):
            if anchor.asset.company_id != sequence.company_id:
                raise ValueError("Materialet måste tillhöra sekvensens företag.")
            validate_film_asset(anchor.asset, settings["aspect_ratio"], 120)
            pieces.append((f"anchor-{anchor.pk}", anchor.asset, headline_frames if not pieces else 120))
    else:
        clips = list(sequence.clips.exclude(status="archived").select_related("selected_version__generation", "start_anchor", "end_anchor").order_by("position"))
        bridges = list(sequence.bridges.exclude(status="archived").select_related("selected_version__generation", "start_anchor", "end_anchor"))
        consumed = set()
        for index, clip in enumerate(clips):
            asset, frames = _video_asset(clip.selected_version, settings["aspect_ratio"])
            if asset.company_id != sequence.company_id:
                raise ValueError("Materialet måste tillhöra sekvensens företag.")
            pieces.append((f"clip-{clip.pk}", asset, frames))
            if index + 1 < len(clips):
                next_clip = clips[index + 1]
                between = [b for b in bridges if b.left_clip_id == clip.pk and b.right_clip_id == next_clip.pk]
                if len(between) > 1 or (not between and clip.end_anchor_id != next_clip.start_anchor_id):
                    raise ValueError("Två klipp saknar en tydlig övergång. Använd samma hållpunkt eller välj en övergång mellan dem.")
                if between:
                    bridge = between[0]
                    asset, frames = _video_asset(bridge.selected_version, settings["aspect_ratio"])
                    if asset.company_id != sequence.company_id:
                        raise ValueError("Materialet måste tillhöra sekvensens företag.")
                    consumed.add(bridge.pk)
                    pieces.append((f"bridge-{bridge.pk}", asset, frames))
        if consumed != {b.pk for b in bridges}:
            raise ValueError("En övergång ligger utanför klippordningen. Kontrollera sekvensen innan export.")
    if not pieces:
        raise ValueError("Lägg till minst en bild, eller granska och välj dina videoklipp först.")
    if len(pieces) > 23 or sum(p[2] for p in pieces) + ending_frames > 120 * 30:
        raise ValueError("Gör filmen kortare: högst 23 delar och 120 sekunder inklusive slutbild.")
    scenes = [dict(id=sid, component="footage", duration_frames=frames,
        props={"asset_id": str(asset.pk), "headline": settings["headline"] if i == 0 and frames >= headline_frames else ""})
        for i, (sid, asset, frames) in enumerate(pieces)]
    scenes.append(dict(id="ending", component="end-card", duration_frames=ending_frames,
        props={"headline": settings["headline"], "cta": settings["cta"], "eyebrow": sequence.company.name[:80]}))
    return validate_spec(dict(template_id="sequence-film", aspect_ratio=settings["aspect_ratio"],
        brand_id="golfkuponger" if sequence.company.name.casefold() == "golfkuponger" else "workspace",
        scenes=scenes, audio={"enabled": settings["music"] != "none", "music": settings["music"], "fade_frames": 30}))


def assert_film_current(project, revision):
    if project.source_sequence_id and compile_film(project.source_sequence, project.sequence_settings) != revision.spec:
        raise ValueError("Sekvensens material har ändrats. Förbered en ny filmversion och granska den igen.")


@transaction.atomic
def prepare_film(company, user, sequence_id, *, settings, expected_revision, key):
    service._owner(company, user)
    Company.objects.select_for_update().get(pk=company.pk)
    sequence = SequenceProject.objects.select_for_update(of=("self",)).select_related("company", "source_run").filter(pk=sequence_id, company=company).first()
    if not sequence:
        raise ValueError("Sekvensen finns inte i detta företag.")
    settings = FilmSettings.model_validate(settings).model_dump()
    spec = compile_film(sequence, settings)
    action, new = begin_action(company, user, action="sequence_film", key=key,
        payload={"sequence_id": str(sequence.pk), "settings": settings, "spec": spec, "expected_revision": expected_revision})
    if not new:
        return service.get_project(company, action.result["project_id"])
    project = MotionProject.objects.select_for_update().filter(source_sequence=sequence).first()
    if type(expected_revision) is not int or expected_revision != (project.current_revision if project else 0):
        raise ValueError("Filmen har ändrats. Öppna sekvensen igen innan du sparar.")
    if project:
        revision = project.revisions.get(number=project.current_revision)
        if revision.spec != spec:
            service._revision(project, spec, project.current_revision + 1)
            project.current_revision += 1
            project.approved_preview = None
    else:
        if sequence.source_run_id and MotionProject.objects.filter(run_id=sequence.source_run_id).exists():
            raise ValueError("Utkastet har redan en film. Öppna den via Motion eller skapa sekvensen från ett nytt utkast.")
        project = service.create_project(company, user, title=sequence.title[:160], spec=spec,
            key=hashlib.sha256((key + ":motion").encode()).hexdigest(), run=sequence.source_run)
        project.source_sequence = sequence
    project.sequence_settings = settings
    project.save()
    finish_action(action, result={"project_id": str(project.pk), "revision": project.current_revision})
    return project
