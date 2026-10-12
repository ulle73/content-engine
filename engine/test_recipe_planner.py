"""Recipe → cut spec planner, shot-list tagging, the recipe MCP tools and the AI critic of finished cuts."""

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import av
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from .ad_studio.models import AdFact, AssetTags
from .edit import critic, footage, planner, service
from .edit.models import EditJob
from .media import store_asset
from .models import CatalogProduct, Company, MediaAsset
from .review import discord
from .review.models import Lesson, Review
from .test_edit import AUTH, EditTestCase, movie, picture


def clip(company, seconds, *, shots=(), description="", verified=True, kind="video"):
    asset = store_asset(company, movie(seconds) if kind == "video" else picture())
    if shots or description:
        AssetTags.objects.create(asset=asset, tags=list(shots), roles=["footage"], description=description,
                                 verified=verified)
    return asset


def scene(plan, scene_id):
    return next(s for s in plan["spec"]["scenes"] if s["id"] == scene_id)


class FootageTagTests(EditTestCase):
    def test_shot_ids_come_from_filmlista(self):
        shots = footage.shots()
        self.assertIn("fa-m1", shots)
        self.assertIn("bo-1", shots)
        self.assertIn("ljusen av", shots["fa-m1"]["text"])
        self.assertTrue(shots["fa-m1"]["star"])
        self.assertEqual(footage.clean_ids(["FA-M1", " gk-o1 ", "fa-m1"]), ["fa-m1", "gk-o1"])
        self.assertEqual(footage.clean_ids("fa-m1, fa-p5"), ["fa-m1", "fa-p5"])
        with self.assertRaisesRegex(footage.FootageError, "Okända filmlista-id: fa-zz"):
            footage.clean_ids(["fa-m1", "fa-zz"])
        groups = footage.grouped(self.company)  # FAIV: fa- and shared bo- shots only
        ids = {s["id"] for g in groups for s in g["shots"]}
        self.assertIn("fa-m1", ids)
        self.assertIn("bo-1", ids)
        self.assertNotIn("gk-o1", ids)

    def test_ids_in_filename(self):
        self.assertEqual(footage.ids_in_filename("fa-m1_volvo.mp4"), ["fa-m1"])
        self.assertEqual(footage.ids_in_filename("C:/film/FA-P5 slowmo.mp4"), ["fa-p5"])
        self.assertEqual(footage.ids_in_filename("gk-o1-och-bo-1.mp4"), ["gk-o1", "bo-1"])
        self.assertEqual(footage.ids_in_filename("fa-m12.mp4"), [])
        self.assertEqual(footage.ids_in_filename("semester.mp4"), [])

    def test_set_tags_replaces_shot_ids_and_keeps_other_tags(self):
        asset = clip(self.company, 1.0)
        AssetTags.objects.create(asset=asset, tags=["natt", "fa-m2"], roles=["hook"], description="")
        tags = footage.set_tags(self.company, asset.pk, ["fa-m1"])
        self.assertEqual(sorted(tags.tags), ["fa-m1", "natt"])
        self.assertEqual(tags.roles, ["footage", "hook"])
        self.assertIn("ljusen av", tags.description)
        with self.assertRaisesRegex(footage.FootageError, "finns inte i bolagets mediabank"):
            footage.set_tags(self.company, self.foreign.pk, ["fa-m1"])
        with self.assertRaisesRegex(footage.FootageError, "Bara video och bilder"):
            footage.set_tags(self.company, self.music.pk, ["fa-m1"])

    def test_upload_auto_tags_from_filename_and_dialog_saves_ids(self):
        self.client.force_login(self.user)
        url = reverse("engine:media_library_upload", kwargs={"workspace_id": self.company.pk})
        response = self.client.post(url, {"file": SimpleUploadedFile("fa-m1_volvo.mp4", movie(1.0), "video/mp4")},
                                    follow=True)
        self.assertContains(response, "fa-m1")
        asset = MediaAsset.objects.filter(company=self.company, kind="video").order_by("-created_at").first()
        self.assertEqual(asset.ad_tags.tags, ["fa-m1"])
        self.assertFalse(asset.ad_tags.verified)

        page = self.client.get(reverse("engine:media_library", kwargs={"workspace_id": self.company.pk}))
        self.assertContains(page, "Filmlista-id")
        self.assertContains(page, "footage-picker-template")
        self.assertContains(page, "<code>fa-p5</code>")
        save = reverse("engine:media_library_footage", kwargs={"workspace_id": self.company.pk, "asset_id": asset.pk})
        response = self.client.post(save, {"footage_ids": "fa-m1, fa-m3", "description": "Volvo på skogsväg"},
                                    follow=True)
        self.assertContains(response, "Filmlista-id sparade: fa-m1, fa-m3")
        asset.ad_tags.refresh_from_db()
        self.assertEqual(asset.ad_tags.tags, ["fa-m1", "fa-m3"])
        self.assertEqual(asset.ad_tags.description, "Volvo på skogsväg")
        response = self.client.post(save, {"footage_ids": "fa-xx"}, follow=True)
        self.assertContains(response, "Okända filmlista-id")


