"""Browser fields are derived from the canonical template contract."""

from django import forms
from django.db.models import Q
from django.utils import timezone

from engine.media import publishable_assets
from engine.models import MediaAsset

from .planner import compile_template, template_schema


class MotionForm(forms.Form):
    title = forms.CharField(label="Projektnamn", max_length=160)
    aspect_ratio = forms.ChoiceField(
        label="Format", choices=[("9:16", "Stående · 9:16"), ("1:1", "Kvadrat · 1:1"), ("16:9", "Liggande · 16:9")]
    )
    audio = forms.BooleanField(label="Musik och ljudeffekter", required=False, initial=True)

    @property
    def basic_fields(self):
        required = set(template_schema(self.template_id)["required"])
        return [
            self[name]
            for name in self.fields
            if name in required | {"title", "aspect_ratio", "headline", "body", "cta"}
        ]

    @property
    def advanced_fields(self):
        basic = {field.name for field in self.basic_fields}
        return [self[name] for name in self.fields if name not in basic]

    def __init__(self, company, template_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company, self.template_id = company, template_id
        schema = template_schema(template_id)
        assets = publishable_assets(
            MediaAsset.objects.filter(company=company).filter(Q(expires_at=None) | Q(expires_at__gt=timezone.now()))
        )
        for name, prop in schema["properties"].items():
            options = {"label": prop["title"], "required": name in schema["required"]}
            if name.endswith("asset_id"):
                choices = (
                    assets.filter(kind="video")
                    if name == "end_card_asset_id"
                    else assets.filter(kind__in=["image", "video"])
                )
                field = forms.ModelChoiceField(queryset=choices, empty_label="Ingen fil", **options)
                field.label_from_instance = lambda asset: asset.alt_text or asset.brief[:80] or asset.get_kind_display()
            elif prop["type"] == "integer":
                field = forms.IntegerField(min_value=prop["minimum"], max_value=prop["maximum"], **options)
            elif prop["type"] == "number":
                field = forms.FloatField(min_value=prop["minimum"], max_value=prop["maximum"], **options)
            elif prop["type"] == "array":
                field = forms.CharField(
                    widget=forms.Textarea(attrs={"rows": 4}),
                    help_text="En punkt per rad. Nyckeltal: namn | värde.",
                    **options,
                )
            else:
                field = forms.CharField(
                    max_length=prop["maxLength"],
                    widget=forms.Textarea(attrs={"rows": 3}) if name == "body" else forms.TextInput(),
                    **options,
                )
            self.fields[name] = field

    def clean_items(self):
        rows = []
        for line in self.cleaned_data.get("items", "").splitlines():
            if not line.strip():
                continue
            parts = line.rsplit("|", 1)
            item = {"label": parts[0].strip()}
            if len(parts) == 2:
                try:
                    item["value"] = float(parts[1].strip().replace(",", "."))
                except ValueError:
                    raise forms.ValidationError("Ange ett tal efter |.") from None
            rows.append(item)
        return rows

    def compile(self):
        fields = {}
        for name in template_schema(self.template_id)["properties"]:
            value = self.cleaned_data.get(name)
            if value is not None and value != "" and value != []:
                fields[name] = str(value.pk) if isinstance(value, MediaAsset) else value
        return compile_template(
            self.template_id,
            fields,
            aspect_ratio=self.cleaned_data["aspect_ratio"],
            audio=self.cleaned_data["audio"],
            brand_id="golfkuponger" if self.company.name.casefold() == "golfkuponger" else "workspace",
        )


def revision_initial(project, spec):
    initial = {"title": project.title, "aspect_ratio": spec["aspect_ratio"], "audio": spec["audio"]["enabled"]}
    for scene in spec["scenes"]:
        for name, value in scene["props"].items():
            if value and name not in initial:
                initial[name] = value
    if spec["template_id"] == "monthly-wrapped":
        scenes = spec["scenes"]
        initial.update(
            month=scenes[0]["props"]["headline"].split("\n")[0],
            count=scenes[1]["props"]["value"],
            total=scenes[2]["props"]["value"],
            area=scenes[3]["props"]["items"][0]["label"],
        )
    if isinstance(initial.get("items"), list):
        initial["items"] = "\n".join(
            item["label"] + (" | " + str(item["value"]) if "value" in item else "") for item in initial["items"]
        )
    initial["end_card_asset_id"] = spec.get("end_card_asset_id")
    return initial


def template_editable(project, spec):
    """Do not silently overwrite scene/audio customizations made through MCP."""
    try:
        form = MotionForm(project.company, spec["template_id"], data=revision_initial(project, spec))
        return form.is_valid() and form.compile() == spec
    except (ValueError, KeyError, IndexError):
        return False
