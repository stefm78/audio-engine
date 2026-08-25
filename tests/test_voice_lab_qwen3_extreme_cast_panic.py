from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from audio_engine.voice_lab_qwen3_extreme_cast_panic import (
    CHARACTERS,
    NEUTRAL_MIN_SCORE,
    PANIC_MIN_SCORE,
    _write_player,
    panic_instruction,
    reference_instruction,
)


class ExtremeCastPanicTests(unittest.TestCase):
    def test_cast_is_deliberately_far_and_natural(self):
        self.assertIn("66 ans", CHARACTERS["claire"]["instruct"])
        self.assertIn("Contralto", CHARACTERS["claire"]["instruct"])
        self.assertIn("21 ans", CHARACTERS["lucie"]["instruct"])
        self.assertIn("Soprano", CHARACTERS["lucie"]["instruct"])
        self.assertIn("non caricaturale", CHARACTERS["claire"]["instruct"])
        self.assertIn("non caricaturale", CHARACTERS["lucie"]["instruct"])

    def test_same_identity_description_is_reused_for_reference_and_panic(self):
        for role in ("claire", "lucie"):
            base = CHARACTERS[role]["instruct"]
            self.assertTrue(reference_instruction(role).startswith(base))
            self.assertTrue(panic_instruction(role).startswith(base))
            self.assertIn("Conserve cette identité vocale", panic_instruction(role))

    def test_automatic_gate_is_strict(self):
        self.assertGreaterEqual(NEUTRAL_MIN_SCORE, 80.0)
        self.assertGreaterEqual(PANIC_MIN_SCORE, 60.0)

    def test_player_is_radio_only(self):
        trial = {
            "id": "panic", "label": "Panique", "text": "Test",
            "references": [
                {"role":"claire","label":"Référence 1","file":"reference-claire.wav"},
                {"role":"lucie","label":"Référence 2","file":"reference-lucie.wav"},
            ],
            "options": [
                {"letter":"A","role":"claire","file":"clips/claire--panic.wav"},
                {"letter":"B","role":"lucie","file":"clips/lucie--panic.wav"},
            ],
            "correct_reference_for_A": "Référence 1",
        }
        with tempfile.TemporaryDirectory() as tmp:
            _write_player(Path(tmp), trial)
            html = (Path(tmp) / "index.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("<select", html)
        self.assertIn('type="radio"', html)


if __name__ == "__main__":
    unittest.main()
