"""Recover already-submitted media jobs without creating new paid work."""
from django.core.management.base import BaseCommand

from engine.media import recover_media_jobs


class Command(BaseCommand):
    help = "Poll/recover existing running/saving media generations. Never submits queued generations."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        result = recover_media_jobs(limit=options["limit"])
        self.stdout.write(" ".join(f"{key}={value}" for key, value in result.items()))
