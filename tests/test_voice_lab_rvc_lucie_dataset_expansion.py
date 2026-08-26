from __future__ import annotations

import unittest

from audio_engine.voice_lab_rvc_lucie_dataset_expansion import CANDIDATES, expansion_spec, seed_for


class RvcLucieDatasetExpansionTests(unittest.TestCase):
    def test_exact_fixed_candidate_set(self):
        ids = [cid for cid, _ in CANDIDATES]
        self.assertEqual(len(ids), 60)
        self.assertEqual(ids, [f"n{i:02d}" for i in range(11, 71)])
        self.assertEqual(len(set(text for _, text in CANDIDATES)), 60)

    def test_no_very_short_or_obvious_emotion_stage_directions(self):
        forbidden = ("panique", "tristesse", "colère", "effray", "sanglot", "crie", "hurle")
        for cid, text in CANDIDATES:
            self.assertGreaterEqual(len(text.split()), 11, cid)
            self.assertFalse(any(word in text.lower() for word in forbidden), (cid, text))

    def test_seeds_are_unique_and_deterministic(self):
        first = {cid: seed_for(cid) for cid, _ in CANDIDATES}
        second = {cid: seed_for(cid) for cid, _ in CANDIDATES}
        self.assertEqual(first, second)
        self.assertEqual(len(set(first.values())), 60)

    def test_corpus_gates_are_preregistered(self):
        spec = expansion_spec()
        self.assertEqual(spec["candidate_count"], 60)
        self.assertEqual(spec["render_shards"], 6)
        self.assertEqual(spec["candidates_per_shard"], 10)
        self.assertEqual(spec["retries"], 0)
        self.assertEqual(spec["substitutions"], 0)
        self.assertFalse(spec["emotion_instruction"])
        self.assertFalse(spec["training_authorized_by_generation_workflow"])
        self.assertIn(">=300", spec["final_dataset_gates"]["accepted_duration_seconds"])
        self.assertIn("<=0.05", spec["final_dataset_gates"]["aggregate_french"])
        self.assertIn(">=0.85", spec["final_dataset_gates"]["expansion_acceptance_rate"])


if __name__ == "__main__":
    unittest.main()
