from django.test import SimpleTestCase

from .creative_core import (
    Complexity,
    CreativeBrief,
    CreativeContext,
    EvidenceLevel,
    ReferenceRole,
    RECIPE_REGISTRY_VERSION,
)
from .creative_director import (
    HIGGSFIELD_SAFE_PROMPT_CHARS,
    compile_parameters,
    compile_prompt,
    eligible_models,
    route_model,
)
from .creative_recipes import get_recipe, registry as recipe_registry, resolve_recipe
from .creative_registry import get_model


H2_RECIPE_IDS = (
    "premium_product_reveal",
    "product_showcase",
    "hyper_motion_product",
    "before_after",
    "ugc_testimonial",
    "ugc_product_demo",
    "problem_solution_paid_ad",
    "curiosity_hook_paid_ad",
    "landscape_environment_hero",
    "luxury_brand_film",
)


class GeneralCommercialRecipesH2Tests(SimpleTestCase):
    def setUp(self):
        self.context = CreativeContext(
            company_name="Golfkuponger",
            profile="Golf value product",
            voice="Warm, premium and clear",
            current_facts="Use only approved current facts.",
        )

    def i2v(self, *, end=False, audio=False, intent="Show the referenced product clearly."):
        refs = [ReferenceRole.start_image.value]
        if end:
            refs.append(ReferenceRole.end_image.value)
        return CreativeBrief(
            user_intent=intent,
            kind="video",
            mode="image-to-video",
            platform="instagram_reel",
            visual_style=["premium", "photoreal"],
            duration_seconds=12,
            aspect_ratio="9:16",
            resolution="720p",
            audio_intent="native" if audio else "none",
            reference_media=refs,
            preserve=["product identity", "visible text"],
        )

    def t2v(self, *, audio=False, intent="Create a concise commercial."):
        return CreativeBrief(
            user_intent=intent,
            kind="video",
            mode="text-to-video",
            platform="instagram_reel",
            visual_style=["photoreal"],
            duration_seconds=12,
            aspect_ratio="9:16",
            resolution="720p",
            audio_intent="native" if audio else "none",
        )

    def test_registry_contains_complete_h2_family_with_reproducible_methods(self):
        recipes = {item.recipe_id: item for item in recipe_registry()}
        self.assertEqual(set(H2_RECIPE_IDS) - set(recipes), set())
        self.assertEqual(RECIPE_REGISTRY_VERSION, "2026-09-25.2")
        for recipe_id in H2_RECIPE_IDS:
            with self.subTest(recipe_id=recipe_id):
                recipe = recipes[recipe_id]
                self.assertEqual(recipe.kinds, ("video",))
                self.assertIn("commercial", recipe.format_tags)
                self.assertEqual(recipe.draft_policy, "draft_then_final")
                self.assertTrue(recipe.narrative_strategy)
                self.assertTrue(recipe.camera_strategy)
                self.assertTrue(recipe.motion_strategy)
                self.assertTrue(recipe.continuity_strategy)
                self.assertTrue(recipe.negative_constraints)
                self.assertTrue(recipe.required_model_capabilities)
                self.assertTrue(recipe.evaluation_rules)
                self.assertTrue(recipe.good_result_criteria)
                self.assertTrue(recipe.bad_result_signals)
                self.assertTrue(recipe.evidence_sources)
                self.assertEqual(recipe.verified_at, "2026-09-25")
                self.assertEqual(recipe.evidence_level, EvidenceLevel.verified)

    def test_every_h2_recipe_has_at_least_one_verified_compatible_execution_path(self):
        cases = {
            "premium_product_reveal": self.i2v(),
            "product_showcase": self.i2v(),
            "hyper_motion_product": self.i2v(),
            "before_after": self.i2v(end=True),
            "ugc_testimonial": self.t2v(audio=True, intent='Dialogue: "I use this every round."'),
            "ugc_product_demo": self.i2v(audio=True, intent='Dialogue: "Here is how it works." Demonstrate the approved feature.'),
            "problem_solution_paid_ad": self.t2v(intent="Problem: booking feels complicated. Solution: show the approved simpler flow."),
            "curiosity_hook_paid_ad": self.t2v(intent="Open on a mysterious golf gift, then reveal the approved product."),
            "landscape_environment_hero": self.t2v(intent="Create one cinematic golf-course environment hero shot."),
            "luxury_brand_film": self.t2v(intent="Create a restrained premium golf brand film."),
        }
        for recipe_id, brief in cases.items():
            with self.subTest(recipe_id=recipe_id):
                recipe, _ = resolve_recipe(brief, recipe_id=recipe_id)
                candidates = eligible_models(brief, recipe=recipe)
                self.assertTrue(candidates)
                for model in candidates:
                    self.assertTrue(set(recipe.required_model_capabilities) <= set(model.recipe_capabilities))
                model, routed = route_model(brief, Complexity.medium, recipe=recipe)
                prompt = compile_prompt(brief, self.context, model, [], recipe=recipe)
                self.assertIn("STORY METHOD:", prompt)
                self.assertLessEqual(len(prompt), HIGGSFIELD_SAFE_PROMPT_CHARS)
                self.assertIn("recipe_capabilities_supported", routed.reason_codes)

    def test_product_reveal_compiles_on_kling_ordered_motion_without_fake_end_frame_support(self):
        brief = self.i2v(intent="Premium product reveal with a slow push in.")
        recipe, _ = resolve_recipe(brief, recipe_id="premium_product_reveal")
        kling = get_model("higgsfield", "kling-video/v2.5-turbo/pro")
        self.assertIn(kling, eligible_models(brief, recipe=recipe))
        prompt = compile_prompt(brief, self.context, kling, [], recipe=recipe)
        self.assertIn("STORY METHOD:", prompt)
        self.assertIn("FORMAT MODE: Product-led commercial.", prompt)
        self.assertIn(recipe.camera_strategy[0], prompt)
        self.assertIn(recipe.negative_constraints[0], prompt)
        params, issues = compile_parameters(brief, kling, count=1, shape="portrait")
        self.assertEqual(params["provider_model"], "kling-video/v2.5-turbo/pro/image-to-video")
        self.assertEqual(params["reference_fields"], {ReferenceRole.start_image.value: "image_url"})
        self.assertFalse([item for item in issues if item.severity == "error"])

    def test_optional_product_end_anchor_automatically_filters_kling(self):
        brief = self.i2v(end=True)
        for recipe_id in ("premium_product_reveal", "product_showcase", "hyper_motion_product"):
            with self.subTest(recipe_id=recipe_id):
                recipe, _ = resolve_recipe(brief, recipe_id=recipe_id)
                ids = {item.model_id for item in eligible_models(brief, recipe=recipe)}
                self.assertTrue({"bytedance/seedance-2.5", "bytedance/seedance-2.0"} <= ids)
                self.assertNotIn("kling-video/v2.5-turbo/pro", ids)

    def test_before_after_requires_real_before_and_after_anchors(self):
        with self.assertRaisesRegex(ValueError, "END_IMAGE"):
            resolve_recipe(self.i2v(), recipe_id="before_after")
        brief = self.i2v(end=True, intent="Transform only the supplied before state into the supplied after state.")
        recipe, _ = resolve_recipe(brief, recipe_id="before_after")
        ids = {item.model_id for item in eligible_models(brief, recipe=recipe)}
        self.assertTrue({"bytedance/seedance-2.5", "bytedance/seedance-2.0"} <= ids)
        self.assertNotIn("kling-video/v2.5-turbo/pro", ids)
        model = get_model("higgsfield", "bytedance/seedance-2.5")
        prompt = compile_prompt(brief, self.context, model, [], recipe=recipe)
        self.assertIn("FORMAT MODE: Before/after proof.", prompt)
        self.assertIn("END FRAME:", prompt)
        self.assertIn("invented result", prompt)

    def test_ugc_recipes_fail_closed_without_explicit_audio_intent(self):
        with self.assertRaisesRegex(ValueError, "requires native audio"):
            resolve_recipe(self.t2v(intent="Give a natural testimonial."), recipe_id="ugc_testimonial")
        with self.assertRaisesRegex(ValueError, "requires native audio"):
            resolve_recipe(self.i2v(intent="Demonstrate the product naturally."), recipe_id="ugc_product_demo")

    def test_ugc_testimonial_routes_only_to_native_audio_models_and_compiles_claim_guard(self):
        brief = self.t2v(
            audio=True,
            intent='Dialogue: "I use this when I want a simple golf gift." Do not add any other claim.',
        )
        recipe, _ = resolve_recipe(brief, recipe_id="ugc_testimonial")
        ids = {item.model_id for item in eligible_models(brief, recipe=recipe)}
        self.assertTrue({"bytedance/seedance-2.5", "bytedance/seedance-2.0"} <= ids)
        self.assertNotIn("kling-video/v2.5-turbo/pro", ids)
        model = get_model("higgsfield", "bytedance/seedance-2.5")
        prompt = compile_prompt(brief, self.context, model, [], recipe=recipe)
        self.assertIn("FORMAT MODE: Authentic creator-style UGC.", prompt)
        self.assertIn("never invent personal experience", prompt)
        self.assertIn("Use only approved dialogue, voiceover and claims", prompt)
        params, issues = compile_parameters(brief, model, count=1, shape="portrait")
        self.assertTrue(params["generate_audio"])
        self.assertEqual(params["provider_model"], "bytedance/seedance-2.5/text-to-video")
        self.assertFalse([item for item in issues if item.severity == "error"])

    def test_ugc_product_demo_uses_precomposed_start_reference_and_native_audio(self):
        brief = self.i2v(
            audio=True,
            intent='Dialogue: "Here is how it works." Demonstrate only the approved feature visible in the brief.',
        )
        recipe, _ = resolve_recipe(brief, recipe_id="ugc_product_demo")
        ids = {item.model_id for item in eligible_models(brief, recipe=recipe)}
        self.assertTrue({"bytedance/seedance-2.5", "bytedance/seedance-2.0"} <= ids)
        self.assertNotIn("kling-video/v2.5-turbo/pro", ids)
        model = get_model("higgsfield", "bytedance/seedance-2.0")
        prompt = compile_prompt(brief, self.context, model, [], recipe=recipe)
        self.assertIn("FORMAT MODE: Authentic creator-style UGC product demo.", prompt)
        self.assertIn("FIRST FRAME AND BLOCKING:", prompt)
        self.assertIn("invented feature", prompt)
        params, _ = compile_parameters(brief, model, count=1, shape="portrait")
        self.assertTrue(params["generate_audio"])
        self.assertEqual(params["reference_fields"][ReferenceRole.start_image.value], "image_url")

    def test_paid_ad_methods_compile_different_story_structures(self):
        model = get_model("higgsfield", "bytedance/seedance-2.5")
        cases = {
            "problem_solution_paid_ad": self.t2v(intent="Show the supplied problem and approved solution."),
            "curiosity_hook_paid_ad": self.t2v(intent="Open on an unanswered visual detail and reveal the approved product."),
            "luxury_brand_film": self.t2v(intent="Create a restrained premium brand film."),
            "landscape_environment_hero": self.t2v(intent="Create a cinematic environment hero."),
        }
        prompts = {}
        for recipe_id, brief in cases.items():
            recipe, _ = resolve_recipe(brief, recipe_id=recipe_id)
            prompts[recipe_id] = compile_prompt(brief, self.context, model, [], recipe=recipe)
            self.assertLessEqual(len(prompts[recipe_id]), HIGGSFIELD_SAFE_PROMPT_CHARS)
        self.assertEqual(len(set(prompts.values())), len(prompts))
        self.assertIn("Beat 1: make one concrete problem", prompts["problem_solution_paid_ad"])
        self.assertIn("unanswered visual question", prompts["curiosity_hook_paid_ad"])
        self.assertIn("Luxury brand film.", prompts["luxury_brand_film"])
        self.assertIn("Environment hero.", prompts["landscape_environment_hero"])

    def test_generic_video_default_remains_unchanged_and_audio_is_not_silently_enabled(self):
        brief = self.t2v()
        recipe, selection = resolve_recipe(brief)
        self.assertEqual(recipe.recipe_id, "generic_video")
        self.assertFalse(recipe.requires_native_audio)
        self.assertEqual(recipe.narrative_strategy, ())
        self.assertIn("compatibility_default", selection.reason_codes)
        model, _ = route_model(brief, Complexity.simple, recipe=recipe)
        params, _ = compile_parameters(brief, model, count=1, shape="portrait")
        if "generate_audio" in params:
            self.assertFalse(params["generate_audio"])