class PlannerTests(EditTestCase):
    def setUp(self):
        super().setUp()
        # Keep the base fixtures out of the candidate pool so each test controls the media bank.
        MediaAsset.objects.filter(pk__in=[self.clip.pk, self.still.pk]).delete()

    def test_empty_media_bank_reports_every_shot_to_film(self):
        plan = planner.plan_cut(self.company, "faiv-dark-to-light-reveal")
        self.assertFalse(plan["ready"])
        self.assertEqual(plan["spec"]["scenes"], [])
        self.assertEqual([m["scene"] for m in plan["missing"]], ["s1", "s2", "s3", "s4", "s5"])
        s1 = plan["missing"][0]
        self.assertEqual(s1["footage_ids"], ["fa-m1"])
        self.assertIn("Filma fa-m1", s1["hint"])
        self.assertIn("fa-m1_klipp.mp4", s1["hint"])
        self.assertIn("kling", plan["missing"][1]["hint"])  # AI alternative from the recipe's ai_upgrade
        self.assertEqual(plan["spec"]["cta"]["text"], "Montering i Kungälv · faiv.se")  # graphic CTA → end card
        self.assertTrue(any("ingen musik" in n for n in plan["notes"]))

    def test_picks_tagged_least_recently_used_and_continues_same_shot(self):
        used = clip(self.company, 6.0, shots=["fa-m1"])
        fresh = clip(self.company, 6.0, shots=["fa-m1"])
        EditJob.objects.create(company=self.company, cut_spec={"scenes": [{"asset_id": str(used.pk)}]})
        cone = clip(self.company, 4.0, description="Ljuskäglan över vägen och reflexstolpar i mörkret")
        clip(self.company, 4.0, description="Golfbana i solnedgång")
        plan = planner.plan_cut(self.company, "faiv-dark-to-light-reveal")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(fresh.pk))
        self.assertEqual(scene(plan, "s1")["trim_start_s"], 1.0)  # skip the first second (FILMLISTA: 1 s före)
        # s3 asks for fa-m1 again: the unused second take is taken first, never the same file twice when avoidable.
        self.assertEqual(scene(plan, "s3")["asset_id"], str(used.pk))
        self.assertEqual(scene(plan, "s4")["asset_id"], str(cone.pk))
        why = next(c["why"] for c in plan["choices"] if c["scene"] == "s4")
        self.assertIn("beskrivningen matchar", why)
        self.assertEqual({m["scene"] for m in plan["missing"]}, {"s2", "s5"})
        self.assertEqual(scene(plan, "s1")["text_style"], "nextphase.zak.caption")
        self.assertIn("hyperframes.registry.camera-shake", scene(plan, "s3")["effects"])
        self.assertIsNone(scene(plan, "s1")["transition_in"])
        self.assertEqual(scene(plan, "s3")["transition_in"], "motion-studio.transition.hard-cut-on-drop")

    def test_single_take_is_reused_with_later_trim(self):
        only = clip(self.company, 8.0, shots=["fa-m1"])  # long enough for s1 and s3 with their reading time
        plan = planner.plan_cut(self.company, "faiv-dark-to-light-reveal")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(only.pk))
        self.assertEqual(scene(plan, "s3")["asset_id"], str(only.pk))
        s1 = scene(plan, "s1")
        self.assertEqual(scene(plan, "s3")["trim_start_s"],  # continues where s1 ended (lights on)
                         round(s1["trim_start_s"] + s1["duration_s"], 2))
        self.assertTrue(any("samma klipp" in n for n in plan["notes"]))

    def test_text_of_a_missing_scene_moves_to_the_next_scene(self):
        clip(self.company, 6.0, shots=["fa-n1"])
        clip(self.company, 8.0, shots=["fa-n3"])  # no fa-n2: s2 ("Det är inte älgen …") has no material
        plan = planner.plan_cut(self.company, "faiv-winter-mood")
        self.assertEqual([s["id"] for s in plan["spec"]["scenes"]], ["s1", "s3"])
        s3 = scene(plan, "s3")
        self.assertEqual(s3["text"], "Det är inte älgen du ska oroa dig för. Det är att du inte ser den.")
        # Takes over s2's screen time (5 s) and gets the reading time for both lines: 66 characters / 12 cps + 0.9 s.
        self.assertEqual(s3["duration_s"], 6.4)
        self.assertTrue(any("hinner läsas" in n for n in plan["notes"]))
        self.assertTrue(any("texten från s2" in n for n in plan["notes"]))

    def test_reading_time(self):
        from .edit import spec as cut_spec

        self.assertEqual(cut_spec.read_seconds(""), 0.0)
        self.assertEqual(cut_spec.read_seconds("Ja."), round(5 / 6 + 0.9, 2))  # never under 5/6 s on screen
        self.assertEqual(cut_spec.read_seconds("Det är inte älgen du ska oroa dig för."), 4.07)  # 38 chars / 12 + 0.9

    def test_short_clip_shortens_scene_and_stills_get_motion(self):
        clip(self.company, 1.2, shots=["fa-m1"])
        still = clip(self.company, 0, shots=["fa-p5"], kind="image")
        plan = planner.plan_cut(self.company, "faiv-dark-to-light-reveal")
        self.assertEqual(scene(plan, "s1")["duration_s"], 1.15)
        self.assertEqual(scene(plan, "s5")["asset_id"], str(still.pk))
        self.assertEqual(scene(plan, "s5")["effects"][0], planner.STILL_MOTION)

    def test_fact_placeholders_only_when_verified(self):
        gk = Company.objects.create(owner=self.user, name="Golfkuponger")
        recipe = planner.load_recipe("gk-pov-hr-mail")
        notes = recipe["scenes"][-1]["notes"]
        plan = planner.Planner(gk, recipe, fmt="9:16", overrides={}, materialize=False)
        text = plan.resolve_text("Sök på Golfkuponger i din förmånsportal\n{fact:F1}", where="Scen s6", notes_text=notes)
        self.assertEqual(text, "Kolla hur mycket friskvårdsbidrag du har kvar.")  # the recipe's safe wording
        self.assertTrue(any("inte verifierat" in n for n in plan.notes))
        self.assertEqual(plan.resolve_text("1. {fact:F2}", where="x"), "")  # no safe wording → line dropped
        self.assertEqual(plan.resolve_text("Bra\n{fact:F2}", where="x"), "Bra")

        claim = "Golfkuponger finns att köpa i förmånsportaler. Nämnda i repot: Epassi, Benify/Benifex, Söderberg & Partners"
        AdFact.objects.create(company=gk, claim=claim, status="unverified")
        fresh = planner.Planner(gk, recipe, fmt="9:16", overrides={}, materialize=False)
        self.assertEqual(fresh.resolve_text("{fact:F1}", where="x"), "")
        AdFact.objects.filter(company=gk).update(status="verified")
        verified = planner.Planner(gk, recipe, fmt="9:16", overrides={}, materialize=False)
        self.assertEqual(verified.resolve_text("{fact:F1}", where="x"), claim)

    def test_product_and_free_placeholders(self):
        recipe = planner.load_recipe("faiv-product-in-nordic-context")
        CatalogProduct.objects.create(company=self.company, source="woocommerce", external_id="1",
                                      name="Lumen grillkit Volvo XC60", categories=["Grillkit"],
                                      image_urls=["https://faiv.se/img/xc60.jpg"])
        plan = planner.Planner(self.company, recipe, fmt="9:16", overrides={}, materialize=False)
        # Without {car_model} the catalog query falls back to "grillkit" and says so; unverified F4 is dropped.
        self.assertEqual(plan.resolve_text("{product} · {fact:F4}", where="s6"), "Lumen grillkit Volvo XC60")
        self.assertTrue(any("saknar {car_model}" in n for n in plan.notes))
        self.assertTrue(any("F4 är inte verifierat" in n for n in plan.notes))
        plan = planner.Planner(self.company, recipe, fmt="9:16", materialize=False,
                               overrides={"placeholders": {"car_model": "Volvo"}})
        self.assertEqual(plan.resolve_text("{product} · {fact:F4}", where="s6"), "Lumen grillkit Volvo XC60")
        self.assertEqual(plan.resolve_text("Din {car_model} – fast som från fabrik.", where="s1"),
                         "Din Volvo – fast som från fabrik.")
        empty = planner.Planner(self.company, recipe, fmt="9:16", overrides={}, materialize=False)
        self.assertEqual(empty.resolve_text("Rullar in: {car_model}", where="s1"), "")
        self.assertTrue(any("overrides.placeholders.car_model" in n for n in empty.notes))

    def test_product_image_is_pending_in_plan_and_downloaded_on_render(self):
        product = CatalogProduct.objects.create(company=self.company, source="woocommerce", external_id="1",
                                                name="Lumen grillkit Volvo XC60", categories=["Grillkit"],
                                                image_urls=["https://faiv.se/img/xc60.jpg"])
        for shots in (["fa-b4"], ["fa-b2"], ["fa-m1"], ["fa-b3"]):
            clip(self.company, 5.0, shots=shots)
        overrides = {"placeholders": {"car_model": "Volvo"}}
        plan = planner.plan_cut(self.company, "faiv-product-in-nordic-context", overrides=overrides)
        self.assertEqual(plan["missing"], [])
        self.assertEqual(plan["pending_downloads"][0]["product_id"], product.pk)
        self.assertFalse(plan["ready"])
        self.assertEqual(plan["spec"]["cta"]["text"], "Lumen grillkit Volvo XC60")
        self.assertEqual(plan["product"]["name"], "Lumen grillkit Volvo XC60")

        def fake_materialize(prod, indexes=None):
            asset = store_asset(self.company, picture())
            prod.assets.add(asset)
            return [asset]

        with mock.patch("engine.product_catalog.materialize", side_effect=fake_materialize) as download:
            plan, job = planner.render_recipe(self.company, "faiv-product-in-nordic-context", overrides=overrides)
        download.assert_called_once()
        self.assertTrue(plan["ready"])
        self.assertEqual(job.status, "queued")
        self.assertEqual(job.recipe_id, "faiv-product-in-nordic-context")
        product_scene = scene(plan, "s3")
        self.assertEqual(product_scene["text"], "Lumen grillkit Volvo XC60")
        self.assertEqual(MediaAsset.objects.get(pk=product_scene["asset_id"]).kind, "image")

    def test_render_refuses_missing_unless_allowed(self):
        clip(self.company, 6.0, shots=["fa-m1"])
        with self.assertRaisesRegex(planner.PlanError, "Material saknas för 3 scen"):
            planner.render_recipe(self.company, "faiv-dark-to-light-reveal")
        self.assertFalse(EditJob.objects.exists())
        plan, job = planner.render_recipe(self.company, "faiv-dark-to-light-reveal", allow_missing=True)
        self.assertEqual([s["id"] for s in job.cut_spec["scenes"]], ["s1", "s3"])
        self.assertIsNone(job.cut_spec["scenes"][0]["transition_in"])
        self.assertTrue(job.cut_spec["cta"])
        MediaAsset.objects.filter(company=self.company, kind="video").delete()
        with self.assertRaisesRegex(planner.PlanError, "Inget material"):
            planner.render_recipe(self.company, "faiv-dark-to-light-reveal", allow_missing=True)

    def test_lessons_remove_avoided_and_prefer_liked(self):
        gk = Company.objects.create(owner=self.user, name="Golfkuponger")
        liked = clip(gk, 4.0, shots=["gk-o1"])
        other = clip(gk, 4.0, shots=["gk-o1"])
        disliked = clip(gk, 4.0, shots=["gk-o2"])
        clip(gk, 4.0, shots=["gk-o2"])
        Lesson.objects.create(company=gk, target_type="library", target_id="hyperframes.registry.cut-the-curve",
                              target_label="Cut the curve", polarity="avoid", rule="Undvik kurvövergången")
        Lesson.objects.create(company=gk, target_type="library", target_id="hyperframes.registry.whip-pan",
                              target_label="Whip pan", polarity="prefer", rule="Mer whip pan")
        Lesson.objects.create(company=gk, target_type="library", target_id="nextphase.zak.caption",
                              target_label="Zak-caption", polarity="avoid", rule="Undvik zak-captions")
        Lesson.objects.create(company=gk, target_type="library", target_id=str(liked.pk), target_label="Kaffeklippet",
                              polarity="prefer", rule="Bra klipp")
        Lesson.objects.create(company=gk, target_type="library", target_id=str(disliked.pk), target_label="Suddigt",
                              polarity="avoid", rule="Suddigt klipp")
        Lesson.objects.create(company=gk, target_type="aspect", target_id="pacing", polarity="adjust",
                              rule="Snabbare klipp i början")
        plan = planner.plan_cut(gk, "gk-office-to-course-match-cut")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(liked.pk))
        self.assertEqual(scene(plan, "s2")["asset_id"], str(other.pk))
        self.assertEqual(scene(plan, "s2")["transition_in"], "hyperframes.registry.whip-pan")
        self.assertIsNone(scene(plan, "s1")["text_style"])
        self.assertNotIn(str(disliked.pk), [s["asset_id"] for s in plan["spec"]["scenes"]])
        applied = " ".join(a["applied"] for a in plan["lessons_applied"])
        self.assertIn("Cut the curve", applied)
        self.assertIn("Whip pan", applied)
        self.assertIn("Kaffeklippet", applied)
        self.assertIn("Suddigt", applied)
        self.assertTrue(any("Snabbare klipp i början" in n for n in plan["notes"]))
        self.assertTrue(any(n.startswith("Lärdom tillämpad") for n in plan["notes"]))
        # Golfkuponger has a brand outro: the CTA graphic is replaced by it.
        self.assertIsNone(plan["spec"]["cta"])
        self.assertTrue(any("slutbild" in n for n in plan["notes"]))

    def test_music_and_overrides(self):
        AssetTags.objects.create(asset=self.music, tags=["music"], roles=[])
        clip(self.company, 6.0, shots=["fa-m1"])
        chosen = clip(self.company, 6.0)
        plan = planner.plan_cut(self.company, "faiv-dark-to-light-reveal", format="1:1", overrides={
            "title": "Egen titel", "scenes": {"s1": {"asset_id": str(chosen.pk), "text": "Mörkt?"},
                                              "s2": {"skip": True}}})
        self.assertEqual(plan["spec"]["music_asset_id"], str(self.music.pk))
        self.assertEqual(plan["spec"]["title"], "Egen titel")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(chosen.pk))
        self.assertEqual(scene(plan, "s1")["text"], "Mörkt?")
        self.assertNotIn("s2", [s["id"] for s in plan["spec"]["scenes"]])
        self.assertEqual(plan["spec"]["format"], "1:1")
        with self.assertRaisesRegex(planner.PlanError, "okänt fält speed"):
            planner.plan_cut(self.company, "faiv-dark-to-light-reveal", overrides={"scenes": {"s1": {"speed": 2}}})
        with self.assertRaisesRegex(planner.PlanError, "receptet har ingen sådan scen"):
            planner.plan_cut(self.company, "faiv-dark-to-light-reveal", overrides={"scenes": {"s9": {}}})
        with self.assertRaisesRegex(planner.PlanError, "inte för FAIV"):
            planner.plan_cut(self.company, "gk-office-to-course-match-cut")
        with self.assertRaisesRegex(planner.PlanError, "finns inte"):
            planner.plan_cut(self.company, "finns-inte")


