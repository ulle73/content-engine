from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .learning import FEATURE_VERSION, generation_guidance, generation_guidance_summary
from .learning_targets import DEFAULTS
from .models import Company, ContentEvent, ContentRun, OwnOutcome, Prediction


class GenerationLearningGuidanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="learning-user", password="x")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger")
        self.now = timezone.now()

    def make_outcome(self, *, title, angle, label, index):
        run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={"channel": "organic"},
            ideas=[
                {
                    "title": title,
                    "angle": angle,
                    "photo_brief": "Egen golfbild",
                    "source_quote": "Verifierad fakta.",
                    "source_field": "current",
                    "signal_id": "",
                    "profile_relevance": 2,
                    "current_relevance": 3,
                }
            ],
            selected=0,
            draft={"instagram": f"Slutlig copy för {title}", "facebook": ""},
            model="test",
            channel="organic",
        )
        prediction = Prediction.objects.create(
            run=run,
            idea_index=0,
            channel="organic",
            features={"numeric": {}},
            feature_version=FEATURE_VERSION,
            model_version="heuristic-only",
            target=DEFAULTS["organic"],
            mode="shadow",
        )
        OwnOutcome.objects.create(
            prediction=prediction,
            source="manual_verified",
            external_id=f"post-{index}",
            published_at=self.now - timedelta(days=8 + index),
            window_end=self.now - timedelta(days=1 + index),
            observed_at=self.now - timedelta(days=index),
            metrics={"impressions": 1000, "likes": int(label), "comments": 0},
            label=float(label),
            evidence=f"https://example.com/{index}",
            target=DEFAULTS["organic"],
            platform="instagram",
        )
        return run

    def test_verified_outcomes_feed_performance_profile(self):
        low = self.make_outcome(title="Svag idé", angle="Svag vinkel", label=50, index=1)
        mid = self.make_outcome(title="Normal idé", angle="Normal vinkel", label=100, index=2)
        high = self.make_outcome(title="Stark idé", angle="Stark vinkel", label=200, index=3)

        ContentEvent.objects.create(run=high, idea_index=0, action="selected", data={"idea": high.ideas[0]})
        ContentEvent.objects.create(run=low, idea_index=0, action="rejected", data={"idea": low.ideas[0]})
        ContentEvent.objects.create(
            run=mid,
            idea_index=0,
            action="edited",
            data={
                "before": {"instagram": "Lång och vag text före redigering."},
                "after": {"instagram": "Kortare och tydligare text efter redigering."},
            },
        )

        guidance = generation_guidance(self.company, "organic")

        self.assertEqual(guidance["performance"]["sample_size"], 3)
        self.assertEqual(guidance["performance"]["confidence"], "early")
        self.assertEqual(guidance["performance"]["strong_examples"][0]["title"], "Stark idé")
        self.assertEqual(guidance["performance"]["strong_examples"][0]["relative_to_own_norm"], 2.0)
        self.assertEqual(guidance["editorial"]["selected_examples"][0]["title"], "Stark idé")
        self.assertEqual(guidance["editorial"]["rejected_examples"][0]["title"], "Svag idé")
        self.assertEqual(len(guidance["editorial"]["edit_examples"]), 1)

        summary = generation_guidance_summary(self.company, "organic")
        self.assertEqual(summary["performance_examples"], 3)
        self.assertEqual(summary["editorial_signals"], 2)
        self.assertEqual(summary["edit_examples"], 1)

    def test_editorial_feedback_never_becomes_performance_evidence(self):
        run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={"channel": "organic"},
            ideas=[{"title": "Bortvald idé", "angle": "Vinkel"}],
            model="test",
            channel="organic",
        )
        ContentEvent.objects.create(run=run, idea_index=0, action="rejected", data={"idea": run.ideas[0]})

        guidance = generation_guidance(self.company, "organic")

        self.assertEqual(guidance["performance"]["sample_size"], 0)
        self.assertEqual(guidance["performance"]["strong_examples"], [])
        self.assertEqual(guidance["editorial"]["signal_count"], 1)
        self.assertEqual(guidance["editorial"]["rejected_examples"][0]["title"], "Bortvald idé")
