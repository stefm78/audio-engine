from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab_qwen3_customvoice_identity_emotion import (
    CASES,
    CHARACTERS,
    COMMON_TEXT,
    MODEL_ID,
    _build_trials,
    _write_player,
    experiment_spec,
    topology_gate,
)


class CustomVoiceIdentityEmotionTests(unittest.TestCase):
    def test_architecture_separates_speaker_and_emotion_channels(self):
        spec = experiment_spec()
        self.assertEqual(MODEL_ID, "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        self.assertEqual(set(CHARACTERS), {"serena", "vivian"})
        self.assertEqual([case["id"] for case in CASES], ["panic", "sadness-contained"])
        self.assertTrue(spec["generation_contract"]["same_text_across_emotions"])
        self.assertEqual(spec["generation_contract"]["clip_count"], 4)
        self.assertEqual(spec["generation_contract"]["speaker_channel"], "fixed built-in speaker id")
        self.assertEqual(spec["generation_contract"]["emotion_channel"], "instruct only")
        self.assertTrue(COMMON_TEXT.startswith("Ils sont là"))

    def test_emotion_instructions_do_not_carry_speaker_identity(self):
        speakers = {item["speaker"].lower() for item in CHARACTERS.values()}
        for case in CASES:
            instruction = case["instruction"].lower()
            self.assertTrue(all(speaker not in instruction for speaker in speakers))

    def test_topology_gate_has_no_tuned_absolute_threshold(self):
        good = {
            "same_serena": {"score": 22.0},
            "same_vivian": {"score": 18.0},
            "cross_panic": {"score": 41.0},
            "cross_sadness-contained": {"score": 35.0},
        }
        result = topology_gate(good)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["topology_margin"], 13.0)

        bad = dict(good)
        bad["same_serena"] = {"score": 36.0}
        self.assertFalse(topology_gate(bad)["eligible"])

    def test_two_screen_gate_reuses_only_four_clips_and_is_radio_only(self):
        rendered = {
            (role, case["id"]): f"clips/{role}--{case['id']}.wav"
            for role in CHARACTERS
            for case in CASES
        }
        trials = _build_trials(rendered, seed=17)
        self.assertEqual(len(trials), 2)
        files = {
            item["file"]
            for trial in trials
            for item in trial["references"] + trial["options"]
        }
        self.assertEqual(len(files), 4)
        self.assertEqual(
            {trial["target_emotion"] for trial in trials},
            {"panic", "sadness-contained"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write_player(Path(tmp), trials)
            html = (Path(tmp) / "index.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("<select", html)
        self.assertIn('type="radio"', html)
        for group in ("identity", "actinga", "actingb", "french"):
            self.assertIn(f"radio('{group}'", html)

    def test_no_promotion_claims(self):
        claims = experiment_spec()["claims"]
        self.assertFalse(claims["architecture_qualified"])
        self.assertFalse(claims["custom_character_catalog_qualified"])
        self.assertFalse(claims["long_form_qualified"])
        self.assertFalse(claims["age_lineage"])
        self.assertFalse(claims["production_promoted"])


if __name__ == "__main__":
    unittest.main()
