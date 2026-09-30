from django import forms
from django.utils import timezone

from .models import Company, MediaAsset


class BrandForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["profile", "voice", "current", "source", "valid_until"]
        labels = {
            "profile": "Vad gör ni och vilka vill ni nå?",
            "voice": "Klistra in texter som låter som er",
            "current": "Aktuellt just nu",
            "source": "Varifrån kommer uppgifterna?",
            "valid_until": "Aktuellt till och med",
        }
        widgets = {
            "profile": forms.Textarea(attrs={"rows": 4, "maxlength": 16000}),
            "voice": forms.Textarea(attrs={"rows": 5, "maxlength": 16000}),
            "current": forms.Textarea(attrs={"rows": 4, "maxlength": 16000}),
            "valid_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean(self):
        data = super().clean()
        for field in ["profile", "voice", "current"]:
            if len(data.get(field, "")) > 16000:
                self.add_error(field, "Högst 16 000 tecken.")
        return data


def validate_context(context):
    if not context.profile.strip() or not context.current.strip() or not context.source.strip():
        raise ValueError("Fyll i företagsprofil, aktuella uppgifter och källa först.")
    if not context.valid_until:
        raise ValueError("Ange hur länge de aktuella uppgifterna gäller.")
    if context.valid_until < timezone.localdate():
        raise ValueError("De aktuella uppgifterna har gått ut. Uppdatera dem först.")


def snapshot_company_context(company):
    """Capture company facts without fetching providers or inventing missing data."""
    return {
        "company": company.name,
        "profile": company.profile,
        "voice": company.voice,
        "current": company.current,
        "source": company.source,
        "valid_until": company.valid_until.isoformat() if company.valid_until else "",
        "captured_at": timezone.now().isoformat(),
    }


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name"]
        labels = {"name": "Företagets namn"}


class MediaCreationForm(forms.Form):
    """One company-scoped contract for the editor and free local plan preview."""

    token = forms.UUIDField(widget=forms.HiddenInput)
    kind = forms.ChoiceField(choices=[("image", "Bild"), ("video", "Video")], widget=forms.HiddenInput)
    brief = forms.CharField(label="Vad ska h\u00e4nda?", max_length=6000,
                            widget=forms.Textarea(attrs={"rows": 4, "id": "media-brief", "placeholder": "Kameran n\u00e4rmar sig golfbollen. Bollen lyfter och flyger mot kameran."}))
    source_asset = forms.ModelChoiceField(queryset=MediaAsset.objects.none(), required=False, label="Startbild", empty_label="Ingen startbild")
    end_asset = forms.ModelChoiceField(queryset=MediaAsset.objects.none(), required=False, label="Slutbild", empty_label="Ingen slutbild")
    shape = forms.ChoiceField(label="Format", choices=[("portrait", "St\u00e5ende / Reel"), ("square", "Kvadrat"), ("landscape", "Liggande")], initial="portrait", required=False)
    count = forms.TypedChoiceField(label="Antal bilder", choices=[(str(i), f"{i} bild" if i == 1 else f"{i} bilder") for i in range(1, 5)], coerce=int, initial=1, required=False, empty_value=1)
    priority = forms.ChoiceField(label="Prioritet", choices=[("balanced", "Balanserad"), ("quality", "Prioritera kvalitet"), ("economy", "Spara kostnad")], initial="balanced", required=False)
    include_logo = forms.BooleanField(label="L\u00e4gg p\u00e5 f\u00f6retagets exakta logga", required=False)
    recipe_id = forms.ChoiceField(label="Mall", required=False)
    duration_seconds = forms.TypedChoiceField(label="L\u00e4ngd", choices=[("", "Auto")]+[(str(i), f"{i} sekunder") for i in range(4, 31)], coerce=int, empty_value=None, required=False)
    camera = forms.ChoiceField(label="Kameran ska", required=False)
    subject_motion = forms.ChoiceField(label="Motivet ska", required=False)
    ending = forms.ChoiceField(label="Avslut", required=False)
    audio = forms.ChoiceField(label="Ljud", choices=[("auto", "F\u00f6lj min id\u00e9"), ("none", "Utan ljud"), ("native", "Med ljud")], initial="auto", required=False)
    resolution = forms.ChoiceField(label="Uppl\u00f6sning", choices=[("auto", "Auto"), ("480p", "480p"), ("720p", "720p"), ("1080p", "1080p"), ("4k", "4K")], initial="auto", required=False)
    model_override = forms.CharField(label="Modell", max_length=120, required=False, widget=forms.Select)

    def __init__(self, *args, company, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        from .media import publishable_assets
        from .creative_controls import CAMERAS, MOTIONS, ENDINGS, TEMPLATE_LABELS, creation_catalog
        from .creative_recipes import registry
        kind = (self.data if self.is_bound else self.initial).get("kind", "image")
        self.catalog = creation_catalog(kind)
        images = publishable_assets(company.media_assets.filter(kind="image").filter(
            Q(purpose="content") | Q(pk=company.official_logo_id)).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))).order_by("-created_at")
        for name in ("source_asset", "end_asset"):
            self.fields[name].queryset = images
            self.fields[name].label_from_instance = lambda asset: asset.alt_text or f"Bild {str(asset.pk)[:8]}"
            self.fields[name].widget.attrs["class"] = "creator-reference-select"
        for name, options in (("camera", CAMERAS), ("subject_motion", MOTIONS), ("ending", ENDINGS)):
            self.fields[name].choices = [(key, label) for key, (label, _) in options.items()]
            self.fields[name].initial = "auto"
        self.fields["recipe_id"].choices = [("", "Egen id\u00e9 / Auto")] + [
            (r.recipe_id, TEMPLATE_LABELS.get(r.recipe_id, (r.name, ""))[0]) for r in registry() if kind in r.kinds]
        # Include an invalid previously-selected model so it is never silently reset to Auto.
        values = self.data if self.is_bound else self.initial
        roles = {role for field, role in (("source_asset", "START_IMAGE"), ("end_asset", "END_IMAGE")) if values.get(field)}
        mode = ("image-to-video" if "START_IMAGE" in roles else "text-to-video") if kind == "video" else ("image-to-image" if roles else "text-to-image")
        models = {item["id"]: item["label"] for item in self.catalog["models"]
                  if item["mode"] == mode and roles <= set(item["roles"]) and set(item["required"]) <= roles}
        selected = (self.data if self.is_bound else self.initial).get("model_override", "")
        if selected and selected not in models:
            models[selected] = selected + " (inte tillg\u00e4nglig)"
        self.fields["model_override"].widget.choices = [("", "Auto \u00b7 rekommenderas"), *models.items()]
        for name, field in self.fields.items():
            if name not in {"token", "kind"}:
                field.widget.attrs["data-creator-field"] = name

    def clean(self):
        data = super().clean()
        if data.get("end_asset") and not data.get("source_asset"):
            self.add_error("end_asset", "V\u00e4lj en startbild f\u00f6rst, eller ta bort slutbilden.")
        if data.get("kind") == "image" and data.get("end_asset"):
            self.add_error("end_asset", "Slutbild anv\u00e4nds bara f\u00f6r video.")
        return data

    def job_options(self):
        from .creative_controls import CreativeControls
        data = self.cleaned_data
        controls = CreativeControls.model_validate({key: data.get(key) or (None if key == "duration_seconds" else "auto")
                                                   for key in CreativeControls.model_fields})
        return {"kind": data["kind"], "brief": data["brief"], "count": data.get("count") or 1,
                "shape": data.get("shape") or "portrait", "source": data.get("source_asset"),
                "end_source": data.get("end_asset"), "include_logo": data.get("include_logo", False),
                "priority": data.get("priority") or "balanced", "recipe_id": data.get("recipe_id") or None,
                "model_override": data.get("model_override", ""), "controls": controls.model_dump(mode="json")}
