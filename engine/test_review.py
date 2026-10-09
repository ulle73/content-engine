import json
from unittest import mock

import httpx
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .ad_studio import library
from .models import Company, MediaAsset
from .openrouter import OpenRouterError
from .review import discord, lessons, service
from .review.manifest import candidates, clean, from_brief
from .review.models import Lesson, Review

JONAS = {"id": "388380559606546432", "name": "Jonas"}
ENV = {"CONTENT_N8N_SECRET": "s3cret", "CONTENT_N8N_DISCORD_URL": "https://n8n.example/webhook/ce-discord"}
MANIFEST = {
    "global": [{"id": "hf.template.punchy", "type": "template", "label": "Punchy promo"}],
    "scenes": [
        {"id": "hook", "start": 0, "end": 3, "purpose": "hook", "text": "Har du glömt bidraget?",
         "items": [{"id": "animate.effect.boil-line", "type": "effect", "label": "Kokande linje"}]},
        {"id": "cta", "start": 3, "end": 8, "purpose": "cta",
         "items": [{"id": "hf.transition.glitch", "type": "transition", "label": "Glitch-övergång"}]},
    ],
}


def interpretation(**kwargs):
    data = {"points": [], "clarification": "", "summary": "Glitch-övergången upplevs billig."}
    data.update(kwargs)
    return service.Interpretation(**data)


AVOID_GLITCH = {"target_type": "library", "target_id": "hf.transition.glitch", "target_label": "x", "polarity": "avoid",
                "rule": "Inga glitch-övergångar, de ser billiga ut.", "fix_now": "Byt till hård klipp."}


