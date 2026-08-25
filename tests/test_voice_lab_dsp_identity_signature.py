from __future__ import annotations

import math
import tempfile
import unittest
import wave
from pathlib import Path

from audio_engine.voice_lab_dsp_identity_signature import (
    MAX_OTHER_DROP,
    MIN_PANIC_GAIN,
    PROFILES,
    _write_player,
    apply_signature,
    diagnostic_gate,
    filter_chain,
    validate_profiles,
)


class DspIdentitySignatureTests(unittest.TestCase):
    def test_profiles_are_bounded_and_pitch_free(self):
        validate_profiles()
        for role, bands in PROFILES.items():
            self.assertTrue(all(abs(gain) <= 3.0 for _, gain in bands))
            chain = filter_chain(role).lower()
            self.assertIn("equalizer=", chain)
            self.assertNotIn("rubberband", chain)
            self.assertNotIn("atempo", chain)
            self.assertNotIn("pitch", chain)
            self.assertNotIn("formant", chain)

    def test_diagnostic_gate_requires_panic_gain_and_no_large_drop(self):
        good = {
            "neutral": {"score": 80.0},
            "panic": {"score": 46.644 + MIN_PANIC_GAIN},
            "wonder": {"score": 60.0},
            "sadness-contained": {"score": 34.0},
        }
        self.assertTrue(diagnostic_gate(good)["eligible"])
        bad_panic = dict(good)
        bad_panic["panic"] = {"score": 46.644 + MIN_PANIC_GAIN - 0.001}
        self.assertFalse(diagnostic_gate(bad_panic)["eligible"])
        bad_other = dict(good)
        bad_other["neutral"] = {"score": 84.226 - MAX_OTHER_DROP - 0.001}
        self.assertFalse(diagnostic_gate(bad_other)["eligible"])

    def test_transform_is_deterministic_and_preserves_wav_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.wav"
            rate = 24000
            samples = [int(8000 * math.sin(2 * math.pi * 220 * i / rate)) for i in range(rate // 4)]
            with wave.open(str(source), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(rate)
                stream.writeframes(b"".join(int(v).to_bytes(2, "little", signed=True) for v in samples))
            first, second = root / "first.wav", root / "second.wav"
            one = apply_signature(source, first, "claire")
            two = apply_signature(source, second, "claire")
            self.assertEqual(one["output_sha256"], two["output_sha256"])
            self.assertEqual(one["sample_rate"], rate)
            self.assertEqual(one["frames"], len(samples))

    def test_player_is_radio_only(self):
        trials = [
            {
                "id": "panic",
                "label": "Panique urgente",
                "text": "Test",
                "references": [
                    {"role": "claire", "label": "Référence 1", "file": "reference-claire.wav"},
                    {"role": "lucie", "label": "Référence 2", "file": "reference-lucie.wav"},
                ],
                "options": [
                    {"letter": "A", "role": "claire", "file": "clips/a.wav"},
                    {"letter": "B", "role": "lucie", "file": "clips/b.wav"},
                ],
                "correct_reference_for_A": "Référence 1",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _write_player(Path(tmp), trials)
            html = (Path(tmp) / "index.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("<select", html)
        self.assertIn('type="radio"', html)
        for group in ("identity", "actinga", "actingb", "french"):
            self.assertIn(f"radio('{group}'", html)


if __name__ == "__main__":
    unittest.main()
