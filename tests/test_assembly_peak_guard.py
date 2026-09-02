import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.audio import encode_concat


PROFILE = {
    "loudness_lufs": -16,
    "true_peak_db": -2.5,
    "lra": 11,
    "codec": "libmp3lame",
    "bitrate_kbps": 80,
    "sample_rate_hz": 24000,
    "channels": 1,
}


class AssemblyPeakGuardTests(unittest.TestCase):
    def test_reencodes_from_source_with_peak_limiter_without_lowering_loudnorm_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "block.mp3"
            with (
                patch("audio_engine.audio.run_ffmpeg") as render,
                patch(
                    "audio_engine.audio.measure_encoded_true_peak_dbtp",
                    side_effect=[0.31, -2.4],
                ),
            ):
                report = encode_concat(
                    [root / "scene-a.mp3", root / "scene-b.mp3"],
                    out,
                    PROFILE,
                )

            self.assertEqual(render.call_count, 2)
            first = render.call_args_list[0].args[0]
            second = render.call_args_list[1].args[0]
            self.assertIn("loudnorm=I=-16:TP=-2.500:LRA=11", first)
            self.assertNotIn("alimiter=", first)
            self.assertIn("loudnorm=I=-16:TP=-2.500:LRA=11", second)
            self.assertIn("alimiter=limit=", second)
            self.assertIn("attack=5:release=50:level=false", second)
            self.assertEqual(report["attempts"], 2)
            self.assertEqual(report["measured_encoded_true_peak_dbtp"], -2.4)
            self.assertEqual(report["effective_loudnorm_true_peak_dbtp"], -2.5)
            self.assertEqual(report["effective_limiter_ceiling_dbfs"], -5.81)

    def test_no_overshoot_does_not_enable_limiter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "block.mp3"
            with (
                patch("audio_engine.audio.run_ffmpeg") as render,
                patch(
                    "audio_engine.audio.measure_encoded_true_peak_dbtp",
                    return_value=-2.4,
                ),
            ):
                report = encode_concat([root / "scene.mp3"], out, PROFILE)

            self.assertEqual(render.call_count, 1)
            args = render.call_args_list[0].args[0]
            self.assertIn("loudnorm=I=-16:TP=-2.500:LRA=11", args)
            self.assertNotIn("alimiter=", args)
            self.assertIsNone(report["effective_limiter_ceiling_dbfs"])

    def test_fails_closed_after_bounded_peak_guard_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("audio_engine.audio.run_ffmpeg") as render,
                patch(
                    "audio_engine.audio.measure_encoded_true_peak_dbtp",
                    side_effect=[0.0, 0.0, 0.0],
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "after 3 attempts"):
                    encode_concat([root / "scene.mp3"], root / "block.mp3", PROFILE)
            self.assertEqual(render.call_count, 3)


if __name__ == "__main__":
    unittest.main()
