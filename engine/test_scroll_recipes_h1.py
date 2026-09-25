from django.test import SimpleTestCase

from .creative_core import CreativeBrief, CreativeContext, EvidenceLevel, ReferenceRole, RECIPE_REGISTRY_VERSION
from .creative_director import compile_parameters, compile_prompt, eligible_models, route_model
from .creative_recipes import get_recipe, registry as recipe_registry, resolve_recipe
from .creative_registry import get_model


SCROLL_RECIPE_IDS = (
    "scroll_orbit_hero",
    "scroll_dolly_reveal",
    "scroll_macro_flythrough",
    "scroll_exploded_reveal",
    "scroll_environment_transition",
    "scroll_transition_bridge",
    "scroll_product_showcase",
    "scroll_landscape_flythrough",
)


class ScrollRecipeFamilyH1Tests(SimpleTestCase):
    def setUp(self):
        self.context = CreativeContext(
            company_name="Golfkuponger",
            profile="Golf vouchers",
            voice="Premium",
            current_facts="Current facts",
        )
        self.brief = CreativeBrief(
            user_intent="Create one premium continuous scroll shot between the supplied anchors.",
            kind="video",
            mode="image-to-video",
            platform="web",
            environment="A premium golf environment with readable foreground and background depth",
            visual_style=["premium cinematic", "photoreal"],
            realism="natural materials",
            camera_movement=["controlled motion"],
            duration_seconds=5,
            aspect_ratio="16:9",
            resolution="720p",
            audio_intent="none",
            reference_media=[ReferenceRole.start_image.value, ReferenceRole.end_image.value],
            preserve=["hero subject geometry", "lighting direction"],
        )

    def test_registry_contains_complete_h1_family_with_required_contracts(self):
        recipes = {item.recipe_id: item for item in recipe_registry()}
        self.assertEqual(set(SCROLL_RECIPE_IDS) - set(recipes), set())
        self.assertEqual(RECIPE_REGISTRY_VERSION, "2026-09-25.2")

        for recipe_id in SCROLL_RECIPE_IDS:
            recipe = recipes[recipe_id]
            self.assertEqual(recipe.kinds, ("video",))
            self.assertEqual(recipe.supported_modes, ("image-to-video",))
            self.assertEqual(
                recipe.required_reference_roles,
                (ReferenceRole.start_image, ReferenceRole.end_image),
            )
            self.assertEqual(
                set(recipe.required_model_capabilities),
                {"reference_animation", "single_continuous_shot", "first_last_frame"},
            )
            self.assertIn("scroll", recipe.format_tags)
            self.assertIn("scrub_friendly", recipe.format_tags)
            self.assertTrue(recipe.camera_strategy)
            self.assertTrue(recipe.motion_strategy)
            self.assertTrue(recipe.continuity_strategy)
            self.assertTrue(recipe.negative_constraints)
            self.assertTrue(recipe.evaluation_rules)
            self.assertTrue(recipe.good_result_criteria)
            self.assertTrue(recipe.bad_result_signals)
            self.assertTrue(recipe.evidence_sources)
            self.assertEqual(recipe.verified_at, "2026-09-25")
            self.assertIn(recipe.evidence_level, {EvidenceLevel.official, EvidenceLevel.verified})

    def test_every_scroll_recipe_routes_only_to_verified_first_last_frame_models(self):
        for recipe_id in SCROLL_RECIPE_IDS:
            with self.subTest(recipe_id=recipe_id):
                recipe, selection = resolve_recipe(self.brief, recipe_id=recipe_id)
                candidates = eligible_models(self.brief, recipe=recipe)
                ids = {model.model_id for model in candidates}
                self.assertTrue({"bytedance/seedance-2.5", "bytedance/seedance-2.0"} <= ids)
                self.assertNotIn("kling-video/v2.5-turbo/pro", ids)
                for model in candidates:
                    self.assertTrue(set(recipe.required_model_capabilities) <= set(model.recipe_capabilities))
                _, routed = route_model(self.brief, self.brief_complexity(), recipe=recipe)
                self.assertIn("recipe_capabilities_supported", routed.reason_codes)
                self.assertEqual(selection.registry_version, RECIPE_REGISTRY_VERSION)

    def brief_complexity(self):
        from .creative_director import analyze_complexity
        return analyze_complexity(self.brief)

    def test_seedance_25_compiles_every_recipe_with_exact_scroll_and_endpoint_contract(self):
        model = get_model("higgsfield", "bytedance/seedance-2.5")
        self.assertIsNotNone(model)
        for recipe_id in SCROLL_RECIPE_IDS:
            with self.subTest(recipe_id=recipe_id):
                recipe = get_recipe(recipe_id)
                prompt = compile_prompt(self.brief, self.context, model, [], recipe=recipe)
                self.assertIn("FORMAT MODE: Single continuous shot.", prompt)
                self.assertIn("forward and backward scroll scrubbing", prompt)
                self.assertIn("FIRST FRAME AND BLOCKING:", prompt)
                self.assertIn("END FRAME:", prompt)
                self.assertIn(recipe.camera_strategy[0], prompt)
                self.assertIn(recipe.motion_strategy[0], prompt)
                self.assertIn(recipe.continuity_strategy[0], prompt)
                self.assertIn("FORBID:", prompt)
                self.assertIn(recipe.negative_constraints[0], prompt)
                params, issues = compile_parameters(self.brief, model, count=1, shape="landscape")
                self.assertEqual(params["provider_model"], "bytedance/seedance-2.5/image-to-video")
                self.assertEqual(params["reference_fields"][ReferenceRole.start_image.value], "image_url")
                self.assertEqual(params["reference_fields"][ReferenceRole.end_image.value], "end_image_url")
                self.assertEqual(params["resolution"], "720p")
                self.assertFalse(params["generate_audio"])
                self.assertFalse([item for item in issues if item.severity == "error"])

    def test_seedance_20_compiles_every_recipe_with_exact_scroll_and_endpoint_contract(self):
        model = get_model("higgsfield", "bytedance/seedance-2.0")
        self.assertIsNotNone(model)
        for recipe_id in SCROLL_RECIPE_IDS:
            with self.subTest(recipe_id=recipe_id):
                recipe = get_recipe(recipe_id)
                prompt = compile_prompt(self.brief, self.context, model, [], recipe=recipe)
                self.assertIn("FORMAT MODE: Single continuous shot.", prompt)
                self.assertIn("FIRST FRAME AND BLOCKING:", prompt)
                self.assertIn("END FRAME:", prompt)
                self.assertIn(recipe.camera_strategy[0], prompt)
                self.assertIn(recipe.motion_strategy[0], prompt)
                self.assertIn(recipe.continuity_strategy[0], prompt)
                params, issues = compile_parameters(self.brief, model, count=1, shape="landscape")
                self.assertEqual(params["provider_model"], "bytedance/seedance-2.0/image-to-video")
                self.assertEqual(params["reference_fields"][ReferenceRole.start_image.value], "image_url")
                self.assertEqual(params["reference_fields"][ReferenceRole.end_image.value], "end_image_url")
                self.assertEqual(params["resolution"], "720p")
                self.assertFalse(params["generate_audio"])
                self.assertFalse([item for item in issues if item.severity == "error"])

    def test_recipe_specific_methods_are_not_one_generic_prompt(self):
        model = get_model("higgsfield", "bytedance/seedance-2.5")
        prompts = {}
        for recipe_id in SCROLL_RECIPE_IDS:
            recipe = get_recipe(recipe_id)
            prompts[recipe_id] = compile_prompt(self.brief, self.context, model, [], recipe=recipe)
        self.assertEqual(len(set(prompts.values())), len(SCROLL_RECIPE_IDS))
        self.assertIn("orbital camera move", prompts["scroll_orbit_hero"])
        self.assertIn("digital zoom", prompts["scroll_dolly_reveal"])
        self.assertIn("camera clipping through solid surfaces", prompts["scroll_macro_flythrough"])
        self.assertIn("component identity", prompts["scroll_exploded_reveal"])
        self.assertIn("persistent landmarks", prompts["scroll_environment_transition"])
        self.assertIn("motion over spectacle", " ".join(get_recipe("scroll_transition_bridge").motion_strategy))
        self.assertIn("label hallucination", prompts["scroll_product_showcase"])
        self.assertIn("terrain morphing", prompts["scroll_landscape_flythrough"])

    def test_missing_end_anchor_fails_before_model_routing(self):
        brief = self.brief.model_copy(
            update={"reference_media": [ReferenceRole.start_image.value]}
        )
        for recipe_id in SCROLL_RECIPE_IDS:
            with self.subTest(recipe_id=recipe_id):
                with self.assertRaisesRegex(ValueError, "END_IMAGE"):
                    resolve_recipe(brief, recipe_id=recipe_id)

    def test_generic_video_default_remains_unforced_by_h1(self):
        brief = self.brief.model_copy(
            update={"reference_media": [ReferenceRole.start_image.value]}
        )
        recipe, selection = resolve_recipe(brief)
        self.assertEqual(recipe.recipe_id, "generic_video")
        self.assertEqual(recipe.required_model_capabilities, ())
        self.assertIn("compatibility_default", selection.reason_codes)
