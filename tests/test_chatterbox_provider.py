import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_missing_declared_system_runtime_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, package = self.make_fixture(tmp)
            package["runtime"]["system_dependencies"] = [{
                "name": "ffmpeg",
                "commands": ["ffmpeg", "ffprobe"],
                "reference_version": "7:6.1.1-3ubuntu5",
            }]
            package_path.write_text(json.dumps(package), encoding="utf-8")
            fake_probe = types.SimpleNamespace(
                returncode=0,
                stdout="ffmpeg version 6.1.1\n",
            )
            with patch(
                "audio_engine.providers.chatterbox_mtl_v3.shutil.which",
                side_effect=lambda command: None if command == "ffprobe" else "/usr/bin/ffmpeg",
            ), patch(
                "audio_engine.providers.chatterbox_mtl_v3.subprocess.run",
                return_value=fake_probe,
            ):
                with self.assertRaisesRegex(
                    ContractError,
                    "system runtime command is unavailable: 'ffprobe'",
                ):
                    ChatterboxMultilingualV3Provider(
                        package_path,
                        workspace_root=tmp,
                        model_dir=model,
                    )

    def test_system_runtime_version_participates_in_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, package = self.make_fixture(tmp)
            package["runtime"]["system_dependencies"] = [{
                "name": "ffmpeg",
                "commands": ["ffmpeg", "ffprobe"],
                "reference_version": "7:6.1.1-3ubuntu5",
            }]
            package_path.write_text(json.dumps(package), encoding="utf-8")

            def make_provider(version):
                fake = types.SimpleNamespace(returncode=0, stdout=version + "\n")
                with patch(
                    "audio_engine.providers.chatterbox_mtl_v3.shutil.which",
                    side_effect=lambda command: f"/usr/bin/{command}",
                ), patch(
                    "audio_engine.providers.chatterbox_mtl_v3.subprocess.run",
                    return_value=fake,
                ):
                    return ChatterboxMultilingualV3Provider(
                        package_path,
                        workspace_root=tmp,
                        model_dir=model,
                        model_factory=lambda *_: object(),
                    )

            first = make_provider("ffmpeg version 6.1.1")
            second = make_provider("ffmpeg version 6.1.2")
            self.assertNotEqual(first.cache_identity(), second.cache_identity())

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

    def test_synthesize_declares_known_wav_format_without_ffprobe_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            observed = {}

            class FakeModel:
                sr = 24000
                def generate(self, *args, **kwargs):
                    return object()

            fake_numpy = types.ModuleType("numpy")
            fake_numpy.random = types.SimpleNamespace(seed=lambda value: None)

            fake_torch = types.ModuleType("torch")
            fake_torch.manual_seed = lambda value: None

            fake_torchaudio = types.ModuleType("torchaudio")
            def fake_save(path, wav, sample_rate):
                Path(path).write_bytes(b"RIFFfake")
            fake_torchaudio.save = fake_save

            class FakeAudio:
                rms = 1
                dBFS = -20.0
                def set_frame_rate(self, value):
                    return self
                def set_channels(self, value):
                    return self
                def apply_gain(self, value):
                    return self
                def export(self, path, format=None):
                    Path(path).write_bytes(b"RIFFnormalized")

            class FakeAudioSegment:
                @staticmethod
                def from_file(path, format=None):
                    observed["format"] = format
                    return FakeAudio()

            fake_pydub = types.ModuleType("pydub")
            fake_pydub.AudioSegment = FakeAudioSegment

            previous = {
                name: sys.modules.get(name)
                for name in ("numpy", "torch", "torchaudio", "pydub")
            }
            sys.modules.update({
                "numpy": fake_numpy,
                "torch": fake_torch,
                "torchaudio": fake_torchaudio,
                "pydub": fake_pydub,
            })
            try:
                provider = ChatterboxMultilingualV3Provider(
                    package_path,
                    workspace_root=tmp,
                    model_dir=model,
                    model_factory=lambda *_: FakeModel(),
                )
                output = Path(tmp) / "out.mp3"
                with patch(
                    "audio_engine.providers.chatterbox_mtl_v3.run_ffmpeg",
                    side_effect=lambda args: output.write_bytes(b"mp3"),
                ):
                    provider.synthesize(
                        {
                            "sequence": 1,
                            "text": "Bonjour.",
                            "voice": "slot",
                        },
                        output,
                    )
            finally:
                for name, value in previous.items():
                    if value is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = value

            self.assertEqual(observed["format"], "wav")
            self.assertTrue(output.is_file())

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
