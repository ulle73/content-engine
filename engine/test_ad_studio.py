import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from .ad_studio import blueprints, service, skills
from .media import store_asset
from .models import Company
from .motion.models import MotionProject


def picture():
    import io

    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", (1080, 1920), "green").save(out, "PNG")
    return out.getvalue()


class AdStudioBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ad-studio")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger", profile="Golf")
        self.assets = {name: store_asset(self.company, picture()) for name in ["hook", "portal", "purchase", "app", "proof"]}

    def storyboard(self):
        bp = blueprints.blueprint("friskvard-portal-ad")
        texts = {
            "hook": "DITT FRISKVÅRDSBIDRAG / BRINNER INNE",
            "portal": "SÖK GOLFKUPONGER / I DIN PORTAL",
            "purchase": "VÄLJ BELOPP",
            "app": "KODEN HAMNAR I APPEN",
            "proof": "MER GOLF NÄSTA SÄSONG",
            "end": "GÖR BIDRAGET TILL GOLF",
        }
        scenes = []
        for slot in bp["scenes"]:
            scene = {"id": slot["id"], "purpose": slot["purpose"], "duration_s": slot["duration_s"],
                     "on_screen_text": texts[slot["id"]]}
            if slot["needs_asset"]:
                scene["asset_id"] = str(self.assets[slot["id"]].pk)
            scenes.append(scene)
        return {
            "objective": "conversion",
            "audience": "Golfare med friskvårdsbidrag kvar",
            "angle": {"title": "Pengarna försvinner", "hook": "DITT FRISKVÅRDSBIDRAG BRINNER INNE"},
            "assets": [{"asset_id": str(a.pk), "role": "screen" if k in {"portal", "purchase", "app"} else "footage"}
                       for k, a in self.assets.items()],
            "engine": {"engine": "remotion", "remotion_template_id": "friskvard-portal-ad"},
            "duration_s": bp["duration_s"],
            "scenes": scenes,
            "copy": {"headline": "Golf för friskvårdsbidraget"},
        }



