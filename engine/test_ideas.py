from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from engine import follow_lists
from engine.ideas import discord as idea_discord
from engine.ideas import service
from engine.ideas.models import IdeaCard
from engine.models import Company, Competitor, CompetitorImport, CompetitorPost, CompetitorSnapshot
from engine.references.models import ReferenceVideo
from engine.review import discord as review_discord

JONAS = "388380559606546432"

PLAN = {
    "title": "HR-mailet", "angle": "x", "why_this_angle": "x", "keep_from_reference": [], "beat_the_reference": [],
    "hook": "x", "music": "x", "end_card": "x", "duration_s": 14.6,
    "scenes": [
        {"ref_scene": "s1", "start_s": 0, "end_s": 2, "shows": "kontor", "camera": "POV", "material": "filma",
         "material_detail": "Någon som suckar vid datorn, filmat över axeln"},
        {"ref_scene": "s2", "start_s": 2, "end_s": 4, "shows": "kupong", "camera": "närbild",
         "material": "produktbild", "material_detail": "Golfkupongen i handen, framifrån"},
        {"ref_scene": "s3", "start_s": 4, "end_s": 6, "shows": "bana", "camera": "drönare", "material": "ai-video"},
    ],
    "to_film": ["Någon som suckar vid datorn, filmat över axeln"],
    "facts_to_verify": [{"claim": "Gäller på 300 banor", "why": "styrker erbjudandet"}],
}