class RecipeMcpTests(EditTestCase):
    def call(self, name, *args, **kwargs):
        from engine import mcp_server

        token = SimpleNamespace(claims={"django_user_id": self.user.pk})
        with mock.patch("engine.mcp_auth.get_access_token", return_value=token):
            return mcp_server.mcp._tool_manager.get_tool(name).fn(str(self.company.pk), *args, **kwargs)

    def test_tools_are_registered(self):
        from asgiref.sync import async_to_sync

        from engine import mcp_server

        tools = {tool.name: tool for tool in async_to_sync(mcp_server.mcp.list_tools)()}
        for name in ("plan_cut_from_recipe", "render_recipe", "tag_media"):
            self.assertIn(name, tools)
        self.assertTrue(tools["plan_cut_from_recipe"].annotations.read_only_hint)
        self.assertFalse(tools["render_recipe"].annotations.read_only_hint)
        from engine.ad_studio.mcp import FLOW

        self.assertIn("plan_cut_from_recipe", FLOW)
        self.assertIn("render_recipe", FLOW)

    def test_tag_plan_and_render_through_mcp(self):
        from mcp.server.mcpserver.exceptions import ToolError

        with self.assertRaises(ToolError):
            self.call("tag_media", str(self.clip.pk), ["fa-nope"])
        tagged = self.call("tag_media", str(self.clip.pk), ["fa-m1"], description="Volvo, ljus av och på")
        self.assertEqual(tagged["footage_ids"], ["fa-m1"])
        self.assertEqual(tagged["tags"]["description"], "Volvo, ljus av och på")
        plan = self.call("plan_cut_from_recipe", "faiv-dark-to-light-reveal")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(self.clip.pk))
        self.assertFalse(EditJob.objects.exists())  # planning has no side effects
        with self.assertRaises(ToolError):
            self.call("render_recipe", "faiv-dark-to-light-reveal")
        result = self.call("render_recipe", "faiv-dark-to-light-reveal", allow_missing=True)
        self.assertEqual(result["job"]["status"], "queued")
        self.assertIsNone(result["job"]["ai_critique"])
        self.assertTrue(result["plan"]["missing"])


