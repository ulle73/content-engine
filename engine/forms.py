from django import forms
from django.utils import timezone

from .models import BrandContext


class BrandForm(forms.ModelForm):
    class Meta:
        model = BrandContext
        fields = ["profile", "voice", "current", "source", "valid_until"]
        labels = {
            "profile": "Om företaget, målgrupp och mål",
            "voice": "Så låter vi — klistra in 3–5 egna inlägg",
            "current": "Aktuellt just nu",
            "source": "Varifrån kommer uppgifterna?",
            "valid_until": "Uppgifterna gäller till och med",
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
