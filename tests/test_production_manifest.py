import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.contract import ContractError
from audio_engine.production import (
    hydrate_production_unit_assets,
    production_plan,
    validate_production_manifest,
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ProductionManifestTests(unittest.TestCase):
    def base_manifest(self):
        return {
            "schema_version": 1,
            "id": "sample-production",
            "engine_ref": "1" * 40,
            "units": [
                {
                    "id": "u1",
                    "state": "ready",
                    "provider": "edge",
                    "program": "u1.json",
                    "program_sha256": "a" * 64,
                    "voice_pack": "voices.json",
                    "voice_pack_sha256": "b" * 64,
                },
                {
                    "id": "u2",
                    "state": "hold",
                    "provider": "promoted-local",
                    "hold_reason": "voice package not promoted",
                },
            ],
            "assemblies": [{"id": "g1", "units": ["u1", "u2"]}],
            "master": {"assemblies": ["g1"]},
        }

    def test_hold_unit_does_not_require_missing_files(self):
        manifest = self.base_manifest()
        self.assertIs(validate_production_manifest(manifest), manifest)

    def test_provider_is_mandatory_no_implicit_fallback(self):
        manifest = self.base_manifest()
        del manifest["units"][0]["provider"]
        with self.assertRaisesRegex(ContractError, "provider is required"):
            validate_production_manifest(manifest)

    def test_ready_hashes_are_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "u1.json").write_text('{"id":"u1"}', encoding="utf-8")
            (root / "voices.json").write_text('{"version":1}', encoding="utf-8")
            manifest = self.base_manifest()
            manifest["units"][0]["program_sha256"] = sha256(root / "u1.json")
            manifest["units"][0]["voice_pack_sha256"] = sha256(root / "voices.json")
            path = root / "production.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            plan = production_plan(path, workspace_root=root)
            self.assertEqual([u["id"] for u in plan["ready_units"]], ["u1"])
            self.assertEqual([u["id"] for u in plan["held_units"]], ["u2"])
            self.assertEqual(plan["assemblies"][0]["state"], "hold")
            self.assertEqual(plan["master"]["state"], "hold")

    def test_ready_multi_provider_unit_binds_package_and_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "u1.json").write_text('{"id":"u1"}', encoding="utf-8")
            (root / "voices.json").write_text('{"version":1}', encoding="utf-8")
            package = {
                "schema_version": 1,
                "id": "local-provider-v1",
                "provider": {"id": "local-test", "implementation_version": "1.0.0"},
                "runtime": {
                    "kind": "python",
                    "python": "3.11.16",
                    "device": "cpu",
                    "dependencies": [{"name": "local-test", "version": "1.0.0"}],
                },
                "model": {
                    "id": "example/model",
                    "source": "local",
                    "revision": "model-v1",
                    "integrity": [{"name": "weights.bin", "sha256": "c" * 64}],
                },
                "voice_pack_sha256": sha256(root / "voices.json"),
                "synthesis": {"seed": 7, "parameters": {}},
                "references": [],
                "fallback": "fail",
            }
            package_path = root / "provider.json"
            package_path.write_text(json.dumps(package), encoding="utf-8")

            manifest = self.base_manifest()
            unit = manifest["units"][0]
            unit["providers"] = ["edge", "local-test"]
            unit.pop("provider")
            unit["program_sha256"] = sha256(root / "u1.json")
            unit["voice_pack_sha256"] = sha256(root / "voices.json")
            unit["provider_packages"] = [{
                "provider": "local-test",
                "package": "provider.json",
                "package_sha256": sha256(package_path),
            }]
            manifest_path = root / "production.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            plan = production_plan(manifest_path, workspace_root=root)
            ready = plan["ready_units"][0]
            self.assertEqual(ready["providers"], ["edge", "local-test"])
            self.assertEqual(ready["provider_package_count"], 1)
            self.assertEqual(ready["python_version"], "3.11.16")
            self.assertEqual(
                ready["provider_packages"][0]["provider"],
                "local-test",
            )

    def test_ready_non_edge_provider_without_package_is_rejected(self):
        manifest = self.base_manifest()
        unit = manifest["units"][0]
        unit["providers"] = ["edge", "local-test"]
        unit.pop("provider")
        with self.assertRaisesRegex(ContractError, "needs provider_packages"):
            validate_production_manifest(manifest)

    def test_locked_asset_can_be_absent_at_plan_then_hydrated_by_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "u1.json").write_text('{"id":"u1"}', encoding="utf-8")
            (root / "voices.json").write_text('{"version":1}', encoding="utf-8")
            payload = b"locked-ambience"
            digest = hashlib.sha256(payload).hexdigest()

            manifest = self.base_manifest()
            unit = manifest["units"][0]
            unit["program_sha256"] = sha256(root / "u1.json")
            unit["voice_pack_sha256"] = sha256(root / "voices.json")
            unit["assets"] = [{
                "id": "ambience",
                "path": "assets/ambience.wav",
                "sha256": digest,
                "source": {
                    "type": "github_release",
                    "repository": "owner/repo",
                    "tag": "assets-v1",
                    "asset": "ambience.wav",
                },
            }]
            manifest_path = root / "production.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            plan = production_plan(manifest_path, workspace_root=root)
            self.assertEqual(plan["ready_units"][0]["asset_count"], 1)
            self.assertFalse((root / "assets" / "ambience.wav").exists())

            class Response:
                def __enter__(self):
                    from io import BytesIO
                    self.stream = BytesIO(payload)
                    return self
                def __exit__(self, *args):
                    return False
                def read(self, size=-1):
                    return self.stream.read(size)

            with patch("audio_engine.production.urllib.request.urlopen", return_value=Response()):
                report = hydrate_production_unit_assets(
                    manifest_path,
                    "u1",
                    workspace_root=root,
                )
            self.assertEqual(report["status"], "ready")
            self.assertEqual((root / "assets" / "ambience.wav").read_bytes(), payload)
            self.assertFalse(report["assets"][0]["cache_hit"])

    def test_ready_hash_mismatch_fails_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "u1.json").write_text("x", encoding="utf-8")
            (root / "voices.json").write_text("y", encoding="utf-8")
            manifest = self.base_manifest()
            path = root / "production.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "mismatch"):
                production_plan(path, workspace_root=root)


if __name__ == "__main__":
    unittest.main()
