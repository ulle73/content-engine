"""Lab: break reference videos down locally, compare models side by side, and plan our version – no database writes.

    python manage.py reference_lab --company Faiv --top 3 --models google/gemini-3.1-flash-lite,google/gemini-3.8-flash
    python manage.py reference_lab --company Golfkuponger --url https://www.instagram.com/reel/... --adapt

Writes work/references/<slug>/: video.mp4, proxy.mp4, sheet.jpg, measurements.json, breakdown-<model>.json,
our-version-<model>.json and report.md, plus work/references/comparison.md with cost per model. Paid calls go to
OpenRouter; the cost of each call is printed and saved.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from engine.models import Company
from engine.openrouter import OpenRouterError
from engine.references import adapt, breakdown, fetch, measure, service

OUT = Path(__file__).resolve().parents[3] / "work" / "references"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:60] or "ref"


class Command(BaseCommand):
    help = "Break reference videos down (ffmpeg measurements + vision model) and plan our version. No DB writes."

    def add_arguments(self, parser):
        parser.add_argument("--company", default="Faiv", help="Company name (for --top and --adapt).")
        parser.add_argument("--url", action="append", default=[], help="Video URL (repeatable).")
        parser.add_argument("--ad", action="append", default=[], help="Meta Ad Library ad id (repeatable).")
        parser.add_argument("--top", type=int, default=0, help="Take the N best monitored ads with video.")
        parser.add_argument("--models", default="", help="Comma-separated OpenRouter model ids (default: video tier).")
        parser.add_argument("--adapt", action="store_true", help="Also plan our version (with the first model).")
        parser.add_argument("--angle", default="", help="Wanted angle for our version.")
        parser.add_argument("--sleep", type=float, default=25.0, help="Seconds between Facebook fetches (429 guard).")
        parser.add_argument("--out", default=str(OUT))

    def handle(self, **options):
        company = Company.objects.filter(name__iexact=options["company"]).first()
        if not company:
            raise CommandError(f"Hittar inget företag som heter {options['company']}.")
        models = [m.strip() for m in options["models"].split(",") if m.strip()] or [breakdown.default_model()]
        out = Path(options["out"])
        out.mkdir(parents=True, exist_ok=True)
        jobs = [(u, {}) for u in options["url"]] + [(fetch.ad_library_url(a), {}) for a in options["ad"]]
        pool = service.candidates(company, limit=60, known={}) if options["top"] else []
        rows, tried = [], 0
        for entry in [(u, {}) for u, _ in jobs] + [(c["url"], c) for c in pool]:
            if options["top"] and len(rows) >= options["top"] + len(jobs):
                break
            url, cand = entry
            if tried and "facebook.com" in url:
                time.sleep(options["sleep"])
            tried += 1
            label = f"{cand.get('advertiser', '')} {cand.get('ad_id', '')}".strip() or url
            self.stdout.write(f"\n== {label}")
            try:
                got = fetch.fetch(url)
            except fetch.FetchError as exc:
                self.stdout.write(f"   hoppar över: {exc}")
                if "429" in str(exc):
                    self.stdout.write("   Facebook begränsar – väntar 120 s")
                    time.sleep(120)
                continue
            rows.append(self._one(company, got, cand, models, out, options))
        self._comparison(out, rows, models)

    def _one(self, company, got, cand, models, out, options) -> dict:
        title = cand.get("headline") or got.title or ""
        author = cand.get("advertiser") or got.author or ""
        folder = out / _slug(f"{author}-{cand.get('ad_id') or title or got.source_url}")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "video.mp4").write_bytes(got.data)
        started = time.monotonic()
        result = measure.measure(got.data, title=f"{author} – {title}".strip(" –")[:110])
        proxy, sheet = result.pop("proxy"), result.pop("sheet")
        (folder / "proxy.mp4").write_bytes(proxy)
        (folder / "sheet.jpg").write_bytes(sheet)
        (folder / "measurements.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        s = result["summary"]
        self.stdout.write(f"   {s['duration_s']} s, {s['scene_count']} scener, snitt {s['avg_shot_s']} s/bild, "
                          f"tempo {result['audio'].get('tempo_bpm')} BPM  ({time.monotonic() - started:.0f} s)")
        context = {"url": got.source_url, "ad_text": cand.get("text"), "days_running": cand.get("days_running")}
        row = {"folder": folder.name, "author": author, "title": title, "url": got.source_url,
               "days_running": cand.get("days_running"), "eu_reach": cand.get("eu_reach"), "summary": s, "runs": {}}
        for model in models:
            started = time.monotonic()
            try:
                data, meta = breakdown.run(proxy, result, model=model, title=title, author=author, context=context)
            except OpenRouterError as exc:
                self.stdout.write(f"   {model}: FEL {exc}")
                row["runs"][model] = {"error": str(exc)}
                continue
            usage = meta.get("usage") or {}
            run = {"cost_usd": meta.get("cost_usd"), "seconds": round(time.monotonic() - started, 1),
                   "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                   "scenes": len(data["scenes"]), "quality_score": data["quality_score"]}
            row["runs"][model] = run
            (folder / f"breakdown-{_slug(model)}.json").write_text(
                json.dumps({"meta": meta, "breakdown": data}, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(f"   {model}: {run['cost_usd']} USD, {run['prompt_tokens']}+{run['completion_tokens']} "
                              f"tokens, {run['seconds']} s – {data['summary']}")
            if options["adapt"] and "adaptation" not in row:
                reference = {"title": title, "author": author, "url": got.source_url, "measurements": s,
                             "breakdown": data}
                try:
                    plan = adapt.run(company, reference, sheet=sheet, angle=options["angle"], model=model)
                except OpenRouterError as exc:
                    self.stdout.write(f"   vår version: FEL {exc}")
                    continue
                row["adaptation"] = {"model": plan["model"], "cost_usd": plan["cost_usd"]}
                (folder / f"our-version-{_slug(model)}.json").write_text(
                    json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
                self.stdout.write(f"   vår version: {plan['plan']['title']} ({plan['cost_usd']} USD, "
                                  f"{len(plan['warnings'])} varningar)")
        return row

    def _comparison(self, out: Path, rows: list[dict], models: list[str]) -> None:
        lines = ["# Referenser – jämförelse av modeller", "",
                 "| Referens | Dagar | Längd | Scener | " + " | ".join(models) + " |",
                 "|---|---|---|---|" + "---|" * len(models)]
        totals = dict.fromkeys(models, 0.0)
        for row in rows:
            cells = []
            for model in models:
                run = row["runs"].get(model) or {}
                if run.get("cost_usd") is not None:
                    totals[model] += float(run["cost_usd"])
                cells.append("fel" if run.get("error") else f"{run.get('cost_usd')} USD · {run.get('seconds')} s · "
                             f"betyg {run.get('quality_score')}")
            lines.append(f"| [{row['author']} – {row['title'][:40]}]({row['folder']}/sheet.jpg) | "
                         f"{row.get('days_running') or ''} | {row['summary']['duration_s']} s | "
                         f"{row['summary']['scene_count']} | " + " | ".join(cells) + " |")
        lines += ["", "Totalt: " + ", ".join(f"{m} {round(v, 4)} USD" for m, v in totals.items())]
        (out / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.stdout.write("\n" + "\n".join(lines))