CRITIQUE = critic.CutCritique(
    score=7, summary="Stark krok men texten i s2 är för liten.",
    hook={"score": 8, "note": "Mörkret syns direkt."}, legibility={"score": 5, "note": "Liten text i s2."},
    pacing={"score": 7, "note": "Bra tempo."}, brand_fit={"score": 7, "note": "Passar FAIV."},
    fixes=[{"scene_id": "s2", "item_id": "nextphase.persa.grade", "fix": "Större text och mindre grade."},
           {"scene_id": "s9", "item_id": "påhittat", "fix": "Okänd scen."}])


class CriticTests(EditTestCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict("os.environ", {"EDIT_AI_CRITIC": "1", "OPENROUTER_API_KEY": "test-key",
                                             "EDIT_GATE_MAX_STILL_SHARE": "1"})
        env.start()
        self.addCleanup(env.stop)

    def deliver(self):
        job = service.create_job(self.company, self.spec())
        payload = self.client.post("/internal/edit/claim/", json.dumps({"worker_id": "w", "job_id": str(job.pk)}),
                                   content_type="application/json", **AUTH).json()["job"]
        with mock.patch("engine.review.discord.send") as send:
            send.side_effect = lambda review: Review.objects.filter(pk=review.pk).update(discord_message_id="1")
            response = self.client.post(f"/internal/edit/output/{job.pk}/",
                                        {"file": SimpleUploadedFile("m.mp4", movie(3.0), "video/mp4"),
                                         "meta": json.dumps({"duration_s": 3.0})},
                                        HTTP_X_EDIT_LEASE=payload["lease"], **AUTH)
        self.assertEqual(response.status_code, 200, response.content)
        job.refresh_from_db()
        return job, send

    def test_critique_is_stored_shown_on_card_and_in_get_cut_job(self):
        seen = {}

        def fake(**kwargs):
            seen.update(kwargs)
            return CRITIQUE, {"model": "google/gemini-3.1-flash-lite", "cost_usd": 0.0004}

        with mock.patch("engine.openrouter.structured_analysis", side_effect=fake):
            job, send = self.deliver()
        self.assertEqual(job.status, "done")
        data = job.ai_critique
        self.assertEqual((data["status"], data["score"]), ("done", 7))
        self.assertEqual(data["fixes"][0], {"scene_id": "s2", "item_id": "nextphase.persa.grade",
                                            "fix": "Större text och mindre grade."})
        self.assertEqual(data["fixes"][1]["scene_id"], "global")  # unknown scene ids are not trusted
        self.assertEqual(data["fixes"][1]["item_id"], "")
        self.assertEqual(data["input"], "video")  # the model watches the whole cut with sound
        self.assertEqual(len(seen["videos"]), 1)
        self.assertTrue(seen["videos"][0].startswith("data:video/mp4;base64,"))
        self.assertNotIn("images", seen)
        self.assertEqual(seen["payload"]["recipe"]["id"], "faiv-dark-to-light-reveal")
        self.assertIn("scenes", seen["payload"]["manifest"])
        self.assertIn("0–2 s", seen["system"])  # the rubric
        self.assertEqual(data["footage"]["score"], 5)  # aspects the model left out are marked unjudged
        card = discord.card(job.review)
        self.assertIn("AI-granskning 7/10", card["message"]["embeds"][0]["description"])
        self.assertIn("Större text", card["message"]["embeds"][0]["description"])
        self.assertEqual(service.serialize(job)["ai_critique"]["score"], 7)
        send.assert_called_once()

    def test_frames_when_the_video_is_refused_or_too_large(self):
        from .openrouter import OpenRouterError

        calls = []

        def video_refused(**kwargs):
            calls.append(kwargs)
            if kwargs.get("videos"):
                raise OpenRouterError("Modellen tar inte emot video.", status_code=400)
            return CRITIQUE, {"model": "m", "cost_usd": 0.0001}

        with mock.patch("engine.openrouter.structured_analysis", side_effect=video_refused):
            job, _ = self.deliver()
        self.assertEqual(len(calls), 2)
        self.assertEqual((job.ai_critique["status"], job.ai_critique["input"]), ("done", "frames"))
        self.assertTrue(calls[1]["images"][0].startswith("data:image/jpeg;base64,"))
        self.assertEqual(calls[1]["payload"]["frames"][0]["scene_id"], "s1")

        calls.clear()
        with mock.patch.dict("os.environ", {"EDIT_CRITIC_VIDEO_MAX_MB": "0.000001"}), \
                mock.patch("engine.openrouter.structured_analysis", side_effect=video_refused):
            job, _ = self.deliver()
        self.assertEqual(len(calls), 1)  # too large for the video route: straight to frames
        self.assertEqual(job.ai_critique["input"], "frames")

    def test_openrouter_sends_video_parts_to_the_video_model(self):
        from . import openrouter

        sent = {}

        def post(url, **kwargs):
            sent.update(kwargs["json"])
            return SimpleNamespace(status_code=200, json=lambda: {
                "model": "g", "choices": [{"message": {"content": CRITIQUE.model_dump_json()}}]})

        with mock.patch.object(openrouter.httpx, "post", side_effect=post), \
                mock.patch.dict("os.environ", {"OPENROUTER_VIDEO_MODEL": "google/gemini-3.1-flash"}):
            openrouter.structured_analysis(system="s", payload={}, schema=critic.CutCritique,
                                           videos=["data:video/mp4;base64,AAAA"])
        self.assertEqual(sent["model"], "google/gemini-3.1-flash")
        parts = sent["messages"][1]["content"]
        self.assertEqual(parts[1], {"type": "video_url", "video_url": {"url": "data:video/mp4;base64,AAAA"}})

    def test_critic_fails_open(self):
        from .openrouter import OpenRouterError

        with mock.patch("engine.openrouter.structured_analysis", side_effect=OpenRouterError("nere")):
            job, send = self.deliver()
        self.assertEqual(job.status, "done")
        self.assertEqual(job.ai_critique["status"], "failed")
        send.assert_called_once()
        self.assertNotIn("AI-granskning", discord.card(job.review)["message"]["embeds"][0]["description"])

        with mock.patch("engine.openrouter.structured_analysis", side_effect=RuntimeError("frames")):
            job, _ = self.deliver()
        self.assertEqual(job.ai_critique["status"], "failed")

    def test_skipped_without_key_or_when_disabled(self):
        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}), \
                mock.patch("engine.openrouter.structured_analysis") as call:
            job, _ = self.deliver()
        call.assert_not_called()
        self.assertEqual(job.ai_critique["status"], "skipped")
        with mock.patch.dict("os.environ", {"EDIT_AI_CRITIC": "0"}):
            self.assertEqual(critic.run(job, b"x")["status"], "skipped")

    def test_frames_and_vision_route(self):
        times = critic.frame_times(15.0)
        self.assertEqual(len(times), critic.FRAMES)
        self.assertEqual(times[:2], [0.3, 1.5])
        self.assertEqual(critic.frame_times(1.0), [0.3])
        frames = critic.extract_frames(movie(3.0, size=(720, 1280)), critic.frame_times(3.0))
        self.assertGreaterEqual(len(frames), 3)
        import io

        from PIL import Image

        self.assertLessEqual(max(Image.open(io.BytesIO(frames[0][1])).size), critic.FRAME_PX)

        from engine import openrouter

        tried = []

        def fake_call(model, **kwargs):
            tried.append((model, bool(kwargs.get("images"))))
            return "ok", {"model": model}

        with mock.patch.object(openrouter, "_call", side_effect=fake_call), \
                mock.patch.dict("os.environ", {"OPENROUTER_ANALYSIS_LAST_RESORT_MODEL": "google/gemini-3.1-flash-lite"}):
            openrouter.structured_analysis(system="s", payload={}, schema=critic.CutCritique, images=["data:x"])
            openrouter.structured_analysis(system="s", payload={}, schema=critic.CutCritique)
        self.assertEqual(tried[0], ("google/gemini-3.1-flash-lite", True))
        self.assertNotEqual(tried[1][0], "google/gemini-3.1-flash-lite")
        self.assertFalse(tried[1][1])

    def test_card_line(self):
        self.assertEqual(critic.card_line(None), "")
        self.assertEqual(critic.card_line({"status": "failed"}), "")
        line = critic.card_line({"status": "done", "score": 6, "summary": "Ok.", "fixes": [
            {"scene_id": "s1", "item_id": "", "fix": "Kortare krok."}]})
        self.assertEqual(line, "🤖 **AI-granskning 6/10:** Ok. Först: Kortare krok. (s1)")


