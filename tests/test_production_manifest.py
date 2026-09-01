import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.contract import ContractError
from audio_engine.production import production_plan, validate_production_manifest


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
