from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from audio_engine.voice_lab_knnvc_identity_lock import (
    CASES,
    ECAPA_REVISION,
    KNNVC_REVISION,
    SOURCE_RUN_ID,
    _build_trials,
    _write_player,
    experiment_spec,
    smoke_gate,
    topology_gate,
)


class KNNVCIdentityLockTests(unittest.TestCase):
    def test_contract_is_lab_only_zero_new_tts_and_four_conversions(self):
        spec = experiment_spec()
        self.assertEqual(spec["engine"]["source_revision"], KNNVC_REVISION)
        self.assertEqual(spec["source"]["run_id"], SOURCE_RUN_ID)
        self.assertFalse(spec["source"]["new_tts_generation"])
        self.assertEqual(spec["conversion_budget"]["maximum_conversions"], 4)
        self.assertEqual(spec["conversion_budget"]["new_tts_clips"], 0)
        self.assertEqual(spec["independent_verifier"]["revision"], ECAPA_REVISION)
        self.assertFalse(spec["independent_verifier"]["used_by_converter"])
        self.assertFalse(spec["claims"]["production_promoted"])
        self.assertFalse(spec["claims"]["long_form_qualified"])
        self.assertFalse(spec["licenses"]["checkpoint_legal_qualification"])

    def test_smoke_gate_is_relative_and_independent(self):
        good = smoke_gate(0.31, 0.32)
        self.assertTrue(good["eligible"])
        self.assertTrue(good["verifier_independent_of_converter"])
        self.assertFalse(smoke_gate(0.72, 0.71)["eligible"])
        self.assertFalse(smoke_gate(0.5, 0.5)["eligible"])
        self.assertFalse(good["absolute_threshold"])

    def test_topology_gate_requires_target_rank_and_emotion_invariance(self):
        refs = {
            "panic:claire": {"claire": 0.82, "lucie": 0.41},
            "panic:lucie": {"claire": 0.38, "lucie": 0.79},
            "sadness-contained:claire": {"claire": 0.80, "lucie": 0.43},
            "sadness-contained:lucie": {"claire": 0.39, "lucie": 0.77},
        }
        pairs = {
            "same_claire": 0.88,
            "same_lucie": 0.86,
            "cross_panic": 0.49,
            "cross_sadness-contained": 0.51,
        }
        good = topology_gate(refs, pairs)
        self.assertTrue(good["eligible"])
        self.assertGreater(good["topology_margin"], 0)
        self.assertFalse(good["absolute_threshold"])

        refs_bad = {key: dict(value) for key, value in refs.items()}
        refs_bad["panic:lucie"] = {"claire": 0.81, "lucie": 0.79}
        self.assertFalse(topology_gate(refs_bad, pairs)["eligible"])

        pairs_bad = dict(pairs)
        pairs_bad["cross_sadness-contained"] = 0.90
        self.assertFalse(topology_gate(refs, pairs_bad)["eligible"])

    def test_trials_reuse_exactly_four_converted_clips(self):
        rendered = {
            f"{case['id']}:{target}": f"clips/{case['id']}--{target}.wav"
            for case in CASES
            for target in ("claire", "lucie")
        }
        trials = _build_trials(rendered)
        self.assertEqual(len(trials), 2)
        used = {item["file"] for trial in trials for item in trial["options"]}
        self.assertEqual(used, set(rendered.values()))

    def test_human_gate_is_radio_only(self):
        rendered = {
            f"{case['id']}:{target}": f"clips/{case['id']}--{target}.wav"
            for case in CASES
            for target in ("claire", "lucie")
        }
        trials = _build_trials(rendered)
        with TemporaryDirectory() as tmp:
            _write_player(Path(tmp), trials)
            html = (Path(tmp) / "index.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("<select", html)
        self.assertIn('type="radio"', html)
        for group in ("identity", "actinga", "actingb", "french"):
            self.assertIn(f"radio('{group}'", html)
        self.assertIn("2 écrans", html)


if __name__ == "__main__":
    unittest.main()
