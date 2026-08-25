from __future__ import annotations

import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from audio_engine.voice_casting_distance import (
    CastingDistanceError,
    acoustic_profile,
    compare_anchors,
    contrast_gate,
)


def _write_voice(path, *, f0, seconds=1.4, harmonics=(1.0, 0.4, 0.2), amplitude=0.5, sr=24000):
    frame_count = int(sr * seconds)
    norm = sum(abs(value) for value in harmonics)
    values = []
    for index in range(frame_count):
        t = index / sr
        signal = sum(
            weight * math.sin(2.0 * math.pi * f0 * harmonic * t)
            for harmonic, weight in enumerate(harmonics, 1)
        )
        signal *= amplitude / norm
        values.append(max(-32767, min(32767, int(signal * 32767))))
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sr)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))


class VoiceCastingDistanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_profile_extracts_basic_voice_features(self):
        voice = self.root / "voice.wav"
        _write_voice(voice, f0=180)
        profile = acoustic_profile(voice)
        self.assertEqual(profile["sample_rate"], 24000)
        self.assertAlmostEqual(profile["duration_seconds"], 1.4, places=2)
        self.assertGreater(profile["rms"], 0)
        self.assertGreater(profile["f0_hz"], 150)
        self.assertLess(profile["f0_hz"], 220)
        self.assertEqual(len(profile["spectral_shape"]), 7)
        self.assertAlmostEqual(sum(profile["spectral_shape"]), 1.0, places=5)

    def test_near_pair_scores_far_below_contrasting_pair(self):
        a = self.root / "a.wav"
        near = self.root / "near.wav"
        far = self.root / "far.wav"
        _write_voice(a, f0=180, harmonics=(1.0, 0.4, 0.2))
        _write_voice(near, f0=190, seconds=1.43, harmonics=(1.0, 0.42, 0.18))
        _write_voice(far, f0=265, seconds=1.05, harmonics=(1.0, 0.1, 0.6, 0.2))
        near_score = compare_anchors(a, near)["score"]
        far_score = compare_anchors(a, far)["score"]
        self.assertLess(near_score, far_score)
        self.assertGreater(far_score - near_score, 20)

    def test_contrast_gate_uses_known_confusable_baseline(self):
        baseline_a = self.root / "baseline-a.wav"
        baseline_b = self.root / "baseline-b.wav"
        candidate_a = self.root / "candidate-a.wav"
        candidate_b = self.root / "candidate-b.wav"
        _write_voice(baseline_a, f0=180, harmonics=(1.0, 0.4, 0.2))
        _write_voice(baseline_b, f0=190, harmonics=(1.0, 0.42, 0.18))
        _write_voice(candidate_a, f0=145, seconds=1.6, harmonics=(1.0, 0.55, 0.08))
        _write_voice(candidate_b, f0=270, seconds=1.05, harmonics=(1.0, 0.05, 0.7, 0.25))
        result = contrast_gate(candidate_a, candidate_b, baseline_a, baseline_b)
        self.assertTrue(result["eligible"])
        self.assertGreaterEqual(result["candidate_score"], result["required_score"])
        self.assertEqual(result["claim"], "prefilter-only-not-speaker-identity-qualification")

    def test_rejects_non_mono_pcm16(self):
        bad = self.root / "bad.wav"
        with wave.open(str(bad), "wb") as stream:
            stream.setnchannels(2)
            stream.setsampwidth(2)
            stream.setframerate(24000)
            stream.writeframes(b"\x00\x00\x00\x00" * 100)
        with self.assertRaises(CastingDistanceError):
            acoustic_profile(bad)


if __name__ == "__main__":
    unittest.main()
