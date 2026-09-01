import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from audio_engine.contract import ContractError
from audio_engine.provider_package import (
    hydrate_provider_model,
    provider_package_report,
    validate_provider_package,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ProviderPackageTests(unittest.TestCase):
    def package(self):
        return {
            "schema_version": 1,
            "id": "local-tts-v1",
            "provider": {"id": "local-tts", "implementation_version": "1.0.0"},
            "runtime": {
                "kind": "python",
                "python": "3.11",
                "dependencies": [
                    {"name": "local-tts", "revision": "1" * 40},
                    {"name": "torch", "version": "2.8.0"},
                ],
            },
            "model": {
                "id": "example/model",
                "revision": "model-rev-1",
                "integrity": [{"name": "weights", "sha256": "a" * 64}],
            },
            "voice_pack_sha256": "b" * 64,
            "synthesis": {"seed": 1234, "parameters": {"temperature": 0.7}},
            "references": [],
            "fallback": "fail",
        }

    def test_fail_fallback_is_mandatory(self):
        package = self.package()
        package["fallback"] = "edge"
        with self.assertRaisesRegex(ContractError, "fallback must be exactly 'fail'"):
            validate_provider_package(package)

    def test_dependency_revision_must_be_exact_git_sha(self):
        package = self.package()
        package["runtime"]["dependencies"][0]["revision"] = "main"
        with self.assertRaisesRegex(ContractError, "exact 40-char Git SHA"):
            validate_provider_package(package)

    def test_hydrate_exact_huggingface_snapshot_and_verify_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = b"locked-model"
            digest = hashlib.sha256(expected).hexdigest()
            package = self.package()
            package["model"] = {
                "id": "Example/Model",
                "source": "huggingface",
                "revision": "4" * 40,
                "integrity": [{"name": "weights.bin", "sha256": digest}],
            }
            package_path = root / "provider.json"
            package_path.write_text(json.dumps(package), encoding="utf-8")

            calls = []
            def fake_snapshot_download(**kwargs):
                calls.append(kwargs)
                destination = Path(kwargs["local_dir"])
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "weights.bin").write_bytes(expected)
                return str(destination)

            fake_module = types.SimpleNamespace(snapshot_download=fake_snapshot_download)
            previous = sys.modules.get("huggingface_hub")
            sys.modules["huggingface_hub"] = fake_module
            try:
                report = hydrate_provider_model(package_path, cache_root=root / "cache")
            finally:
                if previous is None:
                    sys.modules.pop("huggingface_hub", None)
                else:
                    sys.modules["huggingface_hub"] = previous

            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["model_revision"], "4" * 40)
            self.assertEqual(report["verified"][0]["sha256"], digest)
            self.assertEqual(calls[0]["revision"], "4" * 40)
            self.assertEqual(calls[0]["allow_patterns"], ["weights.bin"])

    def test_verify_voice_pack_and_reference_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            voice = root / "voices.json"
            voice.write_text('{"version":1}', encoding="utf-8")
            ref = root / "reference.wav"
            ref.write_bytes(b"reference")
            package = self.package()
            package["voice_pack_sha256"] = sha(voice)
            package["references"] = [{"id": "reference", "path": "reference.wav", "sha256": sha(ref)}]
            path = root / "provider.json"
            path.write_text(json.dumps(package), encoding="utf-8")
            report = provider_package_report(
                path,
                workspace_root=root,
                verify_files=True,
                voice_pack_path="voices.json",
            )
            self.assertEqual(report["status"], "valid")
            self.assertTrue(report["files_verified"])


if __name__ == "__main__":
    unittest.main()