def pexels_video(video_id, seconds=8, width=1080, height=1920):
    return {"id": video_id, "duration": seconds, "url": f"https://www.pexels.com/video/{video_id}/",
            "user": {"name": "Fotograf"},
            "video_files": [
                {"file_type": "video/mp4", "width": width, "height": height,
                 "link": f"https://videos.pexels.com/video-files/{video_id}/hd.mp4"},
                {"file_type": "video/mp4", "width": 3840 * 2, "height": 2160 * 2,
                 "link": f"https://videos.pexels.com/video-files/{video_id}/8k.mp4"},
                {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "https://evil.example/x.mp4"},
            ]}


class StockTests(EditTestCase):
    """Free Pexels clips stand in for mood/environment shots that have not been filmed yet."""

    def setUp(self):
        super().setUp()
        MediaAsset.objects.filter(pk__in=[self.clip.pk, self.still.pk]).delete()
        env = mock.patch.dict("os.environ", {"PEXELS_API_KEY": "test-key", "EDIT_STOCK": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.requests = []

    def pexels(self, videos):
        import httpx

        def handler(request):
            self.requests.append(str(request.url))
            if request.url.host == "api.pexels.com":
                self.assertEqual(request.headers["Authorization"], "test-key")
                return httpx.Response(200, json={"videos": videos})
            return httpx.Response(200, content=movie(4.0, size=(54, 96)))

        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_queries_only_cover_mood_shots(self):
        from .edit import stock

        self.assertEqual(stock.query_for(["fa-m4", "fa-n2"]), ("fa-n2", "moose warning road sign snow"))
        self.assertIsNone(stock.query_for(["fa-m1"]))  # product proof never comes from stock
        self.assertIsNone(stock.query_for(["fa-h1", "gk-b2", "gk-o1"]))  # customers, brand screens, match cuts
        self.assertTrue(set(stock.queries()) <= set(footage.shots()))
        chosen = stock.pick_file(pexels_video(1), "9:16")
        self.assertTrue(chosen["link"].endswith("/hd.mp4"))
        self.assertIsNone(stock.pick_file(pexels_video(1), "16:9"))  # portrait only for a portrait search

    def test_plan_lists_stock_as_pending_and_render_downloads_it(self):
        from .edit import stock

        plan = planner.plan_cut(self.company, "faiv-winter-mood")
        pending = {p["scene"]: p for p in plan["pending_downloads"]}
        self.assertEqual(pending["s1"]["footage_id"], "fa-n1")
        self.assertEqual(pending["s3"]["query"], "northern lights")
        self.assertNotIn("s4", pending)  # fa-m2 (light on in snow) is product proof
        self.assertIn("s4", {m["scene"] for m in plan["missing"]})
        self.assertTrue(any("Pexels" in n and "Filma fa-n1" in n for n in plan["notes"]))
        self.assertFalse(self.requests)  # planning alone never calls Pexels

        videos = [pexels_video(11), pexels_video(12), pexels_video(13, seconds=1), pexels_video(14)]
        with mock.patch.object(stock, "_client", side_effect=lambda: self.pexels(videos)):
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        s1, s3 = scene(plan, "s1"), scene(plan, "s3")
        self.assertNotEqual(s1["asset_id"], s3["asset_id"])
        asset = MediaAsset.objects.get(pk=s1["asset_id"])
        self.assertEqual((asset.kind, asset.provider), ("video", "pexels"))
        self.assertEqual(asset.ad_tags.tags, ["fa-n1"])
        self.assertEqual(asset.ad_tags.roles, ["footage", "stock"])
        self.assertIn("Fotograf", asset.ad_tags.source)
        self.assertFalse(any("evil.example" in u or "8k" in u for u in self.requests))
        self.assertIn("Pexels", next(c["why"] for c in plan["choices"] if c["scene"] == "s1"))

        # Next time the downloaded clip is reused without a new download, and own film of the shot wins over it.
        self.requests.clear()
        plan = planner.plan_cut(self.company, "faiv-winter-mood")
        self.assertEqual(scene(plan, "s1")["asset_id"], s1["asset_id"])
        own = clip(self.company, 6.0, shots=["fa-n1"])
        plan = planner.plan_cut(self.company, "faiv-winter-mood")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(own.pk))

    def test_stock_film_beats_an_own_still_of_a_mood_shot(self):
        from .edit import stock

        still = clip(self.company, 0, shots=["fa-n3"], kind="image")
        with mock.patch.object(stock, "_client", side_effect=lambda: self.pexels([pexels_video(i) for i in (21, 22, 23)])):
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        self.assertNotEqual(scene(plan, "s3")["asset_id"], str(still.pk))
        self.assertTrue(any("bara en stillbild" in n for n in plan["notes"]))

    def test_without_key_nothing_changes(self):
        with mock.patch.dict("os.environ", {"PEXELS_API_KEY": ""}):
            plan = planner.plan_cut(self.company, "faiv-winter-mood")
        self.assertFalse(plan["pending_downloads"])
        self.assertIn("s1", {m["scene"] for m in plan["missing"]})

    def test_pexels_errors_fall_back_to_missing(self):
        import httpx

        from .edit import stock

        def failing():
            return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429)))

        with mock.patch.object(stock, "_client", side_effect=failing):
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        self.assertIn("s1", {m["scene"] for m in plan["missing"]})


