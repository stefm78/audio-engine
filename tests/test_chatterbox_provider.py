import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.contract import ContractError
from audio_engine.providers.chatterbox_mtl_v3 import ChatterboxMultilingualV3Provider


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ChatterboxProviderTests(unittest.TestCase):
    def make_fixture(self, root):
        root = Path(root)
        model = root / "model"
        model.mkdir()
        weight = model / "weights.bin"
        weight.write_bytes(b"locked-model")
        reference = root / "reference.wav"
        reference.write_bytes(b"locked-reference")
        package = {
            "schema_version": 1,
            "id": "chatterbox-mtl-v3-test",
            "provider": {
                "id": "chatterbox-multilingual-v3",
                "implementation_version": "1.0.0",
            },
            "runtime": {
                "kind": "python",
                "python": "3.11.16",
                "device": "cpu",
                "dependencies": [
                    {"name": "chatterbox-tts", "revision": "1" * 40},
                    {"name": "torch", "version": "2.6.0"},
                ],
            },
            "model": {
                "id": "ResembleAI/chatterbox",
                "revision": "2" * 40,
                "integrity": [
                    {"name": "weights.bin", "sha256": sha(weight)},
                ],
            },
            "voice_pack_sha256": "3" * 64,
            "synthesis": {
                "seed": 650100,
                "parameters": {
                    "language_id": "fr",
                    "reference": "synthetic-vivienne",
                    "exaggeration": 0.34,
                    "cfg_weight": 0.5,
                    "temperature": 0.74,
                },
                "normalization": {"target_dbfs": -20.0},
            },
            "references": [
                {
                    "id": "synthetic-vivienne",
                    "path": "reference.wav",
                    "sha256": sha(reference),
                }
            ],
            "fallback": "fail",
        }
        package_path = root / "provider.json"
        package_path.write_text(json.dumps(package), encoding="utf-8")
        return package_path, model, package

    def test_init_verifies_model_and_reference_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            provider = ChatterboxMultilingualV3Provider(
                package_path,
                workspace_root=tmp,
                model_dir=model,
                model_factory=lambda *_: object(),
            )
            self.assertEqual(provider.name, "chatterbox-multilingual-v3")
            self.assertEqual(len(provider.cache_identity()), 64)

    def test_model_integrity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            (model / "weights.bin").write_bytes(b"changed")
            with self.assertRaisesRegex(ContractError, "model asset SHA-256 mismatch"):
                ChatterboxMultilingualV3Provider(
                    package_path,
                    workspace_root=tmp,
                    model_dir=model,
                )

    def test_reference_integrity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            (Path(tmp) / "reference.wav").write_bytes(b"changed")
            with self.assertRaisesRegex(ContractError, "reference SHA-256 mismatch"):
                ChatterboxMultilingualV3Provider(
                    package_path,
                    workspace_root=tmp,
                    model_dir=model,
                )

    def test_seed_defaults_to_locked_base_plus_resolved_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            provider = ChatterboxMultilingualV3Provider(
                package_path,
                workspace_root=tmp,
                model_dir=model,
                model_factory=lambda *_: object(),
            )
            seed, language, reference, controls = provider._resolved_controls({
                "sequence": 8,
                "text": "Bonjour.",
                "voice": "slot",
            })
            self.assertEqual(seed, 650108)
            self.assertEqual(language, "fr")
            self.assertEqual(reference.name, "reference.wav")
            self.assertEqual(controls["temperature"], 0.74)

            explicit, _, _, _ = provider._resolved_controls({
                "sequence": 8,
                "provider_seed": 42,
                "text": "Bonjour.",
                "voice": "slot",
            })
            self.assertEqual(explicit, 42)

    def test_unknown_provider_control_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            provider = ChatterboxMultilingualV3Provider(
                package_path,
                workspace_root=tmp,
                model_dir=model,
            )
            with self.assertRaisesRegex(ContractError, "Unsupported Chatterbox synthesis parameters"):
                provider._resolved_controls({
                    "sequence": 1,
                    "text": "Bonjour.",
                    "voice": "slot",
                    "provider_parameters": {"mystery_knob": 1},
                })

    def test_model_factory_is_lazy(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            calls = []
            sentinel = object()
            provider = ChatterboxMultilingualV3Provider(
                package_path,
                workspace_root=tmp,
                model_dir=model,
                model_factory=lambda model_dir, device: calls.append((model_dir, device)) or sentinel,
            )
            self.assertEqual(calls, [])
            self.assertIs(provider._load_model(), sentinel)
            self.assertEqual(len(calls), 1)
            self.assertIs(provider._load_model(), sentinel)
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
