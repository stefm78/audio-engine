import unittest

from audio_engine.voice_lab_evaluation import summarize_human_evaluation


class VoiceLabEvaluationTests(unittest.TestCase):
    def payload(self):
        return {
            "schema": "voice-casting-human-evaluation-v1",
            "exported_at": "2026-08-24T09:32:02Z",
            "mode": "complete",
            "responses": {
                "gate": {"cmp-1": "A", "cmp-2": "tie", "cmp-3": "reject-both"},
                "identity_abx": {"abx-1": "B", "abx-2": "A"},
                "age": {
                    "age-1": {"stage": "young_adult", "favorite": True},
                    "age-2": {"stage": "mature"},
                },
            },
            "mapping": {
                "gate": [
                    {"id": "cmp-1", "left_voice": "voice-a", "right_voice": "voice-b"},
                    {"id": "cmp-2", "left_voice": "voice-a", "right_voice": "voice-b"},
                    {"id": "cmp-3", "left_voice": "voice-a", "right_voice": "voice-c"},
                ],
                "abx": [
                    {
                        "id": "abx-1",
                        "emotion": "panic",
                        "reference_voice": "voice-a",
                        "distractor_voice": "voice-b",
                        "correct": "B",
                    },
                    {
                        "id": "abx-2",
                        "emotion": "tenderness",
                        "reference_voice": "voice-a",
                        "distractor_voice": "voice-c",
                        "correct": "B",
                    },
                ],
                "age": [
                    {"id": "age-1", "voice_id": "voice-a"},
                    {"id": "age-2", "voice_id": "voice-b"},
                ],
            },
        }

    def test_summarizes_pairwise_abx_and_age_without_auto_promotion(self):
        result = summarize_human_evaluation(self.payload())
        self.assertEqual(result["gate"]["answer_count"], 3)
        voice_a = next(item for item in result["gate"]["voices"] if item["voice"] == "voice-a")
        self.assertEqual(voice_a["wins"], 1)
        self.assertEqual(voice_a["ties"], 1)
        self.assertEqual(voice_a["rejects"], 1)
        self.assertEqual(voice_a["pairwise_score"], 0.5)
        self.assertEqual(result["identity_abx"]["correct"], 1)
        self.assertEqual(result["identity_abx"]["total"], 2)
        self.assertEqual(result["identity_abx"]["accuracy"], 0.5)
        self.assertEqual(result["age"]["distribution"], {"mature": 1, "young_adult": 1})
        self.assertEqual(result["age"]["favorite_voices"], ["voice-a"])
        self.assertFalse(result["promotion"]["automatic"])

    def test_rejects_unknown_schema(self):
        payload = self.payload()
        payload["schema"] = "other"
        with self.assertRaisesRegex(ValueError, "unsupported human evaluation schema"):
            summarize_human_evaluation(payload)

    def test_rejects_unknown_gate_decision(self):
        payload = self.payload()
        payload["responses"]["gate"]["cmp-1"] = "maybe"
        with self.assertRaisesRegex(ValueError, "unsupported gate decision"):
            summarize_human_evaluation(payload)


if __name__ == "__main__":
    unittest.main()
