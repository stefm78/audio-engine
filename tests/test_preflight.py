import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.preflight import preflight_program


class PreflightTests(unittest.TestCase):
    def _write_program(self, root, data, name="program.json"):
        path = Path(root) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_resolves_validated_preset_without_tts(self):
        with tempfile.TemporaryDirectory() as temp_value:
            program = self._write_program(temp_value, {
                "schema_version": 1,
                "id": "preflight-ok",
                "title": "Preflight OK",
                "segments": [
                    {"preset": "narrateur-vif", "text": "Bonjour."}
                ],
            })
            result = preflight_program(program)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["segment_count"], 1)
            self.assertEqual(result["preset_segments"], 1)
            self.assertEqual(result["tts_calls"], 0)
            self.assertFalse(result["network_access"])

    def test_rejects_unknown_preset_before_tts(self):
        with tempfile.TemporaryDirectory() as temp_value:
            program = self._write_program(temp_value, {
                "schema_version": 1,
                "id": "preflight-bad-preset",
                "title": "Bad preset",
                "segments": [
                    {"preset": "does-not-exist", "text": "Bonjour."}
                ],
            })
            with self.assertRaisesRegex(ValueError, "Unknown voice preset"):
                preflight_program(program)

    def test_rejects_missing_sound_file_before_tts(self):
        with tempfile.TemporaryDirectory() as temp_value:
            program = self._write_program(temp_value, {
                "schema_version": 3,
                "id": "preflight-missing-sound",
                "title": "Missing sound",
                "soundscape": {
                    "events": [
                        {"file": "assets/missing.wav", "at_ms": 0}
                    ]
                },
                "segments": [
                    {"preset": "narrateur-vif", "text": "Bonjour."}
                ],
            })
            with self.assertRaises(FileNotFoundError):
                preflight_program(program)

    def test_resolves_local_sound_without_rendering_it(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            assets = root / "assets"
            assets.mkdir()
            # Preflight checks exact local input resolution/hash only; decode/render
            # remains a later stage.
            (assets / "event.wav").write_bytes(b"locked-reference-bytes")
            program = self._write_program(root, {
                "schema_version": 3,
                "id": "preflight-local-sound",
                "title": "Local sound",
                "soundscape": {
                    "events": [
                        {"file": "assets/event.wav", "at_ms": 0}
                    ]
                },
                "segments": [
                    {"preset": "narrateur-vif", "text": "Bonjour."}
                ],
            })
            result = preflight_program(program)
            self.assertTrue(result["soundscape_resolved"])
            self.assertTrue(result["static_inputs_resolved"])
            self.assertEqual(result["tts_calls"], 0)

    def test_explicit_provider_voice_is_not_live_network_checked(self):
        with tempfile.TemporaryDirectory() as temp_value:
            program = self._write_program(temp_value, {
                "schema_version": 1,
                "id": "preflight-explicit-voice",
                "title": "Explicit voice",
                "segments": [
                    {"voice": "fr-FR-SomeProviderVoice", "text": "Bonjour."}
                ],
            })
            result = preflight_program(program)
            self.assertEqual(result["explicit_provider_voice_segments"], 1)
            self.assertEqual(
                result["provider_voice_availability"],
                "not-network-checked",
            )
            self.assertFalse(result["network_access"])


if __name__ == "__main__":
    unittest.main()
