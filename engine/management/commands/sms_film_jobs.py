from django.core.management.base import BaseCommand

from engine.smsfilm import service


class Command(BaseCommand):
    help = "Återköar SMS-filmer vars renderare försvann och väcker GitHub för filmer som väntat för länge."

    def add_arguments(self, parser):
        parser.add_argument("--no-dispatch", action="store_true")

    def handle(self, *args, no_dispatch=False, **options):
        stats = service.recover(redispatch=not no_dispatch)
        self.stdout.write(f"SMS-filmer: {stats['requeued']} återköade, {stats['failed']} misslyckade, "
                          f"{stats['redispatched']} väckta.")
