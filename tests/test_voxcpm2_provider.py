import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.contract import ContractError
from audio_engine.providers.voxcpm2 import VoxCPM2Provider


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class VoxCPM2ProviderTests(unittest.TestCase):
    def make_fixture(self, root):
        root = Path(root)
        model = root / "model"
        model.mkdir()
        files = {
            "config.json": b"{}",
            "model.safetensors": b"model",
            "audiovae.pth": b"vae",
            "tokenizer.json": b"{}",
        }
        integrity = []
        for name, payload in files.items():
            target = model / name
            target.write_bytes(payload)
            integrity.append({"name": name, "sha256": sha(target)})

        reference = root / "claire.wav"
        reference.write_bytes(b"reference")
        voice_pack = root / "voices.json"
        voice_pack.write_text('{"version":1}', encoding="utf-8")

        package = {
            "schema_version": 1,
            "id": "voxcpm2-test",
            "provider": {"id": "voxcpm2", "implementation_version": "1.0.0"},
            "runtime": {
                "kind": "python",
                "python": "3.11.16",
                "device": "cpu",
                "dependencies": [
                    {"name": "voxcpm", "revision": "e" * 40},
                    {"name": "torch", "version": "2.7.1+cpu"},
                ],
            },
            "model": {
                "id": "openbmb/VoxCPM2",
                "source": "huggingface",
                "revision": "3" * 40,
                "integrity": integrity,
            },
            "voice_pack_sha256": sha(voice_pack),
            "synthesis": {
                "seed": 2026090100,
                "parameters": {
                    "reference": "claire",
                    "control": "Quiet intelligent invitation.",
                    "cfg_value": 2.0,
                    "inference_timesteps": 10,
                    "normalize_model_output": False,
                    "denoise": False,
                    "retry_badcase": False,
                },
                "normalization": {"target_dbfs": -20.0},
            },
            "references": [{
                "id": "claire",
                "path": "claire.wav",
                "sha256": sha(reference),
            }],
            "fallback": "fail",
        }
        package_path = root / "provider.json"
        package_path.write_text(json.dumps(package), encoding="utf-8")
        return package_path, model, package

    def test_init_verifies_assets_and_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            provider = VoxCPM2Provider(
                package_path,
                workspace_root=tmp,
                model_dir=model,
                model_factory=lambda *_: object(),
            )
            self.assertEqual(provider.name, "voxcpm2")
            self.assertEqual(len(provider.cache_identity()), 64)

    def test_model_integrity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            (model / "model.safetensors").write_bytes(b"changed")
            with self.assertRaisesRegex(ContractError, "model asset SHA-256 mismatch"):
                VoxCPM2Provider(package_path, workspace_root=tmp, model_dir=model)

    def test_seed_defaults_to_base_plus_sequence_and_can_be_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            provider = VoxCPM2Provider(
                package_path,
                workspace_root=tmp,
                model_dir=model,
                model_factory=lambda *_: object(),
            )
            seed, reference, control, cfg, steps, controls = provider._resolved_controls({
                "sequence": 6,
                "text": "Ulysse.",
                "voice": "slot",
            })
            self.assertEqual(seed, 2026090106)
            self.assertEqual(reference.name, "claire.wav")
            self.assertEqual(control, "Quiet intelligent invitation.")
            self.assertEqual(cfg, 2.0)
            self.assertEqual(steps, 10)
            self.assertFalse(controls["denoise"])

            explicit, *_ = provider._resolved_controls({
                "sequence": 6,
                "provider_seed": 42,
                "text": "Ulysse.",
                "voice": "slot",
            })
            self.assertEqual(explicit, 42)

    def test_unknown_control_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model, _ = self.make_fixture(tmp)
            provider = VoxCPM2Provider(package_path, workspace_root=tmp, model_dir=model)
            with self.assertRaisesRegex(ContractError, "Unsupported VoxCPM2"):
                provider._resolved_controls({
                    "sequence": 1,
                    "text": "Ulysse.",
                    "voice": "slot",
                    "provider_parameters": {"mystery": 1},
                })

    def test_synthesize_preserves_exact_prompt_seed_and_model_switches(self):
        with tempfile.TemporaryDirectory() as tmp:
            package_path, model_dir, _ = self.make_fixture(tmp)
            observed = {}

            class FakeTTS:
                sample_rate = 24000

            class FakeModel:
                tts_model = FakeTTS()
                def generate(self, **kwargs):
                    observed.update(kwargs)
                    return object()

            fake_numpy = types.ModuleType("numpy")
            fake_numpy.random = types.SimpleNamespace(seed=lambda value: observed.setdefault("numpy_seed", value))

            fake_torch = types.ModuleType("torch")
            fake_torch.manual_seed = lambda value: observed.setdefault("torch_seed", value)

            fake_soundfile = types.ModuleType("soundfile")
            fake_soundfile.write = lambda path, wav, sr: Path(path).write_bytes(b"RIFFraw")

            class FakeAudio:
                rms = 1
                dBFS = -20.0
                def set_frame_rate(self, value): return self
                def set_channels(self, value): return self
                def apply_gain(self, value): observed["gain"] = value; return self
                def export(self, path, format=None): Path(path).write_bytes(b"RIFFnormalized")

            class FakeAudioSegment:
                @staticmethod
                def from_file(path, format=None):
                    observed["input_format"] = format
                    return FakeAudio()

            fake_pydub = types.ModuleType("pydub")
            fake_pydub.AudioSegment = FakeAudioSegment

            previous = {name: sys.modules.get(name) for name in ("numpy","torch","soundfile","pydub")}
            sys.modules.update({
                "numpy": fake_numpy,
                "torch": fake_torch,
                "soundfile": fake_soundfile,
                "pydub": fake_pydub,
            })
            try:
                provider = VoxCPM2Provider(
                    package_path,
                    workspace_root=tmp,
                    model_dir=model_dir,
                    model_factory=lambda *_: FakeModel(),
                )
                output = Path(tmp) / "out.mp3"
                with patch(
                    "audio_engine.providers.voxcpm2.run_ffmpeg",
                    side_effect=lambda args: output.write_bytes(b"mp3"),
                ):
                    provider.synthesize({
                        "sequence": 2,
                        "provider_seed": 2026090102,
                        "text": "Ulysse d’Ithaque.",
                        "voice": "slot",
                    }, output)
            finally:
                for name, value in previous.items():
                    if value is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = value

            self.assertEqual(
                observed["text"],
                "(Quiet intelligent invitation.)Ulysse d’Ithaque.",
            )
            self.assertEqual(observed["seed"], 2026090102)
            self.assertEqual(observed["cfg_value"], 2.0)
            self.assertEqual(observed["inference_timesteps"], 10)
            self.assertFalse(observed["normalize"])
            self.assertFalse(observed["denoise"])
            self.assertFalse(observed["retry_badcase"])
            self.assertEqual(observed["input_format"], "wav")
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
