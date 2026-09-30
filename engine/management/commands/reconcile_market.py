"""Attach a known Virlo agent to an uncertain local reservation; never start a run."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from engine import virlo
from engine.models import Company, ScrapeRequest


class Command(BaseCommand):
    help = "Reconcile an unknown Virlo start using an operator-verified agent id. Read-only provider call."

    def add_arguments(self, parser):
        parser.add_argument("--company", required=True)
        parser.add_argument("--request", required=True, type=int)
        parser.add_argument("--agent", required=True)
        parser.add_argument("--reported-cost-usd", help="Optional actual amount verified in Virlo billing; never an estimate.")

    def handle(self, **options):
        try:
            request = ScrapeRequest.objects.get(pk=options["request"], state__company_id=options["company"], state__source="virlo")
            remote, _ = virlo.api("GET", virlo.agent_path(options["agent"]))
            cost = Decimal(options["reported_cost_usd"]) if options["reported_cost_usd"] is not None else None
            if cost is not None and (not cost.is_finite() or cost < 0):
                raise ValueError
        except Exception:
            raise CommandError("Kunde inte verifiera fÃ¶retag, reservation, agent eller kostnad.") from None
        # Prevent accidental linking to another company's agent or a recurring monitor.
        if (remote.get("id") != options["agent"] or remote.get("is_recurring") is not False
                or remote.get("platforms") != ["instagram"] or remote.get("meta_ads_enabled") is not True
                or remote.get("intent") != request.inputs.get("intent")
                or remote.get("keywords") != request.inputs.get("keywords")):
            raise CommandError("Agentens konfiguration matchar inte den reserverade fÃ¶retagsresearchen.")
        with transaction.atomic():
            Company.objects.select_for_update().get(pk=request.state.company_id)
            request = ScrapeRequest.objects.select_for_update().get(pk=request.pk)
            if request.status not in {"starting", "unknown"} or request.actor_run_id:
                raise CommandError("Reservationen behÃ¶ver ingen manuell koppling.")
            request.actor_run_id, request.status = "virlo:" + options["agent"], "running"
            request.cost_usd = cost
            request.result = {"provider": "virlo", "remote_id": options["agent"], "reconciled": True}
            request.save()
        self.stdout.write("Agenten Ã¤r kopplad. NÃ¤sta run_daily hÃ¤mtar samma kÃ¶rning utan ny betald start.")
