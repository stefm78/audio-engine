import unittest

from audio_engine.voice_lab_qwen3_contrast_emotion import (
    CASES,
    EXPECTED_ANCHOR_SHA256,
    SELECTED,
    character_spec,
    experiment_spec,
    expressive_instruction,
)


class ContrastEmotionSpecTests(unittest.TestCase):
    def test_selected_pair_is_frozen_to_human_qualified_contrast_casting(self):
        self.assertEqual(SELECTED, {"claire": "claire-a", "lucie": "lucie-b"})
        self.assertEqual(len(EXPECTED_ANCHOR_SHA256["claire"]), 64)
        self.assertEqual(len(EXPECTED_ANCHOR_SHA256["lucie"]), 64)

    def test_three_discriminating_emotions_only(self):
        self.assertEqual([case["id"] for case in CASES], ["panic", "wonder", "sadness-contained"])

    def test_character_identity_description_is_preserved_in_emotion_instruction(self):
        for role in ("claire", "lucie"):
            base = character_spec(role)["instruct"]
            for case in CASES:
                instruction = expressive_instruction(role, case["id"])
                self.assertIn(base, instruction)
                self.assertIn(case["acting"], instruction)
                self.assertIn("Conserve cette identité vocale", instruction)

    def test_gates_are_hard_and_no_production_claim(self):
        spec = experiment_spec()
        self.assertEqual(spec["gates"]["identity"], "3/3 blind A-to-reference mappings correct")
        self.assertEqual(spec["gates"]["french"], "both-good on all 3 screens")
        self.assertEqual(spec["gates"]["acting"], ">=5/6 total and >=2/3 per character")
        self.assertFalse(spec["claims"]["emotion_qualified"])
        self.assertFalse(spec["claims"]["long_form_qualified"])
        self.assertFalse(spec["claims"]["age_lineage"])
        self.assertFalse(spec["claims"]["production_promoted"])

    def test_unknown_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            character_spec("nobody")
        with self.assertRaises(ValueError):
            expressive_instruction("claire", "unknown")


if __name__ == "__main__":
    unittest.main()
