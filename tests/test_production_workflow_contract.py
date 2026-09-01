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

    def test_scene_cache_restore_is_cross_engine_but_still_content_addressed(self):
        self.assertIn("scene-v2-${{ matrix.id }}-${{ matrix.program_sha256 }}", self.workflow)
        self.assertIn("${{ matrix.provider_packages_fingerprint }}", self.workflow)
        self.assertIn("${{ needs.plan.outputs.engine_ref }}", self.workflow)
        self.assertIn("restore-keys: |", self.workflow)
        self.assertIn(
            "${{ inputs.cache_namespace }}-${{ runner.os }}-${{ github.repository }}-scene-v2-${{ matrix.id }}-",
            self.workflow,
        )

    def test_production_releases_never_clobber_existing_assets(self):
        self.assertNotIn("gh release upload", self.workflow)
        self.assertNotIn("--clobber", self.workflow)
        self.assertIn("immutable review assets will not be replaced", self.workflow)
        self.assertIn("immutable master assets will not be replaced", self.workflow)


if __name__ == "__main__":
    unittest.main()
