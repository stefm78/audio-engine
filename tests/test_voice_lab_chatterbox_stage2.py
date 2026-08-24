import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audio_engine.voice_lab_chatterbox_stage2 import experiment_spec, render_experiment


class FakeProvider:
    def __init__(self):
        self.segments = []

    def synthesize(self, segment, path):
        self.segments.append(dict(segment))
        Path(path).write_bytes(b"audio")


class ChatterboxStage2Tests(unittest.TestCase):
    def test_spec_is_two_voices_four_intentions_and_non_promoting(self):
        spec = experiment_spec()
        self.assertFalse(spec["production_promotion"])
        self.assertEqual(len(spec["voices"]), 2)
        self.assertEqual(len(spec["cases"]), 4)
        self.assertEqual(spec["chatterbox_bundle"]["exaggeration"], 0.8)
        self.assertEqual(spec["chatterbox_bundle"]["cfg_weight"], 0.3)
        self.assertEqual(spec["identity_intentions"], ["panic", "mystery"])

    def test_render_creates_16_comparison_clips_and_12_blind_trials(self):
        edge = FakeProvider()
        chatterbox = FakeProvider()
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            with mock.patch(
                "audio_engine.voice_lab_chatterbox_stage2._convert_reference",
                side_effect=lambda source, target: Path(target).write_bytes(b"wav"),
            ):
                result = render_experiment(root, edge=edge, chatterbox=chatterbox)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["rendered_count"], 16)
            self.assertEqual(result["failure_count"], 0)
            html = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("12 décisions", html)
            self.assertIn("localStorage", html)
            self.assertIn("voice-casting-chatterbox-stage2-v1", html)
            self.assertEqual(len(edge.segments), 10)  # 2 references + 8 baselines
            self.assertEqual(len(chatterbox.segments), 8)
            self.assertTrue(all(s.get("language_id") == "fr" for s in chatterbox.segments))
            self.assertTrue(all(s.get("exaggeration") == 0.8 for s in chatterbox.segments))
            self.assertTrue(all(s.get("cfg_weight") == 0.3 for s in chatterbox.segments))


if __name__ == "__main__":
    unittest.main()
