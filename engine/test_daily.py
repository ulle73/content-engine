import io
import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from .daily import AlreadyRunning, Result, Stage, acquire, run_daily
from .daily_stages import collect_media, competitor_units, import_account
from .models import Company, Competitor, CompetitorImport, ContentRun, DailyRun, DailyStep, MediaGeneration


class DailyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="daily-owner")
        self.a = Company.objects.create(owner=self.owner, name="A")
        self.b = Company.objects.create(owner=self.owner, name="B")

    def test_failure_isolated_by_item_and_company_success_not_repeated(self):
        fail = Mock(side_effect=RuntimeError("SECRET-this-must-not-be-stored"))
        succeed = Mock(return_value=Result(data={"observation":"saved"}))
        other = Mock(return_value=Result())
        stage = Stage("observations", lambda c: [("bad", fail), ("good", succeed)] if c.pk == self.a.pk else [("other", other)])
        run = run_daily(stages=[stage], wait_seconds=0)
        self.assertEqual(run.status, "partial")
        self.assertEqual(run.steps.filter(status="success").count(), 2)
        self.assertNotIn("SECRET", str(list(run.steps.values())))
        fail.side_effect = None
        fail.return_value = Result()
        again = run_daily(stages=[stage], wait_seconds=0)
        self.assertEqual(again.pk, run.pk)
        self.assertEqual(again.status, "success")
        self.assertEqual(succeed.call_count, 1)
        self.assertEqual(other.call_count, 1)
        self.assertEqual(fail.call_count, 2)
        self.assertEqual(again.attempts, 2)

    def test_discovery_failure_does_not_prevent_other_stage_or_company(self):
        def factory(company):
            if company.pk == self.a.pk:
                raise ValueError("private response")
            return [("ok", lambda: Result())]
        run = run_daily(stages=[Stage("broken", factory), Stage("cleanup", lambda c: [("ok", lambda: Result())])], wait_seconds=0)
        self.assertEqual(run.status, "partial")
        self.assertEqual(run.steps.filter(status="success").count(), 3)

    def test_invalid_item_result_does_not_prevent_other_work(self):
        run = run_daily(company_id=self.a.pk, stages=[Stage("results", lambda c: [
            ("broken", lambda: None), ("good", lambda: Result())])], wait_seconds=0)
        self.assertEqual(run.status, "partial")
        self.assertEqual(run.steps.get(key="broken").status, "failed")
        self.assertEqual(run.steps.get(key="good").status, "success")

    def test_pending_resume_and_stale_claim_preserve_completed_work(self):
        fn = Mock(side_effect=[Result("pending"), Result()])
        run = run_daily(company_id=self.a.pk, stages=[Stage("collect", lambda c: [("remote-id", fn)])], wait_seconds=0)
        self.assertEqual(run.status, "partial")
        run.status, run.lease_until, run.lease_token = "running", timezone.now()-timedelta(seconds=1), uuid.uuid4()
        run.save()
        step = run.steps.get(key="remote-id")
        step.status = "running"
        step.save()
        again = run_daily(company_id=self.a.pk, stages=[Stage("collect", lambda c: [("remote-id", fn)])], wait_seconds=0)
        self.assertEqual(again.status, "success")
        self.assertEqual(fn.call_count, 2)

    def test_live_lease_blocks_concurrent_start(self):
        acquire(timezone.localdate())
        with self.assertRaises(AlreadyRunning):
            acquire(timezone.localdate())
        self.assertEqual(DailyRun.objects.count(), 1)

    @patch("engine.daily_stages.import_account", return_value=Result())
    def test_early_manual_check_does_not_suppress_refresh_due_later_same_day(self, refresh):
        account = Competitor.objects.create(company=self.a, name="Reference", username="reference", last_success_at=timezone.now())
        stages = [Stage("competitor_import", competitor_units)]
        run_daily(company_id=self.a.pk, stages=stages, wait_seconds=0)
        refresh.assert_not_called()
        account.last_success_at -= timedelta(hours=24)
        account.save()
        run_daily(company_id=self.a.pk, stages=stages, wait_seconds=0)
        self.assertEqual(refresh.call_count, 1)
        run_daily(company_id=self.a.pk, stages=stages, wait_seconds=0)
        self.assertEqual(refresh.call_count, 1)

    def test_pending_resource_completed_elsewhere_does_not_stay_pending_forever(self):
        stage = Stage("media", lambda c: [("job", lambda: Result("pending"))])
        run_daily(company_id=self.a.pk, stages=[stage], wait_seconds=0)
        run = run_daily(company_id=self.a.pk, stages=[Stage("media", lambda c: [])], wait_seconds=0)
        self.assertEqual(run.status, "success")
        self.assertEqual(run.steps.get(key="job").status, "skipped")

    def test_future_training_requires_complete_outcomes_without_scheduler_change(self):
        outcomes = Mock(return_value=Result("failed", "Missing observations"))
        train = Mock(return_value=Result(data={"mode":"shadow", "artifact":"model-v1"}))
        stages = [Stage("outcomes", lambda c: [("window", outcomes)]),
                  Stage("training", lambda c: [("window-model-v1", train)], requires=("outcomes",))]
        run_daily(company_id=self.a.pk, stages=stages, wait_seconds=0)
        train.assert_not_called()
        outcomes.return_value = Result()
        run = run_daily(company_id=self.a.pk, stages=stages, wait_seconds=0)
        self.assertEqual(run.status, "success")
        self.assertEqual(train.call_count, 1)

    @patch("engine.daily_stages.advance_job")
    def test_daily_never_starts_queued_paid_generation(self, advance):
        run = ContentRun.objects.create(workspace=self.a, context={})
        job = MediaGeneration.objects.create(run=run, kind="image", provider="openai")
        result = collect_media(job)
        self.assertEqual(result.status, "attention")
        advance.assert_not_called()

    @patch("engine.daily_stages.start_import")
    @patch("engine.daily_stages.collect_import")
    def test_import_resumes_same_provider_id_without_new_start(self, collect, start):
        account = Competitor.objects.create(company=self.a, name="Ref", username="ref")
        existing = CompetitorImport.objects.create(competitor=account, actor_run_id="real-id", status="running")
        collect.return_value = existing
        self.assertEqual(import_account(account).status, "pending")
        start.assert_not_called()
        self.assertEqual(collect.call_args.args[0].actor_run_id, "real-id")
        existing.actor_run_id = None
        existing.status = "unknown"
        existing.save()
        self.assertEqual(import_account(account).status, "attention")
        start.assert_not_called()

    @patch("engine.management.commands.run_daily.run_daily")
    def test_partial_command_warns_but_total_failure_exits_nonzero(self, daily):
        run = DailyRun.objects.create(day=timezone.localdate(), status="partial", summary={"needs_attention":1})
        daily.return_value = run
        output = io.StringIO()
        call_command("run_daily", stdout=output)
        self.assertIn("::warning", output.getvalue())
        run.status = "failed"
        with self.assertRaises(CommandError):
            call_command("run_daily", stdout=io.StringIO())
