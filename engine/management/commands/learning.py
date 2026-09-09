import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from engine.learning import promote, record_outcome, shadow_evaluation, train
from engine.models import Company, ContentRun, LearningModel


class Command(BaseCommand):
    help = "Import real own outcomes, train/evaluate shadow models, or explicitly promote a qualified model."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["import", "train", "evaluate", "promote"])
        parser.add_argument("--company", required=True)
        parser.add_argument("--channel", choices=["organic", "paid"], default="organic")
        parser.add_argument("--file", help="JSON list of own seven-day result records; never competitor data.")
        parser.add_argument("--model", help="Exact saved model version for evaluation/promotion.")

    def handle(self, **options):
        company = Company.objects.get(pk=options["company"])
        action = options["action"]
        if action == "train":
            result = train(company, options["channel"])
        elif action in ("evaluate", "promote"):
            if not options["model"]:
                raise CommandError("Ange --model med exakt versions-id.")
            model = LearningModel.objects.get(company=company, channel=options["channel"], version=options["model"])
            try:
                if action == "promote":
                    promote(model)
                result = shadow_evaluation(model)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
        else:
            if not options["file"]:
                raise CommandError("Ange --file med resultatfilens sökväg.")
            rows = json.loads(Path(options["file"]).read_text(encoding="utf-8"))
            if not isinstance(rows, list) or len(rows)>1000:
                raise CommandError("Resultatfilen ska innehålla högst 1000 poster.")
            result = {"saved":[], "failed":[]}
            for index, row in enumerate(rows):
                try:
                    run = ContentRun.objects.get(pk=row["run_id"], workspace=company, channel=options["channel"])
                    outcome = record_outcome(run, source=row["source"], external_id=row["external_id"],
                        published_at=datetime.fromisoformat(row["published_at"]), window_end=datetime.fromisoformat(row["window_end"]),
                        observed_at=datetime.fromisoformat(row["observed_at"]), metrics=row["metrics"], evidence=row["evidence"])
                    result["saved"].append(outcome.pk)
                except (ValueError, KeyError, TypeError, ContentRun.DoesNotExist) as exc:
                    result["failed"].append({"row":index, "reason":str(exc) if isinstance(exc, ValueError) else "Ogiltigt resultat eller innehåll."})
        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str))
