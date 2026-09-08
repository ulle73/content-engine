from django.core.management.base import BaseCommand

from engine.media import cleanup_expired


class Command(BaseCommand):
    help = "Remove expired, unused media previews (never previously selected media)."

    def handle(self, **options):
        self.stdout.write(f"Removed {cleanup_expired(limit=1000)} expired previews.")
