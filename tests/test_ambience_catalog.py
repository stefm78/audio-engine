import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.ambience.catalog import ambience_info, load_catalog, public_catalog


class AmbienceCatalogTests(unittest.TestCase):
    def test_bundled_catalog_exposes_policy_even_when_empty(self):
        catalog = public_catalog()
        self.assertEqual(catalog["version"], 1)
        self.assertIn("policy", catalog)
        self.assertEqual(catalog["count"], len(catalog["entries"]))
        self.assertEqual(catalog["policy"]["production"], "locked-snapshot")

    def test_catalog_filters_tags_and_resolves_id(self):
        with tempfile.TemporaryDirectory() as temp_value:
            source = Path(temp_value) / "catalog.json"
            source.write_text(json.dumps({
                "version": 1,
                "policy": {"production": "locked-snapshot"},
                "entries": [
                    {"id": "forest-light", "tags": ["nature", "calm"]},
                    {"id": "city-busy", "tags": ["urban", "busy"]},
                ],
            }), encoding="utf-8")
            filtered = public_catalog(source, tags=["nature"])
            self.assertEqual(filtered["count"], 1)
            self.assertEqual(filtered["entries"][0]["id"], "forest-light")
            info = ambience_info("city-busy", source)
            self.assertEqual(info["entry"]["id"], "city-busy")

    def test_catalog_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temp_value:
            source = Path(temp_value) / "catalog.json"
            source.write_text(json.dumps({
                "version": 1,
                "entries": [{"id": "same"}, {"id": "same"}],
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_catalog(source)


if __name__ == "__main__":
    unittest.main()
