from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Company, ScrapeRequest
from .sync import state_for, analysis
from .scraper_efficiency import record_yield, discovery_due, discovery_limit


class EfficiencyTests(TestCase):
    def setUp(self):
        self.company=Company.objects.create(name="Measured",owner=get_user_model().objects.create_user(username="measured"))
        self.state=state_for(self.company,"meta_ads","123:SE")

    def record(self, key, before, after, mode="discovery", complete=True):
        r=ScrapeRequest.objects.create(state=self.state,key=key,actor="actor",mode=mode,max_cost_usd=.15,cost_usd=Decimal('.04'),status="succeeded",finished_at=timezone.now())
        record_yield(r,returned=20,before=before,after=after,complete=complete,capabilities={"date":True})
        r.refresh_from_db()
        self.state.refresh_from_db()
        return r

    def test_exact_yield_and_cost_replay_and_ai_attribution(self):
        old={str(i):"old" for i in range(17)}
        new={str(i):("changed" if i<2 else "old") for i in range(20)}
        r=self.record("one",old,new)
        self.assertEqual({k:r.result["yield"][k] for k in ("returned","new","changed","known")},{"returned":20,"new":3,"changed":2,"known":15})
        self.assertEqual(Decimal(r.result["yield"]["cost_per_useful_usd"]),Decimal('.008'))
        original=r.result["yield"].copy()
        record_yield(r,returned=20,before=new,after=new,complete=True,capabilities={})
        r.refresh_from_db()
        self.assertEqual(r.result["yield"],original)
        work=Mock(return_value={"hook":"question"})
        analysis(self.company,"creative","model",work,scrape_request_id=r.pk)
        analysis(self.company,"creative","model",work,scrape_request_id=r.pk)
        self.assertEqual(work.call_count,1)
        self.assertEqual(r.analysis_memos.count(),1)

    def test_quiet_accounts_back_off_busy_accounts_recover_and_refresh_is_separate(self):
        for i in range(3):
            self.record(str(i),{"1":"same"},{"1":"same"})
        self.assertEqual(self.state.details["discovery_interval_days"],7)
        self.assertFalse(discovery_due(self.state))
        self.assertEqual(discovery_limit(self.state),5)
        due=self.state.details["discovery_due_at"]
        self.record("refresh",{}, {str(i):"new" for i in range(20)},mode="refresh")
        self.assertEqual(self.state.details["discovery_due_at"],due)
        self.record("failed",{}, {},complete=False)
        self.assertEqual(self.state.details["discovery_due_at"],due)
        for i in range(2):
            self.record(f"busy{i}",{}, {str(j):"new" for j in range(10)})
        self.assertEqual(self.state.details["discovery_interval_days"],1)
        self.assertEqual(discovery_limit(self.state),20)

    def test_repair_adds_newly_usable_objects_without_recounting_prior_objects(self):
        r=self.record("repair",{}, {"a":"one"},complete=False)
        record_yield(r,returned=20,before={"a":"one"},after={"a":"one","b":"two"},complete=True,capabilities={})
        r.refresh_from_db()
        self.assertEqual(r.result["yield"]["new"],2)
        self.assertEqual(r.result["yield"]["known"],0)
        self.assertEqual(Decimal(r.result["yield"]["cost_per_useful_usd"]),Decimal('.02'))