class AdStudioFlowTests(AdStudioBase):
    def test_blueprint_exposes_portal_template_scenes(self):
        bp = blueprints.blueprint("friskvard-portal-ad")
        self.assertEqual([s["id"] for s in bp["scenes"]], ["hook", "portal", "purchase", "app", "proof", "end"])
        self.assertEqual(bp["duration_s"], 15)
        self.assertEqual(bp["scenes"][0]["purpose"], "hook")
        self.assertEqual(bp["scenes"][-1]["purpose"], "cta")

    def test_full_flow_from_message_to_motion_project(self):
        draft = service.start_draft(self.company, self.user, message="Använd friskvårdsbidraget innan det brinner inne")
        data = service.serialize(draft)
        self.assertEqual(data["missing"][0], "objective")
        self.assertIsNotNone(data["next_question"])

        draft = service.update_draft(self.company, draft.pk, changes=self.storyboard(), expected_revision=1)
        self.assertTrue(service.serialize(draft)["lockable"], service.serialize(draft)["problems"])

        draft = service.lock_draft(self.company, draft.pk, expected_revision=draft.revision)
        self.assertEqual(draft.status, "locked")

        result = service.produce(self.company, self.user, draft.pk, key=str(uuid.uuid4()))
        self.assertEqual(result["status"], "motion_project_created")
        project = MotionProject.objects.get(pk=result["motion_project_id"])
        spec = project.revisions.get(number=1).spec
        self.assertEqual(spec["scenes"][0]["props"]["headline"], "DITT FRISKVÅRDSBIDRAG\nBRINNER INNE")
        self.assertEqual(spec["scenes"][1]["props"]["asset_id"], str(self.assets["portal"].pk))
        # No unverified template defaults leak into the ad.
        self.assertNotIn("300+", str(spec))
        self.assertNotIn("31/12", str(spec))

    def test_missing_text_blocks_lock_instead_of_using_template_default(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        board = self.storyboard()
        board["scenes"][4]["on_screen_text"] = ""
        draft = service.update_draft(self.company, draft.pk, changes=board, expected_revision=1)
        with self.assertRaisesMessage(ValueError, "standardtext"):
            service.lock_draft(self.company, draft.pk, expected_revision=draft.revision)

    def test_stale_revision_is_rejected(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        with self.assertRaisesMessage(ValueError, "ändrats"):
            service.update_draft(self.company, draft.pk, changes={"audience": "x"}, expected_revision=5)

    def test_unknown_asset_rejected(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        with self.assertRaisesMessage(ValueError, "finns inte"):
            service.update_draft(self.company, draft.pk, changes={"assets": [{"asset_id": str(uuid.uuid4()), "role": "hook"}]},
                                 expected_revision=1)

    def test_locked_brief_cannot_be_edited_and_unlocked_can(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        draft = service.update_draft(self.company, draft.pk, changes=self.storyboard(), expected_revision=1)
        draft = service.lock_draft(self.company, draft.pk, expected_revision=draft.revision)
        with self.assertRaisesMessage(ValueError, "låst"):
            service.update_draft(self.company, draft.pk, changes={"audience": "x"}, expected_revision=draft.revision)
        draft = service.reopen_draft(self.company, draft.pk)
        self.assertEqual(draft.status, "draft")

    def test_produce_requires_lock(self):
        draft = service.start_draft(self.company, self.user, message="Test")
        with self.assertRaisesMessage(ValueError, "låst"):
            service.produce(self.company, self.user, draft.pk, key="k")

    def test_other_company_cannot_read_draft(self):
        other = Company.objects.create(owner=self.user, name="Annat", profile="x")
        draft = service.start_draft(self.company, self.user, message="Test")
        with self.assertRaises(ValueError):
            service.get_draft(other, draft.pk)

    def test_tag_and_search_bank(self):
        service.tag_asset(self.company, self.assets["hook"].pk, description="Golfare slår ut i morgonljus",
                          tags=["golf", "morgon", "utslag"], roles=["hook"], theme="friskvard", mood="lugn")
        service.tag_asset(self.company, self.assets["portal"].pk, description="Skärminspelning Epassi-portal",
                          tags=["portal", "epassi"], roles=["screen"], theme="friskvard", source="Epassi")
        result = service.search_assets(self.company, query="morgon golf", role="hook")
        self.assertEqual(result["results"][0]["id"], str(self.assets["hook"].pk))
        self.assertEqual(result["untagged_count"], 3)
        screens = service.search_assets(self.company, query="epassi")
        self.assertEqual([r["id"] for r in screens["results"]], [str(self.assets["portal"].pk)])

    def test_bad_role_rejected(self):
        with self.assertRaisesMessage(ValueError, "Okända roller"):
            service.tag_asset(self.company, self.assets["hook"].pk, description="x", tags=[], roles=["hero"])

    def test_skills_are_readable(self):
        names = {s["name"] for s in skills.available()}
        self.assertTrue({"golfkuponger-brand", "golfkuponger-friskvard"} <= names)
        self.assertIn("Faktabank", skills.read("golfkuponger-friskvard"))
        with self.assertRaises(ValueError):
            skills.read("../settings")


class AdStudioVisualTests(AdStudioBase):
    def _draft(self):
        draft = service.start_draft(self.company, self.user, message="Använd friskvårdsbidraget innan det brinner inne")
        return service.update_draft(self.company, draft.pk, changes=self.storyboard(), expected_revision=1)

    def _is_jpeg(self, data):
        import io as _io

        from PIL import Image as PILImage
        image = PILImage.open(_io.BytesIO(data))
        self.assertEqual(image.format, "JPEG")
        return image

    def test_storyboard_image_has_one_panel_per_scene(self):
        image = self._is_jpeg(service.storyboard_image(self.company, self._draft().pk))
        self.assertGreater(image.width, 6 * 270)

    def test_storyboard_requires_scenes(self):
        draft = service.start_draft(self.company, self.user, message="x")
        with self.assertRaisesMessage(ValueError, "inga scener"):
            service.storyboard_image(self.company, draft.pk)

    def test_picker_sheet(self):
        ids = [str(a.pk) for a in self.assets.values()]
        self._is_jpeg(service.show_images(self.company, ids, title="Hook-kandidater"))
        with self.assertRaises(ValueError):
            service.show_images(self.company, [str(uuid.uuid4())])

    def test_add_image_stores_tags_and_attaches(self):
        import base64
        draft = service.start_draft(self.company, self.user, message="x")
        data = base64.b64encode(picture()).decode()
        draft, asset = service.add_image(self.company, self.user, draft.pk, image_base64="data:image/png;base64," + data,
                                         role="hook", description="Golfare i motljus", tags=["golf"],
                                         expected_revision=1)
        self.assertEqual(draft.revision, 2)
        self.assertEqual(draft.brief["assets"][0]["asset_id"], str(asset.pk))
        self.assertTrue(asset.ad_tags.verified)
        # Same bytes again: deduplicated, not attached twice.
        draft, again = service.add_image(self.company, self.user, draft.pk, image_base64=data, role="hook",
                                         description="Golfare", tags=[], expected_revision=2)
        self.assertEqual(again.pk, asset.pk)
        self.assertEqual(len(draft.brief["assets"]), 1)

    def test_add_image_rejects_garbage(self):
        draft = service.start_draft(self.company, self.user, message="x")
        with self.assertRaisesMessage(ValueError, "base64"):
            service.add_image(self.company, self.user, draft.pk, image_base64="!!!", role="hook", description="x",
                              tags=[], expected_revision=1)

    def test_suggestions_per_template_slot(self):
        for name, role in [("hook", "hook"), ("portal", "screen"), ("proof", "proof")]:
            service.tag_asset(self.company, self.assets[name].pk, description=name, tags=["friskvård"], roles=[role])
        draft = service.start_draft(self.company, self.user, message="friskvård brinner inne")
        draft = service.update_draft(self.company, draft.pk, expected_revision=1, changes={
            "engine": {"engine": "remotion", "remotion_template_id": "friskvard-portal-ad"}})
        result = service.suggest_scene_assets(self.company, draft.pk)
        by_scene = {s["scene_id"]: s for s in result["scenes"]}
        self.assertEqual(by_scene["hook"]["candidates"][0]["id"], str(self.assets["hook"].pk))
        self.assertEqual(by_scene["portal"]["candidates"][0]["id"], str(self.assets["portal"].pk))
        self.assertNotIn("end", by_scene)  # end card needs no picture

    def test_review_requires_production(self):
        with self.assertRaisesMessage(ValueError, "produce_ad"):
            service.review_image(self.company, self._draft().pk)


class AdStudioSkillTests(TestCase):
    def test_process_skill_available(self):
        self.assertIn("ad-studio", {s["name"] for s in skills.available()})
        self.assertIn("Förslag före frågor", skills.read("ad-studio"))
