import unittest
from unittest.mock import patch

from audio_engine.cli import main


class ProductionAssetsCliTests(unittest.TestCase):
    def test_hydrate_assets_dispatches_to_asset_hydrator(self):
        expected = {
            "schema_version": 1,
            "status": "ready",
            "unit_id": "S08",
            "assets": [],
        }
        with patch(
            "audio_engine.cli.hydrate_production_unit_assets",
            return_value=expected,
        ) as hydrate:
            rc = main([
                "production",
                "hydrate-assets",
                "manifest.json",
                "--unit",
                "S08",
                "--workspace-root",
                ".",
            ])
        self.assertEqual(rc, 0)
        hydrate.assert_called_once_with(
            "manifest.json",
            "S08",
            workspace_root=".",
        )


if __name__ == "__main__":
    unittest.main()
