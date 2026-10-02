"""Isolated manual browser acceptance server. No .env, cloud storage or provider calls."""
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "engine.test_settings"
os.environ["APP_URL"] = "http://127.0.0.1:8771"
os.environ["MEDIA_STORAGE"] = "local"
import engine.test_settings as config

target = ROOT / "data" / "assistant-ui"
target.mkdir(parents=True, exist_ok=True)
config.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(target / "ui.sqlite3")}}
config.MEDIA_ROOT = target / "media"
import django

django.setup()
from django.contrib.auth import get_user_model
from django.core.management import call_command
from PIL import Image, ImageDraw

from engine.assistant import service
from engine.assistant.contracts import Proposal
from engine.media import store_asset
from engine import media_providers
from engine.media_storage import MediaError
from engine.models import Company


def mock_plan(*, payload, **kwargs):
    request = payload["request"]
    workflow = request["workflow"] if request["workflow"] != "auto" else "motion"
    headline = "Mer golf. Mer glädje." if "kortare" not in request["message"].casefold() else "Mer golf."
    return Proposal(answer="Jag har samlat din idé till en plan. Granska materialet och fortsätt med en ändring eller förbered projektet.",
                    title="Golfkuponger · kreativt test", workflow=workflow, brief=payload["previous_brief"] or request["message"],
                    headline=headline, body="Ta med en vän och gör plats för mer golf.", cta="Upptäck Golfkuponger.se",
                    caption="Mer golf. Mer glädje. Ta med en vän till nästa runda.", audio="none"), {"model": "isolated-fixture", "cost_usd": 0}


service.structured_assistant = mock_plan
media_providers.estimate_video = lambda job: (job.parameters["model"], {}, {"estimate": {"usd": "1.0280"}, "fixture": True})
def no_paid_media(*args, **kwargs):
    raise MediaError("Isolerad UI-fixture: betald generation är avstängd.")
media_providers.start_video = no_paid_media
media_providers.generate_images = no_paid_media
call_command("migrate", interactive=False, verbosity=0)
user, _ = get_user_model().objects.get_or_create(username="studio@example.test")
if not user.check_password("Isolated-studio-only-2026!"):
    user.set_password("Isolated-studio-only-2026!")
    user.save()
company, _ = Company.objects.get_or_create(owner=user, name="Golfkuponger TEST", defaults={"profile": "Golfpresentkort. Endast syntetisk testdata.", "voice": "Varm och enkel svenska."})
if not company.media_assets.exists():
    for index, label in enumerate(["Golfbollar på green", "Logga TEST", "Slutbild på mörk bakgrund", *[f"Biblioteksbild TEST {i}" for i in range(25)]]):
        image = Image.new("RGB", (640, 960), "#103d2e" if index % 2 else "#497652")
        draw = ImageDraw.Draw(image)
        draw.ellipse((190, 380, 450, 640), fill="#f4f4ed")
        draw.text((30, 35), label, fill="white")
        stream = io.BytesIO()
        image.save(stream, "PNG")
        store_asset(company, stream.getvalue(), alt_text=label)
(target / "fixture.json").write_text(json.dumps({"company": str(company.pk), "url": f"http://127.0.0.1:8771/company/{company.pk}/studio/"}), encoding="utf-8")
call_command("runserver", "127.0.0.1:8771", use_reloader=False, verbosity=0)
