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

    @patch.dict("os.environ", {"DAILY_PARALLEL": "4"})
    def test_a_parallel_stage_runs_units_side_by_side_and_the_ledger_records_each(self):
        import threading
        import time as real_time

        running, peak, lock = [0], [0], threading.Lock()

        def unit():
            with lock:
                running[0] += 1
                peak[0] = max(peak[0], running[0])
            real_time.sleep(0.2)
            with lock:
                running[0] -= 1
            return Result(data={"thread": threading.current_thread().name})

        stage = Stage("analysis", lambda c: [(f"u{i}", unit) for i in range(4)], parallel=True)
        run = run_daily(company_id=self.a.pk, stages=[stage], wait_seconds=0)
        self.assertEqual(peak[0], 4)
        self.assertEqual(run.steps.filter(stage="analysis", status="success").exclude(key="__discovery__").count(), 4)
        self.assertTrue(all(s.result["thread"].startswith("daily-analysis")
                            for s in run.steps.filter(stage="analysis").exclude(key="__discovery__")))

    @patch.dict("os.environ", {"DAILY_PARALLEL": "4"})
    def test_the_batch_unit_runs_first_and_alone(self):
        order = []
        batch = Mock(side_effect=lambda: order.append("batch") or Result())
        account = Mock(side_effect=lambda: order.append("account") or Result())
        stage = Stage("ads_import", lambda c: [("batch", batch), ("p1", account), ("p2", account)], parallel=True)
        run_daily(company_id=self.a.pk, stages=[stage], wait_seconds=0)
        self.assertEqual(order, ["batch", "account", "account"])

    @patch.dict("os.environ", {"DAILY_PARALLEL": "2"})
    def test_units_still_waiting_when_the_budget_runs_out_stay_pending_and_unattempted(self):
        clock = [0]

        def spend_the_budget():
            clock[0] = 1000  # the two first units use up the 120 s; the two waiting ones must not start
            return Result()

        later = Mock(return_value=Result())
        stage = Stage("analysis", lambda c: [("a", spend_the_budget), ("b", spend_the_budget), ("c", later), ("d", later)],
                      parallel=True)
        with patch("engine.daily.time.monotonic", side_effect=lambda: clock[0]), patch("engine.daily.time.sleep"):
            run_daily(company_id=self.a.pk, stages=[stage], wait_seconds=120)
        later.assert_not_called()
        waiting = DailyStep.objects.filter(stage="analysis", key__in=["c", "d"])
        self.assertEqual({(s.status, s.attempts) for s in waiting}, {("pending", 0)})

    def test_without_daily_parallel_a_parallel_stage_runs_one_at_a_time(self):
        import threading

        names = []
        stage = Stage("analysis", lambda c: [(f"u{i}", lambda: names.append(threading.current_thread().name) or Result())
                                             for i in range(3)], parallel=True)
        run_daily(company_id=self.a.pk, stages=[stage], wait_seconds=0)
        self.assertEqual(set(names), {threading.main_thread().name})

    def test_an_always_stage_still_runs_once_after_slow_stages_spent_the_budget(self):
        clock = iter(range(0, 10_000, 100))  # every reading is 100 s later: the 120 s budget is gone at once
        slow, late, ideas = Mock(return_value=Result()), Mock(return_value=Result()), Mock(return_value=Result())
        stages = [Stage("slow", lambda c: [("a", slow)]), Stage("late", lambda c: [("b", late)]),
                  Stage("ideas", lambda c: [("ideas", ideas)], always=True)]
        with patch("engine.daily.time.monotonic", side_effect=lambda: next(clock)), patch("engine.daily.time.sleep"):
            run_daily(company_id=self.a.pk, stages=stages, wait_seconds=120)
        late.assert_not_called()  # ordinary work still respects the budget
        ideas.assert_called_once()
        self.assertEqual(DailyStep.objects.get(stage="ideas", key="ideas").status, "success")

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
