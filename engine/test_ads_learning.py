from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import ads, apify
from .competitors import start_import
from .daily import run_daily
from .daily_stages import ads_units, ads_analysis_units, learning_units
from .daily import Stage
from .learning import FEATURE_VERSION, TARGETS, dataset, features, generation_learning_profile, predict, promote, record_outcome, record_predictions, train
from .models import (AdAccount, AdObservation, AnalysisMemo, Company, Competitor, CompetitorAd, ContentRun,
                     LearningModel, OwnOutcome, Prediction, ScrapeRequest)
from .sync import analysis, dispatch, organic_plan, state_for


class AdsSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ads-owner")
        self.company = Company.objects.create(owner=self.user, name="Golf", profile="Vi lär ut golf.", current="Boka en lektion.", source="Företagets ägare", valid_until=timezone.localdate()+timedelta(days=30))
        self.account = AdAccount.objects.create(company=self.company, name="Reference", page_url="https://www.facebook.com/12345", page_id="12345")
        self.now = timezone.now()
        self.row = {"adId":"98765", "advertiserPageId":"12345", "adText":"Try our golf training", "headline":"Golf lessons",
                    "isActive":True, "startDate":(self.now-timedelta(days=3)).date().isoformat(), "publisherPlatforms":["facebook", "instagram"]}
        self.client.force_login(self.user)

    def request(self, remote_id="remote1"):
        state = ads.account_state(self.account)
        return ScrapeRequest.objects.create(state=state, key=remote_id, actor=ads.ACTOR, mode="discovery", max_cost_usd=.15,
            inputs={"maxResults":20}, status="running", actor_run_id=remote_id, dataset_id="dataset")

    def remote(self):
        return {"status":"SUCCEEDED", "finishedAt":self.now.isoformat(), "usageTotalUsd":.002}

    def test_metadata_never_invents_performance_or_media(self):
        item = ads.normalize(self.row, self.account)
        self.assertIsNone(item["creative"]["landing_page"])
        self.assertEqual(item["creative"]["format"], "unknown")
        self.assertNotIn("ctr", str(item).lower())
        with self.assertRaises(ValueError):
            ads.normalize({**self.row, "advertiserPageId":"54321"}, self.account)
        with self.assertRaises(ValueError):
            ads.page_url("https://facebook.com.evil.test/12345")
        with self.assertRaises(ValueError):
            ads.page_url("https://www.facebook.com/ads/library/?id=99999")

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_verified_page_id_filters_resellers_and_reuses_paid_dataset(self, remote, items):
        remote.return_value = self.remote()
        items.return_value = [self.row, {**self.row,"adId":"88888","advertiserPageId":"77777"}]
        request = self.request()
        self.account.page_id = ""
        self.account.save()
        first = ads.collect(request, self.account)
        self.assertEqual(first.status, "failed")
        self.assertEqual(CompetitorAd.objects.count(), 0)
        self.account.page_id = "12345"
        self.account.save()
        result = ads.collect(request, self.account, reprocess=True)
        self.assertEqual(result.result["excluded_other_advertisers"], 1)
        self.assertEqual(CompetitorAd.objects.count(), 1)
        ads.collect(request, self.account, reprocess=True)
        self.assertEqual(AdObservation.objects.count(), 1)

    @patch("engine.apify.api")
    def test_ads_inputs_use_verified_library_id_and_supported_platform_enum(self, api):
        api.return_value = {"data":{"id":"verified", "defaultDatasetId":"d"}}
        request = ads.start(self.account)
        self.assertNotIn("pageUrls", request.inputs)
        self.assertIn("view_all_page_id=12345", request.inputs["searchQueries"][0])
        self.assertEqual(request.inputs["publisherPlatforms"], ["FACEBOOK","INSTAGRAM"])

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_ad_identity_snapshot_status_and_analysis_hash_are_separate(self, remote, items):
        remote.return_value, items.return_value = self.remote(), [self.row]
        request = self.request()
        ads.collect(request, self.account)
        ads.collect(request, self.account)
        self.assertEqual(CompetitorAd.objects.count(), 1)
        self.assertEqual(AdObservation.objects.count(), 1)
        ad = CompetitorAd.objects.get()
        original_hash = ad.creative_hash
        original_analysis_hash = ads.classification_hash(ad, self.company)
        items.return_value = [{**self.row, "isActive":False, "endDate":self.now.date().isoformat()}]
        ads.collect(self.request("remote2"), self.account)
        ad.refresh_from_db()
        self.assertEqual(ad.creative_hash, original_hash)
        self.assertEqual(ads.classification_hash(ad, self.company), original_analysis_hash)
        self.assertFalse(ad.is_active)
        self.assertEqual(AdObservation.objects.count(), 2)
        items.return_value = [{**self.row, "adText":"Changed offer"}]
        ads.collect(self.request("remote3"), self.account)
        ad.refresh_from_db()
        self.assertNotEqual(ad.creative_hash, original_hash)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_old_dataset_replay_cannot_rewind_current_ad_or_sync_state(self, remote, items):
        older = self.request("old")
        newer = self.request("new")
        remote.return_value = self.remote()
        items.return_value = [{**self.row, "adText":"Current creative", "isActive":False}]
        ads.collect(newer, self.account)
        state = ads.account_state(self.account)
        watermark = state.watermark
        remote.return_value = {**self.remote(), "finishedAt":(self.now-timedelta(days=2)).isoformat()}
        items.return_value = [self.row]
        ads.collect(older, self.account, reprocess=True)
        ad = CompetitorAd.objects.get()
        self.assertEqual(ad.creative["text"], "Current creative")
        self.assertFalse(ad.is_active)
        self.assertEqual(ad.last_seen_at, self.now)
        self.assertEqual(AdObservation.objects.count(), 2)
        self.assertEqual(ads.account_state(self.account).watermark, watermark)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_partial_results_persist_and_empty_success_does_not_deactivate_ads(self, remote, items):
        remote.return_value, items.return_value = self.remote(), [self.row, {"error":"private provider message"}]
        run = ads.collect(self.request(), self.account)
        self.assertEqual(run.status, "partial")
        self.assertEqual(CompetitorAd.objects.count(), 1)
        self.assertNotIn("private", str(run.result))
        state = ads.account_state(self.account)
        state.refresh_from_db()
        self.assertIsNone(state.watermark)
        items.return_value = []
        run = ads.collect(self.request("empty"), self.account)
        self.assertEqual(run.status, "succeeded")
        self.assertTrue(CompetitorAd.objects.get().is_active)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_cap_pauses_paid_repetition_without_claiming_complete_coverage(self, remote, items):
        remote.return_value = self.remote()
        items.return_value = [{**self.row, "adId":str(10000+i)} for i in range(20)]
        run = ads.collect(self.request(), self.account)
        self.assertTrue(run.result["capped"])
        self.account.refresh_from_db()
        with self.assertRaises(apify.ApifyError):
            ads.start(self.account)
        self.assertEqual(CompetitorAd.objects.count(), 20)

    @patch("engine.apify.api")
    def test_unknown_start_and_daily_reservation_do_not_duplicate_paid_post(self, api):
        api.side_effect = apify.ApifyError("timeout", uncertain=True)
        with self.assertRaises(apify.ApifyError):
            ads.start(self.account)
        request = ads.start(self.account)
        self.assertEqual(request.status, "unknown")
        self.assertEqual(api.call_count, 1)
        state = ads.account_state(self.account)
        state.refresh_from_db()
        self.assertIsNotNone(state.backfill_attempted_at)

    @patch("engine.apify.api")
    def test_failed_weekly_refresh_does_not_repeat_broad_query_next_day(self, api):
        state=ads.account_state(self.account)
        state.backfill_attempted_at=self.now-timedelta(days=20)
        state.watermark=self.now-timedelta(days=1)
        state.last_refresh_at=self.now-timedelta(days=8)
        state.save()
        api.side_effect=apify.ApifyError("rejected",uncertain=False)
        with self.assertRaises(apify.ApifyError):
            ads.start(self.account)
        self.assertEqual(state.requests.get().mode,"refresh")
        tomorrow=self.now+timedelta(days=1)
        api.side_effect=None
        api.return_value={"data":{"id":"tomorrow","defaultDatasetId":"d"}}
        with patch("engine.sync.timezone.localdate",return_value=tomorrow.date()), patch("engine.ads.timezone.now",return_value=tomorrow):
            request=ads.start(self.account)
        self.assertEqual(request.mode,"discovery")
        self.assertEqual(request.inputs["maxResults"],20)

    @patch("engine.apify.api")
    def test_failed_backfill_next_day_is_small_and_no_unbounded_history(self, api):
        api.side_effect = apify.ApifyError("rejected", uncertain=False)
        with self.assertRaises(apify.ApifyError):
            ads.start(self.account)
        next_day = self.now+timedelta(days=1)
        api.side_effect = None
        api.return_value = {"data":{"id":"next", "defaultDatasetId":"d"}}
        with patch("engine.sync.timezone.localdate", return_value=next_day.date()), patch("engine.ads.timezone.now", return_value=next_day):
            result = ads.start(self.account)
        self.assertEqual(result.mode, "discovery")
        self.assertEqual(result.inputs["maxResults"], 20)
        self.assertGreater(result.inputs["adDeliveryDateMin"], (self.now-timedelta(days=5)).date().isoformat())

    @patch("engine.apify.start_actor")
    def test_organic_history_is_initialized_and_manual_rerun_is_bounded(self, sender):
        account = Competitor.objects.create(company=self.company, name="Organic", username="golf", last_success_at=self.now-timedelta(days=1))
        state = state_for(self.company, "instagram", "golf")
        self.assertEqual(organic_plan(account, state), ("discovery", 10))
        sender.return_value = {"id":"organic", "defaultDatasetId":"d"}
        first = start_import(account)
        second = start_import(account)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(first.requested_limit, 10)
        self.assertEqual(first.scrape_request.max_cost_usd, Decimal("0.05"))

    def test_shared_budget_and_analysis_memo_apply_across_entrypoints(self):
        first = state_for(self.company, "instagram", "one")
        second = state_for(self.company, "meta_ads", "two")
        sender = Mock(return_value={"id":"remote", "defaultDatasetId":"d"})
        with patch.dict("os.environ", {"SCRAPER_DAILY_BUDGET_USD":"0.20"}):
            dispatch(first, "actor", "discovery", {}, max_cost="0.15", sender=sender)
            with self.assertRaises(apify.ApifyError):
                dispatch(second, "actor", "discovery", {}, max_cost="0.15", sender=sender)
        self.assertEqual(sender.call_count, 1)
        work = Mock(return_value={"hook":"fråga"})
        analysis(self.company, "same-content", "model", work)
        analysis(self.company, "same-content", "model", work)
        self.assertEqual(work.call_count, 1)
        with patch.dict("os.environ", {"INTELLIGENCE_DAILY_ANALYSES":"1"}):
            with self.assertRaises(ValueError):
                analysis(self.company, "changed", "model", work)

    def test_rate_limited_analysis_retries_later_but_uncertain_does_not(self):
        rejection = RuntimeError("private")
        rejection.status_code = 429
        work = Mock(side_effect=rejection)
        with self.assertRaises(RuntimeError):
            analysis(self.company, "rate-limited", "model", work)
        with self.assertRaises(ValueError):
            analysis(self.company, "rate-limited", "model", work)
        AnalysisMemo.objects.update(last_attempt_at=self.now-timedelta(days=1))
        work.side_effect, work.return_value = None, {"ok":True}
        self.assertEqual(analysis(self.company, "rate-limited", "model", work), {"ok":True})
        self.assertEqual(work.call_count, 2)
        self.assertEqual(AnalysisMemo.objects.get().attempts, 2)
        work.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            analysis(self.company, "uncertain", "model", work)
        AnalysisMemo.objects.update(last_attempt_at=self.now-timedelta(days=2))
        with self.assertRaises(ValueError):
            analysis(self.company, "uncertain", "model", work)

    @patch("engine.views.generate")
    def test_paid_signal_to_ideas_draft_media_and_frozen_prediction(self, generate):
        from .media import create_job
        ad = CompetitorAd.objects.create(account=self.account, first_seen_at=self.now,last_seen_at=self.now, **ads.normalize(self.row,self.account))
        ad.classification = {"hook":"fråga", "mechanisms":["fråga"], "adaptation":"Egen golfvinkel"}
        ad.classification_hash = ads.classification_hash(ad,self.company)
        ad.save()
        generate.return_value = {"ideas":[{"title":f"Egen idé {i}","angle":"Vår golfkunskap","reason":"Egna fakta", "source_quote":"Vi lär ut golf.",
            "source_field":"profile","photo_brief":"Golfbana", "signal_id":f"ad:{ad.pk}","profile_relevance":3,"current_relevance":2} for i in range(3)]}
        url = reverse("engine:ideas",kwargs={"workspace_id":self.company.pk})
        response = self.client.post(url,{"channel":"paid","signal_id":ad.pk})
        self.assertEqual(response.status_code,302)
        idea_context = generate.call_args_list[0].args[0]
        self.assertEqual(idea_context["learning_profile"]["status"], "collecting")
        run = ContentRun.objects.get()
        self.assertEqual(run.channel,"paid")
        self.assertEqual(run.predictions.count(),3)
        self.assertTrue(all(p.channel=="paid" and p.value is None for p in run.predictions.all()))
        self.assertFalse(run.context["competitor_signals"][0]["performance_available"])
        generate.return_value = {"facebook":"Vår golflektion", "instagram":"Vår golflektion", "photo_brief":"Golfbana", "checks":[],
            "headline":"Golflektion", "description":"Lär känna ditt spel", "cta":"Läs mer", "landing_page":""}
        response = self.client.post(reverse("engine:draft",kwargs={"workspace_id":self.company.pk,"run_id":run.pk,"idea_index":0}),follow=True)
        self.assertContains(response,"Meta Ads Manager")
        self.assertNotContains(response,"Skicka utkast till Postiz")
        run.refresh_from_db()
        import uuid
        with patch("engine.media.check_storage"):
            job = create_job(run, token=uuid.uuid4(), kind="image", brief="En egen golfbild")
        self.assertEqual(job.status,"queued")
        with patch("engine.postiz.request") as publish:
            self.client.post(reverse("engine:review",kwargs={"workspace_id":self.company.pk,"run_id":run.pk}),
                {"action":"send","facebook":"Annons","instagram":"Annons","reviewed":"on"})
            publish.assert_not_called()

    def test_ads_are_integrated_and_owner_isolation_holds(self):
        url = reverse("engine:intelligence", kwargs={"workspace_id":self.company.pk})+"?channel=paid"
        response = self.client.get(url)
        self.assertContains(response, "Bevakade annonsörer")
        self.assertContains(response, "Learning · Paid")
        other = get_user_model().objects.create_user(username="other")
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)
        action = reverse("engine:ad_account_action", kwargs={"workspace_id":self.company.pk, "account_id":self.account.pk})
        self.assertEqual(self.client.post(action, {"action":"refresh"}).status_code, 404)

    @patch("engine.apify.dataset_items")
    @patch("engine.apify.get_run")
    def test_daily_recognizes_dataset_repaired_in_ui_without_new_paid_start(self, remote, items):
        from .models import DailyRun, DailyStep
        request=self.request()
        remote.return_value=self.remote()
        items.return_value=[self.row]
        daily=DailyRun.objects.create(day=timezone.localdate())
        step=DailyStep.objects.create(run=daily,company=self.company,stage="ads_import",version="1",key=f"{self.account.pk}:first",
            status="attention",result={"request_id":request.pk})
        ads.collect(request,self.account,reprocess=True)
        units=ads_units(self.company)
        self.assertEqual([key for key,_ in units],[step.key])
        with patch("engine.apify.api") as paid_api:
            result=units[0][1]()
        self.assertEqual(result.status,"success")
        paid_api.assert_not_called()


class LearningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="learning-owner")
        self.company = Company.objects.create(owner=self.user, name="Golf")
        self.now = timezone.now()
        self.idea = {"title":"Golf question", "profile_relevance":2, "current_relevance":3, "source_field":"current", "signal_id":""}

    def content_run(self, channel="organic", days_ago=20):
        run = ContentRun.objects.create(workspace=self.company, channel=channel, context={"captured_at":(self.now-timedelta(days=days_ago)).isoformat()}, ideas=[self.idea.copy()], selected=0)
        record_predictions(run)
        run.predictions.update(created_at=self.now-timedelta(days=days_ago))
        return run

    def outcome(self, run, days_ago=19, index="post-1", **overrides):
        published = self.now-timedelta(days=days_ago)
        params = dict(source="meta_export", external_id=index, published_at=published, window_end=published+timedelta(days=7),
            observed_at=published+timedelta(days=8), metrics={"impressions":1000, "likes":20, "comments":3}, evidence="https://example.test/own-report")
        if run.channel == "paid":
            params["metrics"] = {"impressions":1000, "clicks":15}
        return record_outcome(run, **(params | overrides))

    def test_prediction_is_frozen_without_fake_ml_value_or_retroactive_features(self):
        run = self.content_run()
        p = run.predictions.get()
        self.assertIsNone(p.value)
        self.assertEqual(p.model_version, "heuristic-only")
        run.context["new_fact"] = "later"
        run.save()
        record_predictions(run)
        self.assertEqual(run.predictions.count(), 1)
        self.assertEqual(run.predictions.get().features, p.features)
        with self.assertRaises(ValueError):
            self.outcome(run, days_ago=25)

    def test_only_own_measured_labels_are_accepted_and_reruns_deduplicate(self):
        run = self.content_run()
        outcome = self.outcome(run)
        self.assertEqual(outcome.label, 23)
        self.assertEqual(self.outcome(run).pk, outcome.pk)
        for changes in ({"source":"competitor"}, {"metrics":{"impressions":100}}, {"metrics":{"impressions":100,"likes":float("nan"),"comments":0}}, {"window_end":self.now}):
            with self.assertRaises(ValueError):
                self.outcome(run, **changes)
        paid = self.content_run("paid")
        self.outcome(paid)
        self.assertEqual(len(dataset(self.company, "organic")), 1)
        self.assertEqual(len(dataset(self.company, "paid")), 1)
        self.assertEqual(train(self.company, "paid")["status"], "insufficient")

    def test_cannot_label_same_own_object_as_two_ideas_or_overwrite_label(self):
        a, b = self.content_run(), self.content_run()
        self.outcome(a)
        with self.assertRaises(ValueError):
            self.outcome(b)
        with self.assertRaises(ValueError):
            self.outcome(b, source="manual_verified")
        with self.assertRaises(ValueError):
            self.outcome(a, metrics={"impressions":1000, "likes":40,"comments":3})

    def test_generation_profile_uses_only_prior_measured_own_outcomes(self):
        values = [10, 20, 40, 5]
        titles = []
        for i, value in enumerate(values):
            run = self.content_run(days_ago=40 + i * 2)
            run.ideas[0]["title"] = f"Own idea {i}"
            run.ideas[0]["angle"] = f"Angle {i}"
            run.draft = {"instagram": f"Published-style copy {i}"}
            run.save(update_fields=["ideas", "draft"])
            titles.append(run.ideas[0]["title"])
            self.outcome(
                run,
                days_ago=39 + i * 2,
                index=f"profile-post-{i}",
                metrics={"impressions": 1000, "likes": value, "comments": 0},
            )

        profile = generation_learning_profile(self.company, "organic")
        self.assertEqual(profile["status"], "active")
        self.assertEqual(profile["confidence"], "early")
        self.assertEqual(profile["usable_examples"], 4)
        self.assertEqual(profile["strong_examples"][0]["title"], "Own idea 2")
        self.assertEqual(profile["weak_examples"][0]["title"], "Own idea 3")
        self.assertIn("Published-style copy", profile["strong_examples"][0]["copy_excerpt"])
        self.assertTrue(all("relative_to_own_median" in row for row in profile["strong_examples"]))

        before_results = generation_learning_profile(
            self.company,
            "organic",
            cutoff=self.now - timedelta(days=100),
        )
        self.assertEqual(before_results["status"], "collecting")
        self.assertEqual(before_results["usable_examples"], 0)

    def test_training_is_time_purged_cached_and_shadow_does_not_change_ranking(self):
        for i in range(100):
            age = 230-i*2
            run = self.content_run(days_ago=age)
            value = i % 4
            prediction = run.predictions.get()
            prediction.features["numeric"]["profile_relevance"] = value
            prediction.save()
            outcome = self.outcome(run, days_ago=age-1, index=f"post-{i}", metrics={"impressions":1000,"likes":value*20+5,"comments":0})
            OwnOutcome.objects.filter(pk=outcome.pk).update(recorded_at=outcome.observed_at)
        result = train(self.company, "organic")
        self.assertEqual(result["status"], "trained")
        model = LearningModel.objects.get()
        self.assertEqual(model.mode, "shadow")
        self.assertGreater(model.evaluation["improvement"], .1)
        self.assertEqual(train(self.company, "organic")["status"], "cached")
        self.assertFalse(set(model.evaluation["train_outcome_ids"]) & set(model.evaluation["test_outcome_ids"]))
        held = OwnOutcome.objects.filter(pk__in=model.evaluation["test_outcome_ids"])
        earliest = min(o.prediction.created_at for o in held)
        self.assertTrue(all(max(o.recorded_at,o.window_end,o.observed_at)<earliest for o in OwnOutcome.objects.filter(pk__in=model.evaluation["train_outcome_ids"])))
        run = ContentRun.objects.create(workspace=self.company, context={}, ideas=[{**self.idea,"profile_relevance":0},{**self.idea,"profile_relevance":3}])
        record_predictions(run)
        run.refresh_from_db()
        self.assertEqual(run.ideas[0]["profile_relevance"], 0)
        self.assertEqual(run.predictions.count(), 2)
        self.assertTrue(all(p.mode == "shadow" for p in run.predictions.all()))
        with self.assertRaises(ValueError):
            promote(model)

    def test_daily_future_learning_does_not_require_labels_or_block_ads(self):
        daily = run_daily(company_id=self.company.pk, wait_seconds=0, stages=[Stage("ads",ads_units), Stage("analysis",ads_analysis_units),Stage("learning",learning_units)])
        self.assertEqual(daily.status, "success")
        self.assertEqual(daily.steps.filter(stage="learning", status="skipped").count(), 3)

    def test_production_requires_prospective_shadow_evidence_and_stays_channel_scoped(self):
        from .learning import NUMERIC, shadow_evaluation
        model = LearningModel.objects.create(company=self.company, channel="paid", version="candidate", target=TARGETS["paid"],
            training_cutoff=self.now-timedelta(days=60),
            artifact={"intercept":5., "coefficients":[10.]+[0.]*(len(NUMERIC)-1), "mean":[0.]*len(NUMERIC), "scale":[1.]*len(NUMERIC)},
            evaluation={"baseline":80., "improvement":.5})
        for i in range(20):
            run=self.content_run("paid", days_ago=30)
            self.outcome(run, days_ago=29, index=f"paid:{i}", metrics={"impressions":1000,"clicks":25})
        self.assertTrue(shadow_evaluation(model)["eligible"])
        self.assertEqual(model.mode, "shadow")
        promote(model)
        run=ContentRun.objects.create(workspace=self.company,channel="paid",context={},ideas=[{**self.idea,"profile_relevance":0},{**self.idea,"profile_relevance":3}])
        record_predictions(run)
        self.assertEqual(run.ideas[0]["profile_relevance"],3)
        self.assertTrue(all(p.mode=="production" for p in run.predictions.all()))
        organic=self.content_run()
        self.assertEqual(organic.predictions.get().model_version,"heuristic-only")
