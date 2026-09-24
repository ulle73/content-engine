import io
import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from engine.media import create_job, preview_job, remove_asset, store_asset
from engine.media_providers import higgsfield_configured
from engine.models import Company, ContentRun


def _anchor_png(rgb):
    out = io.BytesIO()
    image = Image.new("RGB", (720, 1280), rgb)
    image.save(out, "PNG")
    return out.getvalue()


def _safe_estimate(usage):
    estimate = usage.get("estimate") if isinstance(usage, dict) else None
    if not isinstance(estimate, dict):
        return {}
    return {
        key: estimate[key]
        for key in ("usd", "credits", "currency")
        if key in estimate and isinstance(estimate[key], (str, int, float))
    }


class Command(BaseCommand):
    help = "Run one non-billable production Higgsfield start-to-end preflight and clean up temporary data."

    def add_arguments(self, parser):
        parser.add_argument("--token", required=True)

    def handle(self, *args, **options):
        token = str(options["token"]).strip()
        if not token.startswith("d2-") or len(token) > 120:
            raise CommandError("D2 preflight token is invalid.")
        if not higgsfield_configured():
            raise CommandError("HIGGSFIELD_API_KEY_GK is not configured; preflight stopped before provider access.")

        company = Company.objects.filter(name__iexact="Golfkuponger").select_related("owner").first()
        if not company:
            companies = list(Company.objects.select_related("owner").all()[:2])
            if len(companies) != 1:
                raise CommandError("Could not identify the Golfkuponger company safely.")
            company = companies[0]

        run = None
        assets = []
        try:
            run = ContentRun.objects.create(
                workspace=company,
                author=company.owner,
                context={
                    "profile": company.profile,
                    "current": company.current,
                    "source": company.source,
                    "ops_preflight": token,
                },
                ideas=[{"title": "D2 Higgsfield preflight", "photo_brief": ""}],
                selected=0,
                draft={"instagram": "D2 preflight", "facebook": "D2 preflight"},
                model="ops-d2-preflight",
            )

            start = store_asset(
                company,
                _anchor_png((24, 92, 58)),
                alt_text="Temporary D2 start anchor",
            )
            assets.append(start)
            end = store_asset(
                company,
                _anchor_png((48, 120, 82)),
                alt_text="Temporary D2 end anchor",
            )
            assets.append(end)

            job = create_job(
                run,
                token=uuid.uuid4(),
                kind="video",
                brief=(
                    "5 second non-billable continuity preflight. "
                    "Create the simplest smooth continuous camera transition from the start frame "
                    "to the end frame. No cuts, no new objects, no audio."
                ),
                count=1,
                shape="portrait",
                source=start,
                end_source=end,
                priority="economy",
                recipe_id="scroll_transition_bridge",
            )
            job = preview_job(job)

            if job.status != "queued":
                raise CommandError(f"Preflight job left queued state unexpectedly: {job.status}")
            if job.provider_id:
                raise CommandError("Preflight unexpectedly created a provider generation id.")
            estimate = _safe_estimate(job.usage or {})
            if not estimate:
                raise CommandError("Higgsfield returned no safe non-billable estimate metadata.")

            result = {
                "token": token,
                "status": job.status,
                "provider_id_present": bool(job.provider_id),
                "provider": job.provider,
                "model": job.parameters.get("model"),
                "provider_model": job.parameters.get("provider_model"),
                "recipe": (job.parameters.get("creative") or {}).get("recipe", {}).get("recipe_id"),
                "reference_roles": sorted(job.references.values_list("role", flat=True)),
                "estimate": estimate,
            }
            self.stdout.write("D2_PREFLIGHT_OK " + json.dumps(result, sort_keys=True))
        finally:
            if run is not None:
                ContentRun.objects.filter(pk=run.pk).delete()
            for asset in assets:
                try:
                    if asset.pk and asset.__class__.objects.filter(pk=asset.pk).exists():
                        remove_asset(asset)
                except Exception as exc:
                    self.stderr.write(f"D2_PREFLIGHT_CLEANUP_WARNING {asset.pk}: {exc}")
