"""Beginner-facing choices over the existing trusted Creative Engine contracts."""
import uuid

from django import forms
from django.db.models import Q
from django.utils import timezone

from .creative_core import ReferenceRole
from .creative_recipes import get_recipe
from .creative_registry import verified_models
from .media import publishable_assets
from .models import MediaAsset

# Presentation labels only. Requirements, prompts and routing remain in the
# trusted recipe/model registries shared by web, Sequence and MCP.
PRESETS = (
    ("", "Egen idé · Auto", ("image", "video"), "Beskriv motivet och resultatet. Motorn väljer ett kompatibelt upplägg."),
    ("premium_product_reveal", "Visa en produkt", ("video",), "Välj en startbild och beskriv produkten. Ett lugnt avslöjande med fokus på produktens detaljer."),
    ("landscape_environment_hero", "Visa en plats", ("video",), "Beskriv platsen och känslan. En sammanhängande miljöbild; startbild är valfri."),
    ("before_after", "Från före till efter", ("video",), "Välj både startbild och slutbild och beskriv förändringen. Inga resultat eller bevis hittas på."),
    ("scroll_orbit_hero", "Rörelse mellan två bilder", ("video",), "Välj två bilder av samma motiv. En sammanhängande kamerarörelse binder ihop dem."),
)


def preset_choices(kind):
    return [(key, label) for key, label, kinds, _ in PRESETS if kind in kinds]


class FrameChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        label = obj.alt_text or obj.brief or "Bild"
        return f"{label[:65]} · {obj.created_at:%d/%m %H:%M} · {str(obj.pk)[:6]}"


class MediaComposerForm(forms.Form):
    token = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    kind = forms.ChoiceField(choices=(("image", "Bild"), ("video", "Video")), widget=forms.HiddenInput)
    brief = forms.CharField(label="Vad vill du skapa?", max_length=6000, widget=forms.Textarea(attrs={
        "id": "media-brief", "rows": 4, "placeholder": "Beskriv vad som ska synas och vilken känsla du vill förmedla. Du behöver inte skriva en teknisk prompt.",
    }))
    preset = forms.ChoiceField(label="Börja med ett upplägg", required=False)
    source_asset = FrameChoice(label="Startbild / referensbild", queryset=MediaAsset.objects.none(), required=False, empty_label="Ingen · skapa från beskrivningen")
    end_asset = FrameChoice(label="Slutbild", queryset=MediaAsset.objects.none(), required=False, empty_label="Ingen · låt videon avslutas naturligt")
    priority = forms.ChoiceField(label="Prioritet", choices=(("balanced", "Balanserad · rekommenderas"), ("quality", "Prioritera kvalitet"), ("economy", "Prioritera låg kostnad")), initial="balanced")
    shape = forms.ChoiceField(label="Format", choices=(("portrait", "Stående / Reel"), ("square", "Kvadrat"), ("landscape", "Liggande")), initial="portrait")
    count = forms.TypedChoiceField(label="Antal bildalternativ", choices=((1, "1 bild · rekommenderas"), (2, "2 bilder"), (3, "3 bilder"), (4, "4 bilder")), coerce=int, initial=1, required=False, empty_value=1)
    include_logo = forms.BooleanField(label="Lägg på företagets exakta loggfil", required=False)
    model_override = forms.CharField(label="Modell", max_length=160, required=False, widget=forms.Select)

    def __init__(self, *args, company, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.kind = self["kind"].value() or "image"
        self.fields["preset"].choices = preset_choices(self.kind)
        images = publishable_assets(company.media_assets.filter(kind="image").filter(
            Q(purpose="content") | Q(pk=company.official_logo_id)
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))).order_by("-created_at")
        self.images = list(images[:120])
        selected = [self[name].value() for name in ("source_asset", "end_asset") if self[name].value()]
        # Include valid older selections in the bounded picker without widening
        # validation to another company, expired media or Motion previews.
        for value in selected:
            try:
                image = images.filter(pk=uuid.UUID(str(value))).first()
            except (ValueError, TypeError):
                image = None
            if image and image not in self.images:
                self.images.append(image)
        for name in ("source_asset", "end_asset"):
            field = self.fields[name]
            field.queryset = images
            field.choices = [("", field.empty_label), *[(str(image.pk), field.label_from_instance(image)) for image in self.images]]
            field.error_messages["invalid_choice"] = "Bilden är inte tillgänglig för företaget. Välj en bild igen."
        modes = ("text-to-video", "image-to-video") if self.kind == "video" else ("text-to-image", "image-to-image")
        models = {model.model_id: model for mode in modes for model in verified_models(self.kind, mode)}
        self.models = list(models.values())
        mode = ("image-to-video" if self["source_asset"].value() else "text-to-video") if self.kind == "video" else ("image-to-image" if self["source_asset"].value() else "text-to-image")
        self.model_options = [
            {"id": model.model_id, "modes": {mode: bool(model.request_contract(mode) and ReferenceRole.end_image in model.request_contract(mode).supported_reference_roles) for mode in modes if model.request_contract(mode)}}
            for model in self.models
        ]
        choices = [item["id"] for item in self.model_options if mode in item["modes"] and (not self["end_asset"].value() or item["modes"][mode])]
        self.fields["model_override"].widget.choices = [("", "Auto · rekommenderas"), *[(model_id, model_id) for model_id in choices]]
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("id", "media-" + name.replace("_", "-"))
        self.fields["preset"].widget.attrs["aria-describedby"] = "composer-preset-help"

    def clean(self):
        data = super().clean()
        kind = data.get("kind")
        source, end = data.get("source_asset"), data.get("end_asset")
        if end and (not source or kind != "video"):
            self.add_error("end_asset", "En slutbild kräver video och en startbild.")
        preset = data.get("preset")
        recipe = get_recipe(preset) if preset else None
        if recipe:
            roles = ({ReferenceRole.start_image} if source else set()) | ({ReferenceRole.end_image} if end else set())
            if ReferenceRole.start_image in recipe.required_reference_roles and not source:
                self.add_error("source_asset", "Välj en startbild för det här upplägget.")
            if ReferenceRole.end_image in recipe.required_reference_roles and not end:
                self.add_error("end_asset", "Välj en slutbild för det här upplägget.")
            allowed = set(recipe.required_reference_roles) | set(recipe.optional_reference_roles)
            if roles - allowed:
                self.add_error("end_asset", "Det här upplägget använder inte slutbild. Välj Egen idé eller ta bort slutbilden.")
        override = data.get("model_override")
        if override and override not in {model.model_id for model in self.models}:
            self.add_error("model_override", "Modellen är inte tillgänglig. Välj Auto eller en modell i listan.")
        if data.get("include_logo") and (kind != "image" or not self.company.official_logo_id):
            self.add_error("include_logo", "Företagets officiella logga behövs och kan bara läggas på bilder.")
        return data

    @property
    def preset_help(self):
        return {key: hint for key, _, kinds, hint in PRESETS if self.kind in kinds}
