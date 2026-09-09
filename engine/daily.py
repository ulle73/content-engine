"""One resumable daily ledger. Each work item commits independently of the others."""

import time
import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

from .models import Company, DailyRun, DailyStep

DONE = ("success", "skipped")
LEASE = timedelta(minutes=20)  # Longer than any bounded external call, not an open DB transaction.


class AlreadyRunning(Exception):
    pass


class LeaseLost(Exception):
    pass


@dataclass
class Result:
    status: str = "success"
    message: str = "Klart."
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Stage:
    name: str
    factory: object  # company -> iterable of (stable key, zero-argument callable returning Result)
    version: str = "v1"
    requires: tuple = ()  # Future outcomes/training can require successful upstream stages.


def acquire(day):
    now, token = timezone.now(), uuid.uuid4()
    with transaction.atomic():
        if connection.vendor == "postgresql":
            # Short transaction-scoped lock: safe with Neon's transaction pooler.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(730091)")
        if DailyRun.objects.filter(lease_until__gt=now).exists():
            raise AlreadyRunning("En daglig körning arbetar redan. Ingen ny körning startades.")
        DailyRun.objects.filter(status="running").update(status="partial", finished_at=now)
        run, _ = DailyRun.objects.get_or_create(day=day)
        run.lease_token, run.lease_until = token, now + LEASE
        run.status, run.finished_at = "running", None
        run.attempts += 1
        run.save()
    return run, token


def heartbeat(run, token):
    if not DailyRun.objects.filter(pk=run.pk, lease_token=token, lease_until__gt=timezone.now()).update(lease_until=timezone.now()+LEASE):
        raise LeaseLost("Körningens lås har löpt ut. Stoppar innan mer arbete startas.")


def safe_error(exc):
    # Never persist third-party response bodies, URLs, database credentials or arbitrary exception text.
    status = getattr(exc, "status_code", None)
    suffix = f", HTTP {status}" if isinstance(status, int) else ""
    return f"{type(exc).__name__}{suffix}. Momentet behöver nytt försök eller kontroll av leverantörens status."


def summarize(run):
    counts = Counter(run.steps.values_list("status", flat=True))
    outstanding = sum(counts[s] for s in ("failed", "attention", "pending", "running", "blocked"))
    if not outstanding:
        status = "success"
    elif counts["success"] or counts["pending"] or counts["blocked"] or counts["running"]:
        status = "partial"
    else:
        status = "failed"
    return status, {"counts": dict(counts), "needs_attention": outstanding}


def run_daily(*, company_id=None, wait_seconds=720, stages=None, write=lambda message: None):
    from .daily_stages import STAGES

    stages = STAGES if stages is None else stages
    registered = set()
    for stage in stages:
        if stage.name in registered or not set(stage.requires).issubset(registered):
            raise ValueError("Daily stages must be unique and follow their dependencies.")
        registered.add(stage.name)
    companies = list(Company.objects.filter(pk=company_id) if company_id else Company.objects.order_by("pk"))
    run, token = acquire(timezone.localdate())
    deadline = time.monotonic() + max(0, wait_seconds)
    tried = set()

    def step_for(company, stage, key):
        return DailyStep.objects.get_or_create(run=run, company=company, stage=stage.name, version=stage.version, key=str(key))[0]

    def save_result(step, result):
        heartbeat(run, token)
        step.status, step.message, step.result = result.status, result.message[:500], result.data
        step.finished_at = timezone.now()
        step.save()
        write(f"{step.company_id} / {step.stage} / {step.key}: {step.status} — {step.message}")

    try:
        first_pass = True
        while True:
            for stage in stages:
                for company in companies:
                    heartbeat(run, token)
                    run.steps.filter(company=company, stage=stage.name).exclude(version=stage.version).exclude(status__in=DONE).update(
                        status="skipped", message="Ersatt av en ny stegversion.", finished_at=timezone.now())
                    discovery = step_for(company, stage, "__discovery__")
                    dependencies = run.steps.filter(company=company, stage__in=stage.requires)
                    if stage.requires and (set(dependencies.values_list("stage", flat=True)) != set(stage.requires) or dependencies.exclude(status__in=DONE).exists()):
                        save_result(discovery, Result("blocked", "Inväntar lyckat underlag: " + ", ".join(stage.requires)))
                        continue
                    try:
                        units = list(stage.factory(company))
                        keys = [str(key) for key, _ in units]
                        if len(keys) != len(set(keys)) or any(not key or len(key) > 160 or key.startswith("__") for key in keys):
                            raise ValueError("Daily work keys must be unique, stable and at most 160 characters.")
                        # A resource may have finished/deactivated outside the scheduler (e.g. in the UI).
                        for obsolete in run.steps.filter(company=company, stage=stage.name, version=stage.version, status__in=("pending", "running")).exclude(key__in=keys+["__discovery__"]):
                            save_result(obsolete, Result("skipped", "Arbetet ingår inte längre i aktuellt urval.", {"previous_result": obsolete.result}))
                        if discovery.status not in DONE:
                            save_result(discovery, Result("skipped", "Arbetsmoment identifierade."))
                    except Exception as exc:
                        save_result(discovery, Result("failed", safe_error(exc)))
                        continue
                    for key, work in units:
                        step = step_for(company, stage, key)
                        if step.status in DONE or (step.pk in tried and step.status != "pending"):
                            continue
                        if not first_pass and time.monotonic() >= deadline:
                            continue
                        if wait_seconds > 0 and time.monotonic() >= deadline:
                            continue
                        heartbeat(run, token)
                        step.status, step.started_at, step.finished_at = "running", timezone.now(), None
                        step.attempts += 1
                        step.save()
                        tried.add(step.pk)
                        try:
                            result = work()
                            if not isinstance(result, Result) or result.status not in (*DONE, "failed", "attention", "pending", "blocked") or not isinstance(result.message, str) or not isinstance(result.data, dict):
                                raise ValueError("Invalid daily work result.")
                            json.dumps(result.data, allow_nan=False)
                        except Exception as exc:
                            result = Result("failed", safe_error(exc))
                        save_result(step, result)
            first_pass = False
            pending = run.steps.filter(company__in=companies, status="pending").exists()
            if not pending or time.monotonic() >= deadline:
                break
            time.sleep(min(15, max(0, deadline-time.monotonic())))
        status, summary = summarize(run)
        heartbeat(run, token)
        DailyRun.objects.filter(pk=run.pk, lease_token=token).update(status=status, summary=summary, finished_at=timezone.now())
    except Exception as exc:
        status, summary = summarize(run)
        summary["interrupted"] = safe_error(exc)
        DailyRun.objects.filter(pk=run.pk, lease_token=token).update(
            status="partial" if run.steps.filter(status="success").exists() else "failed", summary=summary, finished_at=timezone.now())
        raise
    finally:
        # A killed process leaves a visible running step and an expiring lease; the next run resumes it.
        DailyRun.objects.filter(pk=run.pk, lease_token=token).update(lease_token=None, lease_until=None)
    run.refresh_from_db()
    return run
