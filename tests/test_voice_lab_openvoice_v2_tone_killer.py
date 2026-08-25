from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from audio_engine import voice_lab_openvoice_v2_tone_killer as lab


def _write_wav(path: Path, *, frequency_byte: int = 1, frames: int = 32000, rate: int = 16000):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = bytes([frequency_byte, 0]) * frames
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(payload)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeProvider:
    identity_mode = "openvoice-v2-tone-color"

    def __init__(self):
        self.extract_calls = []
        self.convert_calls = []

    def extract_embedding(self, path):
        self.extract_calls.append(Path(path).name)
        return {"anchor": Path(path).name}

    def convert(self, source_audio, target_embedding, output_path):
        self.convert_calls.append((Path(source_audio).name, target_embedding["anchor"]))
        shutil.copy2(source_audio, output_path)
        return Path(output_path)


class OpenVoiceV2ToneKillerTests(unittest.TestCase):
    def _fixture(self, root: Path):
        anchors = root / "anchors"
        donors = root / "donors"
        _write_wav(anchors / "claire.wav", frequency_byte=2)
        _write_wav(anchors / "lucie.wav", frequency_byte=3)
        _write_wav(donors / "mystery.wav", frequency_byte=4)
        _write_wav(donors / "wonder.wav", frequency_byte=5)
        _write_wav(donors / "sad.wav", frequency_byte=6)
        characters = {
            "claire": {"label": "Référence 1", "anchor_file": "claire.wav", "sha256": _sha(anchors / "claire.wav")},
            "lucie": {"label": "Référence 2", "anchor_file": "lucie.wav", "sha256": _sha(anchors / "lucie.wav")},
        }
        cases = (
            {"id": "mystery", "label": "mystère", "text": "Texte 1", "donor_file": "mystery.wav", "donor_sha256": _sha(donors / "mystery.wav")},
            {"id": "wonder", "label": "émerveillement", "text": "Texte 2", "donor_file": "wonder.wav", "donor_sha256": _sha(donors / "wonder.wav")},
            {"id": "sadness-contained", "label": "tristesse", "text": "Texte 3", "donor_file": "sad.wav", "donor_sha256": _sha(donors / "sad.wav")},
        )
        return anchors, donors, characters, cases

    def test_spec_declares_hard_gates_and_no_promotion(self):
        spec = lab.experiment_spec()
        self.assertEqual(spec["schema"], "openvoice-v2-tone-killer-v1")
        self.assertEqual(spec["decision"]["identity_pass"], "3/3 pair mappings correct")
        self.assertTrue(spec["decision"]["no_tuning"])
        self.assertFalse(spec["decision"]["production_promotion"])
        self.assertFalse(spec["decision"]["age_lineage"])
        self.assertEqual(spec["openvoice"]["source_revision"], "74a1d147b17a8c3092dd5430504bd83ef6c7eb23")

    def test_render_and_bundle_with_fake_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors, donors, characters, cases = self._fixture(root)
            with mock.patch.object(lab, "CHARACTERS", characters), mock.patch.object(lab, "CASES", cases):
                provider_a = FakeProvider()
                provider_b = FakeProvider()
                out_a = root / "results" / "claire"
                out_b = root / "results" / "lucie"
                result_a = lab.render_character("claire", anchors, donors, out_a, provider=provider_a)
                result_b = lab.render_character("lucie", anchors, donors, out_b, provider=provider_b)
                self.assertEqual(result_a["rendered_count"], 3)
                self.assertEqual(result_b["rendered_count"], 3)
                self.assertEqual(len(provider_a.extract_calls), 1)
                self.assertEqual(len(provider_a.convert_calls), 3)
                bundle = lab.assemble_bundle(root / "results", root / "bundle", seed=7)
                self.assertEqual(bundle["trial_count"], 3)
                self.assertTrue((root / "bundle" / "index.html").is_file())
                self.assertTrue((root / "bundle" / "manifest.json").is_file())
                for trial in bundle["trials"]:
                    self.assertIn(trial["correct_reference_for_A"], {"Référence 1", "Référence 2"})
                    self.assertEqual({o["letter"] for o in trial["options"]}, {"A", "B"})

    def test_wrong_provider_mode_fails_before_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors, donors, characters, cases = self._fixture(root)
            provider = FakeProvider()
            provider.identity_mode = "wrong"
            with mock.patch.object(lab, "CHARACTERS", characters), mock.patch.object(lab, "CASES", cases):
                with self.assertRaisesRegex(ValueError, "provider"):
                    lab.render_character("claire", anchors, donors, root / "out", provider=provider)
            self.assertEqual(provider.convert_calls, [])

    def test_donor_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchors, donors, characters, cases = self._fixture(root)
            (donors / "mystery.wav").write_bytes(b"tampered")
            provider = FakeProvider()
            with mock.patch.object(lab, "CHARACTERS", characters), mock.patch.object(lab, "CASES", cases):
                with self.assertRaisesRegex(ValueError, "donor hash mismatch"):
                    lab.render_character("claire", anchors, donors, root / "out", provider=provider)
            self.assertEqual(provider.extract_calls, [])


if __name__ == "__main__":
    unittest.main()
