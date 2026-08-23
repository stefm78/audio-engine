import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine.audio import run_ffmpeg
from audio_engine.sound import acquisition


class SoundAcquisitionTests(unittest.TestCase):
    def test_commons_license_mapping_accepts_only_auto_policy_licenses(self):
        self.assertEqual(acquisition._commons_license_id("CC0"), "CC0-1.0")
        self.assertEqual(acquisition._commons_license_id("CC BY 4.0"), "CC-BY-4.0")
        self.assertEqual(acquisition._commons_license_id("Public domain"), "Public-Domain")
        self.assertIsNone(acquisition._commons_license_id("CC BY-SA 4.0"))

    def test_wikimedia_discovery_extracts_audio_and_machine_observed_metadata(self):
        payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 123,
                        "title": "File:Cathedral bell.ogg",
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/example.ogg",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Cathedral_bell.ogg",
                            "mime": "audio/ogg",
                            "mediatype": "AUDIO",
                            "size": 1000,
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC0"},
                                "LicenseUrl": {"value": "https://creativecommons.org/publicdomain/zero/1.0/"},
                                "Artist": {"value": "Example author"},
                                "ImageDescription": {"value": "A distant cathedral bell"},
                            },
                        }],
                    }
                ]
            }
        }
        with patch.object(acquisition, "_http_json", return_value=payload):
            results = acquisition.discover_wikimedia("cathedral bell", limit=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["license_id"], "CC0-1.0")
        self.assertTrue(results[0]["source_metadata_verified"])
        self.assertIn("cathedral", results[0]["tags"])
        self.assertEqual(results[0]["provider"], "wikimedia-commons")

    def test_openverse_non_commons_result_is_discovery_only_and_not_promoted(self):
        payload = {
            "results": [{
                "id": "ov-1",
                "foreign_landing_url": "https://freesound.org/s/123/",
                "license": "cc0",
                "license_version": "1.0",
                "url": "https://example.test/a.ogg",
            }]
        }
        with patch.object(acquisition, "_http_json", return_value=payload):
            results = acquisition.discover_openverse("bell", limit=3)
        self.assertEqual(results, [])

    def test_catalog_hit_avoids_network(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            catalog = root / "sounds.json"
            catalog.write_text(json.dumps({
                "version": 1,
                "description": "test",
                "entries": [{
                    "id": "cathedral-calm",
                    "type": "ambience",
                    "status": "validated",
                    "tags": ["cathedral", "calm"],
                    "content_sha256": "a" * 64,
                    "license": {"id": "CC0-1.0", "verified": True},
                    "asset": {"file": "assets/cathedral.ogg"},
                }],
            }), encoding="utf-8")
            with patch.object(acquisition, "discover_candidates", side_effect=AssertionError("network should not run")):
                result = acquisition.ensure_sound(
                    "quiet cathedral",
                    sound_type="ambience",
                    sound_id="cathedral-calm",
                    catalog_path=catalog,
                )
            self.assertEqual(result["status"], "catalog-hit")
            self.assertFalse(result["network_requests_required"])

    def test_ensure_materializes_selected_commons_event_and_runtime_catalog(self):
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            source = root / "source.wav"
            run_ffmpeg([
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=1",
                "-ac", "2", "-c:a", "pcm_s16le", str(source),
            ])
            record = {
                "id": "commons-123",
                "provider": "wikimedia-commons",
                "discovery_provider": "wikimedia-commons",
                "rank": 1,
                "query": "cathedral bell",
                "title": "Cathedral bell",
                "description": "distant bell",
                "download_url": "https://upload.wikimedia.org/example.wav",
                "source_page": "https://commons.wikimedia.org/wiki/File:Cathedral_bell.wav",
                "source_identifier": "File:Cathedral bell.wav",
                "license_id": "CC0-1.0",
                "attribution": "Example",
                "tags": ["cathedral", "bell", "distant"],
                "source_metadata_verified": True,
                "mime": "audio/wav",
            }

            def fake_download(_record, directory, max_bytes=acquisition.MAX_DOWNLOAD_BYTES):
                destination = Path(directory) / "commons-123.wav"
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                return destination

            with patch.object(acquisition, "discover_candidates", return_value=([record], [{"provider": "wikimedia-commons", "status": "success", "count": 1}])), \
                 patch.object(acquisition, "_download", side_effect=fake_download):
                result = acquisition.ensure_sound(
                    "cathedral bell",
                    sound_type="event",
                    sound_id="church-bell-distant",
                    required_tags=["bell"],
                    output_dir=root / "out",
                    min_score=60,
                )

            self.assertEqual(result["status"], "selected")
            self.assertEqual(result["selected_id"], "church-bell-distant")
            asset = Path(result["materialized"]["asset"])
            catalog_path = Path(result["materialized"]["render_catalog"])
            self.assertTrue(asset.exists())
            self.assertTrue(catalog_path.exists())
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            entry = catalog["entries"][0]
            self.assertEqual(entry["id"], "church-bell-distant")
            self.assertTrue(entry["license"]["verified"])
            self.assertEqual(entry["asset"]["file"], f"assets/{asset.name}")
            self.assertEqual(entry["provenance"]["selection"], "automatic")

    def test_provider_failure_does_not_abort_other_sources(self):
        with patch.object(acquisition, "discover_wikimedia", side_effect=RuntimeError("down")), \
             patch.object(acquisition, "discover_openverse", return_value=[]):
            results, diagnostics = acquisition.discover_candidates("forest", providers=["wikimedia-commons", "openverse"])
        self.assertEqual(results, [])
        self.assertEqual(diagnostics[0]["status"], "error")
        self.assertEqual(diagnostics[1]["status"], "success")


if __name__ == "__main__":
    unittest.main()
