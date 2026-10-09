from django.core.management.base import BaseCommand

from engine.edit.service import recover


class Command(BaseCommand):
    help = ("Cloud edit jobs: requeue jobs whose renderer vanished, retry Discord posts and dispatch the "
            "Edit Render workflow for queued jobs (needs GITHUB_DISPATCH_TOKEN).")

    def add_arguments(self, parser):
        parser.add_argument("--no-discord", action="store_true",
                            help="Skip Discord retries (when APP_URL is not the public app URL, e.g. in GitHub Actions).")

    def handle(self, **options):
        stats = recover(send_discord=not options["no_discord"], redispatch=True)
        self.stdout.write("Klippjobb: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
