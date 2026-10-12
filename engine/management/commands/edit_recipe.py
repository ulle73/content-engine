import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from engine.edit import planner
from engine.edit.models import EditJob
from engine.edit.service import serialize
from engine.media_storage import open_asset
from engine.models import Company


class Command(BaseCommand):
    help = ("Test cut of a production recipe: plan it from the media bank (free stock fills unfilmed mood shots), "
            "render it on Edit Render, wait for the result and save the master, critique and gate verdict.")

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True)
        parser.add_argument("--recipe", required=True)
        parser.add_argument("--format", default="9:16")
        parser.add_argument("--wait", type=int, default=900, help="Seconds to wait for the render (0 = do not wait).")
        parser.add_argument("--out", default="", help="Folder for master.mp4 and report.json.")

    def handle(self, **options):
        company = Company.objects.filter(name__iexact=options["company"]).first()
        if not company:
            raise CommandError(f"Hittar inget bolag: {options['company']}")
        try:
            plan, job = planner.render_recipe(company, options["recipe"], format=options["format"], allow_missing=True)
        except planner.PlanError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Recept {plan['recipe_id']} för {company.name}: {len(plan['spec']['scenes'])} scener, "
                          f"{plan['duration_s']} s. Jobb {job.pk}.")
        for choice in plan["choices"]:
            self.stdout.write(f"  {choice['scene']}: {choice['kind']} {choice['asset_id']} – {choice['why']}")
        for missing in plan["missing"]:
            self.stdout.write(f"  saknas {missing['scene']}: {missing['hint']}")
        for note in plan["notes"]:
            self.stdout.write(f"  not: {note}")
        report = {"plan": {k: plan[k] for k in ("recipe_id", "duration_s", "choices", "missing", "notes", "warnings")}}
        deadline = time.monotonic() + max(0, options["wait"])
        while options["wait"] and time.monotonic() < deadline:
            job = EditJob.objects.select_related("company", "review").get(pk=job.pk)
            if job.status in {"done", "failed"}:
                break
            time.sleep(15)
        job = EditJob.objects.select_related("company", "review", "output_asset").get(pk=job.pk)
        data = serialize(job)
        report["job"] = data
        self.stdout.write(f"Status: {data['status']} – {data['next_step']}")
        critique = data.get("ai_critique") or {}
        if critique.get("status") == "done":
            self.stdout.write(f"AI-granskning {critique['score']}/10 ({critique.get('input')}): {critique['summary']}")
            for fix in critique.get("fixes") or []:
                self.stdout.write(f"  rätta {fix['scene_id']}: {fix['fix']}")
        if options["out"]:
            out = Path(options["out"])
            out.mkdir(parents=True, exist_ok=True)
            if job.output_asset:
                with open_asset(job.output_asset) as file:
                    (out / "master.mp4").write_bytes(file.read())
            (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str),
                                             encoding="utf-8")
        if job.status == "failed":
            raise CommandError(f"Renderingen misslyckades: {job.error}")
