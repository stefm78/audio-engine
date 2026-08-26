from __future__ import annotations

import unittest

from audio_engine.voice_lab_rvc_lucie_dataset_pilot import (
    BASE_MODEL_ID,
    CANDIDATES,
    LUCIE_ANCHOR_SHA256,
    pilot_spec,
    seed_for,
)


class LucieRvcDatasetPilotTests(unittest.TestCase):
    def test_candidate_set_is_fixed_and_unique(self):
        self.assertEqual(len(CANDIDATES), 10)
        ids = [item[0] for item in CANDIDATES]
        texts = [item[1] for item in CANDIDATES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(texts), len(set(texts)))

    def test_seeds_are_deterministic_and_distinct(self):
        seeds = [seed_for(cid) for cid, _ in CANDIDATES]
        self.assertEqual(seeds, [seed_for(cid) for cid, _ in CANDIDATES])
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertTrue(all(0 <= seed < 2**32 for seed in seeds))

    def test_contract_forbids_retries_and_emotion_instruction(self):
        spec = pilot_spec()
        self.assertEqual(spec["retries"], 0)
        self.assertFalse(spec["emotion_instruction"])
        self.assertFalse(spec["training_authorized"])
        self.assertFalse(spec["human_gate"])
        self.assertEqual(spec["candidate_count"], 10)

    def test_uses_frozen_human_qualified_anchor_and_base_model(self):
        self.assertEqual(
            LUCIE_ANCHOR_SHA256,
            "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822",
        )
        self.assertEqual(BASE_MODEL_ID, "Qwen/Qwen3-TTS-12Hz-1.7B-Base")


if __name__ == "__main__":
    unittest.main()