@override_settings(APP_URL="https://ce.example")
class ReviewLoopTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", password="x")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger", review_channel_id="123")
        self.asset = MediaAsset.objects.create(company=self.company, kind="video", origin="generated", provider="higgsfield",
                                               storage_backend="local", storage_key="t/v.mp4", mime_type="video/mp4",
                                               byte_size=4 * 1024 * 1024)
        self.review = service.create(self.company, self.asset, title="Friskvård v1", caption="Använd bidraget!",
                                     manifest=MANIFEST)

    def handle(self, custom_id, user=JONAS, **extra):
        return discord.handle({"custom_id": custom_id.format(id=self.review.pk), "user": user, **extra})["reply"]

    def test_manifest_cleaning_and_candidates(self):
        manifest = clean({"scenes": [{"duration_s": 2, "items": ["a.b", {"id": ""}]}, {"duration_s": 3}]})
        self.assertEqual([(s["start"], s["end"]) for s in manifest["scenes"]], [(0, 2), (2, 5)])
        self.assertEqual(manifest["scenes"][0]["items"][0]["id"], "a.b")
        found = candidates(self.review.manifest, "Övergången vid 0:05 känns billig")
        self.assertEqual(found[0]["id"], "hf.transition.glitch")
        brief = {"engine": {"remotion_template_id": "tpl"}, "scenes": [{"id": "s1", "duration_s": 2, "transition_in": "fade"}]}
        self.assertEqual(from_brief(brief)["scenes"][0]["items"][0]["id"], "fade")

    def test_card_attaches_small_video_and_links_large(self):
        card = discord.card(self.review)
        self.assertEqual(card["channel_id"], "123")
        ids = [c["custom_id"] for row in card["message"]["components"] for c in row["components"]]
        self.assertEqual([i.split(":")[1] for i in ids], ["ok", "no", "edit", "note", "rate"])
        self.assertTrue(card["attachment"]["url"].startswith("https://ce.example/review/v/"))
        self.asset.byte_size = 50 * 1024 * 1024
        self.assertIsNone(discord.card(self.review)["attachment"])
        self.assertIn("för stor", discord.card(self.review)["message"]["embeds"][0]["description"])

    def test_send_through_n8n_relay(self):
        def handler(request):
            self.assertEqual(request.headers["X-Content-Engine-Secret"], "s3cret")
            self.assertEqual(json.loads(request.content)["channel_id"], "123")
            return httpx.Response(200, json={"message_id": "999"})
        with mock.patch.dict("os.environ", ENV):
            discord.send(self.review, client=httpx.Client(transport=httpx.MockTransport(handler)))
        self.assertEqual(Review.objects.get().discord_message_id, "999")
        with self.assertRaises(service.ReviewError):
            discord.send(self.review)

    def test_only_reviewers_can_act_and_verdicts_are_stored(self):
        self.assertIn("inte godkänna", self.handle("ce:ok:{id}", user={"id": "1", "name": "x"}))
        self.assertIn("Godkänd", self.handle("ce:ok:{id}"))
        self.assertIn("7/10", self.handle("ce:rate:{id}", values=["7"]))
        self.review.refresh_from_db()
        self.assertEqual((self.review.status, self.review.rating), ("approved", 7))
        self.assertIn("1–10", self.handle("ce:rate:{id}", values=["11"]))

    def test_comment_becomes_lesson_and_strengthens(self):
        reply_point = interpretation(points=[AVOID_GLITCH, dict(AVOID_GLITCH, target_id="made.up.id")])
        with mock.patch("engine.review.service.structured_analysis", return_value=reply_point):
            reply = self.handle("ce:notetext:{id}", text="Glitchen vid 0:05 är billig")
        self.assertIn("Glitch-övergång", reply)
        lesson = Lesson.objects.get()
        self.assertEqual((lesson.target_id, lesson.polarity, lesson.evidence), ("hf.transition.glitch", "avoid", 1))
        with mock.patch("engine.review.service.structured_analysis", return_value=interpretation(points=[AVOID_GLITCH])):
            self.assertIn("2:e gången", self.handle("ce:notetext:{id}", text="igen glitch"))
        self.assertEqual(Lesson.objects.get().evidence, 2)
        self.assertTrue(any("glitch" in rule.lower() for rule in lessons.for_prompt(self.company)))

    def test_change_request_and_clarification(self):
        unclear = interpretation(clarification="Menar du kokande linjen eller glitch-övergången?")
        with mock.patch("engine.review.service.structured_analysis", return_value=unclear):
            self.assertIn("Menar du", self.handle("ce:edittext:{id}", text="effekten är dålig"))
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, "changes")
        self.assertFalse(Lesson.objects.exists())

    def test_failed_interpretation_is_retried_later(self):
        with mock.patch("engine.review.service.structured_analysis", side_effect=OpenRouterError("down")):
            self.assertIn("i natt", self.handle("ce:notetext:{id}", text="glitchen är billig"))
        with mock.patch("engine.review.service.structured_analysis", return_value=interpretation(points=[AVOID_GLITCH])):
            self.assertEqual(service.interpret_pending(), 1)
        self.assertTrue(Lesson.objects.filter(target_id="hf.transition.glitch").exists())

    def test_lessons_and_ratings_steer_library_search(self):
        lessons.remember(self.company, target_type="library", target_id="hf.transition.glitch", target_label="Glitch",
                         polarity="avoid", rule="Ser billigt ut")
        service.rate(self.review, 9, JONAS)
        feedback = lessons.library_feedback(self.company)
        self.assertLess(feedback["hf.transition.glitch"]["multiplier"], 0.3)
        self.assertGreater(feedback["animate.effect.boil-line"]["multiplier"], 1.2)
        items = [{"id": "hf.transition.glitch", "type": "transition", "name": "glitch", "status": "", "formats": ["any"],
                  "medium": "video", "kit": "k", "tags": [], "description": ""},
                 {"id": "hf.transition.cut", "type": "transition", "name": "glitch cut", "status": "", "formats": ["any"],
                  "medium": "video", "kit": "k", "tags": [], "description": ""}]
        with mock.patch.object(library, "items", return_value=items):
            results = library.search("glitch", feedback=feedback)["results"]
        self.assertEqual(results[0]["id"], "hf.transition.cut")
        self.assertIn("Undvik", results[1]["our_feedback"]["notes"][0])
        lessons.remember(self.company, target_type="library", target_id="hf.transition.glitch", target_label="Glitch",
                         polarity="prefer", rule="Funkar i hooken")
        self.assertFalse(Lesson.objects.get(polarity="avoid").active)

    def test_endpoint_requires_secret_and_video_link_is_signed(self):
        url = reverse("engine_review_discord")
        body = json.dumps({"custom_id": f"ce:ok:{self.review.pk}", "user": JONAS})
        with mock.patch.dict("os.environ", ENV):
            self.assertEqual(self.client.post(url, body, content_type="application/json").status_code, 403)
            response = self.client.post(url, body, content_type="application/json", HTTP_X_CONTENT_ENGINE_SECRET="s3cret")
        self.assertIn("Godkänd", response.json()["reply"])
        link = service.video_link(self.review).replace("https://ce.example", "")
        self.assertEqual(self.client.get(link[:-3] + "xx/").status_code, 404)
        self.assertEqual(self.client.get(link).status_code, 404)  # file missing locally, but the token was accepted
        self.assertEqual(self.client.get(link).content.decode(), "Filen saknas.")

    def test_new_version_supersedes_old(self):
        v2 = service.create(self.company, self.asset, title="v2", parent=self.review)
        self.assertEqual(v2.version, 2)
        self.assertIn("nyare version", self.handle("ce:ok:{id}"))