class GateTests(EditTestCase):
    """The quality gate holds weak cuts back from Discord: AI score under 7 or mostly still images."""

    deliver = CriticTests.deliver

    def setUp(self):
        super().setUp()
        env = mock.patch.dict("os.environ", {"EDIT_AI_CRITIC": "1", "OPENROUTER_API_KEY": "test-key",
                                             "EDIT_GATE_MAX_STILL_SHARE": "0.5"})
        env.start()
        self.addCleanup(env.stop)

    def critique(self, score):
        return lambda **_: (CRITIQUE.model_copy(update={"score": score}), {"model": "m", "cost_usd": 0})

    def test_assess(self):
        from .edit import gate

        spec = {"scenes": [{"duration_s": 2, "asset_kind": "video"}, {"duration_s": 3, "asset_kind": "image"}]}
        self.assertEqual(gate.still_share(spec), 0.6)
        result = gate.assess(spec, {"status": "done", "score": 6})
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["reasons"]), 2)
        self.assertIn("6/10", result["reasons"][0])
        self.assertIn("60 %", result["reasons"][1])
        film = {"scenes": [{"duration_s": 4, "asset_kind": "video"}, {"duration_s": 1, "asset_kind": "image"}]}
        self.assertTrue(gate.assess(film, {"status": "done", "score": 7})["passed"])
        self.assertTrue(gate.assess(film, {"status": "failed"})["passed"])  # no critique: judged on stills only
        with mock.patch.dict("os.environ", {"EDIT_QUALITY_GATE": "0"}):
            self.assertTrue(gate.assess(spec, {"status": "done", "score": 2})["passed"])

    def test_low_score_is_held_back_until_sent_anyway(self):
        with mock.patch.dict("os.environ", {"EDIT_GATE_MAX_STILL_SHARE": "1"}), \
                mock.patch("engine.openrouter.structured_analysis", side_effect=self.critique(5)):
            job, send = self.deliver()
        send.assert_not_called()
        self.assertEqual(job.status, "done")
        self.assertFalse(job.quality_gate["passed"])
        data = service.serialize(job)
        self.assertIn("Behöver omtag", data["next_step"])
        self.assertIn("5/10", data["next_step"])
        self.assertIn("Större text", data["next_step"])
        self.assertFalse(data["discord_posted"])
        with mock.patch("engine.review.discord.send") as later:
            self.assertEqual(service.recover(redispatch=False)["discord"], 0)
            later.assert_not_called()
            later.side_effect = lambda review: Review.objects.filter(pk=review.pk).update(discord_message_id="9")
            job = service.send_anyway(self.company, job.pk)
            later.assert_called_once()
        self.assertTrue(job.quality_gate["override"])
        job.review.refresh_from_db()
        self.assertTrue(service.serialize(job)["discord_posted"])

    def test_mostly_stills_is_held_back_even_with_a_good_score(self):
        with mock.patch("engine.openrouter.structured_analysis", side_effect=self.critique(8)):
            job, send = self.deliver()
        send.assert_not_called()
        self.assertIn("stillbilder", " ".join(job.quality_gate["reasons"]))

    def test_render_meta_is_kept_and_manifest_follows_snapped_beats(self):
        with mock.patch("engine.openrouter.structured_analysis", side_effect=self.critique(8)), \
                mock.patch.dict("os.environ", {"EDIT_GATE_MAX_STILL_SHARE": "1"}):
            job = service.create_job(self.company, self.spec())
            payload = self.client.post("/internal/edit/claim/", json.dumps({"worker_id": "w", "job_id": str(job.pk)}),
                                       content_type="application/json", **AUTH).json()["job"]
            meta = {"duration_s": 7.4, "qa": {"black_s": 0, "loudness_lufs": -14.1}, "sfx": ["impact@0"],
                    "beats": {"bpm": 120, "snaps": [{"after": "s1", "from": 2.0, "to": 1.9, "delta": -0.1}]},
                    "unknown": "dropped"}
            with mock.patch("engine.review.discord.send") as send:
                send.side_effect = lambda review: Review.objects.filter(pk=review.pk).update(discord_message_id="1")
                self.client.post(f"/internal/edit/output/{job.pk}/",
                                 {"file": SimpleUploadedFile("m.mp4", movie(3.0), "video/mp4"), "meta": json.dumps(meta)},
                                 HTTP_X_EDIT_LEASE=payload["lease"], **AUTH)
        job.refresh_from_db()
        render = service.serialize(job)["render"]
        self.assertEqual(render["qa"]["loudness_lufs"], -14.1)
        self.assertEqual(render["beats"]["bpm"], 120)
        self.assertNotIn("unknown", render)
        scenes = job.review.manifest["scenes"]
        self.assertEqual((scenes[0]["end"], scenes[1]["start"]), (1.9, 1.9))
        send.assert_called_once()

    def test_send_anyway_tool_is_registered(self):
        from engine import mcp_server

        self.assertIsNotNone(mcp_server.mcp._tool_manager.get_tool("send_cut_for_review"))


