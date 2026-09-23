"""Isolated UX fixture server. Run: .venv/Scripts/python scripts/ux_preview.py

Only synthetic content, a dedicated SQLite file and local media. No production
database, credentials, generation or publishing. Login: preview@example.test /
preview-only. Reuse the dedicated fixture database across server restarts.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.update(
    DJANGO_SETTINGS_MODULE="engine.test_settings",
    APP_URL="http://127.0.0.1:8877", RENDER_EXTERNAL_URL="",
    SECRET_KEY="isolated-ux-preview-not-for-production",
    DATABASE_URL="sqlite:///:memory:", MEDIA_STORAGE="local",
    POSTIZ_ENCRYPTION_SECRET="isolated-ux-preview-not-for-production",
)
# Prevent .env from supplying live provider credentials to this test process.
for key in ("OPENAI_API_KEY", "HIGGSFIELD_API_KEY", "HIGGSFIELD_API_SECRET",
            "APIFY_TOKEN", "APIFY_API_TOKEN", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
            "R2_ENDPOINT_URL", "R2_ACCOUNT_ID", "POSTIZ_API_KEY"):
    os.environ[key] = ""

import django  # noqa: E402
from django.conf import settings  # noqa: E402

preview_dir = ROOT / "data" / "ux-preview"
preview_dir.mkdir(parents=True, exist_ok=True)
settings.DATABASES["default"]["NAME"] = str(preview_dir / "fixtures.sqlite3")
settings.MEDIA_ROOT = preview_dir / "media"
settings.DEBUG = True
settings.TEMPLATES[0]["APP_DIRS"] = False
settings.TEMPLATES[0]["OPTIONS"]["loaders"] = [
    "django.template.loaders.filesystem.Loader", "django.template.loaders.app_directories.Loader",
]
django.setup()

from django.core.management import call_command  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402
from engine.models import (  # noqa: E402
    Company, ContentRun, Competitor, CompetitorPost, CompetitorSnapshot,
    CompetitorImport, AdAccount, CompetitorAd, OwnPost, OwnSnapshot,
    MediaGeneration, DailyRun, DailyStep,
)
from engine import signals, ads  # noqa: E402

call_command("migrate", verbosity=0)
user, created = get_user_model().objects.get_or_create(username="preview@example.test")
if created:
    user.set_password("preview-only")
    user.save()
now = timezone.now()
company, created = Company.objects.get_or_create(owner=user, name="Golfkuponger", defaults={
    "profile": "Golfkuponger hjälper golfare att upptäcka fler banor tillsammans.",
    "voice": "Varm, kunnig och inspirerande. Tydlig svenska utan överdrifter.",
    "current": "Höstens golf handlar om nya banor och tid tillsammans.",
    "source": "Godkänt kampanjunderlag · hösten 2026",
    "valid_until": now.date() + timedelta(days=60),
})
if created:
    Company.objects.create(owner=user, name="Tom arbetsyta – test")
    caption = ("En runda till, innan hösten tar över.\n\n"
               "Det bästa med golf är sällan siffran på scorekortet. Det är samtalen längs fairway, "
               "den första koppen kaffe och känslan när ett slag äntligen sitter. "
               "Vilken bana längtar du tillbaka till? Ta med någon som gör rundan bättre.\n\n")
    ideas = [
        {"title": "En ny bana. Samma golfkompis.", "angle": "Lyft glädjen i att upptäcka något nytt tillsammans.",
         "reason": "En konkret situation gör det lätt att känna igen sig och vilja dela vidare.",
         "source_quote": "Golfkuponger hjälper golfare att upptäcka fler banor tillsammans.",
         "source_field": "profile", "photo_brief": "Två golfare promenerar mot nästa tee i mjukt höstljus."},
        {"title": "Mer av det du spelar för", "angle": "Fokusera på upplevelsen runt spelet.",
         "reason": "Bygger på företagets varma tonalitet och gemenskap.",
         "source_quote": "Höstens golf handlar om nya banor och tid tillsammans.",
         "source_field": "current", "photo_brief": "Närbild på golfbagar vid klubbhuset."},
        {"title": "Din nästa favoritbana väntar", "angle": "Bjud in till upptäckarlust.",
         "reason": "Öppen fråga skapar utrymme för egna erfarenheter.",
         "source_quote": "Upptäck fler banor tillsammans.", "source_field": "profile",
         "photo_brief": "En stilla fairway med morgondimma."},
    ]
    context = {"source": company.source, "valid_until": company.valid_until.isoformat(),
               "company": company.name, "profile": company.profile, "current": company.current,
               "voice": company.voice}
    ContentRun.objects.create(workspace=company, author=user, context=context, ideas=ideas, model="fixture")
    draft = ContentRun.objects.create(workspace=company, author=user, context=context, ideas=ideas,
        selected=0, draft={"facebook": caption * 7, "instagram": caption * 3,
        "photo_brief": "En redaktionell golfbild. " * 70, "checks": ["Stäm av aktuellt underlag.", "Kontrollera rättigheterna till bilden."]}, model="fixture")
    ContentRun.objects.create(workspace=company, author=user, context=context, ideas=ideas, selected=1,
        channel="paid", draft={"facebook": caption, "instagram": caption, "headline": "Mer golf tillsammans",
        "description": "Upptäck din nästa favoritbana", "cta": "Läs mer", "landing_page": "https://example.test/golf"}, model="fixture")
    ContentRun.objects.create(workspace=company, author=user, context=context, ideas=ideas, selected=2,
        draft={"facebook": caption, "instagram": caption}, delivery_status="sent", model="fixture")
    competitor = Competitor.objects.create(company=company, name="Nordic Golf Club", username="preview_golf")
    imported = CompetitorImport.objects.create(competitor=competitor, actor="fixture", status="succeeded", item_count=8)
    for i in range(8):
        post = CompetitorPost.objects.create(competitor=competitor, shortcode=f"preview-{i}",
            url="https://example.test/original", published_at=now - timedelta(days=i+1),
            caption=caption * (4 if i == 0 else 1), format="image",
            classification={"why": "Inlägget börjar med en igenkännbar situation och slutar med en enkel fråga. Det kan göra det lättare att kommentera.",
                "topic": "Golfgemenskap", "mechanisms": ["Igenkänning", "Öppen fråga"],
                "adaptation": "Visa två vänner på väg till en ny bana. Fråga: vem tar du med på nästa runda?"})
        post.classification_hash = signals.classification_hash(post, company)
        post.save()
        CompetitorSnapshot.objects.create(post=post, import_run=imported, observed_at=now,
            likes=420 if i == 0 else 60+i*10, comments=24+i, views=None)
    account = AdAccount.objects.create(company=company, name="Nordic Golf", page_id="123456",
        page_url="https://www.facebook.com/123456", country="SE")
    for i, headline in enumerate(["Dela rundan. Upptäck mer.", "En helg på fairway", "Din nästa golfupplevelse börjar här"]):
        ad = CompetitorAd.objects.create(account=account, external_id=f"fixture-{i}",
            creative={"headline": headline, "text": caption * (4 if i == 0 else 1), "format": "image",
                "platforms": ["FACEBOOK", "INSTAGRAM"], "variant_count": 3, "cta": "LEARN_MORE"},
            creative_hash=f"fixture-{i}", first_seen_at=now-timedelta(days=14), last_seen_at=now, is_active=True,
            classification={"hook": "Golf tillsammans", "message": "En upplevelse att dela", "offer": "Inget verifierat erbjudande",
                "cta": "Läs mer", "themes": ["Gemenskap", "Upptäckarlust"],
                "adaptation": "Utgå från en riktig golfupplevelse och låt gemenskapen vara huvudbudskapet."})
        ad.classification_hash = ads.classification_hash(ad, company)
        ad.save()
    own = OwnPost.objects.create(company=company, postiz_id="fixture", integration_id="fixture",
        platform="instagram", format="image", caption=caption*4, url="https://example.test/published", published_at=now-timedelta(days=5), run=draft)
    OwnSnapshot.objects.create(post=own, observed_at=now, source_day=now.date(), metrics={"likes":420, "reach":8400, "comments":32}, raw={}, baseline={"relative":1.8, "metric":"likes", "peers":12, "confidence_label":"moderate"})
    for state in ("completed", "failed", "unknown"):
        MediaGeneration.objects.create(run=draft, kind="image", provider="fixture", brief=caption*15,
            prompt="test"*1500, parameters={"example":"long-value-"*100}, status=state,
            error=("Tjänsten kunde inte nås. " + '{"request_id":"' + "x"*350 + '","status":"timeout"}') if state != "completed" else "")
    day = DailyRun.objects.create(day=now.date(), status="completed")
    DailyStep.objects.create(run=day, company=company, stage="fixture", key="request-"+"x"*140,
        status="failed", message="Testfel: " + "LångtFelUtanMellanslag"*20,
        result={"status":"fixture"})
    print("Synthetic fixture content created.")
print(f"Preview: http://127.0.0.1:8877/company/{company.pk}/", flush=True)
# A clearly labelled synthetic aspect-ratio fixture, never production media.
if not company.media_assets.exists():
    from io import BytesIO
    from PIL import Image, ImageDraw
    from engine.media import store_asset
    for size in ((900, 1200), (1200, 700), (900, 900)):
        picture = Image.new("RGB", size, "#e7eedf")
        draw = ImageDraw.Draw(picture)
        draw.rectangle((24, 24, size[0]-25, size[1]-25), outline="#24563d", width=8)
        draw.ellipse((size[0]*.25, size[1]*.25, size[0]*.75, size[1]*.75), fill="#77936b")
        draw.text((48, 48), f"UX TEST MEDIA - {size[0]} x {size[1]}", fill="#183b29", font_size=32)
        stream = BytesIO()
        picture.save(stream, format="PNG")
        asset = store_asset(company, stream.getvalue(), alt_text=f"Testbild {size[0]} gånger {size[1]} pixlar")
        if size == (900, 1200):
            draft = company.contentrun_set.filter(delivery_status="draft", selected=0).first()
            draft.media_asset = asset
            draft.save(update_fields=["media_asset"])
            asset.generation = draft.media_jobs.filter(status="completed").first()
            asset.save(update_fields=["generation"])
if "--seed-only" not in sys.argv:
    call_command("runserver", "127.0.0.1:8877", use_reloader=False)
