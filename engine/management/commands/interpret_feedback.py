from django.core.management.base import BaseCommand

from engine.review.service import interpret_pending


class Command(BaseCommand):
    help = "Interpret review comments whose AI interpretation failed earlier, and turn them into lessons."

    def handle(self, **options):
        self.stdout.write(f"Tolkade {interpret_pending()} sparade kommentarer.")
