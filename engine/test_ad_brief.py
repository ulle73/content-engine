import unittest

from .ad_studio.brief import AdBrief, BriefNotReady


def ready_brief(**overrides):
    data = {
        "message": "Använd friskvårdsbidraget på golf innan det brinner inne",
        "objective": "conversion",
        "audience": "Anställda med outnyttjat friskvårdsbidrag som spelar golf",
        "angle": {"title": "Pengarna försvinner", "hook": "DITT FRISKVÅRDSBIDRAG BRINNER INNE"},
        "assets": [
            {"asset_id": "a-hook", "role": "hook"},
            {"asset_id": "a-portal", "role": "screen"},
            {"asset_id": "a-proof", "role": "proof"},
        ],
        "engine": {"engine": "remotion", "remotion_template_id": "friskvard-portal-ad"},
        "duration_s": 9,
        "scenes": [
            {"id": "hook", "purpose": "hook", "duration_s": 2, "asset_id": "a-hook", "on_screen_text": "DITT BIDRAG BRINNER INNE"},
            {"id": "portal", "purpose": "how", "duration_s": 3, "asset_id": "a-portal", "on_screen_text": "SÖK GOLFKUPONGER I DIN PORTAL"},
            {"id": "proof", "purpose": "proof", "duration_s": 2, "asset_id": "a-proof"},
            {"id": "end", "purpose": "cta", "duration_s": 2, "on_screen_text": "Golfkuponger.se"},
        ],
        "copy": {"headline": "Golf för friskvårdsbidraget"},
        "facts": [{"claim": "Finns i förmånsportaler", "source": "skills/golfkuponger-friskvard", "verified": True}],
    }
    data.update(overrides)
    return AdBrief.model_validate(data)


class AdBriefTests(unittest.TestCase):
    def test_empty_brief_lists_what_to_ask_next(self):
        self.assertEqual(AdBrief().missing()[:3], ["message", "objective", "audience"])

    def test_ready_brief_locks_and_verifies(self):
        locked = ready_brief().lock()
        self.assertEqual(locked.status, "locked")
        self.assertTrue(locked.verify_lock())

    def test_tampering_breaks_lock(self):
        locked = ready_brief().lock()
        tampered = locked.model_copy(update={"message": "Något annat"})
        self.assertFalse(tampered.verify_lock())

    def test_too_many_words_on_screen(self):
        brief = ready_brief()
        brief.scenes[0].on_screen_text = "ett två tre fyra fem sex sju åtta nio"
        with self.assertRaises(BriefNotReady) as ctx:
            brief.lock()
        self.assertIn("max 8", str(ctx.exception))

    def test_duration_must_match_scenes(self):
        with self.assertRaises(BriefNotReady):
            ready_brief(duration_s=15).lock()

    def test_story_must_start_with_hook_and_end_with_cta(self):
        brief = ready_brief()
        brief.scenes.reverse()
        problems = brief.problems()
        self.assertTrue(any("hook" in p for p in problems))
        self.assertTrue(any("CTA" in p for p in problems))

    def test_higgsfield_needs_cost_approval(self):
        brief = ready_brief(engine={"engine": "higgsfield", "estimated_cost_sek": 40})
        self.assertTrue(any("kostnaden" in p for p in brief.problems()))

    def test_unknown_asset_is_rejected(self):
        brief = ready_brief()
        brief.scenes[1].asset_id = "finns-inte"
        self.assertTrue(any("finns-inte" in p for p in brief.problems()))

    def test_unverified_claim_blocks_lock(self):
        brief = ready_brief(facts=[{"claim": "5000 kr skattefritt", "source": "minne"}])
        with self.assertRaises(BriefNotReady):
            brief.lock()

    def test_locked_without_hash_is_invalid(self):
        with self.assertRaises(ValueError):
            ready_brief(status="locked")


if __name__ == "__main__":
    unittest.main()
