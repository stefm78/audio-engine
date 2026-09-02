import unittest
from pathlib import Path


class ProductionWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "production.yml"
        ).read_text(encoding="utf-8")

    def test_review_release_is_explicit_and_machine_ready_only(self):
        self.assertIn("publish_review_release:", self.workflow)
        self.assertIn("review_release_tag:", self.workflow)
        self.assertIn("No machine-ready browser-review audio exists", self.workflow)
        self.assertIn('"state")!="ready"', self.workflow)
        self.assertIn("This is not a final master release.", self.workflow)

    def test_scene_v3_cache_is_content_addressed_and_migrates_v2(self):
        self.assertIn("scene-v3-${{ matrix.id }}-${{ matrix.program_sha256 }}", self.workflow)
        self.assertIn("${{ matrix.provider_packages_fingerprint }}", self.workflow)
        self.assertIn("${{ needs.plan.outputs.engine_ref }}", self.workflow)
        self.assertIn("Restore optional scene-v2 migration source", self.workflow)
        self.assertIn(
            "${{ inputs.cache_namespace }}-${{ runner.os }}-${{ github.repository }}-scene-v2-${{ matrix.id }}-",
            self.workflow,
        )
        self.assertIn(
            "${{ inputs.cache_namespace }}-${{ runner.os }}-${{ github.repository }}-scene-v3-${{ matrix.id }}-",
            self.workflow,
        )

    def test_legacy_scene_cache_migration_can_be_forced_and_exactly_scoped(self):
        self.assertIn("legacy_scene_cache_engine_ref:", self.workflow)
        self.assertIn("legacy_scene_cache_voice_pack_sha256:", self.workflow)
        self.assertIn("legacy_scene_cache_force_units_json:", self.workflow)
        self.assertIn("default: '[]'", self.workflow)
        self.assertIn("force_legacy=", self.workflow)
        self.assertIn("forced legacy cache migration requires legacy_scene_cache_engine_ref", self.workflow)
        self.assertIn("forced legacy cache migration requires legacy_scene_cache_voice_pack_sha256", self.workflow)
        self.assertIn("legacy_scene_cache_voice_pack_sha256 must be an exact 64-hex SHA-256", self.workflow)
        self.assertIn("Restore exact pre-scene-v2 cache migration source", self.workflow)
        self.assertIn(
            "${{ matrix.program_sha256 }}-${{ inputs.legacy_scene_cache_voice_pack_sha256 }}",
            self.workflow,
        )
        self.assertIn(
            "opted-in legacy scene cache migration source was not found",
            self.workflow,
        )

    def test_scene_v3_cache_is_saved_only_for_ready_units(self):
        self.assertIn("uses: actions/cache/restore@v4", self.workflow)
        self.assertNotIn("- id: scene-cache-v3\n        name: Restore optional content-addressed scene-v3 cache\n        uses: actions/cache@v4", self.workflow)
        self.assertIn("uses: actions/cache/save@v4", self.workflow)
        self.assertIn("Authorize ready-only scene-v3 cache save", self.workflow)
        self.assertIn('result.get("state") == "ready"', self.workflow)
        self.assertIn("steps.scene-cache-save-gate.outputs.ready == 'true'", self.workflow)
        self.assertIn("steps.scene-cache-v3.outputs.cache-hit != 'true'", self.workflow)


    def test_local_provider_runtime_installers_are_explicit(self):
        self.assertIn("install_chatterbox_mtl_v3_h1b.sh", self.workflow)
        self.assertIn("install_voxcpm2_p4_runtime.sh", self.workflow)
        self.assertIn("requirements/chatterbox-mtl-v3-h1b-runtime.txt", self.workflow)
        self.assertIn("requirements/voxcpm2-p4-runtime.txt", self.workflow)
        self.assertIn("voxcpm2)", self.workflow)

    def test_production_releases_never_clobber_existing_assets(self):
        self.assertNotIn("gh release upload", self.workflow)
        self.assertNotIn("--clobber", self.workflow)
        self.assertIn("immutable review assets will not be replaced", self.workflow)
        self.assertIn("immutable master assets will not be replaced", self.workflow)


if __name__ == "__main__":
    unittest.main()
