"""Explicit live check. Uses synthetic source material and never writes company data or publishes."""

import json
from datetime import timedelta
from time import monotonic

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from engine.generation import generate


class Command(BaseCommand):
    help = "Make two live AI requests using synthetic source data. No publishing."

    def handle(self, **options):
        context = {
            "company": "Testföretag (endast verifiering)",
            "profile": "En fiktiv golfklubb för programvarutest.",
            "voice": "Vi skriver enkelt och sakligt. Välkommen ut på rangen!",
            "current": "Vi har bytt rangebollar. Nya bollar finns nu i bollautomaten.",
            "source": "Syntetiskt testunderlag",
            "recent_posts": [],
            "valid_until": (timezone.localdate() + timedelta(days=7)).isoformat(),
        }
        started = monotonic()
        ideas = generate(context)
        draft = generate(context, idea=ideas["ideas"][0])
        report = {
            "model": settings.OPENAI_MODEL,
            "seconds": round(monotonic() - started, 1),
            "source": context,
            "ideas": ideas,
            "draft": draft,
            "published": False,
        }
        destination = settings.ENGINE_ROOT / "data" / "generation-check.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(
            f"Live AI verified: {len(ideas['ideas'])} ideas, FB {len(draft['facebook'])} chars, IG {len(draft['instagram'])} chars, {report['seconds']}s. Report: {destination}"
        )
