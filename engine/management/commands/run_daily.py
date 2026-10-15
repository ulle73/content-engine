import json
import os
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from engine.daily import AlreadyRunning, run_daily, safe_error
from engine.models import Company


class Command(BaseCommand):
    help = "Run/resume daily imports, media collection, cleanup and analysis. Partial success is retained."

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Only this company UUID.")
        parser.add_argument("--wait-seconds", type=int, default=720, help="Shared time budget; 0 runs one pass without polling.")
        parser.add_argument("--phase", choices=("full", "start"), default="full",
                            help="start: only start the day's scrapes (one pass, no waiting) so a full run later "
                                 "finds them finished; full: everything, resuming the same day's ledger.")

    def handle(self, **options):
        if options["wait_seconds"] < 0:
            raise CommandError("--wait-seconds must be non-negative.")
        if options["company"]:
            try:
                company_id = uuid.UUID(options["company"])
            except ValueError:
                raise CommandError("--company must be a company UUID.")
            if not Company.objects.filter(pk=company_id).exists():
                raise CommandError("Company not found.")
        stages, wait_seconds = None, options["wait_seconds"]
        if options["phase"] == "start":
            from engine.daily_stages import START_STAGES
            stages, wait_seconds = START_STAGES, 0
        try:
            run = run_daily(company_id=options["company"], wait_seconds=wait_seconds, stages=stages,
                            write=self.stdout.write)
        except AlreadyRunning as exc:
            self.stdout.write(str(exc))
            return
        except Exception as exc:
            raise CommandError(safe_error(exc)) from None
        self.stdout.write(json.dumps({"daily_run": str(run.pk), "day": str(run.day), "status": run.status, **run.summary}))
        summary = f"# Content Engine daily: {run.status}\n\nRun `{run.pk}` · {run.day} · attempt {run.attempts}\n\n"
        summary += "| Company | Stage | Item | Status | Attempts |\n|---|---|---|---|---|\n"
        for step in run.steps.order_by("company_id", "stage", "key"):
            # Generated identifiers only; no user/provider strings can inject workflow commands or Markdown.
            summary += f"| {step.company_id} | {step.stage} | {step.key} | {step.status} | {step.attempts} |\n"
        summary += "\nRerun the same command to resume incomplete work. Successful items are retained. Details are in company Settings.\n"
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as file:
                file.write(summary)
        if options["phase"] == "start":
            return  # pending scrapes are the point of this phase; the full run collects them
        if run.status == "partial":
            self.stdout.write("::warning title=Daily partial success::Completed work was saved. Check company Settings and rerun incomplete items.")
        elif run.status == "failed":
            raise CommandError("Daily failed: no work succeeded. See persisted status in company Settings.")