@override_settings(APP_URL="https://app.example")
class IdeaCardTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="ideas")
        self.company = Company.objects.create(owner=user, name="Golfkuponger", profile="Golf.",
                                              review_channel_id="123")
        self.now = timezone.now()

    def account(self, username, views, *, own=False):
        account = Competitor.objects.create(company=self.company, name=username, platform="instagram",
                                            username=username, own=own)
        run = CompetitorImport.objects.create(competitor=account, actor="a", status="succeeded")
        for i, value in enumerate(views):
            post = CompetitorPost.objects.create(
                competitor=account, shortcode=f"{username}{i}", url=f"https://www.instagram.com/reel/{username}{i}/",
                published_at=self.now - timedelta(days=5 + i), format="reel")
            CompetitorSnapshot.objects.create(post=post, import_run=run, observed_at=self.now, views=value)
        return account

    def reference(self):
        return ReferenceVideo.objects.create(
            company=self.company, source_url="https://www.instagram.com/reel/x/", storage_backend="local",
            storage_key="k", sha256="s", status="analyzed", breakdown={"summary": "Kontorsmeme om HR-mail."})

    def test_hits_put_our_own_posts_first_and_need_three_times_the_normal(self):
        self.account("timeplan", (1000, 1000, 1000, 1000, 9000, 2500))   # 9× and 2.5× its normal
        self.account("golfkuponger", (100, 100, 100, 100, 400), own=True)  # our own, 4×
        rows = service.hits(self.company)
        self.assertEqual([r["post_id"] for r in rows], ["golfkuponger4", "timeplan4"])
        self.assertTrue(rows[0]["own"])
        self.assertIn("Ert eget inlägg", service._why(rows[0]))
        self.assertIn("9.0× kontots vanliga", service._why(rows[1]))

    def fake_pitch(self, fit):
        def call(**kwargs):
            self.assertEqual(kwargs["operation"], "idea_pitch")
            return service.Pitch(summary="Kontorsmeme.", spin="HR-mailet om friskvårdsbidraget som ingen läser.",
                                 fit=fit, fit_note="Passar Q4."), {"cost_usd": 0.001}
        return call

    def test_only_good_ideas_are_sent_and_at_most_two_a_week(self):
        self.account("timeplan", (1000, 1000, 1000, 1000, 9000, 8000, 7000))
        ref = self.reference()
        posted = []
        with mock.patch("engine.references.service.process", return_value=ref), \
                mock.patch("engine.openrouter.structured_analysis", side_effect=self.fake_pitch(8)), \
                mock.patch.object(review_discord, "post", side_effect=lambda p, c, client=None: posted.append(p) or {"message_id": "9"}), \
                mock.patch.dict("os.environ", {"IDEA_DAILY_LIMIT": "3"}):
            first = service.daily(self.company)
            second = service.daily(self.company)
            third = service.daily(self.company)
        self.assertEqual(len(first["pitched"]), 3)
        self.assertTrue(first["sent"] and second["sent"])
        self.assertIsNone(third["sent"])  # the week is full
        self.assertEqual(len(posted), 2)
        message = posted[0]["message"]
        self.assertIn("ny idé", message["content"])
        self.assertIn("Vår spinn:", message["embeds"][0]["description"])
        self.assertEqual(message["embeds"][0]["url"], "https://www.instagram.com/reel/timeplan4/")
        self.assertEqual(IdeaCard.objects.filter(status="sent").count(), 2)

    def test_weak_ideas_are_never_sent(self):
        self.account("timeplan", (1000, 1000, 1000, 1000, 9000))
        with mock.patch("engine.references.service.process", return_value=self.reference()), \
                mock.patch("engine.openrouter.structured_analysis", side_effect=self.fake_pitch(5)), \
                mock.patch.object(review_discord, "post") as post:
            result = service.daily(self.company)
        post.assert_not_called()
        self.assertIsNone(result["sent"])
        self.assertEqual(IdeaCard.objects.get().status, "skipped")

    def test_a_failed_hit_is_not_retried(self):
        self.account("timeplan", (1000, 1000, 1000, 1000, 9000))
        with mock.patch("engine.references.service.process", side_effect=RuntimeError("429")):
            result = service.daily(self.company)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(IdeaCard.objects.get().status, "failed")
        self.assertEqual(service.hits(self.company), [])

    def test_a_failed_hit_is_tried_once_more_after_two_days_then_never(self):
        self.account("timeplan", (1000, 1000, 1000, 1000, 9000))
        with mock.patch("engine.references.service.process", side_effect=RuntimeError("TikTok blockerade")):
            service.daily(self.company)
        IdeaCard.objects.update(created_at=timezone.now() - timedelta(days=3))
        self.assertEqual(len(service.hits(self.company)), 1)  # due for its second try

        with mock.patch("engine.references.service.process", side_effect=RuntimeError("TikTok blockerade")):
            service.daily(self.company)
        card = IdeaCard.objects.get()
        self.assertEqual((card.status, card.error), ("failed", "Andra försöket: TikTok blockerade"))
        self.assertEqual(service.hits(self.company), [])  # a second failure is final

    def test_a_retried_hit_that_works_is_pitched_and_its_old_error_cleared(self):
        self.account("timeplan", (1000, 1000, 1000, 1000, 9000))
        with mock.patch("engine.references.service.process", side_effect=RuntimeError("TikTok blockerade")):
            service.daily(self.company)
        IdeaCard.objects.update(created_at=timezone.now() - timedelta(days=3))
        with mock.patch("engine.references.service.process", return_value=self.reference()),                 mock.patch("engine.openrouter.structured_analysis", side_effect=self.fake_pitch(5)):
            service.daily(self.company)
        card = IdeaCard.objects.get()
        self.assertEqual((card.status, card.error), ("skipped", ""))

    def test_skapa_plans_and_answers_with_what_we_must_supply(self):
        card = IdeaCard.objects.create(company=self.company, reference=self.reference(), source_key="instagram:x",
                                       source_url="https://www.instagram.com/reel/x/", why="x", spin="HR-mailet",
                                       fit=8, status="sent", discord_message_id="77", discord_channel_id="123")
        posted = []
        entry = {"id": "abc", "plan": PLAN, "cost_usd": 0.02}
        with mock.patch("engine.references.service.plan_our_version", return_value=entry) as planner, \
                mock.patch.object(service, "background", side_effect=lambda work: work()), \
                mock.patch.object(review_discord, "post", side_effect=lambda p, c, client=None: posted.append(p) or {}):
            answer = review_discord.handle({"custom_id": f"ce:ok:{card.pk}", "user": {"id": JONAS, "name": "Jonas"}})
        self.assertIn("Kör", answer["reply"])
        self.assertIn("👍 Skapa av Jonas", answer["card_content"])
        planner.assert_called_once()
        self.assertEqual(planner.call_args.kwargs["angle"], "HR-mailet")
        card.refresh_from_db()
        self.assertEqual(card.status, "approved")
        self.assertEqual(card.needs, ["🎥 Filma: Någon som suckar vid datorn, filmat över axeln",
                                      "📷 Bild: Golfkupongen i handen, framifrån",
                                      "✔️ Bekräfta: Gäller på 300 banor"])
        reply = posted[0]["message"]
        self.assertEqual(reply["message_reference"]["message_id"], "77")
        self.assertIn("Det här behöver vi från er", reply["content"])
        self.assertIn(f"https://app.example/company/{self.company.pk}/media/", reply["content"])

    def test_rating_comment_and_no_are_stored_as_feedback(self):
        card = IdeaCard.objects.create(company=self.company, source_key="instagram:y", source_url="https://x.se/",
                                       why="x", spin="y", status="sent")
        user = {"id": JONAS, "name": "Jonas"}
        review_discord.handle({"custom_id": f"ce:rate:{card.pk}", "values": ["9"], "user": user})
        review_discord.handle({"custom_id": f"ce:notetext:{card.pk}", "text": "För lik originalet", "user": user})
        answer = review_discord.handle({"custom_id": f"ce:no:{card.pk}", "user": user})
        card.refresh_from_db()
        self.assertEqual((card.rating, card.status), (9, "rejected"))
        self.assertEqual([f["kind"] for f in card.feedback], ["rating", "comment", "reject"])
        self.assertIn("⭐ 9/10", answer["card_content"])
        stranger = review_discord.handle({"custom_id": f"ce:ok:{card.pk}", "user": {"id": "1"}})
        self.assertIn("kan se", stranger["reply"])

    def test_own_accounts_come_from_the_follow_list(self):
        with mock.patch("engine.follow_lists.start_import"):
            follow_lists.apply(self.company)
        own = Competitor.objects.get(company=self.company, own=True)
        self.assertEqual((own.platform, own.username), ("instagram", "golfkuponger"))
        self.assertEqual(Competitor.objects.filter(company=self.company, own=True).count(), 1)

    def test_card_is_short(self):
        card = IdeaCard(company=self.company, source_url="https://x.se/", why="Timeplan: 9× kontots vanliga",
                        summary="Kontorsmeme.", spin="HR-mailet.")
        text = idea_discord.card(card)["message"]["embeds"][0]["description"]
        self.assertEqual(len(text.splitlines()), 3)

    def test_instagram_without_views_is_measured_on_likes(self):
        account = Competitor.objects.create(company=self.company, name="golfstar", platform="instagram",
                                            username="golfstar")
        run = CompetitorImport.objects.create(competitor=account, actor="a", status="succeeded")
        for i, likes in enumerate((50, 60, 55, 40, 400)):
            post = CompetitorPost.objects.create(
                competitor=account, shortcode=f"g{i}", url=f"https://www.instagram.com/reel/g{i}/",
                published_at=self.now - timedelta(days=5 + i), format="reel")
            CompetitorSnapshot.objects.create(post=post, import_run=run, observed_at=self.now, likes=likes)
        rows = service.hits(self.company)
        self.assertEqual([r["post_id"] for r in rows], ["g4"])
        self.assertIn("400 gillningar, 7.3× kontots vanliga", service._why(rows[0]))
