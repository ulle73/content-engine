from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from .models import Company, ContentRun, OwnPost, OwnSnapshot, OwnOutcome
from .own_performance import discover,collect,create_outcomes,normalize_metrics,update_baselines
from .learning import record_predictions,record_outcome,dataset
from .learning_targets import AUTO_ORGANIC,available_paid,actual


class OwnPerformanceTests(TestCase):
    def setUp(self):
        self.now=timezone.now()
        self.user=get_user_model().objects.create_user(username="own")
        self.company=Company.objects.create(owner=self.user,name="Own",postiz_channels=[{"id":"ig","identifier":"instagram"},{"id":"fb","identifier":"facebook"}])
        self.company.postiz_key="test-key"
        self.company.save()
        self.run=ContentRun.objects.create(workspace=self.company,context={},ideas=[{"title":"Own"}],selected=0,channel="organic",delivery_status="sent",delivery_result=[{"postId":"published","integration":"ig"}])
        record_predictions(self.run)
        self.run.predictions.update(created_at=self.now-timedelta(days=10))
        self.row={"id":"published","releaseId":"native","releaseURL":"https://instagram.com/p/example/","state":"PUBLISHED","content":"Own text", "publishDate":(self.now-timedelta(days=7,hours=2)).isoformat(),"settings":{"post_type":"reel"},"integration":{"id":"ig","providerIdentifier":"instagram"}}

    def raw(self,likes="9"):
        return [{"label":name,"percentageChange":999,"data":[{"total":value,"date":self.now.date().isoformat()}]} for name,value in (("Views","1000"),("Reach","500"),("Likes",likes),("Comments","1"),("Saves","0"))]

    @patch("engine.postiz.request")
    def test_published_post_to_snapshot_to_outcome_and_no_duplicate_refresh(self,request):
        request.return_value={"posts":[self.row,{**self.row,"id":"draft","state":"DRAFT"},{**self.row,"id":"foreign","integration":{"id":"other","providerIdentifier":"instagram"}}]}
        self.assertEqual(discover(self.company)["new"],1)
        self.assertEqual(discover(self.company)["status"],"skipped")
        self.assertEqual(request.call_count,1)
        post=OwnPost.objects.get()
        self.assertEqual(post.run_id,self.run.pk)
        self.assertEqual(post.format,"reel")
        request.return_value=self.raw()
        self.assertEqual(collect(post)["status"],"success")
        self.assertEqual(collect(post)["status"],"skipped")
        self.assertEqual(request.call_count,2)
        snapshot=OwnSnapshot.objects.get()
        self.assertEqual(snapshot.metrics["views"],1000)
        self.assertNotIn("impressions",snapshot.metrics)
        self.assertEqual(snapshot.metrics["saves"],0)
        self.assertEqual(create_outcomes(self.company)["saved"],1)
        self.assertEqual(create_outcomes(self.company)["saved"],0)
        outcome=OwnOutcome.objects.get()
        self.assertEqual(outcome.target,AUTO_ORGANIC["instagram"])
        self.assertEqual(outcome.label,10.)
        self.assertEqual(outcome.snapshot_id,snapshot.pk)
        self.assertEqual(len(dataset(self.company,"organic",target=outcome.target)),1)
        self.assertEqual(len(dataset(self.company,"paid",target=outcome.target)),0)

    @patch("engine.postiz.request")
    def test_daily_keeps_successful_own_snapshot_when_other_post_fails(self,request):
        from .daily import Stage,run_daily
        from .daily_stages import own_discovery_units,own_snapshot_units,own_learning_units,learning_units
        from .postiz import PostizError
        def provider(key,method,path,**kwargs):
            if path=="/posts":
                return {"posts":[self.row,{**self.row,"id":"bad","releaseId":"bad","publishDate":(self.now-timedelta(days=8)).isoformat()}]}
            if path.endswith("bad"):
                raise PostizError("temporary")
            return self.raw()
        request.side_effect=provider
        daily=run_daily(company_id=self.company.pk,wait_seconds=0,stages=[Stage("own_discovery",own_discovery_units),Stage("own_snapshots",own_snapshot_units),Stage("own_outcomes",own_learning_units),Stage("learning",learning_units)])
        self.assertEqual(daily.status,"partial")
        self.assertEqual(OwnSnapshot.objects.count(),1)
        self.assertEqual(OwnOutcome.objects.count(),1)
        self.assertEqual(daily.steps.filter(stage="own_snapshots",status="attention").count(),1)
        self.assertFalse(daily.steps.filter(status="failed").exists())

    @patch("engine.postiz.request")
    def test_old_manual_posts_build_history_without_fabricated_prepublication_features(self,request):
        request.return_value={"posts":[{**self.row,"id":"manual","publishDate":(self.now-timedelta(days=30)).isoformat(),"settings":{"post_type":"post"}}]}
        discover(self.company)
        post=OwnPost.objects.get()
        self.assertIsNone(post.run_id)
        self.assertEqual(post.format,"unknown")
        request.return_value=self.raw()
        collect(post)
        self.assertEqual(create_outcomes(self.company)["saved"],0)
        self.assertEqual(OwnOutcome.objects.count(),0)
        post.refresh_from_db()
        self.assertIsNotNone(post.finalized_at)

    def test_missing_metrics_stay_missing_and_ambiguous_series_are_rejected(self):
        metrics,_=normalize_metrics(self.raw(),"instagram",self.now)
        self.assertNotIn("shares",metrics)
        self.assertNotIn("percentageChange",metrics)
        for raw in ([],[{"label":"Views","data":[{"date":self.now.date().isoformat(),"total":"nan"}]}],
                    [{"label":"Views","data":[{"date":self.now.date().isoformat(),"total":"1"}]*2}]):
            with self.assertRaises(ValueError):
                normalize_metrics(raw,"instagram",self.now)
        metrics,_=normalize_metrics([{"label":"Impressions","data":[{"total":"20","date":self.now.date().isoformat()}]}],"facebook",self.now)
        self.assertEqual(metrics,{"reach":20})

    @patch("engine.postiz.request")
    def test_final_checkpoint_does_not_reuse_an_earlier_same_day_snapshot(self,request):
        post=OwnPost.objects.create(company=self.company,postiz_id="final",integration_id="ig",release_id="final",platform="instagram",published_at=self.now-timedelta(days=7,hours=1),run=self.run,url="https://instagram.com/p/final/")
        earlier=OwnSnapshot.objects.create(post=post,source_day=self.now.date(),observed_at=self.now-timedelta(hours=2),metrics={"views":500,"likes":1,"comments":0},raw=[])
        request.return_value=self.raw()
        collect(post)
        self.assertEqual(post.snapshots.count(),2)
        self.assertEqual(create_outcomes(self.company)["saved"],1)
        self.assertEqual(OwnOutcome.objects.get().snapshot.checkpoint,"final")
        earlier.refresh_from_db()
        self.assertEqual(earlier.metrics["views"],500)

    def test_baseline_is_age_platform_format_matched_and_excludes_future(self):
        for i in range(6):
            post=OwnPost.objects.create(company=self.company,postiz_id=str(i),integration_id="ig",release_id=str(i),platform="instagram",format="reel",published_at=self.now-timedelta(days=7,hours=3))
            OwnSnapshot.objects.create(post=post,source_day=self.now.date(),observed_at=self.now-timedelta(minutes=6-i),metrics={"likes":9,"comments":1},raw=[])
        target=OwnSnapshot.objects.latest("pk")
        target.metrics={"likes":17,"comments":1}
        target.save()
        # Future huge value must not enter the existing point-in-time comparison.
        post=OwnPost.objects.create(company=self.company,postiz_id="future",integration_id="ig",release_id="future",platform="instagram",format="reel",published_at=self.now-timedelta(days=7))
        OwnSnapshot.objects.create(post=post,source_day=self.now.date(),observed_at=self.now+timedelta(hours=1),metrics={"likes":9999,"comments":1},raw=[])
        update_baselines(self.company)
        target.refresh_from_db()
        self.assertEqual(target.baseline["relative"],1.8)
        self.assertEqual(target.baseline["peers"],5)
        self.assertEqual(target.baseline["confidence_label"],"low")

    @patch("engine.postiz.request")
    def test_failed_first_discovery_does_not_repeat_full_backfill(self,request):
        from .postiz import PostizError
        from .models import ScraperState
        request.side_effect=PostizError("temporary")
        with self.assertRaises(PostizError):discover(self.company)
        ScraperState.objects.update(next_attempt_at=self.now-timedelta(days=1))
        request.side_effect=None
        request.return_value={"posts":[]}
        discover(self.company)
        since=request.call_args.kwargs["params"]["startDate"]
        self.assertGreater(since,(self.now-timedelta(days=5)).isoformat())

    def test_paid_business_targets_use_actuals_and_keep_currency_contracts_separate(self):
        metrics={"impressions":1000,"clicks":50,"conversions":5,"spend":100.,"revenue":400.,"currency":"SEK"}
        targets=available_paid(metrics)
        self.assertIn("roas_7d",targets)
        self.assertIn("cpa_SEK_7d",targets)
        self.assertEqual(actual("roas_7d",metrics),4.)
        self.assertEqual(actual("cpa_SEK_7d",metrics),20.)
        self.assertEqual(actual("conversions_per_100_clicks_7d",metrics),10.)
        with self.assertRaises(ValueError):actual("cpa_USD_7d",metrics)
        self.assertNotIn("roas_7d",available_paid({"impressions":100,"clicks":3}))
        self.assertNotIn("cpa_SEK_7d",available_paid({**metrics,"conversions":0}))

    def test_a_deliberately_activated_cpa_model_prefers_lower_cost(self):
        from .models import LearningModel
        from .learning import NUMERIC
        LearningModel.objects.create(company=self.company,channel="paid",version="cpa-test",target="cpa_SEK_7d",mode="production",training_cutoff=self.now,
            artifact={"intercept":10.,"coefficients":[5.]+[0.]*(len(NUMERIC)-1),"mean":[0.]*len(NUMERIC),"scale":[1.]*len(NUMERIC)},evaluation={})
        run=ContentRun.objects.create(workspace=self.company,channel="paid",context={},ideas=[{"title":"Higher CPA","profile_relevance":3},{"title":"Lower CPA","profile_relevance":0}])
        record_predictions(run)
        self.assertEqual(run.ideas[0]["title"],"Lower CPA")
        self.assertTrue(all(p.target=="cpa_SEK_7d" for p in run.predictions.all()))
