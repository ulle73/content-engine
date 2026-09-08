import time
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from openai import APIError

from engine import apify
from engine.competitors import OPEN_STATUSES, collect_import, start_import
from engine.models import Company, Competitor, CompetitorImport
from engine.signals import analyze_top


class Command(BaseCommand):
    help = "Refresh due Instagram accounts through Apify; safe to repeat, no publishing."

    def add_arguments(self, parser):
        parser.add_argument("--wait", action="store_true", help="Collect completed runs for up to 12 minutes.")
        parser.add_argument("--company", help="Limit to one company UUID.")

    def handle(self, **options):
        accounts = Competitor.objects.filter(active=True).select_related("company")
        if options["company"]:
            accounts = accounts.filter(company_id=options["company"])
        account_ids = list(accounts.values_list("pk", flat=True))
        failures = []
        for account in accounts:
            if account.last_success_at and account.last_success_at > timezone.now() - timedelta(hours=23):
                continue
            # At most one fresh attempt per account/day even when fallback also fails.
            if account.imports.filter(started_at__gte=timezone.now() - timedelta(hours=23)).exists():
                continue
            try:
                run = start_import(account)
                self.stdout.write(f"Account {account.pk}: {run.status}")
            except apify.ApifyError:
                failures.append(account.pk)
                self.stderr.write(f"Account {account.pk}: could not confirm start. Check the app's import status.")
        deadline = time.monotonic() + (720 if options["wait"] else 0)
        while True:
            active = CompetitorImport.objects.filter(
                competitor_id__in=account_ids, status__in=OPEN_STATUSES
            ).select_related("competitor")
            pending = False
            for run in active:
                if not run.actor_run_id:
                    if run.competitor_id not in failures:
                        failures.append(run.competitor_id)
                    continue
                try:
                    collected = collect_import(run)
                    pending = pending or collected.status in OPEN_STATUSES
                    self.stdout.write(
                        f"Import {run.pk}: {collected.status}; {collected.item_count} posts; USD {collected.cost_usd}"
                    )
                except apify.ApifyError:
                    pending = True
            # Include a fallback just dispatched by collect_import.
            pending = (
                pending or CompetitorImport.objects.filter(competitor_id__in=account_ids, status="running").exists()
            )
            if not pending or time.monotonic() >= deadline:
                break
            time.sleep(15)
        for company in Company.objects.filter(competitors__pk__in=account_ids).distinct():
            try:
                self.stdout.write(f"Company {company.pk}: {analyze_top(company)} content mechanisms ready")
            except (ValueError, APIError):
                failures.append(str(company.pk))
                self.stderr.write("AI analysis could not complete; imported observations are retained.")
        if pending or failures:
            raise CommandError(
                "Some imports or analyses need attention; rerun to resume. No automatic duplicate starts."
            )