def textured(seconds=4.0, *, size=(180, 320), speed=1, blur=0.0, cut_at=None, frozen=False, brightness=1.0, seed=1):
    """A clip of drifting random texture (reads like handheld footage to the shot scorer)."""
    import numpy as np
    from PIL import ImageFilter

    rng = np.random.default_rng(seed)

    def scenery():  # soft blobs with fine detail on top: shifts a little per frame like a slow camera move
        blobs = Image.fromarray(rng.integers(0, 255, (size[1] // 8, size[0] // 8, 3), dtype=np.uint8))
        blobs = np.asarray(blobs.resize((size[0] * 2, size[1] * 2), Image.Resampling.BICUBIC), dtype=np.int16)
        detail = rng.integers(-30, 30, blobs.shape, dtype=np.int16)
        return (blobs + detail).clip(0, 255).astype(np.uint8)

    base, other = scenery(), (scenery() * 0.4).astype(np.uint8)  # the second shot is a darker scene
    out = io.BytesIO()
    fps = 10
    with av.open(out, mode="w", format="mp4") as container:
        stream = container.add_stream("libx264", rate=fps)
        stream.width, stream.height, stream.pix_fmt = size[0], size[1], "yuv420p"
        for i in range(int(seconds * fps)):
            src = other if cut_at is not None and i / fps >= cut_at else base
            shift = 0 if frozen else i * speed
            crop = src[shift % size[1]:shift % size[1] + size[1], shift % size[0]:shift % size[0] + size[0]]
            image = Image.fromarray((crop * brightness).clip(0, 255).astype("uint8")).filter(
                ImageFilter.GaussianBlur(blur)) if blur or brightness != 1.0 else Image.fromarray(crop)
            for packet in stream.encode(av.VideoFrame.from_image(image)):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return out.getvalue()


class ShotScoringTests(EditTestCase):
    def test_moving_sharp_footage_beats_frozen_blurred_and_dark(self):
        from .edit import shots

        def score(data, **kw):
            return shots.best_window(shots.analyze(data), 2.0, **kw)["score"]

        good = score(textured())
        self.assertGreater(good, score(textured(frozen=True)))
        self.assertGreater(good, score(textured(blur=4)))
        self.assertGreater(good, score(textured(brightness=0.25)))
        self.assertGreater(score(textured(brightness=0.25), dark_ok=True), score(textured(brightness=0.25)))
        self.assertEqual(shots.analyze(b"not a video"), {})
        self.assertIsNone(shots.best_window({}, 2.0))

    def test_best_window_skips_the_cut_between_two_shots(self):
        from .edit import shots

        analysis = shots.analyze(textured(5.0, cut_at=2.0))
        self.assertTrue(shots.cuts(analysis))
        window = shots.best_window(analysis, 2.0)
        self.assertFalse(window["cut_inside"])
        self.assertTrue(window["start"] >= 1.9 or window["end"] <= 2.1, window)
        self.assertFalse(shots.cuts(shots.analyze(textured(5.0, speed=6))))  # fast movement is not a cut
        self.assertIsNotNone(shots.frame_jpeg(textured(), 1.0))


class StockSelectionTests(EditTestCase):
    """Several stock candidates are scored; only the winner is downloaded in full and placed at its best window."""

    def setUp(self):
        super().setUp()
        MediaAsset.objects.filter(pk__in=[self.clip.pk, self.still.pk]).delete()
        env = mock.patch.dict("os.environ", {"PEXELS_API_KEY": "test-key", "EDIT_STOCK": "1",
                                             "OPENROUTER_API_KEY": "test-key", "EDIT_STOCK_CANDIDATES": "3"})
        env.start()
        self.addCleanup(env.stop)
        self.downloads = []

    def pexels(self, clips):
        import httpx

        videos = []
        for video_id in clips:
            video = pexels_video(video_id)
            video["video_files"].append({"file_type": "video/mp4", "width": 360, "height": 640,
                                         "link": f"https://videos.pexels.com/video-files/{video_id}/sd.mp4"})
            videos.append(video)

        def handler(request):
            if request.url.host == "api.pexels.com":
                return httpx.Response(200, json={"videos": videos})
            video_id = int(request.url.path.split("/")[2])
            self.downloads.append(request.url.path)
            return httpx.Response(200, content=clips[video_id])

        return lambda: httpx.Client(transport=httpx.MockTransport(handler))

    def test_judge_and_technique_pick_the_winner_and_its_best_window(self):
        from .edit import stock

        clips = {31: textured(6.0, frozen=True, seed=3), 32: textured(6.0, cut_at=1.0, seed=4),
                 33: textured(6.0, blur=4, seed=5), 34: textured(6.0, seed=6)}
        verdict = stock.Pick(scores=[4, 9, 6], why="Tydligast och mest äkta.")
        with mock.patch.object(stock, "_client", side_effect=self.pexels(clips)), \
                mock.patch("engine.openrouter.structured_analysis", return_value=(verdict, {"cost_usd": 0.0001})) as call:
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        s1 = scene(plan, "s1")
        asset = MediaAsset.objects.get(pk=s1["asset_id"])
        self.assertEqual(asset.pk, stock_id(self.company, 32))
        self.assertIn("Valt bland 3 kandidater", asset.brief)
        self.assertIn("Tydligast", asset.brief)
        first = call.call_args_list[0].kwargs  # s1; later scenes judge the clips that are left
        self.assertEqual(len(first["images"]), 3)
        self.assertIn("Vinterväg", first["payload"]["scene"])
        self.assertIn("Vintermörker", first["payload"]["film"])  # judged against the film's mood, not just the shot
        highlight = asset.ad_tags.highlights[0]
        self.assertEqual(highlight["judge"], 9)
        self.assertGreaterEqual(highlight["start"], 0.9)  # after the cut at 1.0 s
        self.assertEqual(s1["trim_start_s"], highlight["start"])
        self.assertIn("bästa fönstret", next(c["why"] for c in plan["choices"] if c["scene"] == "s1"))
        full = [p for p in self.downloads if p.endswith("/hd.mp4")]
        self.assertIn("/video-files/32/hd.mp4", full)
        self.assertNotIn("/video-files/31/hd.mp4", full)  # losers are only downloaded small

    def test_a_missing_scene_beats_a_wrong_one(self):
        from .edit import stock

        clips = {51: textured(6.0, seed=10), 52: textured(6.0, seed=11)}
        wrong = stock.Pick(scores=[3, 2], why="Busshållplatsskylt i sommarsol, inte en älgskylt i vinter.")
        with mock.patch.object(stock, "_client", side_effect=self.pexels(clips)), \
                mock.patch("engine.openrouter.structured_analysis", return_value=(wrong, {})):
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        self.assertIn("s1", {m["scene"] for m in plan["missing"]})
        self.assertFalse(plan["spec"]["scenes"])
        self.assertTrue(any("hellre än att visa fel bild" in n for n in plan["notes"]))
        self.assertFalse([p for p in self.downloads if p.endswith("/hd.mp4")])

    def test_a_stock_clip_the_judge_never_passed_is_not_reused(self):
        from .edit import stock

        old = clip(self.company, 6.0, shots=["fa-n1"])
        MediaAsset.objects.filter(pk=old.pk).update(provider="pexels")  # picked before the judge existed
        AssetTags.objects.filter(asset=old).update(roles=["footage", "stock"])
        good = stock.Pick(scores=[8], why="Snöig nattväg.")
        with mock.patch.object(stock, "_client", side_effect=self.pexels({61: textured(6.0, seed=12)})), \
                mock.patch("engine.openrouter.structured_analysis", return_value=(good, {})):
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        self.assertEqual(scene(plan, "s1")["asset_id"], str(stock_id(self.company, 61)))
        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}):  # no judge to ask: old picks stay usable
            self.assertTrue(stock.acceptable(MediaAsset.objects.select_related("ad_tags").get(pk=old.pk)))

    def test_without_judge_technique_decides(self):
        from .edit import stock

        clips = {41: textured(6.0, frozen=True, seed=7), 42: textured(6.0, seed=8), 43: textured(6.0, blur=4, seed=9)}
        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}), \
                mock.patch.object(stock, "_client", side_effect=self.pexels(clips)):
            plan = planner.plan_cut(self.company, "faiv-winter-mood", materialize=True)
        self.assertEqual(scene(plan, "s1")["asset_id"], str(stock_id(self.company, 42)))


def stock_id(company, video_id, fmt="9:16"):
    import uuid

    return uuid.uuid5(uuid.NAMESPACE_URL, f"{company.pk}:pexels:{video_id}:{fmt}")


class EditRecipeCommandTests(EditTestCase):
    def test_plans_queues_and_writes_the_report(self):
        from django.core.management import call_command

        clip(self.company, 6.0, shots=["fa-m1"])
        out = Path(self.tmp.name) / "recipe-out"
        call_command("edit_recipe", company="faiv", recipe="faiv-dark-to-light-reveal", wait=0, out=str(out),
                     stdout=io.StringIO())
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["plan"]["recipe_id"], "faiv-dark-to-light-reveal")
        self.assertEqual(report["job"]["status"], "queued")
        self.assertTrue(report["plan"]["missing"])  # cut anyway (allow_missing) so the test shows what is there
        self.assertFalse((out / "master.mp4").exists())
