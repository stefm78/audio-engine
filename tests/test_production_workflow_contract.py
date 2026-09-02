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

    def test_scene_v4_cache_is_content_addressed_and_migrates_v2(self):
        self.assertIn("scene-v4-${{ matrix.id }}-${{ matrix.program_sha256 }}", self.workflow)
        self.assertIn("${{ matrix.provider_packages_fingerprint }}", self.workflow)
        self.assertIn("${{ needs.plan.outputs.engine_ref }}", self.workflow)
        self.assertIn("Restore optional scene-v2 migration source", self.workflow)
        self.assertIn(
            "${{ inputs.cache_namespace }}-${{ runner.os }}-${{ github.repository }}- scene-v2-${{ matrix.id }}-",
            self.workflow,
        )
        self.assertIn(
            "${{ inputs.cache_namespace }}-${{ runner.os }}-${{ github.repository }}- scene-v4-${{ matrix.id }}-",
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

    def test_fresh_scene_cache_units_skip_all_restore_paths(self):
        self.assertIn("fresh_scene_cache_units_json:", self.workflow)
        self.assertIn("default: '[]'", self.workflow)
        self.assertIn("FRESH_UNITS_JSON", self.workflow)
        self.assertIn("fresh_scene_cache_units_json must be valid JSON", self.workflow)
        self.assertIn("fresh_scene_cache_units_json must be a JSON array of non-empty strings", self.workflow)
        self.assertIn("fresh_scene_cache_units_json must not contain duplicates", self.workflow)
        self.assertIn("fresh scene-cache quarantine conflicts with forced legacy migration", self.workflow)
        self.assertIn("fresh_cache=", self.workflow)
        self.assertGreaterEqual(
            self.workflow.count("steps.cache-migration-policy.outputs.fresh_cache != 'true'"),
            5,
        )

    def test_forced_recovery_is_isolated_from_non_forced_units(self):
        self.assertIn("force_mode=", self.workflow)
        self.assertIn(
            "steps.cache-migration-policy.outputs.force_mode != 'true'",
            self.workflow,
        )
        self.assertIn(
            "Require non-forced cache source during forced recovery",
            self.workflow,
        )
        self.assertIn(
            "forced recovery mode forbids remote resynthesis for non-forced unit",
            self.workflow,
        )

    def test_scene_v3_generation_is_quarantined_from_restore_paths(self):
        self.assertNotIn("Restore optional content-addressed scene-v3 cache", self.workflow)
        self.assertNotIn("scene-cache-v3", self.workflow)
        self.assertNotIn("scene-v3-${{ matrix.id }}-", self.workflow)
        self.assertIn("Restore optional scene-v2 migration source", self.workflow)

    def test_scene_v4_cache_is_saved_only_for_ready_units(self):
        self.assertIn("uses: actions/cache/restore@v4", self.workflow)
        self.assertNotIn("- id: scene-cache-v4\n        name: Restore optional content-addressed scene-v4 cache\n        uses: actions/cache@v4", self.workflow)
        self.assertIn("uses: actions/cache/save@v4", self.workflow)
        self.assertIn("Authorize ready-only scene-v4 cache save", self.workflow)
        self.assertIn('result.get("state") == "ready"', self.workflow)
        self.assertIn("steps.scene-cache-save-gate.outputs.ready == 'true'", self.workflow)
        self.assertIn("steps.scene-cache-v4.outputs.cache-hit != 'true'", self.workflow)


    def test_local_provider_runtimes_are_isolated_and_final_render_is_cache_only(self):
        self.assertNotIn("Install exact promoted provider runtime", self.workflow)
        self.assertIn("Prewarm promoted provider voice caches in isolated runtimes", self.workflow)
        self.assertIn('python -m venv "$venv"', self.workflow)
        self.assertIn('source "$venv/bin/activate"', self.workflow)
        self.assertIn("install_chatterbox_mtl_v3_h1b.sh", self.workflow)
        self.assertIn("install_voxcpm2_p4_runtime.sh", self.workflow)
        self.assertIn("requirements/chatterbox-mtl-v3-h1b-runtime.txt", self.workflow)
        self.assertIn("requirements/voxcpm2-p4-runtime.txt", self.workflow)
        self.assertIn("--no-deps ./.audio-engine", self.workflow)
        self.assertIn("audio-engine provider-cache prewarm", self.workflow)
        self.assertIn("--cache-only-promoted-provider", self.workflow)
        self.assertIn("provider cache identity mismatch", self.workflow)
        self.assertIn("was not cache-only in final render", self.workflow)
        self.assertIn('cp -R "$work/provider-prewarm" "$publish/provider-prewarm"', self.workflow)

    def test_production_releases_never_clobber_existing_assets(self):
        self.assertNotIn("gh release upload", self.workflow)
        self.assertNotIn("--clobber", self.workflow)
        self.assertIn("immutable review assets will not be replaced", self.workflow)
        self.assertIn("immutable master assets will not be replaced", self.workflow)


if __name__ == "__main__":
    unittest.main()
