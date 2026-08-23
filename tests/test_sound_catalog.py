import json
import tempfile
import unittest
from pathlib import Path

from audio_engine.sound.catalog import load_catalog, public_catalog, sound_info


GOOD_SHA = "a" * 64


def entry(sound_id, sound_type, tags=None):
    return {
        "id": sound_id,
        "type": sound_type,
        "status": "validated",
        "tags": tags or [],
        "content_sha256": GOOD_SHA,
        "source": {"provider": "test", "page": "https://example.test/source"},
        "license": {"id": "CC0-1.0", "verified": True, "attribution": None},
        "asset": {"location": "locked-test-asset"},
    }


class SoundCatalogTests(unittest.TestCase):
    def _write(self, root, entries):
        path = Path(root) / "sounds.json"
        path.write_text(json.dumps({
            "version": 1,
            "policy": {"publication": "validated-only"},
            "entries": entries,
        }), encoding="utf-8")
        return path

    def test_catalog_filters_type_and_tags_and_resolves_id(self):
        with tempfile.TemporaryDirectory() as temp_value:
            path = self._write(temp_value, [
                entry("forest-light", "ambience", ["nature", "calm"]),
                entry("church-bell", "event", ["bell", "historic"]),
            ])
            result = public_catalog(path, tags=["historic"], sound_type="event")
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["entries"][0]["id"], "church-bell")
            found, source = sound_info("forest-light", path)
            self.assertEqual(found["type"], "ambience")
            self.assertEqual(source, path)

    def test_catalog_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temp_value:
            path = self._write(temp_value, [entry("same", "ambience"), entry("same", "event")])
            with self.assertRaises(ValueError):
                load_catalog(path)

    def test_catalog_rejects_unverified_or_candidate_entries(self):
        with tempfile.TemporaryDirectory() as temp_value:
            bad_license = entry("bad-license", "ambience")
            bad_license["license"]["verified"] = False
            with self.assertRaises(ValueError):
                load_catalog(self._write(temp_value, [bad_license]))

        with tempfile.TemporaryDirectory() as temp_value:
            candidate = entry("candidate", "ambience")
            candidate["status"] = "candidate"
            with self.assertRaises(ValueError):
                load_catalog(self._write(temp_value, [candidate]))

    def test_catalog_requires_content_hash(self):
        with tempfile.TemporaryDirectory() as temp_value:
            bad = entry("missing-hash", "event")
            bad["content_sha256"] = "not-a-sha"
            with self.assertRaises(ValueError):
                load_catalog(self._write(temp_value, [bad]))


if __name__ == "__main__":
    unittest.main()
