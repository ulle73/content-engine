"""Provider request contracts and recommendation safety for the expanded catalog."""
import os
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from .assistant.workflows import recommendation
from .creative_budget import known_video_cost
from .creative_controls import creation_catalog
from .creative_core import Complexity, CreativeBrief, ReferenceRole
from .creative_director import build_plan, compile_parameters, eligible_models, route_model
from .creative_registry import get_model, verified_models
from .media_providers import _account_description_estimate, estimate_video, video_payload
from .media_storage import MediaError
from .model_catalog import model_label
from .test_creative_core import CreativeCoreTests


@patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "100"})
class ModelContractTests(SimpleTestCase):
    def brief(self, *, model=None, duration=10, resolution="auto", audio="none", end=True):
        return CreativeBrief(user_intent="Animate a golf ball, preserve its details.", kind="video", mode="image-to-video",
                             duration_seconds=duration, resolution=resolution, audio_intent=audio, aspect_ratio="9:16",
                             reference_media=[ReferenceRole.start_image.value, *([ReferenceRole.end_image.value] if end else [])])

    def test_catalog_exposes_all_verified_profiles_with_human_names_and_price_hints(self):
        models = creation_catalog("video")["models"]
        self.assertEqual(len({item["id"] for item in models}), 15)
        self.assertEqual(model_label("kling-video/v3.0/std"), "Kling 3.0 Standard")
        self.assertTrue(any(item["label"] == "LTX 2.5 Fast" and item["rates"]["720p"] for item in models))
        self.assertTrue(any(item["preview"] and item["label"] == "MiniMax H3" for item in models))

    def test_kling_uses_real_last_frame_field_and_string_audio_switch(self):
        model = get_model("higgsfield", "kling-video/v3.0/pro")
        brief = self.brief(audio="none")
        parameters, _ = compile_parameters(brief, model)
        self.assertEqual(parameters["reference_fields"]["END_IMAGE"], "last_image_url")
        self.assertEqual(parameters["sound"], "off")
        payload = video_payload(SimpleNamespace(prompt="A golf ball rolls.", parameters=parameters))
        self.assertEqual(payload["sound"], "off")
        self.assertFalse(payload["multi_shots"])
        self.assertNotIn("aspect_ratio", payload)
        self.assertNotIn("generate_audio", payload)
        native, _ = compile_parameters(self.brief(audio="native"), model)
        self.assertEqual(native["sound"], "on")

    def test_fixed_4k_model_does_not_send_unsupported_resolution_parameter(self):
        model = get_model("higgsfield", "kling-video/v3.0/4k")
        parameters, _ = compile_parameters(self.brief(resolution="4k"), model)
        self.assertEqual(parameters["resolution"], "4k")
        self.assertNotIn("resolution", video_payload(SimpleNamespace(prompt="Golf ball.", parameters=parameters)))

    def test_wan_retains_explicit_ratio_audio_and_two_anchor_contract(self):
        model = get_model("higgsfield", "alibaba/wan-3.0")
        parameters, _ = compile_parameters(self.brief(audio="native"), model)
        self.assertEqual(parameters["reference_fields"]["END_IMAGE"], "end_image_url")
        payload = video_payload(SimpleNamespace(prompt="Golf ball.", parameters=parameters))
        self.assertEqual(payload["aspect_ratio"], "9:16")
        self.assertTrue(payload["generate_audio"])
        self.assertEqual(payload["resolution"], "720p")

    def test_ltx_rejects_unsupported_duration_and_square_before_provider_work(self):
        model = get_model("higgsfield", "lightricks/ltx-2.5/fast")
        brief = self.brief(duration=4)
        with self.assertRaisesRegex(ValueError, "exact requested duration"):
            route_model(brief, Complexity.medium, model_override=model.model_id)
        square = self.brief(duration=8).model_copy(update={"aspect_ratio": "1:1"})
        self.assertNotIn(model, eligible_models(square))
        self.assertIn(model, eligible_models(self.brief(duration=8)))

    def test_preview_is_available_manually_and_never_selected_automatically(self):
        model = get_model("higgsfield", "minimax/h3")
        with patch("engine.creative_director.eligible_models", return_value=[model]):
            with self.assertRaisesRegex(ValueError, "No verified model"):
                route_model(self.brief(), Complexity.medium)
            chosen, _ = route_model(self.brief(), Complexity.medium, model_override=model.model_id)
        self.assertEqual(chosen, model)

    def test_no_end_frame_models_are_excluded_from_scroll_anchors(self):
        ids = {model.model_id for model in eligible_models(self.brief())}
        self.assertNotIn("kling-video/v2.6/pro", ids)
        self.assertNotIn("alibaba/happy-horse/v1.1", ids)
        self.assertIn("kling-video/v3.0/std", ids)
        self.assertIn("lightricks/ltx-2.5/pro", ids)

    def test_resolution_specific_prices_do_not_treat_high_resolution_as_cheapest_rate(self):
        self.assertEqual(str(known_video_cost("alibaba/wan-3.0", 10, "1080p")), "2.0000")
        self.assertEqual(str(known_video_cost("wan/v2.7", 10, "1080p")), "1.5000")
        self.assertIsNone(known_video_cost("wan/v2.7", 10, "unsupported"))
        self.assertEqual(str(known_video_cost("lightricks/ltx-2.5/fast", 10, "720p")), "0.9000")
        self.assertIsNone(known_video_cost("lightricks/ltx-2.5/fast", 10, "4k"))

    def test_current_account_tariff_uses_units_and_rounds_up_for_budget(self):
        fixed = _account_description_estimate("kling-video/v3.0/std/text-to-video", {"duration": 5},
                                              {"type": "fixed", "pricing_description": "$0.42001 / generation"})
        self.assertEqual(fixed["estimate"]["usd"], "0.4201")
        seconds = _account_description_estimate("kling-video/v3.0/std/text-to-video", {"duration": 5},
                                                {"type": "per_second", "pricing_description": "$0.084 / second"})
        self.assertEqual(seconds["estimate"]["usd"], "0.4200")
        self.assertIsNone(_account_description_estimate("test", {"duration": 5},
                                                      {"type": "fixed", "pricing_description": "$0.42-$1.05 / generation"}))

    def test_account_price_above_server_limit_is_stopped(self):
        with patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "0.40"}):
            with self.assertRaisesRegex(MediaError, "kostnadsgräns"):
                _account_description_estimate("test", {"duration": 5},
                                             {"type": "per_second", "pricing_description": "$0.084 / second"})

    @patch("engine.media_providers.reference_asset", return_value=None)
    def test_unknown_or_changed_account_price_cannot_submit_a_new_model(self, references):
        job = SimpleNamespace(prompt="A golf ball on grass.", parameters={"model": "alibaba/wan-3.0", "provider_model": "alibaba/wan-3.0/text-to-video", "duration": 5, "resolution": "720p"})
        with patch("engine.media_providers.higgs", return_value={"type": "description", "pricing_description": "Pricing changed."}) as provider:
            with self.assertRaisesRegex(MediaError, "bekräfta priset"):
                estimate_video(job)
        self.assertEqual(provider.call_args.args[:2], ("POST", "/estimate/alibaba/wan-3.0/text-to-video"))
        self.assertNotIn("billable", provider.call_args.kwargs)


@patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "100"})
class ExpandedRecommendationTests(TestCase):
    setUp = CreativeCoreTests.setUp

    def test_budget_recommendation_can_choose_new_models_for_the_entire_order(self):
        result = recommendation(self.run, "Animera produkten i 4 sekunder, utan ljud.", kind="video",
                                source=object(), end_source=object(), shape="portrait", budget="1.80", clip_count=3)
        self.assertNotIn(result["model_id"], {"bytedance/seedance-2.5", "bytedance/seedance-2.0"})
        model = get_model("higgsfield", result["model_id"])
        parameters, _ = compile_parameters(ModelContractTests().brief(duration=4), model)
        from decimal import Decimal
        self.assertLessEqual(known_video_cost(model.model_id, 4, parameters.get("resolution", "")) * 3, Decimal("1.80"))
        self.assertFalse(model.preview)
        self.assertIn("budget", result["reason"])

    def test_every_new_mode_compiles_a_real_endpoint_and_model_specific_prompt(self):
        for model in verified_models("video", "text-to-video"):
            if not model.label:
                continue
            for mode in model.modes:
                contract = model.request_contract(mode)
                source = object() if mode == "image-to-video" else None
                end = object() if ReferenceRole.end_image in contract.supported_reference_roles else None
                with self.subTest(model=model.model_id, mode=mode):
                    plan = build_plan(self.run, "Skapa en 10 sekunders film med en golfboll på en green, utan ljud.",
                                      kind="video", source=source, end_source=end, model_override=model.model_id)
                    self.assertEqual(plan.parameters["provider_model"], contract.endpoint)
                    self.assertIn("SCENE:", plan.prompt)
                    if source:
                        self.assertIn("supplied start image", plan.prompt)
                    if end:
                        self.assertIn("END FRAME:", plan.prompt)
                    self.assertNotIn("COMPANY CONTEXT:", plan.prompt)
