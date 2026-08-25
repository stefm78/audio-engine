from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab_qwen3_panic_robust_casting import (
    NEUTRAL_REQUIRED_SCORE,
    PANIC_MINIMUM_MARGIN,
    PANIC_MINIMUM_RATIO,
    _write_player,
    expressive_instruction,
    pair_is_eligible,
    panic_required_score,
)


class PanicRobustCastingTests(unittest.TestCase):
    def test_required_score_uses_stricter_ratio_or_margin(self):
        baseline = 46.644
        expected = max(baseline * PANIC_MINIMUM_RATIO, baseline + PANIC_MINIMUM_MARGIN)
        self.assertEqual(panic_required_score(baseline), round(expected, 3))

    def test_pair_must_pass_neutral_and_panic(self):
        baseline = 46.644
        required = panic_required_score(baseline)
        self.assertTrue(
            pair_is_eligible(
                neutral_score=NEUTRAL_REQUIRED_SCORE,
                panic_score=required,
                baseline_panic_score=baseline,
            )
        )
        self.assertFalse(
            pair_is_eligible(
                neutral_score=NEUTRAL_REQUIRED_SCORE - 0.001,
                panic_score=required + 20,
                baseline_panic_score=baseline,
            )
        )
        self.assertFalse(
            pair_is_eligible(
                neutral_score=NEUTRAL_REQUIRED_SCORE + 20,
                panic_score=required - 0.001,
                baseline_panic_score=baseline,
            )
        )

    def test_instruction_preserves_candidate_identity(self):
        text = expressive_instruction("claire-b", "panic")
        self.assertIn("Conserve cette identité vocale", text)
        self.assertIn("Panique urgente", text)

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
        self.assertGreaterEqual(html.count('type="radio"'), 4)


if __name__ == "__main__":
    unittest.main()
