"""Recipe → cut spec planner, shot-list tagging, the recipe MCP tools and the AI critic of finished cuts."""

import json
from types import SimpleNamespace
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

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
        only = clip(self.company, 6.0, shots=["fa-m1"])
        plan = planner.plan_cut(self.company, "faiv-dark-to-light-reveal")
        self.assertEqual(scene(plan, "s1")["asset_id"], str(only.pk))
        self.assertEqual(scene(plan, "s3")["asset_id"], str(only.pk))
        self.assertEqual(scene(plan, "s3")["trim_start_s"], 3.0)  # continues where s1 ended (lights on)
        self.assertTrue(any("samma klipp" in n for n in plan["notes"]))

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
        self.assertTrue(1 <= len(seen["images"]) <= critic.FRAMES)
        self.assertTrue(seen["images"][0].startswith("data:image/jpeg;base64,"))
        self.assertEqual(seen["payload"]["frames"][0]["scene_id"], "s1")
        self.assertEqual(seen["payload"]["recipe"]["id"], "faiv-dark-to-light-reveal")
        self.assertIn("scenes", seen["payload"]["manifest"])
        card = discord.card(job.review)
        self.assertIn("AI-granskning 7/10", card["message"]["embeds"][0]["description"])
        self.assertIn("Större text", card["message"]["embeds"][0]["description"])
        self.assertEqual(service.serialize(job)["ai_critique"]["score"], 7)
        send.assert_called_once()

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
